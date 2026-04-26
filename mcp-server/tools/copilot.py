import json
import uuid
from datetime import datetime, timezone
import requests
from auth import get_token
from graph import graph_get, graph_get_all, GraphError
from db import get_connection
from tools.ssk_control_map import canonical_control_id

DOMAIN = "copilot"

CONTRIBUTES_TO = {
    "__tool__": [
        canonical_control_id("COP-LICENSE-01"),
        canonical_control_id("COP-ACCESS-01"),
        canonical_control_id("COP-SETTINGS-01"),
        canonical_control_id("COP-USAGE-01"),
    ],
    "copilot_licensed_disabled": [
        canonical_control_id("COP-ACCESS-01"),
        canonical_control_id("COP-LICENSE-01"),
    ],
    "copilot_no_base_license": [canonical_control_id("COP-LICENSE-01")],
    "copilot_scope_gap":       [canonical_control_id("COP-SETTINGS-01")],
}

# Qualifying M365 base licenses required for Copilot for Microsoft 365.
BASE_LICENSE_SKUS: set[str] = {
    "O365_BUSINESS_PREMIUM",
    "O365_BUSINESS_ESSENTIALS",
    "O365_BUSINESS",
    "SPB",
    "SPE_E3",
    "SPE_E5",
    "ENTERPRISEPACK",
    "ENTERPRISEPREMIUM",
    "STANDARDPACK",
    "TEAMS_ESSENTIALS",
    "Microsoft_Teams_Essentials",
}

# SKU partNumbers for Copilot for Microsoft 365.
COPILOT_SKUS: set[str] = {
    "Microsoft_365_Copilot",
    "COPILOT_FOR_M365",
}

COPILOT_SETTINGS_PATH = "/copilot/admin/settings/limitedMode"


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


def copilot_scan_licenses() -> str:
    """Inventory Copilot for Microsoft 365 license assignments.
    Flags disabled accounts holding Copilot (oversharing risk) and Copilot
    assignments without a qualifying base license (misconfiguration).
    Uses Directory.Read.All (already consented)."""
    token = get_token()
    skus = graph_get_all("/subscribedSkus", token)
    sku_part = {s["skuId"]: s.get("skuPartNumber", s["skuId"]) for s in skus}

    users = graph_get_all(
        "/users?$select=id,userPrincipalName,displayName,accountEnabled,assignedLicenses&$top=999",
        token,
    )

    copilot_user_count = 0
    findings_count = 0

    with get_connection() as conn:
        for u in users:
            uid = u["id"]
            upn = u.get("userPrincipalName") or uid
            name = u.get("displayName") or upn
            enabled = u.get("accountEnabled", True)
            licenses = u.get("assignedLicenses") or []
            license_parts = [sku_part.get(lic["skuId"], lic["skuId"]) for lic in licenses]

            has_copilot = any(p in COPILOT_SKUS for p in license_parts)
            if not has_copilot:
                continue

            copilot_user_count += 1
            _upsert_snapshot(conn, "copilot_user", uid, name, {
                "upn": upn,
                "enabled": enabled,
                "license_parts": license_parts,
            })

            if not enabled:
                _upsert_finding(
                    conn, "copilot_user", uid, name,
                    "copilot_licensed_disabled", "High",
                    f"Disabled account {upn} holds a Copilot for M365 license. "
                    "Remove the Copilot license to eliminate oversharing risk "
                    "if this account is ever reactivated.",
                    owner=upn,
                    securesketch_control="COP-ACCESS-01",
                )
                findings_count += 1

            has_base = any(p in BASE_LICENSE_SKUS for p in license_parts)
            if not has_base:
                _upsert_finding(
                    conn, "copilot_user", uid, name,
                    "copilot_no_base_license", "Medium",
                    f"{upn} has Copilot for M365 but no qualifying base license "
                    f"({', '.join(license_parts)}). "
                    "Assign a qualifying M365 base license (E3, Business Premium, etc.) "
                    "or remove the Copilot license.",
                    owner=upn,
                    securesketch_control="COP-LICENSE-01",
                )
                findings_count += 1

    return json.dumps({
        "domain": DOMAIN,
        "scanned_users": len(users),
        "copilot_users": copilot_user_count,
        "findings": findings_count,
    })


def copilot_scan_settings() -> str:
    """Probe Copilot for M365 admin settings via Graph v1.0 endpoint.
    403/404 produces a scope_gap finding. Requires
    CopilotSettings-LimitedMode.Read (Delegated, admin consent required)."""
    token = get_token()
    findings_count = 0

    try:
        settings = graph_get(COPILOT_SETTINGS_PATH, token)
        available = True
    except (GraphError, requests.exceptions.HTTPError) as e:
        status = e.status if isinstance(e, GraphError) else (
            e.response.status_code if e.response is not None else 0
        )
        if status in (400, 403, 404):
            with get_connection() as conn:
                _upsert_finding(
                    conn, "tenant", "copilot-settings", "Copilot Settings",
                    "copilot_scope_gap", "Medium",
                    "Grant CopilotSettings-LimitedMode.Read delegated consent to the "
                    "MCNA-TenantIntel-ReadOnly app registration to enable Copilot settings "
                    "governance visibility.",
                    securesketch_control="COP-SETTINGS-01",
                )
                findings_count += 1
            return json.dumps({
                "domain": DOMAIN,
                "available": False,
                "http_status": status,
                "findings": findings_count,
            })
        raise

    with get_connection() as conn:
        _upsert_snapshot(conn, "copilot_settings", "tenant", "Copilot Settings", settings)

    result: dict = {
        "domain": DOMAIN,
        "available": True,
        "findings": findings_count,
    }
    if "isEnabledInOrg" in settings:
        result["isEnabledInOrg"] = settings["isEnabledInOrg"]
    if "userAccessPolicy" in settings:
        result["userAccessPolicy"] = settings["userAccessPolicy"]
    return json.dumps(result)
