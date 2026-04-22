import json

from db import get_connection
from tools.ssk_actions import ssk_mark_action, ssk_action_queue


def _seed_control(control_id: str = "06-3") -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO ssk_controls
                (control_id, source_version, category, category_name, title, overview,
                 status_descriptions, insufficient_measures_risks, imported_at)
            VALUES (?,?,?,?,?,?,?,?,?)
            """,
            (
                control_id,
                "test-1",
                "06",
                "Assets",
                "Asset control",
                "Overview",
                "{}",
                "Risks",
                "2026-01-01T00:00:00+00:00",
            ),
        )


def _seed_action(
    action_id: str = "06-3-a",
    control_id: str = "06-3",
    status: str = "not_started",
    owner: str | None = None,
) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO ssk_recommended_actions
                (action_id, control_id, source_version, sequence, action_text,
                 implementation_status, owner, last_updated)
            VALUES (?,?,?,?,?,?,?,?)
            """,
            (
                action_id,
                control_id,
                "test-1",
                0,
                "Apply asset control procedure.",
                status,
                owner,
                "2026-01-01T00:00:00+00:00",
            ),
        )


# ---------------------------------------------------------------------------
# ssk_mark_action
# ---------------------------------------------------------------------------

def test_ssk_mark_action_updates_status_notes_and_owner(db):
    _seed_control()
    _seed_action()
    result = json.loads(
        ssk_mark_action("06-3-a", "complete", notes="Procedure updated", owner="Security")
    )
    assert result["action_id"] == "06-3-a"
    assert result["implementation_status"] == "complete"
    assert result["implementation_notes"] == "Procedure updated"
    assert result["owner"] == "Security"


def test_ssk_mark_action_rejects_invalid_status(db):
    _seed_control()
    _seed_action()
    result = json.loads(ssk_mark_action("06-3-a", "done"))
    assert "error" in result


def test_ssk_mark_action_returns_error_for_missing_action(db):
    result = json.loads(ssk_mark_action("nonexistent-action", "complete"))
    assert "error" in result


def test_ssk_mark_action_partial_update_preserves_existing_notes(db):
    _seed_control()
    _seed_action()
    ssk_mark_action("06-3-a", "in_progress", notes="Initial notes")
    # second call omits notes — existing notes should be preserved
    result = json.loads(ssk_mark_action("06-3-a", "complete"))
    assert result["implementation_notes"] == "Initial notes"


# ---------------------------------------------------------------------------
# ssk_action_queue
# ---------------------------------------------------------------------------

def test_ssk_action_queue_filters_by_status(db):
    _seed_control()
    _seed_action("06-3-a")
    result = json.loads(ssk_action_queue(status="not_started"))
    assert any(item["action_id"] == "06-3-a" for item in result)


def test_ssk_action_queue_filters_by_owner(db):
    _seed_control()
    _seed_action("06-3-a")
    ssk_mark_action("06-3-a", "in_progress", owner="Dave")
    result = json.loads(ssk_action_queue(owner="Dave", status="in_progress"))
    assert any(item["action_id"] == "06-3-a" for item in result)


def test_ssk_action_queue_excludes_wrong_owner(db):
    _seed_control()
    _seed_action("06-3-a", owner="Alice")
    result = json.loads(ssk_action_queue(owner="Bob", status="not_started"))
    assert not any(item["action_id"] == "06-3-a" for item in result)
