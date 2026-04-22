import sqlite3
from contextlib import contextmanager
from pathlib import Path

KB_PATH = Path(__file__).parent / "kb" / "mcna_amc.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS tenant_snapshot (
    entity_type  TEXT NOT NULL,
    entity_id    TEXT NOT NULL,
    entity_name  TEXT,
    domain       TEXT NOT NULL,
    properties   TEXT,
    last_scanned TEXT NOT NULL,
    PRIMARY KEY (entity_type, entity_id)
);
CREATE TABLE IF NOT EXISTS findings (
    finding_id           TEXT PRIMARY KEY,
    domain               TEXT NOT NULL,
    object_type          TEXT NOT NULL,
    object_id            TEXT NOT NULL,
    object_name          TEXT,
    owner                TEXT,
    finding_type         TEXT NOT NULL,
    severity             TEXT NOT NULL,
    securesketch_control TEXT,
    recommended_action   TEXT,
    evidence_pointer     TEXT,
    status               TEXT NOT NULL DEFAULT 'open',
    first_seen           TEXT NOT NULL,
    last_seen            TEXT NOT NULL,
    source_run           TEXT,
    notes                TEXT
);
CREATE TABLE IF NOT EXISTS baselines (
    entity_type   TEXT NOT NULL,
    entity_id     TEXT NOT NULL,
    baseline_json TEXT NOT NULL,
    set_by        TEXT,
    set_at        TEXT NOT NULL,
    notes         TEXT,
    PRIMARY KEY (entity_type, entity_id)
);
CREATE TABLE IF NOT EXISTS dismissed (
    finding_id   TEXT PRIMARY KEY,
    dismissed_at TEXT NOT NULL,
    reason       TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS activity_log (
    run_id     TEXT PRIMARY KEY,
    timestamp  TEXT NOT NULL,
    tool_name  TEXT NOT NULL,
    domain     TEXT,
    entity_id  TEXT,
    outcome    TEXT NOT NULL,
    detail     TEXT
);
"""

def init_db(path: Path = KB_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.executescript(_SCHEMA)
        conn.commit()

@contextmanager
def get_connection():
    conn = sqlite3.connect(KB_PATH)  # KB_PATH resolved at call time — monkeypatching db.KB_PATH works
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
