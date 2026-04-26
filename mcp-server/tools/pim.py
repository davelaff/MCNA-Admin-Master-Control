import json
import uuid
from datetime import datetime, timezone, timedelta
import requests
from auth import get_token
from graph import graph_get_all
from db import get_connection
from tools.ssk_control_map import canonical_control_id

DOMAIN = "pim"

CONTRIBUTES_TO = {
    "__tool__": [
        canonical_control_id("PIM-PERM-01"),
        canonical_control_id("PIM-NON-ADMIN-01"),
        canonical_control_id("PIM-STALE-01"),
        canonical_control_id("PIM-CUSTOM-01"),
        canonical_control_id("PIM-LIC-01"),
    ],
    "permanent_privileged_assignment":      [canonical_control_id("PIM-PERM-01")],
    "privileged_role_on_non_admin_account": [canonical_control_id("PIM-NON-ADMIN-01")],
    "long_standing_eligible_assignment":    [canonical_control_id("PIM-STALE-01")],
    "unused_custom_role":                   [canonical_control_id("PIM-CUSTOM-01")],
    "pim_not_licensed":                     [canonical_control_id("PIM-LIC-01")],
}

# Roles that grant tenant-impacting authority. Permanent assignments to any of
# these bypass PIM and should be reviewed against MCNA's privileged-access process.
PRIVILEGED_ROLES: set[str] = {
    "Global Administrator",
    "Privileged Role Administrator",
    "Privileged Authentication Administrator",
    "Security Administrator",
    "Exchange Administrator",
    "SharePoint Administrator",
    "User Administrator",
    "Conditional Access Administrator",
    "Application Administrator",
    "Cloud Application Administrator",
    "Teams Administrator",
    "Intune Administrator",
    "Authentication Administrator",
    "Fabric Administrator",
    "Power Platform Administrator",
    "AI Administrator",
}

# UPN prefix Dave uses for dedicated admin accounts. Any privileged role assigned
# to a UPN that does not start with this prefix is flagged for review.
ADMIN_UPN_PREFIX = "nof-"


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
            owner=excluded.owner,
            recommended_action=excluded.recommended_action
    """, (finding_id, DOMAIN, object_type, object_id, object_name, owner,
          finding_type, severity, securesketch_control, recommended_action, now, now))
    return finding_id


def _append_activity(conn, tool_name: str, outcome: str, detail: dict) -> None:
    conn.execute(
        """
        INSERT INTO activity_log (run_id, timestamp, tool_name, domain, outcome, detail)
        VALUES (?,?,?,?,?,?)
        """,
        (str(uuid.uuid4()), _now(), tool_name, DOMAIN, outcome, json.dumps(detail, sort_keys=True)),
    )


def _is_user_principal(principal: dict) -> bool:
    odata = (principal or {}).get("@odata.type", "")
    return "user" in odata.lower() and "servicePrincipal" not in odata


def _try_pim_schedules(path: str, token: str) -> tuple[list, bool]:
    """Call a PIM schedule endpoint. Returns (results, pim_available).
    A 400 response indicates the tenant lacks Azure AD Premium P2."""
    try:
        return graph_get_all(path, token), True
    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == 400:
            return [], False
        raise


def pim_scan_role_assignments() -> str:
    """Scan directory role assignments. Uses PIM schedule endpoints when P2 is
    licensed; otherwise falls back to /roleAssignments (every assignment is
    permanent by construction) and records the licensing gap as a finding."""
    token = get_token()

    role_defs = graph_get_all("/roleManagement/directory/roleDefinitions", token)
    role_name = {r["id"]: r.get("displayName", r["id"]) for r in role_defs}

    active, pim_available = _try_pim_schedules(
        "/roleManagement/directory/roleAssignmentSchedules?$expand=principal", token,
    )
    eligible: list = []
    if pim_available:
        eligible, _ = _try_pim_schedules(
            "/roleManagement/directory/roleEligibilitySchedules?$expand=principal", token,
        )
    else:
        active = graph_get_all(
            "/roleManagement/directory/roleAssignments?$expand=principal", token,
        )

    now = datetime.now(timezone.utc)
    stale_cutoff = now - timedelta(days=90)

    findings_count = 0
    privileged_active_count = 0

    with get_connection() as conn:
        if not pim_available:
            _upsert_finding(
                conn, "tenant", "pim_licensing", "Tenant PIM licensing",
                "pim_not_licensed", "High",
                "PIM schedule endpoints returned 400 — tenant lacks Azure AD Premium P2. "
                "All role assignments are permanent. Compensating controls required for 08-6.",
                securesketch_control="PIM-LIC-01",
            )
            findings_count += 1

        for sched in active:
            sid = sched["id"]
            principal = sched.get("principal") or {}
            pid = sched.get("principalId") or principal.get("id", "")
            rid = sched["roleDefinitionId"]
            rname = role_name.get(rid, rid)
            display = principal.get("displayName") or pid
            upn = principal.get("userPrincipalName")
            owner = upn or display
            # roleAssignmentSchedules carries assignmentType; basic roleAssignments does not.
            # When falling back to /roleAssignments every row is permanent by construction.
            assignment_type = sched.get("assignmentType", "Assigned")
            entity_name = f"{display} → {rname}"
            entity_type = "role_assignment_active" if pim_available else "role_assignment"

            _upsert_snapshot(conn, entity_type, sid, entity_name, sched)

            is_priv = rname in PRIVILEGED_ROLES
            if is_priv:
                privileged_active_count += 1

            if is_priv and assignment_type == "Assigned":
                _upsert_finding(
                    conn, entity_type, sid, entity_name,
                    "permanent_privileged_assignment", "High",
                    f"Permanent assignment of '{rname}' to {display}. "
                    + ("Convert to PIM-eligible." if pim_available
                       else "No PIM available — verify compensating controls."),
                    owner=owner, securesketch_control="PIM-PERM-01",
                )
                findings_count += 1

            if is_priv and _is_user_principal(principal) and upn:
                if not upn.lower().startswith(ADMIN_UPN_PREFIX):
                    _upsert_finding(
                        conn, entity_type, sid, entity_name,
                        "privileged_role_on_non_admin_account", "High",
                        f"'{rname}' held by {upn}. Move privileged role to a dedicated admin account.",
                        owner=owner, securesketch_control="PIM-NON-ADMIN-01",
                    )
                    findings_count += 1

        for sched in eligible:
            sid = sched["id"]
            principal = sched.get("principal") or {}
            pid = sched.get("principalId") or principal.get("id", "")
            rid = sched["roleDefinitionId"]
            rname = role_name.get(rid, rid)
            display = principal.get("displayName") or pid
            upn = principal.get("userPrincipalName")
            entity_name = f"{display} → {rname} (eligible)"

            _upsert_snapshot(conn, "role_assignment_eligible", sid, entity_name, sched)

            created_str = sched.get("createdDateTime")
            if not created_str:
                continue
            created = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
            if created < stale_cutoff:
                _upsert_finding(
                    conn, "role_assignment_eligible", sid, entity_name,
                    "long_standing_eligible_assignment", "Low",
                    f"Eligible assignment of '{rname}' to {display} created {created_str}. "
                    "Confirm still required.",
                    owner=upn or display, securesketch_control="PIM-STALE-01",
                )
                findings_count += 1

        result = {
            "pim_available": pim_available,
            "active_assignments": len(active),
            "eligible_assignments": len(eligible),
            "privileged_active": privileged_active_count,
            "findings": findings_count,
        }
        _append_activity(conn, "pim_scan_role_assignments", "success", result)

    return json.dumps(result)


def pim_scan_role_definitions() -> str:
    """Scan role definitions: flag custom roles with no current assignments."""
    token = get_token()

    defs = graph_get_all("/roleManagement/directory/roleDefinitions", token)

    active, pim_available = _try_pim_schedules(
        "/roleManagement/directory/roleAssignmentSchedules?$expand=principal", token,
    )
    eligible: list = []
    if pim_available:
        eligible, _ = _try_pim_schedules(
            "/roleManagement/directory/roleEligibilitySchedules?$expand=principal", token,
        )
    else:
        active = graph_get_all(
            "/roleManagement/directory/roleAssignments?$expand=principal", token,
        )

    assigned_ids: set[str] = set()
    for sched in active:
        assigned_ids.add(sched["roleDefinitionId"])
    for sched in eligible:
        assigned_ids.add(sched["roleDefinitionId"])

    findings_count = 0
    custom_count = 0

    with get_connection() as conn:
        for rdef in defs:
            rid = rdef["id"]
            name = rdef.get("displayName", rid)
            built_in = rdef.get("isBuiltIn", True)

            _upsert_snapshot(conn, "role_definition", rid, name, rdef)

            if built_in:
                continue
            custom_count += 1

            if rid not in assigned_ids:
                _upsert_finding(
                    conn, "role_definition", rid, name,
                    "unused_custom_role", "Low",
                    f"Custom role '{name}' has no active or eligible assignments. "
                    "Confirm still needed or remove.",
                    securesketch_control="PIM-CUSTOM-01",
                )
                findings_count += 1

        result = {
            "scanned": len(defs),
            "custom_roles": custom_count,
            "findings": findings_count,
            "pim_available": pim_available,
        }
        _append_activity(conn, "pim_scan_role_definitions", "success", result)

    return json.dumps(result)
