import json
import uuid
import requests
from datetime import datetime, timezone
from auth import get_token
from graph import graph_get_all, GraphError
from db import get_connection
from tools.ssk_control_map import canonical_control_id

DOMAIN = "pp"
BAP_BASE = "https://api.bap.microsoft.com"

CONTRIBUTES_TO = {
    "__tool__": [
        canonical_control_id("PP-ENV-01"),
        canonical_control_id("PP-APP-01"),
    ],
    "production_in_default": [canonical_control_id("PP-ENV-01")],
    "inactive_owner":        [canonical_control_id("PP-APP-01")],
}

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

def _bap_get_all(path: str, token: str) -> list:
    url = f"{BAP_BASE}{path}"
    results = []
    while url:
        resp = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=30)
        if resp.status_code in (401, 403):
            raise RuntimeError(f"BAP auth error {resp.status_code} at {url}")
        resp.raise_for_status()
        data = resp.json()
        results.extend(data.get("value", []))
        url = data.get("nextLink")
    return results

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
        ON CONFLICT(finding_id) DO UPDATE SET last_seen=excluded.last_seen, object_name=excluded.object_name, recommended_action=excluded.recommended_action
    """, (finding_id, DOMAIN, object_type, object_id, object_name, owner,
          finding_type, severity, securesketch_control, recommended_action, now, now))
    return finding_id

def pp_scan_environments() -> str:
    """Scan Power Platform environments for governance issues."""
    token = get_token("https://api.bap.microsoft.com")
    envs = _bap_get_all("/providers/Microsoft.BusinessAppPlatform/environments?api-version=2016-11-01", token)

    findings_count = 0
    with get_connection() as conn:
        for env in envs:
            eid = env.get("name", env.get("id"))
            props = env.get("properties", {})
            name = props.get("displayName", eid)
            sku = props.get("environmentSku", "unknown")
            is_default = props.get("isDefault", False)
            _upsert_snapshot(conn, "pp_environment", eid, name, env)

            if is_default and sku not in ("Default", "unknown"):
                _upsert_finding(conn, "pp_environment", eid, name, "production_in_default", "High",
                               f"Environment type '{sku}' should not be in the default environment.",
                               securesketch_control="PP-ENV-01")
                findings_count += 1

    return json.dumps({
        "scanned": len(envs),
        "findings": findings_count,
        "environments": [
            {"id": e.get("name"), "name": e.get("properties", {}).get("displayName"),
             "type": e.get("properties", {}).get("environmentSku")}
            for e in envs
        ],
    })

def pp_scan_apps() -> str:
    """Scan Power Apps for apps owned by disabled/departed users."""
    graph_token = get_token()
    disabled = graph_get_all(
        "/users?$filter=accountEnabled eq false&$select=id,userPrincipalName&$top=999", graph_token
    )
    disabled_ids = {u["id"] for u in disabled}

    pp_token = get_token("https://api.bap.microsoft.com")
    envs = _bap_get_all("/providers/Microsoft.BusinessAppPlatform/environments?api-version=2016-11-01", pp_token)

    total_apps = 0
    findings_count = 0

    with get_connection() as conn:
        for env in envs:
            env_id = env.get("name")
            try:
                apps = _bap_get_all(
                    f"/providers/Microsoft.BusinessAppPlatform/environments/{env_id}"
                    f"/apps?api-version=2016-11-01",
                    pp_token,
                )
            except Exception:
                continue

            total_apps += len(apps)
            for app in apps:
                aid = app.get("name")
                aprops = app.get("properties", {})
                aname = aprops.get("displayName", aid)
                owner = aprops.get("owner", {})
                owner_id = owner.get("id")
                _upsert_snapshot(conn, "pp_app", aid, aname, app)

                if owner_id and owner_id in disabled_ids:
                    _upsert_finding(conn, "pp_app", aid, aname, "inactive_owner", "High",
                                   f"App owned by disabled user {owner.get('userPrincipalName', owner_id)}. Reassign.",
                                   owner=owner.get("userPrincipalName"),
                                   securesketch_control="PP-APP-01")
                    findings_count += 1

    return json.dumps({
        "environments_scanned": len(envs),
        "apps_scanned": total_apps,
        "findings": findings_count,
    })
