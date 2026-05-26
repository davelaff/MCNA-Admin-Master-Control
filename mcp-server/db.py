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
CREATE TABLE IF NOT EXISTS ssk_controls (
    control_id                   TEXT PRIMARY KEY,
    source_version               TEXT NOT NULL,
    category                     TEXT NOT NULL,
    category_name                TEXT,
    title                        TEXT NOT NULL,
    overview                     TEXT,
    status_descriptions          TEXT,
    insufficient_measures_risks  TEXT,
    imported_at                  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS ssk_controls_history (
    history_id                   TEXT PRIMARY KEY,
    control_id                   TEXT NOT NULL,
    source_version               TEXT NOT NULL,
    category                     TEXT,
    category_name                TEXT,
    title                        TEXT,
    overview                     TEXT,
    status_descriptions          TEXT,
    insufficient_measures_risks  TEXT,
    imported_at                  TEXT,
    superseded_at                TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS ssk_categories (
    category       TEXT PRIMARY KEY,
    category_name  TEXT NOT NULL,
    display_order  INTEGER
);
CREATE TABLE IF NOT EXISTS ssk_recommended_actions (
    action_id             TEXT PRIMARY KEY,
    control_id            TEXT NOT NULL,
    source_version        TEXT NOT NULL,
    sequence              INTEGER NOT NULL,
    action_text           TEXT NOT NULL,
    implementation_status TEXT NOT NULL DEFAULT 'not_started',
    implementation_notes  TEXT,
    owner                 TEXT,
    last_updated          TEXT NOT NULL,
    FOREIGN KEY (control_id) REFERENCES ssk_controls(control_id)
);
CREATE TABLE IF NOT EXISTS ssk_control_status (
    control_id           TEXT PRIMARY KEY,
    current_maturity     TEXT NOT NULL DEFAULT 'not_regularly_reviewed',
    target_maturity      TEXT NOT NULL DEFAULT 'Regularly Reviewed',
    gap_summary          TEXT,
    owner                TEXT,
    review_cadence_days  INTEGER NOT NULL DEFAULT 90,
    last_reviewed_at     TEXT,
    next_review_due      TEXT,
    last_updated         TEXT NOT NULL,
    FOREIGN KEY (control_id) REFERENCES ssk_controls(control_id)
);
CREATE TABLE IF NOT EXISTS ssk_evidence (
    evidence_id              TEXT PRIMARY KEY,
    control_id               TEXT NOT NULL,
    evidence_type            TEXT NOT NULL,
    title                    TEXT,
    source_kind              TEXT NOT NULL,
    source_pointer           TEXT NOT NULL,
    source_metadata          TEXT,
    produced_at              TEXT NOT NULL,
    validity_window_days     INTEGER,
    expires_at               TEXT,
    verification_status      TEXT NOT NULL DEFAULT 'unverified',
    verification_checked_at  TEXT,
    recorded_by              TEXT,
    notes                    TEXT,
    FOREIGN KEY (control_id) REFERENCES ssk_controls(control_id)
);
CREATE TABLE IF NOT EXISTS ssk_reviews (
    review_id         TEXT PRIMARY KEY,
    control_id        TEXT,
    control_family    TEXT,
    reviewer          TEXT NOT NULL,
    reviewed_at       TEXT NOT NULL,
    scope_summary     TEXT,
    evidence_ids      TEXT,
    outcome           TEXT NOT NULL,
    quality_flag      TEXT NOT NULL DEFAULT 'ok',
    findings_summary  TEXT,
    next_review_due   TEXT,
    prior_review_id   TEXT,
    CHECK ((control_id IS NOT NULL) <> (control_family IS NOT NULL))
);
CREATE TABLE IF NOT EXISTS ssk_registries (
    registry_entry_id  TEXT PRIMARY KEY,
    registry_name      TEXT NOT NULL,
    control_ids        TEXT,
    entry_key          TEXT NOT NULL,
    entry_data         TEXT,
    entry_pointer      TEXT,
    status             TEXT NOT NULL DEFAULT 'active',
    effective_from     TEXT NOT NULL,
    effective_to       TEXT,
    recorded_by        TEXT,
    recorded_at        TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS ix_ssk_registries_active_key
    ON ssk_registries(registry_name, entry_key)
    WHERE status = 'active';
CREATE TABLE IF NOT EXISTS ssk_control_coverage_snapshots (
    snapshot_id              TEXT PRIMARY KEY,
    run_id                   TEXT NOT NULL,
    control_id               TEXT NOT NULL,
    audit_status             TEXT NOT NULL,
    tooling_status           TEXT NOT NULL,
    evidence_source_type     TEXT NOT NULL,
    evidence_count           INTEGER NOT NULL,
    open_finding_count       INTEGER NOT NULL,
    missing_evidence_action  TEXT,
    rationale                TEXT,
    metadata                 TEXT,
    created_at               TEXT NOT NULL,
    FOREIGN KEY (control_id) REFERENCES ssk_controls(control_id)
);
CREATE INDEX IF NOT EXISTS ix_ssk_control_coverage_snapshots_run
    ON ssk_control_coverage_snapshots(run_id, control_id);
CREATE TABLE IF NOT EXISTS ssk_clauses (
    clause_id      TEXT PRIMARY KEY,
    control_id     TEXT NOT NULL,
    source_version TEXT NOT NULL,
    group_name     TEXT,
    sequence       INTEGER NOT NULL,
    clause_text    TEXT NOT NULL,
    FOREIGN KEY (control_id) REFERENCES ssk_controls(control_id)
);
CREATE TABLE IF NOT EXISTS ssk_audit_evidence_items (
    item_id        TEXT PRIMARY KEY,
    control_id     TEXT NOT NULL,
    source_version TEXT NOT NULL,
    sequence       INTEGER NOT NULL,
    item_text      TEXT NOT NULL,
    FOREIGN KEY (control_id) REFERENCES ssk_controls(control_id)
);
CREATE TABLE IF NOT EXISTS remediation_plans (
    plan_id         TEXT PRIMARY KEY,
    title           TEXT NOT NULL,
    domain          TEXT NOT NULL,
    description     TEXT,
    source_pointer  TEXT,
    owner           TEXT,
    status          TEXT NOT NULL DEFAULT 'open',
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL,
    notes           TEXT
);
CREATE TABLE IF NOT EXISTS remediation_actions (
    action_id            TEXT PRIMARY KEY,
    plan_id              TEXT NOT NULL,
    finding_id           TEXT NOT NULL,
    target_id            TEXT NOT NULL,
    target_name          TEXT,
    proposed_action      TEXT NOT NULL,
    control_id           TEXT,
    risk_notes           TEXT,
    batch_name           TEXT,
    status               TEXT NOT NULL DEFAULT 'pending',
    approved_by          TEXT,
    approved_at          TEXT,
    approval_note        TEXT,
    rejected_by          TEXT,
    rejected_at          TEXT,
    rejection_reason     TEXT,
    closure_evidence_id  TEXT,
    closed_by            TEXT,
    closed_at            TEXT,
    created_at           TEXT NOT NULL,
    updated_at           TEXT NOT NULL,
    UNIQUE (plan_id, finding_id),
    FOREIGN KEY (plan_id) REFERENCES remediation_plans(plan_id),
    FOREIGN KEY (finding_id) REFERENCES findings(finding_id)
);
CREATE TABLE IF NOT EXISTS remediation_events (
    event_id    TEXT PRIMARY KEY,
    plan_id     TEXT,
    action_id   TEXT,
    event_type  TEXT NOT NULL,
    actor       TEXT,
    timestamp   TEXT NOT NULL,
    detail      TEXT
);
"""

def _apply_findings_migration(conn):
    cols = conn.execute("PRAGMA table_info(findings)").fetchall()
    names = {c[1] for c in cols}
    if "closure_evidence_id" not in names:
        conn.execute("ALTER TABLE findings ADD COLUMN closure_evidence_id TEXT")


def _apply_ssk_controls_migration(conn: sqlite3.Connection) -> None:
    _NEW_COLS = {"effective_date": "TEXT", "review_date": "TEXT",
                 "approver": "TEXT", "cadence": "TEXT", "reviewer": "TEXT"}
    for table in ("ssk_controls", "ssk_controls_history"):
        existing = {c[1] for c in conn.execute(f"PRAGMA table_info({table})").fetchall()}
        for col, typ in _NEW_COLS.items():
            if col not in existing:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {typ}")


def init_db(path: Path = KB_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.executescript(_SCHEMA)
        _apply_findings_migration(conn)
        _apply_ssk_controls_migration(conn)
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
