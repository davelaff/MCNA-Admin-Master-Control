import json
from tools.ssk_loader import load_catalog


def _parsed_payload():
    return {
        "source_version": "2026-01-01",
        "categories": {},
        "controls": [
            {
                "control_id": "06-3",
                "source_version": "2026-01-01",
                "category": "06",
                "category_name": "Asset Management Standards",
                "title": "Management of software assets",
                "effective_date": "2026-05-15",
                "review_date": "2027-05-15",
                "approver": "CFO / Executive Sponsor",
                "overview": "Define rules for managing software assets.",
                "cadence": "At least annually.",
                "reviewer": "IT-MIS Director.",
                "status_description": "At least annually.",
                "insufficient_measures_risks": "Vulns may go undetected.",
                "clauses": [
                    {
                        "clause_id": "06-3.1",
                        "group_name": "Software Management",
                        "sequence": 0,
                        "clause_text": "Download software only from authorized vendors.",
                    },
                    {
                        "clause_id": "06-3.2",
                        "group_name": "Software Management",
                        "sequence": 1,
                        "clause_text": "Use IT asset management tools.",
                    },
                ],
                "audit_evidence_items": [
                    {"sequence": 0, "item_text": "Software asset inventory extract."},
                    {"sequence": 1, "item_text": "License management ledger."},
                ],
            }
        ],
        "parse_failures": [],
        "warnings": [],
    }


def test_loader_inserts_control_and_clauses(db):
    from db import get_connection
    result = load_catalog(_parsed_payload())
    assert result["written_controls"] == 1
    assert result["written_clauses"] == 2
    assert result["written_evidence_items"] == 2

    with get_connection() as conn:
        controls = conn.execute("SELECT * FROM ssk_controls").fetchall()
        clauses = conn.execute(
            "SELECT * FROM ssk_clauses ORDER BY sequence"
        ).fetchall()
        evidence = conn.execute(
            "SELECT * FROM ssk_audit_evidence_items ORDER BY sequence"
        ).fetchall()
        status = conn.execute("SELECT * FROM ssk_control_status").fetchall()

    assert len(controls) == 1
    c = controls[0]
    assert c["control_id"] == "06-3"
    assert c["effective_date"] == "2026-05-15"
    assert c["review_date"] == "2027-05-15"
    assert c["approver"] == "CFO / Executive Sponsor"
    assert c["cadence"] == "At least annually."
    assert c["reviewer"] == "IT-MIS Director."
    descriptions = json.loads(c["status_descriptions"])
    assert descriptions == {"Regularly Reviewed": "At least annually."}

    assert len(clauses) == 2
    assert clauses[0]["clause_id"] == "06-3.1"
    assert clauses[0]["clause_text"] == "Download software only from authorized vendors."
    assert clauses[0]["group_name"] == "Software Management"
    assert clauses[0]["sequence"] == 0
    assert clauses[1]["clause_id"] == "06-3.2"

    assert len(evidence) == 2
    assert evidence[0]["item_id"] == "06-3-ae-0"
    assert evidence[0]["item_text"] == "Software asset inventory extract."
    assert evidence[1]["item_id"] == "06-3-ae-1"

    assert len(status) == 1
    assert status[0]["control_id"] == "06-3"
    assert status[0]["current_maturity"] == "not_regularly_reviewed"


def test_loader_upsert_is_idempotent(db):
    from db import get_connection
    payload = _parsed_payload()
    load_catalog(payload)
    load_catalog(payload)
    with get_connection() as conn:
        count = conn.execute("SELECT COUNT(*) AS c FROM ssk_controls").fetchone()["c"]
        clause_count = conn.execute("SELECT COUNT(*) AS c FROM ssk_clauses").fetchone()["c"]
    assert count == 1
    assert clause_count == 2  # DELETE+INSERT, idempotent


def test_loader_moves_old_row_to_history_on_version_bump(db):
    from db import get_connection
    p1 = _parsed_payload()
    load_catalog(p1)
    p2 = _parsed_payload()
    p2["source_version"] = "2026-07-01"
    p2["controls"][0]["source_version"] = "2026-07-01"
    p2["controls"][0]["overview"] = "Updated overview."
    p2["controls"][0]["effective_date"] = "2026-07-01"
    load_catalog(p2)

    with get_connection() as conn:
        current = conn.execute("SELECT * FROM ssk_controls").fetchone()
        history = conn.execute("SELECT * FROM ssk_controls_history").fetchall()
    assert current["source_version"] == "2026-07-01"
    assert current["overview"] == "Updated overview."
    assert current["effective_date"] == "2026-07-01"
    assert len(history) == 1
    assert history[0]["source_version"] == "2026-01-01"
    assert history[0]["effective_date"] == "2026-05-15"
