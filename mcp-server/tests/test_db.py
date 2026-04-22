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
    assert tables == {"tenant_snapshot", "findings", "baselines", "dismissed", "activity_log"}

def test_init_is_idempotent(tmp_db):
    init_db(tmp_db)  # second call must not raise
    with sqlite3.connect(tmp_db) as conn:
        tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    assert len(tables) == 5

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
