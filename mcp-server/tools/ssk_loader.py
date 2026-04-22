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
    written_actions = 0
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
                    " imported_at, superseded_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
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
                " status_descriptions, insufficient_measures_risks, imported_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(control_id) DO UPDATE SET "
                " source_version=excluded.source_version, category=excluded.category, "
                " category_name=excluded.category_name, title=excluded.title, "
                " overview=excluded.overview, status_descriptions=excluded.status_descriptions, "
                " insufficient_measures_risks=excluded.insufficient_measures_risks, "
                " imported_at=excluded.imported_at",
                (
                    c["control_id"], source_version, c["category"], c.get("category_name"),
                    c["title"], c.get("overview", ""), status_descriptions,
                    c.get("insufficient_measures_risks", ""), now,
                ),
            )
            written_controls += 1

            conn.execute(
                "DELETE FROM ssk_recommended_actions WHERE control_id = ?",
                (c["control_id"],),
            )
            for idx, action_text in enumerate(c.get("recommended_actions", [])):
                action_letter = chr(ord("a") + idx)
                action_id = f"{c['control_id']}-{action_letter}"
                conn.execute(
                    "INSERT INTO ssk_recommended_actions "
                    "(action_id, control_id, source_version, sequence, action_text, last_updated) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (action_id, c["control_id"], source_version, idx, action_text, now),
                )
                written_actions += 1

            conn.execute(
                "INSERT INTO ssk_control_status (control_id, last_updated) VALUES (?, ?) "
                "ON CONFLICT(control_id) DO NOTHING",
                (c["control_id"], now),
            )

    return {
        "written_controls": written_controls,
        "written_actions": written_actions,
        "history_moved": history_moved,
    }
