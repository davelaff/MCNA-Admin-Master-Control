import json
import uuid
from datetime import datetime, timezone
from auth import get_token
from graph import graph_get_all
from db import get_connection
from tools.ssk_control_map import canonical_control_id

DOMAIN = "license"

CONTRIBUTES_TO = {
    "__tool__": [
        canonical_control_id("LIC-SKU-OVER-01"),
        canonical_control_id("LIC-SKU-UNUSED-01"),
        canonical_control_id("LIC-STACK-01"),
        canonical_control_id("LIC-DISABLED-01"),
    ],
    "sku_overconsumed":           [canonical_control_id("LIC-SKU-OVER-01")],
    "sku_unused":                 [canonical_control_id("LIC-SKU-UNUSED-01")],
    "productivity_sku_stacking":  [canonical_control_id("LIC-STACK-01")],
    "licensed_disabled_account":  [canonical_control_id("LIC-DISABLED-01")],
}

# Primary productivity SKUs. Any user holding 2+ of these is flagged for
# stacking review — the cheaper/lower license is almost certainly wasted.
# partNumber match because skuId varies by tenant.
PRODUCTIVITY_SKUS: set[str] = {
    "O365_BUSINESS_PREMIUM",      # Microsoft 365 Business Premium (SPB)
    "O365_BUSINESS_ESSENTIALS",   # Microsoft 365 Business Basic
    "O365_BUSINESS",              # Microsoft 365 Business Standard
    "SPB",                        # Microsoft 365 Business Premium (alt partNumber)
    "SPE_E3",                     # Microsoft 365 E3
    "SPE_E5",                     # Microsoft 365 E5
    "ENTERPRISEPACK",             # Office 365 E3
    "ENTERPRISEPREMIUM",          # Office 365 E5
    "STANDARDPACK",               # Office 365 E1
    "EXCHANGESTANDARD",           # Exchange Online Plan 1 (standalone)
    "EXCHANGEENTERPRISE",         # Exchange Online Plan 2 (standalone)
}

# Self-serve / viral SKUs — prepaid=10000 pools where zero consumption is
# expected and not a finding.
VIRAL_SKUS: set[str] = {
    "FLOW_FREE", "POWERAPPS_VIRAL", "CCIBOTS_PRIVPREV_VIRAL", "POWER_BI_STANDARD",
    "MICROSOFT_BUSINESS_CENTER", "Power_Pages_vTrial_for_Makers",
    "PROJECT_MADEIRA_PREVIEW_IW_SKU", "POWERAPPS_DEV", "WINDOWS_STORE",
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


def license_scan_skus() -> str:
    """Scan /subscribedSkus for over-consumption (compliance risk) and unused
    prepaid capacity (procurement waste)."""
    token = get_token()
    skus = graph_get_all("/subscribedSkus", token)

    overconsumed = 0
    unused = 0
    findings_count = 0

    with get_connection() as conn:
        for sku in skus:
            sku_id = sku["skuId"]
            part = sku.get("skuPartNumber", sku_id)
            prepaid = (sku.get("prepaidUnits") or {}).get("enabled", 0)
            consumed = sku.get("consumedUnits", 0)

            _upsert_snapshot(conn, "sku", sku_id, part, sku)

            if consumed > prepaid:
                overconsumed += 1
                _upsert_finding(
                    conn, "sku", sku_id, part,
                    "sku_overconsumed", "High",
                    f"SKU {part}: {consumed} consumed exceeds {prepaid} prepaid. "
                    "Compliance and true-up risk.",
                    securesketch_control="LIC-SKU-OVER-01",
                )
                findings_count += 1
            elif consumed == 0 and prepaid > 0 and part not in VIRAL_SKUS:
                unused += 1
                _upsert_finding(
                    conn, "sku", sku_id, part,
                    "sku_unused", "Low",
                    f"SKU {part}: {prepaid} prepaid, zero consumption. "
                    "Confirm still needed or retire.",
                    securesketch_control="LIC-SKU-UNUSED-01",
                )
                findings_count += 1

    return json.dumps({
        "scanned": len(skus),
        "overconsumed": overconsumed,
        "unused": unused,
        "findings": findings_count,
    })


def license_scan_users() -> str:
    """Scan /users: licensed-but-disabled (stale access / license waste) and
    productivity-SKU stacking (paying twice for the same capability)."""
    token = get_token()

    skus = graph_get_all("/subscribedSkus", token)
    sku_part = {s["skuId"]: s.get("skuPartNumber", s["skuId"]) for s in skus}

    users = graph_get_all(
        "/users?$select=id,userPrincipalName,displayName,accountEnabled,assignedLicenses&$top=999",
        token,
    )

    licensed_disabled = 0
    stacking = 0
    findings_count = 0

    with get_connection() as conn:
        for u in users:
            uid = u["id"]
            upn = u.get("userPrincipalName") or uid
            name = u.get("displayName") or upn
            enabled = u.get("accountEnabled", True)
            licenses = u.get("assignedLicenses") or []
            license_parts = [sku_part.get(lic["skuId"], lic["skuId"]) for lic in licenses]

            _upsert_snapshot(conn, "licensed_user", uid, name, {
                "upn": upn, "enabled": enabled, "license_parts": license_parts,
            })

            if licenses and not enabled:
                licensed_disabled += 1
                _upsert_finding(
                    conn, "licensed_user", uid, name,
                    "licensed_disabled_account", "Medium",
                    f"Disabled account {upn} holds {len(licenses)} license(s): "
                    f"{', '.join(license_parts)}. Remove licenses.",
                    owner=upn, securesketch_control="LIC-DISABLED-01",
                )
                findings_count += 1

            productivity_held = [p for p in license_parts if p in PRODUCTIVITY_SKUS]
            if len(productivity_held) >= 2:
                stacking += 1
                _upsert_finding(
                    conn, "licensed_user", uid, name,
                    "productivity_sku_stacking", "Medium",
                    f"{upn} holds multiple productivity SKUs: "
                    f"{', '.join(productivity_held)}. Retire the redundant license.",
                    owner=upn, securesketch_control="LIC-STACK-01",
                )
                findings_count += 1

    return json.dumps({
        "scanned_users": len(users),
        "scanned_skus": len(skus),
        "licensed_disabled": licensed_disabled,
        "stacking": stacking,
        "findings": findings_count,
    })
