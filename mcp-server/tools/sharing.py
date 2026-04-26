import json
import uuid
from datetime import datetime, timezone, timedelta
from auth import get_token
from graph import graph_get_all
from db import get_connection
from tools.ssk_control_map import canonical_control_id

DOMAIN = "sharing"

CONTRIBUTES_TO = {
    "__tool__": [
        canonical_control_id("SHARING-STALE-01"),
        canonical_control_id("SHARING-VERY-STALE-01"),
    ],
    "stale_site":      [canonical_control_id("SHARING-STALE-01")],
    "very_stale_site": [canonical_control_id("SHARING-VERY-STALE-01")],
}

STALE_DAYS = 365
VERY_STALE_DAYS = 730


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


def sharing_scan_sites() -> str:
    """Enumerate SharePoint sites and flag stale surfaces. Permission-based
    findings (external sharing, guest access) require Sites.FullControl.All
    which is not currently consented — planned for a later expansion."""
    token = get_token()
    sites = graph_get_all("/sites?search=*", token)

    now = datetime.now(timezone.utc)
    stale_cutoff = now - timedelta(days=STALE_DAYS)
    very_stale_cutoff = now - timedelta(days=VERY_STALE_DAYS)

    stale = 0
    very_stale = 0
    findings_count = 0

    with get_connection() as conn:
        for site in sites:
            sid = site["id"]
            name = site.get("displayName") or site.get("name") or sid
            url = site.get("webUrl", "")

            _upsert_snapshot(conn, "sharepoint_site", sid, name, site)

            last_str = site.get("lastModifiedDateTime")
            if not last_str:
                continue
            last = datetime.fromisoformat(last_str.replace("Z", "+00:00"))

            if last < very_stale_cutoff:
                very_stale += 1
                _upsert_finding(
                    conn, "sharepoint_site", sid, name,
                    "very_stale_site", "High",
                    f"Site '{name}' last modified {last_str[:10]} ({(now - last).days} days). "
                    f"Review for archive or deletion. {url}",
                    securesketch_control="SHARING-VERY-STALE-01",
                )
                findings_count += 1
            elif last < stale_cutoff:
                stale += 1
                _upsert_finding(
                    conn, "sharepoint_site", sid, name,
                    "stale_site", "Medium",
                    f"Site '{name}' last modified {last_str[:10]} ({(now - last).days} days). "
                    f"Confirm still needed. {url}",
                    securesketch_control="SHARING-STALE-01",
                )
                findings_count += 1

    return json.dumps({
        "scanned": len(sites),
        "stale": stale,
        "very_stale": very_stale,
        "findings": findings_count,
    })
