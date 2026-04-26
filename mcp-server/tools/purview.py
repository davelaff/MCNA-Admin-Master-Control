import json
import uuid
import requests
from datetime import datetime, timezone
from auth import get_token, get_app_token
from graph import graph_get, graph_get_all, GraphError
from db import get_connection
from tools.ssk_control_map import canonical_control_id

DOMAIN = "purview"

# Application-permission path (org-wide, requires InformationProtectionPolicy.Read.All app perm)
LABELS_URL = "https://graph.microsoft.com/beta/security/informationProtection/sensitivityLabels"
# Delegated fallback (user-scoped, requires InformationProtectionPolicy.Read delegated)
LABELS_URL_ME = "https://graph.microsoft.com/beta/me/security/informationProtection/sensitivityLabels"
AUDIT_PATH = "/auditLogs/directoryAudits"

CONTRIBUTES_TO = {
    "__tool__": [
        canonical_control_id("PURVIEW-SCOPE-01"),
        canonical_control_id("PURVIEW-LABEL-01"),
        canonical_control_id("PURVIEW-AUDIT-01"),
    ],
    "purview_scope_gap":     [canonical_control_id("PURVIEW-SCOPE-01")],
    "no_sensitivity_labels": [canonical_control_id("PURVIEW-LABEL-01")],
    "audit_log_inactive":    [canonical_control_id("PURVIEW-AUDIT-01")],
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
                    securesketch_control: str = None) -> str:
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
    """, (finding_id, DOMAIN, object_type, object_id, object_name, None,
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


def _try_labels() -> tuple[list, bool, str]:
    """Fetch sensitivity labels. Tries application token against org-wide endpoint first
    (InformationProtectionPolicy.Read.All), then falls back to delegated token against
    /me endpoint (InformationProtectionPolicy.Read).
    Returns (labels, available, reason)."""
    attempts = [
        (get_app_token, LABELS_URL),
        (get_token, LABELS_URL_ME),
    ]
    last_reason = "api_unavailable"
    for get_tok, url in attempts:
        try:
            token = get_tok()
            return graph_get_all(url, token), True, ""
        except GraphError as e:
            if e.status == 403:
                last_reason = "api_unavailable" if "Application-Gateway" in str(e) else "permission_denied"
            elif e.status == 400:
                last_reason = "api_unavailable"
            else:
                raise
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code in (400, 404):
                last_reason = "api_unavailable"
            else:
                raise
    return [], False, last_reason


def purview_scan_labels() -> str:
    """Enumerate Microsoft Purview sensitivity labels. No labels = no information
    classification baseline across M365. Requires InformationProtectionPolicy.Read
    (Delegated) or InformationProtectionPolicy.Read.All (Application).
    Tries application token against org-wide endpoint first, falls back to delegated /me path."""
    labels, available, reason = _try_labels()
    findings_count = 0

    with get_connection() as conn:
        if not available:
            if reason == "api_unavailable":
                action = (
                    "The sensitivity labels API endpoint is blocked at the Microsoft "
                    "infrastructure level. This typically means Purview/AIP is not licensed "
                    "or enabled for this tenant. Check Microsoft 365 subscription tier for "
                    "Purview P1/P2 entitlement, or verify the unified labeling feature is "
                    "activated in the Microsoft Purview compliance portal."
                )
            else:
                action = (
                    "Grant InformationProtectionPolicy.Read (Delegated) to the "
                    "MCNA-TenantIntel-ReadOnly app registration and ensure the account "
                    "running the scan has label viewer permissions, then re-run this scan. "
                    "Note: .Read.All does not exist as a Delegated scope for this API."
                )
            _upsert_finding(
                conn, "tenant", "purview", "Microsoft Purview",
                "purview_scope_gap", "Medium",
                action,
                securesketch_control="PURVIEW-SCOPE-01",
            )
            findings_count += 1
            result = {
                "domain": DOMAIN,
                "available": False,
                "labels_found": 0,
                "findings": findings_count,
            }
            _append_activity(conn, "purview_scan_labels", "success", result)
            return json.dumps(result)

        for label in labels:
            _upsert_snapshot(conn, "sensitivity_label", label["id"],
                             label.get("name", label["id"]), label)

        if not labels:
            _upsert_finding(
                conn, "tenant", "purview-labels", "Sensitivity Labels",
                "no_sensitivity_labels", "High",
                "No sensitivity labels defined. Create and publish a sensitivity label taxonomy "
                "in Microsoft Purview to support information classification across M365 services.",
                securesketch_control="PURVIEW-LABEL-01",
            )
            findings_count += 1

        result = {
            "domain": DOMAIN,
            "available": True,
            "labels_found": len(labels),
            "findings": findings_count,
        }
        _append_activity(conn, "purview_scan_labels", "success", result)

    return json.dumps(result)


def purview_scan_audit() -> str:
    """Check M365 audit log accessibility and recent directory event activity.
    Confirms the audit pipeline is accessible and producing events.
    Uses AuditLog.Read.All (already consented). Wired to 16-1."""
    token = get_token()
    findings_count = 0

    try:
        data = graph_get(AUDIT_PATH, token,
                         params={"$top": "5", "$orderby": "activityDateTime desc"})
        events = data.get("value", [])
        available = True
    except GraphError as e:
        if e.status in (400, 403):
            events = []
            available = False
        else:
            raise

    with get_connection() as conn:
        if not available:
            _upsert_finding(
                conn, "tenant", "purview-audit", "M365 Audit Log",
                "purview_scope_gap", "Medium",
                "AuditLog.Read.All consent required to verify audit log activity. "
                "Grant consent to MCNA-TenantIntel-ReadOnly app registration.",
                securesketch_control="PURVIEW-SCOPE-01",
            )
            findings_count += 1
            result = {
                "domain": DOMAIN,
                "available": False,
                "recent_events_found": 0,
                "findings": findings_count,
            }
            _append_activity(conn, "purview_scan_audit", "success", result)
            return json.dumps(result)

        if not events:
            _upsert_finding(
                conn, "tenant", "purview-audit", "M365 Audit Log",
                "audit_log_inactive", "High",
                "No recent directory audit events found. Confirm Microsoft 365 unified audit "
                "logging is enabled in the compliance center.",
                securesketch_control="PURVIEW-AUDIT-01",
            )
            findings_count += 1

        most_recent = events[0].get("activityDateTime") if events else None
        result = {
            "domain": DOMAIN,
            "available": True,
            "recent_events_found": len(events),
            "most_recent_event": most_recent,
            "findings": findings_count,
        }
        _append_activity(conn, "purview_scan_audit", "success", result)

    return json.dumps(result)
