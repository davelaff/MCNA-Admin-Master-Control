import json

from db import get_connection
from tools.ssk_common import append_activity, json_error, json_ok, utc_now

VALID_ACTION_STATUSES = {"not_started", "in_progress", "complete", "n_a"}


def ssk_mark_action(
    action_id: str,
    status: str,
    notes: str | None = None,
    owner: str | None = None,
) -> str:
    """Update implementation status, notes, and owner for a recommended action."""
    if status not in VALID_ACTION_STATUSES:
        return json_error(
            f"status must be one of: {', '.join(sorted(VALID_ACTION_STATUSES))}",
            "InvalidStatus",
        )
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE ssk_recommended_actions
            SET implementation_status = ?,
                implementation_notes  = COALESCE(?, implementation_notes),
                owner                 = COALESCE(?, owner),
                last_updated          = ?
            WHERE action_id = ?
            """,
            (status, notes, owner, utc_now(), action_id),
        )
        changed = conn.execute("SELECT changes()").fetchone()[0]
        if not changed:
            return json_error(f"action '{action_id}' not found", "NotFound")
        row = conn.execute(
            "SELECT * FROM ssk_recommended_actions WHERE action_id = ?",
            (action_id,),
        ).fetchone()
    append_activity(
        "ssk_mark_action",
        "ok",
        {"action_id": action_id, "status": status},
        entity_id=action_id,
    )
    return json_ok(dict(row))


def ssk_action_queue(
    owner: str | None = None,
    status: str = "in_progress",
) -> str:
    """Return recommended actions filtered by implementation status and/or owner."""
    clauses: list[str] = []
    params: list = []
    if status:
        clauses.append("implementation_status = ?")
        params.append(status)
    if owner:
        clauses.append("owner = ?")
        params.append(owner)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    with get_connection() as conn:
        rows = conn.execute(
            f"SELECT * FROM ssk_recommended_actions {where} ORDER BY control_id, sequence",
            params,
        ).fetchall()
    return json_ok([dict(r) for r in rows])
