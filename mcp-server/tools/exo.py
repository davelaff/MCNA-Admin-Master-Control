import json
import uuid
import requests
from datetime import datetime, timezone
from auth import get_token, get_app_token
from graph import graph_get, graph_get_all, GraphError
from db import get_connection
from tools.ssk_control_map import canonical_control_id

DOMAIN = "exo"
INTERNAL_DOMAINS = frozenset({"nofmetalcoatings.us", "nofmetalcoatings.onmicrosoft.com"})

CONTRIBUTES_TO = {
    "__tool__": [
        canonical_control_id("EXO-SCOPE-01"),
        canonical_control_id("EXO-SHARED-ENABLED-01"),
        canonical_control_id("EXO-FORWARD-01"),
    ],
    "exo_scope_gap":              [canonical_control_id("EXO-SCOPE-01")],
    "shared_mailbox_interactive": [canonical_control_id("EXO-SHARED-ENABLED-01")],
    "external_forwarding_rule":   [canonical_control_id("EXO-FORWARD-01")],
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _upsert_snapshot(conn, entity_type: str, entity_id: str, entity_name: str, props: dict) -> None:
    conn.execute("""
        INSERT INTO tenant_snapshot (entity_type, entity_id, entity_name, domain, properties, last_scanned)
        VALUES (?,?,?,?,?,?)
        ON CONFLICT(entity_type, entity_id) DO UPDATE SET
            entity_name=excluded.entity_name,
            properties=excluded.properties,
            last_scanned=excluded.last_scanned
    """, (entity_type, entity_id, entity_name, DOMAIN, json.dumps(props), _now()))


def _upsert_finding(conn, object_type: str, object_id: str, object_name: str,
                    finding_type: str, severity: str, recommended_action: str,
                    owner: str = None, securesketch_control: str = None) -> str:
    finding_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{DOMAIN}.{object_type}.{object_id}.{finding_type}"))
    existing = conn.execute("SELECT status FROM findings WHERE finding_id=?", (finding_id,)).fetchone()
    if existing and existing["status"] == "dismissed":
        return finding_id
    now = _now()
    conn.execute("""
        INSERT INTO findings
            (finding_id,domain,object_type,object_id,object_name,owner,finding_type,
             severity,securesketch_control,recommended_action,status,first_seen,last_seen)
        VALUES (?,?,?,?,?,?,?,?,?,?,'open',?,?)
        ON CONFLICT(finding_id) DO UPDATE SET
            last_seen=excluded.last_seen,
            object_name=excluded.object_name,
            owner=excluded.owner
    """, (finding_id, DOMAIN, object_type, object_id, object_name, owner,
          finding_type, severity, securesketch_control, recommended_action, now, now))
    return finding_id


def _email_domain(address: str) -> str:
    return address.split("@")[-1].lower() if "@" in address else ""


def _is_external(address: str) -> bool:
    # X.500/legacy Exchange DNs (no @) are internal routing artifacts, not external addresses
    if "@" not in address:
        return False
    return _email_domain(address) not in INTERNAL_DOMAINS


def _get_mailbox_settings(uid: str, token: str) -> tuple[dict | None, bool]:
    """Fetch mailboxSettings for a single user. Returns (settings, accessible).
    (None, True) = 404, no Exchange mailbox for this user — skip silently.
    (None, False) = 403, MailboxSettings.Read not consented — emit scope gap.
    (settings_dict, True) = success."""
    try:
        return graph_get(f"/users/{uid}/mailboxSettings", token), True
    except GraphError as e:
        if e.status == 403:
            return None, False
        raise
    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == 404:
            return None, True
        raise


def _get_inbox_rules(uid: str, token: str) -> tuple[list, bool]:
    """Fetch inbox message rules for a user. Returns (rules, accessible).
    accessible=False means 403 — scope gap or delegated access blocked."""
    try:
        return graph_get_all(f"/users/{uid}/mailFolders/inbox/messageRules", token), True
    except GraphError as e:
        if e.status == 403:
            return [], False
        raise
    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == 404:
            return [], True  # no mailbox — not a scope gap
        raise


def _forwarding_targets(rule_actions: dict) -> list[str]:
    """Extract all recipient email addresses from forward/redirect actions."""
    addresses = []
    for key in ("forwardTo", "forwardAsAttachmentTo", "redirectTo"):
        for recipient in rule_actions.get(key) or []:
            addr = recipient.get("emailAddress", {}).get("address", "")
            if addr:
                addresses.append(addr)
    return addresses


def exo_scan_mailboxes() -> str:
    """Enumerate Exchange Online mailboxes by inspecting mailboxSettings.userPurpose
    for each enabled user. Detects shared mailboxes where the underlying Entra
    user account is enabled for interactive sign-in — a lateral movement risk.
    Uses Directory.Read.All (delegated) to enumerate users and MailboxSettings.Read
    (application) to read per-user mailbox settings."""
    token = get_token()
    app_token = get_app_token()
    users = graph_get_all(
        "/users",
        token,
        params={"$select": "id,displayName,userPrincipalName,mail,accountEnabled,assignedLicenses",
                "$top": "999"},
    )

    user_mailboxes = 0
    shared_mailboxes = 0
    resource_mailboxes = 0
    shared_interactive = 0
    findings_count = 0
    scope_gap_emitted = False

    with get_connection() as conn:
        for user in users:
            uid = user.get("id", "")
            upn = user.get("userPrincipalName", "")
            name = user.get("displayName") or upn
            enabled = user.get("accountEnabled", False)

            settings, accessible = _get_mailbox_settings(uid, app_token)

            if settings is None:
                if not accessible and not scope_gap_emitted:
                    _upsert_finding(
                        conn,
                        object_type="tenant",
                        object_id="exo",
                        object_name="Exchange Online",
                        finding_type="exo_scope_gap",
                        severity="Medium",
                        recommended_action=(
                            "Grant MailboxSettings.Read delegated consent to the "
                            "MCNA-TenantIntel-ReadOnly app registration to enable "
                            "Exchange mailbox governance scans."
                        ),
                        securesketch_control="EXO-SCOPE-01",
                    )
                    scope_gap_emitted = True
                    findings_count += 1
                continue

            purpose = settings.get("userPurpose", "user")

            _upsert_snapshot(conn, "mailbox", uid, name, {
                "userPrincipalName": upn,
                "userPurpose": purpose,
                "accountEnabled": enabled,
            })

            if purpose == "shared":
                shared_mailboxes += 1
                if enabled:
                    shared_interactive += 1
                    findings_count += 1
                    _upsert_finding(
                        conn,
                        object_type="mailbox",
                        object_id=uid,
                        object_name=name,
                        finding_type="shared_mailbox_interactive",
                        severity="High",
                        recommended_action=(
                            f"Shared mailbox '{name}' ({upn}) has an enabled Entra user account. "
                            "Shared mailboxes should have their underlying account disabled to "
                            "prevent interactive sign-in. Disable the account in Entra ID: "
                            "Users > select user > Edit properties > Account status = Disabled."
                        ),
                        securesketch_control="EXO-SHARED-ENABLED-01",
                    )
            elif purpose in ("room", "equipment"):
                resource_mailboxes += 1
            else:
                user_mailboxes += 1

    return json.dumps({
        "domain": DOMAIN,
        "users_scanned": len(users),
        "user_mailboxes": user_mailboxes,
        "shared_mailboxes": shared_mailboxes,
        "resource_mailboxes": resource_mailboxes,
        "shared_interactive": shared_interactive,
        "findings": findings_count,
    })


def exo_scan_forwarding() -> str:
    """Scan all user inbox message rules for external mail forwarding and
    redirect actions. External forwarding from a corporate mailbox is a
    data-exfiltration vector and a common indicator of account compromise.
    Uses Directory.Read.All (delegated) to enumerate users and MailboxSettings.Read
    (application) to read per-user inbox rules."""
    token = get_token()
    app_token = get_app_token()
    users = graph_get_all(
        "/users",
        token,
        params={"$select": "id,displayName,userPrincipalName,mail,accountEnabled",
                "$top": "999"},
    )

    users_scanned = 0
    rules_scanned = 0
    external_rules = 0
    findings_count = 0
    scope_gap_emitted = False

    with get_connection() as conn:
        for user in users:
            uid = user.get("id", "")
            upn = user.get("userPrincipalName", "")
            name = user.get("displayName") or upn

            rules, accessible = _get_inbox_rules(uid, app_token)

            if not accessible:
                if not scope_gap_emitted:
                    _upsert_finding(
                        conn,
                        object_type="tenant",
                        object_id="exo",
                        object_name="Exchange Online",
                        finding_type="exo_scope_gap",
                        severity="Medium",
                        recommended_action=(
                            "MailboxSettings.Read delegated access blocked when reading inbox "
                            "rules for users other than the signed-in account. Verify admin "
                            "consent is granted for MailboxSettings.Read on "
                            "MCNA-TenantIntel-ReadOnly."
                        ),
                        securesketch_control="EXO-SCOPE-01",
                    )
                    scope_gap_emitted = True
                    findings_count += 1
                continue

            users_scanned += 1
            rules_scanned += len(rules)

            for rule in rules:
                if not rule.get("isEnabled", True):
                    continue
                targets = _forwarding_targets(rule.get("actions", {}))
                external_targets = [t for t in targets if _is_external(t)]
                if external_targets:
                    external_rules += 1
                    findings_count += 1
                    dest_list = ", ".join(external_targets)
                    _upsert_finding(
                        conn,
                        object_type="mailbox_rule",
                        object_id=f"{uid}:{rule.get('id', '')}",
                        object_name=f"{name} — {rule.get('displayName', 'unnamed rule')}",
                        finding_type="external_forwarding_rule",
                        severity="High",
                        recommended_action=(
                            f"Inbox rule '{rule.get('displayName', 'unnamed')}' on mailbox "
                            f"'{upn}' forwards or redirects mail to external address(es): "
                            f"{dest_list}. Remove the rule unless explicitly business-justified "
                            "and documented. Review the account for signs of compromise."
                        ),
                        owner=upn,
                        securesketch_control="EXO-FORWARD-01",
                    )

    return json.dumps({
        "domain": DOMAIN,
        "users_scanned": users_scanned,
        "rules_scanned": rules_scanned,
        "external_forwarding_rules": external_rules,
        "findings": findings_count,
    })
