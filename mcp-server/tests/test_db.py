import sqlite3
import tempfile
from pathlib import Path
import pytest
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from db import init_db, get_connection

@pytest.fixture
def tmp_db(tmp_path):
    db = tmp_path / "test.db"
    init_db(db)
    return db

def test_init_creates_all_tables(tmp_db):
    with sqlite3.connect(tmp_db) as conn:
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    assert tables == {
        "tenant_snapshot", "findings", "baselines", "dismissed", "activity_log",
        "ssk_controls", "ssk_controls_history", "ssk_categories",
        "ssk_recommended_actions", "ssk_control_status",
        "ssk_evidence", "ssk_reviews", "ssk_registries",
        "ssk_control_coverage_snapshots",
        "remediation_plans", "remediation_actions", "remediation_events",
    }

def test_init_is_idempotent(tmp_db):
    init_db(tmp_db)  # second call must not raise
    with sqlite3.connect(tmp_db) as conn:
        tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    assert len(tables) == 17

def test_get_connection_commits(tmp_db, monkeypatch):
    import db as db_mod
    monkeypatch.setattr(db_mod, "KB_PATH", tmp_db)
    with get_connection() as conn:
        conn.execute("INSERT INTO activity_log VALUES ('r1','2026-01-01','tool','dom','e1','success','ok')")
    with get_connection() as conn:
        row = conn.execute("SELECT run_id FROM activity_log WHERE run_id='r1'").fetchone()
    assert row is not None

def test_get_connection_rolls_back_on_error(tmp_db, monkeypatch):
    import db as db_mod
    monkeypatch.setattr(db_mod, "KB_PATH", tmp_db)
    with pytest.raises(ValueError):
        with get_connection() as conn:
            conn.execute("INSERT INTO activity_log VALUES ('r2','2026-01-01','tool','dom','e1','success','ok')")
            raise ValueError("abort")
    with get_connection() as conn:
        row = conn.execute("SELECT run_id FROM activity_log WHERE run_id='r2'").fetchone()
    assert row is None

def test_ssk_tables_exist(db):
    from db import get_connection
    expected = {
        "ssk_controls", "ssk_controls_history", "ssk_categories",
        "ssk_recommended_actions", "ssk_control_status",
        "ssk_evidence", "ssk_reviews", "ssk_registries",
    }
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    names = {r["name"] for r in rows}
    missing = expected - names
    assert not missing, f"missing ssk tables: {missing}"

def test_findings_has_closure_evidence_id(db):
    from db import get_connection
    with get_connection() as conn:
        cols = conn.execute("PRAGMA table_info(findings)").fetchall()
    names = {c["name"] for c in cols}
    assert "closure_evidence_id" in names

def test_remediation_tables_exist(db):
    expected = {
        "remediation_plans",
        "remediation_actions",
        "remediation_events",
    }
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    names = {r["name"] for r in rows}
    missing = expected - names
    assert not missing, f"missing remediation tables: {missing}"

def test_ssk_control_coverage_snapshot_table_exists(db):
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        cols = conn.execute(
            "PRAGMA table_info(ssk_control_coverage_snapshots)"
        ).fetchall()
    names = {r["name"] for r in rows}
    col_names = {c["name"] for c in cols}
    assert "ssk_control_coverage_snapshots" in names
    assert {
        "snapshot_id",
        "run_id",
        "control_id",
        "audit_status",
        "tooling_status",
        "evidence_source_type",
        "evidence_count",
        "open_finding_count",
        "missing_evidence_action",
        "rationale",
        "metadata",
        "created_at",
    } <= col_names
