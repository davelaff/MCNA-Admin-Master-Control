import json
import uuid
from datetime import datetime, timezone, timedelta
from auth import get_token
from graph import graph_get_all, GraphError
from db import get_connection
from tools.ssk_control_map import canonical_control_id

DOMAIN = "intune"

# Devices not synced in this many days are considered stale.
STALE_DAYS = 30

CONTRIBUTES_TO = {
    "__tool__": [
        canonical_control_id("INTUNE-SCOPE-01"),
        canonical_control_id("INTUNE-NOPOL-01"),
        canonical_control_id("INTUNE-NONCOMPLIANT-01"),
        canonical_control_id("INTUNE-STALE-01"),
        canonical_control_id("INTUNE-ENCRYPT-01"),
    ],
    "intune_not_available": [canonical_control_id("INTUNE-SCOPE-01")],
    "no_compliance_policies": [canonical_control_id("INTUNE-NOPOL-01")],
    "device_not_compliant":   [canonical_control_id("INTUNE-NONCOMPLIANT-01")],
    "stale_device":           [canonical_control_id("INTUNE-STALE-01")],
    "encryption_not_enabled": [canonical_control_id("INTUNE-ENCRYPT-01")],
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


def _try_intune(path: str, token: str) -> tuple[list, bool]:
    """Call an Intune deviceManagement endpoint. Returns (results, available).
    GraphError 403 = scope DeviceManagementManagedDevices.Read.All not consented
    or Intune not licensed. 400 = tenant not provisioned for that endpoint.
    Both treated as 'not available' — emit a finding and return cleanly."""
    try:
        return graph_get_all(path, token), True
    except GraphError as e:
        if e.status in (400, 403):
            return [], False
        raise


def intune_scan_devices() -> str:
    """Scan Intune-managed devices for compliance state, encryption status,
    and check-in staleness. Requires DeviceManagementManagedDevices.Read.All
    consent on the MCNA-TenantIntel-ReadOnly app registration. Emits
    intune_not_available if the scope is missing or Intune is unlicensed."""
    token = get_token()
    devices, available = _try_intune("/deviceManagement/managedDevices", token)

    now = datetime.now(timezone.utc)
    stale_cutoff = now - timedelta(days=STALE_DAYS)

    not_compliant = 0
    stale = 0
    not_encrypted = 0
    findings_count = 0

    with get_connection() as conn:
        if not available:
            _upsert_finding(
                conn,
                object_type="tenant",
                object_id="intune",
                object_name="Intune Device Management",
                finding_type="intune_not_available",
                severity="Medium",
                recommended_action=(
                    "Grant DeviceManagementManagedDevices.Read.All consent to the "
                    "MCNA-TenantIntel-ReadOnly app registration, then re-run this scan. "
                    "If Intune is not licensed, consider enrolling in Microsoft Intune to "
                    "enforce device compliance baselines across managed endpoints."
                ),
                securesketch_control="INTUNE-SCOPE-01",
            )
            findings_count += 1
            return json.dumps({
                "domain": DOMAIN,
                "scanned": 0,
                "intune_available": False,
                "not_compliant": 0,
                "stale": 0,
                "not_encrypted": 0,
                "findings": findings_count,
            })

        for device in devices:
            did = device.get("id", "")
            name = device.get("deviceName") or device.get("userDisplayName") or did
            os_type = device.get("operatingSystem", "")
            compliance_state = device.get("complianceState", "unknown")
            # Default True to avoid false positives when field is absent (e.g., non-Windows platforms)
            is_encrypted = device.get("isEncrypted", True)
            last_sync_raw = device.get("lastSyncDateTime")

            _upsert_snapshot(conn, "managed_device", did, name, {
                "operatingSystem": os_type,
                "complianceState": compliance_state,
                "isEncrypted": is_encrypted,
                "lastSyncDateTime": last_sync_raw,
                "managedDeviceOwnerType": device.get("managedDeviceOwnerType"),
            })

            # Non-compliant check — "unknown" is a valid transient state, not a finding
            if compliance_state not in ("compliant", "unknown"):
                not_compliant += 1
                findings_count += 1
                _upsert_finding(
                    conn,
                    object_type="managed_device",
                    object_id=did,
                    object_name=name,
                    finding_type="device_not_compliant",
                    severity="High",
                    recommended_action=(
                        f"Investigate non-compliant device '{name}' (state: {compliance_state}) in "
                        "Intune. Review compliance policy violations and remediate. If remediation "
                        "is not imminent, block device access via a Conditional Access policy "
                        "targeting the Intune compliance signal."
                    ),
                    securesketch_control="INTUNE-NONCOMPLIANT-01",
                )

            # Stale check — device hasn't checked in recently
            if last_sync_raw:
                try:
                    last_sync = datetime.fromisoformat(last_sync_raw.replace("Z", "+00:00"))
                    if last_sync < stale_cutoff:
                        stale += 1
                        findings_count += 1
                        _upsert_finding(
                            conn,
                            object_type="managed_device",
                            object_id=did,
                            object_name=name,
                            finding_type="stale_device",
                            severity="Low",
                            recommended_action=(
                                f"Device '{name}' has not checked in to Intune for over "
                                f"{STALE_DAYS} days. Verify the device is still in active "
                                "use and corporate-owned. Retire or wipe if abandoned."
                            ),
                            securesketch_control="INTUNE-STALE-01",
                        )
                except (ValueError, TypeError):
                    pass

            # Encryption check — Windows and macOS only; iOS/Android enforce encryption
            # at the OS level and the isEncrypted field behaves differently on those platforms.
            if os_type.lower() in ("windows", "macos") and not is_encrypted:
                not_encrypted += 1
                findings_count += 1
                _upsert_finding(
                    conn,
                    object_type="managed_device",
                    object_id=did,
                    object_name=name,
                    finding_type="encryption_not_enabled",
                    severity="High",
                    recommended_action=(
                        f"Device '{name}' ({os_type}) is not encrypted. Enable BitLocker "
                        "(Windows) or FileVault (macOS) via an Intune device configuration "
                        "profile or add disk encryption to the active compliance policy."
                    ),
                    securesketch_control="INTUNE-ENCRYPT-01",
                )

    return json.dumps({
        "domain": DOMAIN,
        "scanned": len(devices),
        "intune_available": True,
        "not_compliant": not_compliant,
        "stale": stale,
        "not_encrypted": not_encrypted,
        "findings": findings_count,
    })


def intune_scan_compliance_policies() -> str:
    """Check whether device compliance policies are defined in Intune. A tenant
    with Intune enrolled but no compliance policies has no automated compliance
    baseline — any device will self-certify as compliant by default.
    Requires DeviceManagementManagedDevices.Read.All consent."""
    token = get_token()
    policies, available = _try_intune("/deviceManagement/deviceCompliancePolicies", token)

    findings_count = 0

    with get_connection() as conn:
        if not available:
            _upsert_finding(
                conn,
                object_type="tenant",
                object_id="intune",
                object_name="Intune Device Management",
                finding_type="intune_not_available",
                severity="Medium",
                recommended_action=(
                    "Grant DeviceManagementManagedDevices.Read.All consent to the "
                    "MCNA-TenantIntel-ReadOnly app registration, then re-run this scan."
                ),
                securesketch_control="INTUNE-SCOPE-01",
            )
            findings_count += 1
            return json.dumps({
                "domain": DOMAIN,
                "intune_available": False,
                "policies_found": 0,
                "findings": findings_count,
            })

        if not policies:
            _upsert_finding(
                conn,
                object_type="tenant",
                object_id="intune-compliance-policies",
                object_name="Intune Compliance Policies",
                finding_type="no_compliance_policies",
                severity="High",
                recommended_action=(
                    "No device compliance policies are defined in Intune. Create compliance "
                    "policies for Windows, macOS, iOS, and Android covering minimum OS version, "
                    "disk encryption, password requirements, and antivirus status. Wire policies "
                    "to a Conditional Access rule to block or remediate non-compliant devices."
                ),
                securesketch_control="INTUNE-NOPOL-01",
            )
            findings_count += 1

        for policy in policies:
            pid = policy.get("id", "")
            pname = policy.get("displayName") or pid
            _upsert_snapshot(conn, "compliance_policy", pid, pname, {
                "scheduledActionsForRule": policy.get("scheduledActionsForRule"),
                "lastModifiedDateTime": policy.get("lastModifiedDateTime"),
            })

    return json.dumps({
        "domain": DOMAIN,
        "intune_available": True,
        "policies_found": len(policies),
        "findings": findings_count,
    })
