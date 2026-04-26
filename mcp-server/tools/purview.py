import json
import uuid
import requests
from datetime import datetime, timezone
from auth import get_token
from graph import graph_get, graph_get_all, GraphError
from db import get_connection
from tools.ssk_control_map import canonical_control_id

DOMAIN = "purview"

LABELS_URL = "https://graph.microsoft.com/beta/security/informationProtection/sensitivityLabels"
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
            owner=excluded.owner
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


def _try_labels(token: str) -> tuple[list, bool]:
    """Fetch sensitivity labels from beta endpoint. Returns (labels, available).
    403 = InformationProtectionPolicy.Read.All not consented.
    404 = beta feature unavailable in this tenant."""
    try:
        return graph_get_all(LABELS_URL, token), True
    except GraphError as e:
        if e.status in (400, 403):
            return [], False
        raise
    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code in (400, 404):
            return [], False
        raise


def purview_scan_labels() -> str:
    """Enumerate Microsoft Purview sensitivity labels. No labels = no information
    classification baseline across M365. Requires InformationProtectionPolicy.Read.All.
    Uses Graph beta: /beta/security/informationProtection/sensitivityLabels."""
    token = get_token()
    labels, available = _try_labels(token)
    findings_count = 0

    with get_connection() as conn:
        if not available:
            _upsert_finding(
                conn, "tenant", "purview", "Microsoft Purview",
                "purview_scope_gap", "Medium",
                "Grant InformationProtectionPolicy.Read.All delegated consent to the "
                "MCNA-TenantIntel-ReadOnly app registration, then re-run this scan.",
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
