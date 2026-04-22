import json
import uuid
from datetime import datetime, timezone, timedelta
from auth import get_token
from graph import graph_get_all, GraphError
from db import get_connection

DOMAIN = "entra"

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

def entra_scan_app_regs() -> str:
    """Scan all app registrations for governance issues: expired/expiring credentials, missing owners, risky redirect URIs."""
    token = get_token()
    now = datetime.now(timezone.utc)
    warn_date = now + timedelta(days=90)

    apps = graph_get_all(
        "/applications?$select=id,appId,displayName,passwordCredentials,keyCredentials"
        ",requiredResourceAccess,web,publicClient&$top=999",
        token,
    )

    findings_count = 0
    with get_connection() as conn:
        for app in apps:
            aid, name = app["id"], app.get("displayName", app["id"])
            _upsert_snapshot(conn, "app_registration", aid, name, app)

            if not app.get("owners"):
                _upsert_finding(conn, "app_registration", aid, name, "missing_owner", "High",
                               "Assign an owner to this app registration.",
                               securesketch_control="IAM-APP-01")
                findings_count += 1

            for cred in app.get("passwordCredentials", []):
                end = cred.get("endDateTime")
                if not end:
                    continue
                exp = datetime.fromisoformat(end.replace("Z", "+00:00"))
                label = cred.get("displayName") or cred["keyId"]
                if exp < now:
                    _upsert_finding(conn, "app_registration", aid, name, "expired_secret", "Critical",
                                   f"Secret '{label}' expired {end}. Rotate or remove.",
                                   securesketch_control="IAM-APP-02")
                    findings_count += 1
                elif exp < warn_date:
                    _upsert_finding(conn, "app_registration", aid, name, "expiring_secret", "High",
                                   f"Secret '{label}' expires {end}. Rotate before expiry.",
                                   securesketch_control="IAM-APP-02")
                    findings_count += 1

            for cred in app.get("keyCredentials", []):
                end = cred.get("endDateTime")
                if not end:
                    continue
                exp = datetime.fromisoformat(end.replace("Z", "+00:00"))
                if exp < now:
                    label = cred.get("displayName") or cred["keyId"]
                    _upsert_finding(conn, "app_registration", aid, name, "expired_cert", "Critical",
                                   f"Certificate '{label}' expired {end}.",
                                   securesketch_control="IAM-APP-02")
                    findings_count += 1

            web_uris = (app.get("web") or {}).get("redirectUris", [])
            pub_uris = (app.get("publicClient") or {}).get("redirectUris", [])
            for uri in web_uris + pub_uris:
                if "*" in uri:
                    _upsert_finding(conn, "app_registration", aid, name, "wildcard_redirect_uri", "Critical",
                                   f"Wildcard redirect URI: {uri}. Specify exact URIs.",
                                   securesketch_control="IAM-APP-03")
                    findings_count += 1
                elif uri.startswith("http://") and "localhost" not in uri:
                    _upsert_finding(conn, "app_registration", aid, name, "http_redirect_uri", "High",
                                   f"Non-localhost HTTP redirect URI: {uri}. Use HTTPS.",
                                   securesketch_control="IAM-APP-03")
                    findings_count += 1

    return json.dumps({"scanned": len(apps), "findings": findings_count})

def entra_scan_guests() -> str:
    """Scan guest accounts: recently added, inactive (90+ days), never signed in."""
    token = get_token()
    now = datetime.now(timezone.utc)
    stale = now - timedelta(days=90)
    recent = now - timedelta(days=30)

    guests = graph_get_all(
        "/users?$filter=userType eq 'Guest'"
        "&$select=id,displayName,mail,userPrincipalName,createdDateTime,signInActivity"
        "&$top=999",
        token,
    )

    findings_count = 0
    with get_connection() as conn:
        for guest in guests:
            gid = guest["id"]
            name = guest.get("displayName") or guest.get("mail") or gid
            _upsert_snapshot(conn, "guest_user", gid, name, guest)

            created_str = guest.get("createdDateTime")
            created_dt = datetime.fromisoformat(created_str.replace("Z", "+00:00")) if created_str else None

            if created_dt and created_dt > recent:
                _upsert_finding(conn, "guest_user", gid, name, "recently_added_guest", "Low",
                               f"Guest added {created_str}. Verify invitation was authorized.",
                               securesketch_control="IAM-GUEST-01")
                findings_count += 1

            sign_in = (guest.get("signInActivity") or {}).get("lastSignInDateTime")
            if sign_in:
                last = datetime.fromisoformat(sign_in.replace("Z", "+00:00"))
                if last < stale:
                    _upsert_finding(conn, "guest_user", gid, name, "inactive_guest", "Medium",
                                   f"Guest last signed in {sign_in}. Review and remove if no longer needed.",
                                   securesketch_control="IAM-GUEST-02")
                    findings_count += 1
            elif created_dt and created_dt < stale:
                _upsert_finding(conn, "guest_user", gid, name, "never_signed_in_guest", "Medium",
                               "Guest has never signed in and account is over 90 days old.",
                               securesketch_control="IAM-GUEST-02")
                findings_count += 1

    return json.dumps({"scanned": len(guests), "findings": findings_count})
