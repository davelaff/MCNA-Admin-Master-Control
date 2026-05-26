import json
import uuid
from datetime import datetime, timezone
from db import get_connection


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_catalog(parsed: dict) -> dict:
    source_version = parsed["source_version"]
    controls = parsed["controls"]
    categories = parsed.get("categories", {})
    now = _now()

    written_controls = 0
    written_clauses = 0
    written_evidence_items = 0
    history_moved = 0

    with get_connection() as conn:
        for cat_id, cat_name in categories.items():
            conn.execute(
                "INSERT INTO ssk_categories (category, category_name) VALUES (?, ?) "
                "ON CONFLICT(category) DO UPDATE SET category_name = excluded.category_name",
                (cat_id, cat_name),
            )

        for c in controls:
            existing = conn.execute(
                "SELECT * FROM ssk_controls WHERE control_id = ?",
                (c["control_id"],),
            ).fetchone()

            if existing is not None and existing["source_version"] != source_version:
                conn.execute(
                    "INSERT INTO ssk_controls_history "
                    "(history_id, control_id, source_version, category, category_name, "
                    " title, overview, status_descriptions, insufficient_measures_risks, "
                    " effective_date, review_date, approver, cadence, reviewer, "
                    " imported_at, superseded_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        str(uuid.uuid4()),
                        existing["control_id"],
                        existing["source_version"],
                        existing["category"],
                        existing["category_name"],
                        existing["title"],
                        existing["overview"],
                        existing["status_descriptions"],
                        existing["insufficient_measures_risks"],
                        existing["effective_date"],
                        existing["review_date"],
                        existing["approver"],
                        existing["cadence"],
                        existing["reviewer"],
                        existing["imported_at"],
                        now,
                    ),
                )
                history_moved += 1

            status_descriptions = json.dumps(
                {"Regularly Reviewed": c.get("status_description", "")}
            )
            conn.execute(
                "INSERT INTO ssk_controls "
                "(control_id, source_version, category, category_name, title, overview, "
                " status_descriptions, insufficient_measures_risks, "
                " effective_date, review_date, approver, cadence, reviewer, imported_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(control_id) DO UPDATE SET "
                " source_version=excluded.source_version, category=excluded.category, "
                " category_name=excluded.category_name, title=excluded.title, "
                " overview=excluded.overview, status_descriptions=excluded.status_descriptions, "
                " insufficient_measures_risks=excluded.insufficient_measures_risks, "
                " effective_date=excluded.effective_date, review_date=excluded.review_date, "
                " approver=excluded.approver, cadence=excluded.cadence, "
                " reviewer=excluded.reviewer, imported_at=excluded.imported_at",
                (
                    c["control_id"], source_version, c["category"], c.get("category_name"),
                    c["title"], c.get("overview", ""), status_descriptions,
                    c.get("insufficient_measures_risks", ""),
                    c.get("effective_date"), c.get("review_date"), c.get("approver"),
                    c.get("cadence", ""), c.get("reviewer", ""), now,
                ),
            )
            written_controls += 1

            # Clauses (replace-on-import)
            conn.execute(
                "DELETE FROM ssk_clauses WHERE control_id = ?", (c["control_id"],)
            )
            for clause in c.get("clauses", []):
                conn.execute(
                    "INSERT INTO ssk_clauses "
                    "(clause_id, control_id, source_version, group_name, sequence, clause_text) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        clause["clause_id"], c["control_id"], source_version,
                        clause.get("group_name"), clause["sequence"], clause["clause_text"],
                    ),
                )
                written_clauses += 1

            # Audit evidence items (replace-on-import)
            conn.execute(
                "DELETE FROM ssk_audit_evidence_items WHERE control_id = ?", (c["control_id"],)
            )
            for item in c.get("audit_evidence_items", []):
                item_id = f"{c['control_id']}-ae-{item['sequence']}"
                conn.execute(
                    "INSERT INTO ssk_audit_evidence_items "
                    "(item_id, control_id, source_version, sequence, item_text) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (item_id, c["control_id"], source_version, item["sequence"], item["item_text"]),
                )
                written_evidence_items += 1

            # Clear old recommended_actions on reimport (new format has none)
            conn.execute(
                "DELETE FROM ssk_recommended_actions WHERE control_id = ?",
                (c["control_id"],),
            )

            conn.execute(
                "INSERT INTO ssk_control_status (control_id, last_updated) VALUES (?, ?) "
                "ON CONFLICT(control_id) DO NOTHING",
                (c["control_id"], now),
            )

    return {
        "written_controls": written_controls,
        "written_actions": written_clauses,  # backward-compat key
        "written_clauses": written_clauses,
        "written_evidence_items": written_evidence_items,
        "history_moved": history_moved,
    }
