import json
import uuid
from unittest.mock import patch

import pytest
import requests

from graph import GraphError
from db import get_connection
from tools.purview import purview_scan_labels, purview_scan_audit
from tools.kb import kb_get_findings

FAKE_TOKEN = "fake-token"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _label(label_id: str, name: str = None) -> dict:
    return {
        "id": label_id,
        "name": name or f"Label-{label_id}",
        "description": "",
        "isEnabled": True,
        "sensitivity": 3,
    }


def _audit_event(event_id: str, dt: str = "2026-04-23T10:00:00Z") -> dict:
    return {
        "id": event_id,
        "activityDateTime": dt,
        "activityDisplayName": "Update user",
        "category": "UserManagement",
        "operationType": "Update",
        "result": "success",
    }


def _raises_403(*args, **kwargs):
    raise GraphError(403, "/fake", "Forbidden")


def _raises_http_404(*args, **kwargs):
    resp = requests.Response()
    resp.status_code = 404
    e = requests.exceptions.HTTPError(response=resp)
    raise e


# ---------------------------------------------------------------------------
# purview_scan_labels — scope not consented (403)
# ---------------------------------------------------------------------------

def test_scan_labels_scope_gap_returns_not_available(db):
    with patch("tools.purview.get_app_token", return_value=FAKE_TOKEN), \
         patch("tools.purview.get_token", return_value=FAKE_TOKEN), \
         patch("tools.purview.graph_get_all", side_effect=_raises_403):
        result = json.loads(purview_scan_labels())
    assert result["available"] is False
    assert result["api_accessible"] is False
    assert result["labels_found"] == 0
    assert result["error_reason"] == "api_inaccessible"
    assert len(result["endpoint_attempts"]) == 2
    assert result["endpoint_attempts"][0]["endpoint"] == "organization"
    assert result["endpoint_attempts"][0]["status"] == 403
    assert result["endpoint_attempts"][1]["endpoint"] == "me"
    assert result["endpoint_attempts"][1]["status"] == 403


def test_scan_labels_scope_gap_emits_finding(db):
    with patch("tools.purview.get_app_token", return_value=FAKE_TOKEN), \
         patch("tools.purview.get_token", return_value=FAKE_TOKEN), \
         patch("tools.purview.graph_get_all", side_effect=_raises_403):
        result = json.loads(purview_scan_labels())
    assert result["findings"] == 1
    findings = json.loads(kb_get_findings(domain="purview"))
    assert any(f["finding_type"] == "purview_scope_gap" and f["severity"] == "Medium"
               for f in findings)
    finding = next(f for f in findings if f["finding_type"] == "purview_scope_gap")
    assert "may already exist" in finding["recommended_action"]


def test_scan_labels_404_returns_not_available(db):
    with patch("tools.purview.get_app_token", return_value=FAKE_TOKEN), \
         patch("tools.purview.get_token", return_value=FAKE_TOKEN), \
         patch("tools.purview.graph_get_all", side_effect=_raises_http_404):
        result = json.loads(purview_scan_labels())
    assert result["available"] is False
    assert result["api_accessible"] is False
    assert result["findings"] == 1
    assert result["error_reason"] == "api_inaccessible"


# ---------------------------------------------------------------------------
# purview_scan_labels — no labels defined
# ---------------------------------------------------------------------------

def test_scan_labels_none_defined_flagged_high(db):
    with patch("tools.purview.get_app_token", return_value=FAKE_TOKEN), \
         patch("tools.purview.get_token", return_value=FAKE_TOKEN), \
         patch("tools.purview.graph_get_all", return_value=[]):
        result = json.loads(purview_scan_labels())
    assert result["available"] is True
    assert result["api_accessible"] is True
    assert result["labels_found"] == 0
    assert result["findings"] == 1
    findings = json.loads(kb_get_findings(domain="purview"))
    assert any(f["finding_type"] == "no_sensitivity_labels" and f["severity"] == "High"
               for f in findings)


# ---------------------------------------------------------------------------
# purview_scan_labels — labels defined
# ---------------------------------------------------------------------------

def test_scan_labels_defined_no_finding(db):
    labels = [_label("l1", "Confidential"), _label("l2", "Internal")]
    with patch("tools.purview.get_app_token", return_value=FAKE_TOKEN), \
         patch("tools.purview.get_token", return_value=FAKE_TOKEN), \
         patch("tools.purview.graph_get_all", return_value=labels):
        result = json.loads(purview_scan_labels())
    assert result["available"] is True
    assert result["api_accessible"] is True
    assert result["labels_found"] == 2
    assert result["findings"] == 0
    findings = json.loads(kb_get_findings(domain="purview"))
    assert not any(f["finding_type"] == "no_sensitivity_labels" for f in findings)


def test_scan_labels_single_label_no_finding(db):
    with patch("tools.purview.get_app_token", return_value=FAKE_TOKEN), \
         patch("tools.purview.get_token", return_value=FAKE_TOKEN), \
         patch("tools.purview.graph_get_all", return_value=[_label("l3", "Public")]):
        result = json.loads(purview_scan_labels())
    assert result["labels_found"] == 1
    assert result["findings"] == 0


def test_scan_labels_summary_shape(db):
    labels = [_label(f"lx{i}") for i in range(5)]
    with patch("tools.purview.get_app_token", return_value=FAKE_TOKEN), \
         patch("tools.purview.get_token", return_value=FAKE_TOKEN), \
         patch("tools.purview.graph_get_all", return_value=labels):
        result = json.loads(purview_scan_labels())
    assert result["domain"] == "purview"
    assert result["available"] is True
    assert result["api_accessible"] is True
    assert result["labels_found"] == 5
    assert result["findings"] == 0


def test_scan_labels_falls_back_to_me_endpoint(db):
    labels = [_label("l3", "Public")]
    with patch("tools.purview.get_app_token", return_value=FAKE_TOKEN), \
         patch("tools.purview.get_token", return_value=FAKE_TOKEN), \
         patch(
             "tools.purview.graph_get_all",
             side_effect=[GraphError(403, "/org", "Forbidden"), labels],
         ):
        result = json.loads(purview_scan_labels())
    assert result["available"] is True
    assert result["api_accessible"] is True
    assert result["labels_found"] == 1
    assert result["endpoint_attempts"][0]["status"] == 403
    assert result["endpoint_attempts"][1]["status"] == 200
    assert result["endpoint_attempts"][1]["labels_found"] == 1


def test_scan_labels_rewrites_stale_scope_gap_action(db):
    finding_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, "purview.tenant.purview.purview_scope_gap"))
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO findings (
                finding_id, domain, object_type, object_id, object_name, owner,
                finding_type, severity, securesketch_control, recommended_action,
                status, first_seen, last_seen
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'open', ?, ?)
            """,
            (
                finding_id,
                "purview",
                "tenant",
                "purview",
                "Microsoft Purview",
                None,
                "purview_scope_gap",
                "Medium",
                "PURVIEW-SCOPE-01",
                "Old incorrect licensing guidance.",
                "2026-04-26T00:00:00+00:00",
                "2026-04-26T00:00:00+00:00",
            ),
        )

    with patch("tools.purview.get_app_token", return_value=FAKE_TOKEN), \
         patch("tools.purview.get_token", return_value=FAKE_TOKEN), \
         patch("tools.purview.graph_get_all", side_effect=_raises_403):
        purview_scan_labels()

    findings = json.loads(kb_get_findings(domain="purview"))
    finding = next(f for f in findings if f["finding_id"] == finding_id)
    assert "may already exist" in finding["recommended_action"]


# ---------------------------------------------------------------------------
# purview_scan_audit — scope gap (403)
# ---------------------------------------------------------------------------

def test_scan_audit_scope_gap_returns_not_available(db):
    with patch("tools.purview.get_token", return_value=FAKE_TOKEN), \
         patch("tools.purview.graph_get", side_effect=_raises_403):
        result = json.loads(purview_scan_audit())
    assert result["available"] is False
    assert result["recent_events_found"] == 0


def test_scan_audit_scope_gap_emits_finding(db):
    with patch("tools.purview.get_token", return_value=FAKE_TOKEN), \
         patch("tools.purview.graph_get", side_effect=_raises_403):
        result = json.loads(purview_scan_audit())
    assert result["findings"] == 1
    findings = json.loads(kb_get_findings(domain="purview"))
    assert any(f["finding_type"] == "purview_scope_gap" for f in findings)


# ---------------------------------------------------------------------------
# purview_scan_audit — no events
# ---------------------------------------------------------------------------

def test_scan_audit_empty_flagged_high(db):
    with patch("tools.purview.get_token", return_value=FAKE_TOKEN), \
         patch("tools.purview.graph_get", return_value={"value": []}):
        result = json.loads(purview_scan_audit())
    assert result["available"] is True
    assert result["recent_events_found"] == 0
    assert result["findings"] == 1
    findings = json.loads(kb_get_findings(domain="purview"))
    assert any(f["finding_type"] == "audit_log_inactive" and f["severity"] == "High"
               for f in findings)


# ---------------------------------------------------------------------------
# purview_scan_audit — events present
# ---------------------------------------------------------------------------

def test_scan_audit_events_present_no_finding(db):
    events = [_audit_event(f"ev{i}") for i in range(3)]
    with patch("tools.purview.get_token", return_value=FAKE_TOKEN), \
         patch("tools.purview.graph_get", return_value={"value": events}):
        result = json.loads(purview_scan_audit())
    assert result["available"] is True
    assert result["recent_events_found"] == 3
    assert result["findings"] == 0
    findings = json.loads(kb_get_findings(domain="purview"))
    assert not any(f["finding_type"] == "audit_log_inactive" for f in findings)


def test_scan_audit_reports_most_recent_event(db):
    events = [_audit_event("ev1", "2026-04-23T10:00:00Z")]
    with patch("tools.purview.get_token", return_value=FAKE_TOKEN), \
         patch("tools.purview.graph_get", return_value={"value": events}):
        result = json.loads(purview_scan_audit())
    assert result["most_recent_event"] == "2026-04-23T10:00:00Z"


def test_scan_audit_summary_shape(db):
    events = [_audit_event(f"ev{i}", f"2026-04-2{i}T00:00:00Z") for i in range(3, 6)]
    with patch("tools.purview.get_token", return_value=FAKE_TOKEN), \
         patch("tools.purview.graph_get", return_value={"value": events}):
        result = json.loads(purview_scan_audit())
    assert result["domain"] == "purview"
    assert "most_recent_event" in result
    assert result["findings"] == 0


def test_scan_audit_records_success_activity(db):
    events = [_audit_event("activity1")]
    with patch("tools.purview.get_token", return_value=FAKE_TOKEN), \
         patch("tools.purview.graph_get", return_value={"value": events}):
        purview_scan_audit()

    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT * FROM activity_log
            WHERE tool_name = 'purview_scan_audit'
              AND domain = 'purview'
              AND outcome = 'success'
            """
        ).fetchone()

    assert row is not None
    assert json.loads(row["detail"])["recent_events_found"] == 1
