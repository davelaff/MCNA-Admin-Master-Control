import json
import uuid
from datetime import datetime, timezone, timedelta
from auth import get_token
from graph import graph_get_all, GraphError
from db import get_connection
from tools.ssk_control_map import canonical_control_id

DOMAIN = "devices"

CONTRIBUTES_TO = {
    "__tool__": [
        canonical_control_id("INTUNE-NONCOMPLIANT-01"),
    ],
    "unmanaged_entra_device": [canonical_control_id("INTUNE-NONCOMPLIANT-01")],
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
            owner=excluded.owner,
            recommended_action=excluded.recommended_action
    """, (finding_id, DOMAIN, object_type, object_id, object_name, owner,
          finding_type, severity, securesketch_control, recommended_action, now, now))
    return finding_id


def devices_scan_entra() -> str:
    """Scan Entra ID directory registered devices to identify unmanaged endpoints bypassing MDM (Intune).
    
    Requires Directory.Read.All on the MCNA-TenantIntel-ReadOnly registration.
    """
    token = get_token()
    devices = graph_get_all(
        "/devices?$select=id,displayName,isManaged,trustType,operatingSystem,operatingSystemVersion,deviceCategory,approximateLastSignInDateTime&$top=999",
        token,
    )

    unmanaged_count = 0
    findings_count = 0
    with get_connection() as conn:
        for dev in devices:
            did = dev["id"]
            name = dev.get("displayName") or did
            # Store in state snapshot
            _upsert_snapshot(conn, "entra_device", did, name, dev)

            # Check if MDM managed
            is_managed = dev.get("isManaged")
            if is_managed is False:
                unmanaged_count += 1
                findings_count += 1
                
                # Extract detailed context
                trust_type = dev.get("trustType") or "Unknown"
                os_name = dev.get("operatingSystem") or "Unknown OS"
                os_version = dev.get("operatingSystemVersion") or "Unknown Version"
                category = dev.get("deviceCategory") or "Uncategorized"
                last_seen_raw = dev.get("approximateLastSignInDateTime")
                
                # Check for historical sign-ins
                last_seen_str = f", approximate last sign-in: {last_seen_raw}" if last_seen_raw else " (never signed in)"
                
                rec_action = (
                    f"Device '{name}' is registered in Entra ID ({trust_type} on {os_name} {os_version}, Category: {category}) "
                    f"but is NOT enrolled in Intune MDM. Enroll this endpoint into Intune to enforce encryption, "
                    f"compliance baselines, and protect corporate data. If this is an employee-owned device, verify "
                    f"BYOD boundaries or block unauthorized configurations{last_seen_str}."
                )

                _upsert_finding(
                    conn,
                    object_type="entra_device",
                    object_id=did,
                    object_name=name,
                    finding_type="unmanaged_entra_device",
                    severity="Medium",
                    recommended_action=rec_action,
                    securesketch_control="INTUNE-NONCOMPLIANT-01",
                )

    return json.dumps({
        "scanned": len(devices),
        "unmanaged": unmanaged_count,
        "findings": findings_count
    })


def devices_generate_html_report(output_path: str = None) -> str:
    """Generate a styled HTML report of open unmanaged Entra device findings and write it to disk.

    Alias for generate_html_report(domain='devices'). Returns JSON with path and counts.
    """
    from tools.reporting import generate_html_report
    return generate_html_report(domain="devices", output_path=output_path)
