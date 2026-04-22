import json
import pytest
from tools.kb import (
    kb_get_findings, kb_update_finding, kb_dismiss,
    kb_get_snapshot, kb_diff_snapshot
)
from db import get_connection

def _insert_finding(db, finding_id="f1", domain="entra", severity="High", status="open"):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO findings "
            "(finding_id,domain,object_type,object_id,object_name,finding_type,"
            "severity,status,first_seen,last_seen) "
            "VALUES (?,?,'app_reg','obj1','App1','missing_owner',?,?,'2026-01-01','2026-01-01')",
            (finding_id, domain, severity, status)
        )

def test_kb_get_findings_returns_open(db):
    _insert_finding(db, "f1", status="open")
    _insert_finding(db, "f2", status="resolved")
    result = json.loads(kb_get_findings())
    ids = [r["finding_id"] for r in result]
    assert "f1" in ids
    assert "f2" not in ids

def test_kb_get_findings_filters_by_domain(db):
    _insert_finding(db, "f1", domain="entra")
    _insert_finding(db, "f2", domain="ca")
    result = json.loads(kb_get_findings(domain="entra"))
    assert all(r["domain"] == "entra" for r in result)

def test_kb_get_findings_filters_by_severity(db):
    _insert_finding(db, "f1", severity="High")
    _insert_finding(db, "f2", severity="Low")
    result = json.loads(kb_get_findings(severity="High"))
    assert all(r["severity"] == "High" for r in result)

def test_kb_update_finding_resolves(db):
    _insert_finding(db, "f1")
    result = json.loads(kb_update_finding("f1", "resolved"))
    assert result["status"] == "resolved"
    rows = json.loads(kb_get_findings(status="resolved"))
    assert any(r["finding_id"] == "f1" for r in rows)

def test_kb_update_finding_rejects_invalid_status(db):
    _insert_finding(db, "f1")
    result = json.loads(kb_update_finding("f1", "deleted"))
    assert "error" in result

def test_kb_update_finding_returns_error_for_missing(db):
    result = json.loads(kb_update_finding("nonexistent", "resolved"))
    assert "error" in result

def test_kb_dismiss_moves_finding(db):
    _insert_finding(db, "f1")
    result = json.loads(kb_dismiss("f1", "Accepted risk — legacy app"))
    assert result["dismissed"] == "f1"
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM dismissed WHERE finding_id='f1'").fetchone()
    assert row is not None
    assert "legacy app" in row["reason"]

def test_kb_dismiss_returns_error_for_missing(db):
    result = json.loads(kb_dismiss("nonexistent", "reason"))
    assert "error" in result

def test_kb_get_snapshot_returns_all_when_no_filter(db):
    with get_connection() as conn:
        conn.execute("INSERT INTO tenant_snapshot VALUES ('app_reg','id1','App1','entra','{}','2026-01-01')")
        conn.execute("INSERT INTO tenant_snapshot VALUES ('ca_policy','id2','Pol1','ca','{}','2026-01-01')")
    result = json.loads(kb_get_snapshot())
    assert len(result) == 2

def test_kb_get_snapshot_filters(db):
    with get_connection() as conn:
        conn.execute("INSERT INTO tenant_snapshot VALUES ('app_reg','id1','App1','entra','{}','2026-01-01')")
        conn.execute("INSERT INTO tenant_snapshot VALUES ('ca_policy','id2','Pol1','ca','{}','2026-01-01')")
    result = json.loads(kb_get_snapshot(domain="entra"))
    assert len(result) == 1
    assert result[0]["domain"] == "entra"

def test_kb_diff_snapshot_detects_new(db):
    current = [{"id": "id1", "name": "App1"}]
    result = json.loads(kb_diff_snapshot("app_reg", "entra", current))
    assert len(result["new"]) == 1
    assert result["new"][0]["id"] == "id1"
    assert result["removed"] == []
    assert result["changed"] == []

def test_kb_diff_snapshot_detects_removed(db):
    with get_connection() as conn:
        conn.execute("INSERT INTO tenant_snapshot VALUES ('app_reg','id1','App1','entra','{\"id\":\"id1\"}','2026-01-01')")
    result = json.loads(kb_diff_snapshot("app_reg", "entra", []))
    assert "id1" in result["removed"]

def test_kb_diff_snapshot_detects_changed(db):
    with get_connection() as conn:
        conn.execute("INSERT INTO tenant_snapshot VALUES ('app_reg','id1','App1','entra','{\"id\":\"id1\",\"name\":\"Old\"}','2026-01-01')")
    current = [{"id": "id1", "name": "New"}]
    result = json.loads(kb_diff_snapshot("app_reg", "entra", current))
    assert len(result["changed"]) == 1
    assert result["changed"][0]["after"]["name"] == "New"
