import json
import uuid
from datetime import datetime, timezone

from db import get_connection


EVIDENCE_TYPES = {
    "scan_snapshot",
    "control_check",
    "review_minutes",
    "signed_document",
    "attestation",
    "policy_link",
    "registry_entry",
    "external_link",
    "finding_closure",
}

SOURCE_KINDS = {
    "local_file",
    "url",
    "sharepoint",
    "kb_row",
    "scan_run",
    "control_check",
}


class UnknownControlError(ValueError):
    pass


class ReviewScopeError(ValueError):
    pass


class RegistryConflictError(ValueError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def json_ok(payload: dict | list) -> str:
    return json.dumps(payload, indent=2)


def json_error(message: str, error_type: str) -> str:
    return json.dumps({"error": message, "error_type": error_type})


def append_activity(
    tool_name: str,
    outcome: str,
    detail: dict,
    entity_id: str | None = None,
) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO activity_log (run_id, timestamp, tool_name, domain, entity_id, outcome, detail)
            VALUES (?,?,?,?,?,?,?)
            """,
            (
                str(uuid.uuid4()),
                utc_now(),
                tool_name,
                "ssk",
                entity_id,
                outcome,
                json.dumps(detail, separators=(",", ":"), sort_keys=True),
            ),
        )


def require_control(conn, control_id: str) -> None:
    row = conn.execute(
        "SELECT control_id FROM ssk_controls WHERE control_id = ?",
        (control_id,),
    ).fetchone()
    if row is None:
        raise UnknownControlError(f"control '{control_id}' not found")
