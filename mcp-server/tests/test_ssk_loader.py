import json
from tools.ssk_loader import load_catalog


def _parsed_payload():
    return {
        "source_version": "2026-01-01",
        "categories": {"06": "Asset Management"},
        "controls": [
            {
                "control_id": "06-3",
                "source_version": "2026-01-01",
                "category": "06",
                "category_name": "Asset Management",
                "title": "Management of software assets",
                "overview": "Define rules for managing software assets.",
                "status_description": "Inventory of software assets is taken periodically.",
                "recommended_actions": ["Action one.", "Action two."],
                "insufficient_measures_risks": "Vulns may go undetected.",
            }
        ],
        "parse_failures": [],
        "warnings": [],
    }


def test_loader_inserts_control_and_actions(db):
    from db import get_connection
    result = load_catalog(_parsed_payload())
    assert result["written_controls"] == 1
    assert result["written_actions"] == 2

    with get_connection() as conn:
        controls = conn.execute("SELECT * FROM ssk_controls").fetchall()
        actions = conn.execute("SELECT * FROM ssk_recommended_actions ORDER BY sequence").fetchall()
        status = conn.execute("SELECT * FROM ssk_control_status").fetchall()
        cats = conn.execute("SELECT * FROM ssk_categories").fetchall()

    assert len(controls) == 1
    assert controls[0]["control_id"] == "06-3"
    assert controls[0]["source_version"] == "2026-01-01"
    assert controls[0]["category_name"] == "Asset Management"
    descriptions = json.loads(controls[0]["status_descriptions"])
    assert descriptions == {"Regularly Reviewed": "Inventory of software assets is taken periodically."}

    assert len(actions) == 2
    assert [a["action_id"] for a in actions] == ["06-3-a", "06-3-b"]
    assert actions[0]["action_text"] == "Action one."
    assert actions[0]["implementation_status"] == "not_started"

    assert len(status) == 1
    assert status[0]["control_id"] == "06-3"
    assert status[0]["current_maturity"] == "not_regularly_reviewed"
    assert status[0]["target_maturity"] == "Regularly Reviewed"

    assert len(cats) == 1
    assert cats[0]["category"] == "06"
    assert cats[0]["category_name"] == "Asset Management"


def test_loader_upsert_is_idempotent(db):
    from db import get_connection
    payload = _parsed_payload()
    load_catalog(payload)
    load_catalog(payload)
    with get_connection() as conn:
        count = conn.execute("SELECT COUNT(*) AS c FROM ssk_controls").fetchone()["c"]
    assert count == 1


def test_loader_moves_old_row_to_history_on_version_bump(db):
    from db import get_connection
    p1 = _parsed_payload()
    load_catalog(p1)
    p2 = _parsed_payload()
    p2["source_version"] = "2026-07-01"
    p2["controls"][0]["source_version"] = "2026-07-01"
    p2["controls"][0]["overview"] = "Updated overview."
    load_catalog(p2)

    with get_connection() as conn:
        current = conn.execute("SELECT * FROM ssk_controls").fetchone()
        history = conn.execute("SELECT * FROM ssk_controls_history").fetchall()
    assert current["source_version"] == "2026-07-01"
    assert current["overview"] == "Updated overview."
    assert len(history) == 1
    assert history[0]["source_version"] == "2026-01-01"
