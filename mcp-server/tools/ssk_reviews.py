import json
import uuid
from datetime import datetime, timedelta

from db import get_connection
from tools.mail import mail_send_summary
from tools import ssk_common
from tools.ssk_control_map import canonical_control_id
from tools.ssk_common import (
    ReviewScopeError,
    UnknownControlError,
    append_activity,
    json_error,
    json_ok,
    require_control,
)


VALID_OUTCOMES = {"ok", "gaps_identified", "action_required"}
QUALITY_OK = "ok"
QUALITY_NO_EVIDENCE = "no_evidence"
QUALITY_STALE = "stale_evidence"
QUALITY_LOW = "low_evidence_count"
NON_REGULAR_GAP_SUMMARY = (
    "Latest review is missing current, sufficient evidence or still reports "
    "action-required gaps."
)


def _control_family_for(control_id: str) -> str:
    return control_id.split("-", 1)[0]


def _normalize_control_id(control_id: str | None) -> str | None:
    if not isinstance(control_id, str):
        return None
    normalized = control_id.strip()
    if not normalized:
        return None
    return canonical_control_id(normalized) or normalized


def _serialize_evidence_ids(evidence_ids: list[str]) -> str:
    return json.dumps(evidence_ids, separators=(",", ":"))


def _row_to_payload(row) -> dict:
    payload = dict(row)
    if payload.get("evidence_ids"):
        payload["evidence_ids"] = json.loads(payload["evidence_ids"])
    else:
        payload["evidence_ids"] = []
    return payload


def _normalize_scope(control_id: str | None, control_family: str | None) -> tuple[str | None, str | None]:
    normalized_control_id = _normalize_control_id(control_id)
    normalized_family = control_family.strip() if isinstance(control_family, str) else None
    if bool(normalized_control_id) == bool(normalized_family):
        raise ReviewScopeError("exactly one of control_id or control_family must be provided")
    return normalized_control_id, normalized_family


def _normalize_reviewer(reviewer: str | None) -> str:
    normalized = reviewer.strip() if isinstance(reviewer, str) else ""
    if not normalized:
        raise ValueError("reviewer must not be blank")
    return normalized


def _normalize_outcome(outcome: str | None) -> str:
    normalized = outcome.strip() if isinstance(outcome, str) else ""
    if normalized not in VALID_OUTCOMES:
        raise ValueError(f"unsupported outcome '{outcome}'")
    return normalized


def _normalize_evidence_ids_input(evidence_ids: list[str] | None) -> list[str]:
    if evidence_ids is None:
        return []
    if not isinstance(evidence_ids, list):
        raise ValueError("evidence_ids must be a list of evidence ids")
    normalized: list[str] = []
    for evidence_id in evidence_ids:
        if not isinstance(evidence_id, str) or not evidence_id.strip():
            raise ValueError("evidence_ids must only contain non-blank strings")
        normalized.append(evidence_id.strip())
    return normalized


def _affected_control_ids(conn, control_id: str | None, control_family: str | None) -> list[str]:
    if control_id is not None:
        require_control(conn, control_id)
        return [control_id]
    rows = conn.execute(
        "SELECT control_id FROM ssk_controls WHERE control_id LIKE ? ORDER BY control_id",
        (f"{control_family}-%",),
    ).fetchall()
    if not rows:
        raise UnknownControlError(f"control_family '{control_family}' not found")
    return [row["control_id"] for row in rows]


def _fetch_evidence_rows(conn, evidence_ids: list[str]):
    if not evidence_ids:
        return []
    placeholders = ",".join("?" for _ in evidence_ids)
    rows = conn.execute(
        f"SELECT * FROM ssk_evidence WHERE evidence_id IN ({placeholders})",
        evidence_ids,
    ).fetchall()
    row_ids = {row["evidence_id"] for row in rows}
    missing = [evidence_id for evidence_id in evidence_ids if evidence_id not in row_ids]
    if missing:
        raise ValueError(f"unknown evidence id(s): {', '.join(missing)}")
    return rows


def _validate_evidence_scope(
    evidence_rows,
    control_id: str | None,
    control_family: str | None,
) -> None:
    if control_id is not None:
        wrong_scope = [row["evidence_id"] for row in evidence_rows if row["control_id"] != control_id]
        if wrong_scope:
            raise ValueError(
                f"evidence id(s) not linked to control '{control_id}': {', '.join(wrong_scope)}"
            )
        return
    wrong_scope = [
        row["evidence_id"]
        for row in evidence_rows
        if not row["control_id"].startswith(f"{control_family}-")
    ]
    if wrong_scope:
        raise ValueError(
            f"evidence id(s) not linked to control family '{control_family}': {', '.join(wrong_scope)}"
        )


def _is_expired(expires_at: str | None, effective_at: str) -> bool:
    if not expires_at:
        return False
    return datetime.fromisoformat(expires_at) < datetime.fromisoformat(effective_at)


def _quality_flag(
    control_id: str | None,
    control_family: str | None,
    evidence_ids: list[str],
    evidence_rows,
    effective_at: str,
) -> str:
    if evidence_ids == []:
        return QUALITY_NO_EVIDENCE
    if any(
        row["verification_status"] == "unresolvable"
        or _is_expired(row["expires_at"], effective_at)
        for row in evidence_rows
    ):
        return QUALITY_STALE
    if control_family and len(evidence_rows) < 2:
        return QUALITY_LOW
    if control_id and len(evidence_rows) == 1:
        return QUALITY_LOW
    return QUALITY_OK


def _cadence_days_for_scope(conn, control_ids: list[str]) -> int:
    placeholders = ",".join("?" for _ in control_ids)
    row = conn.execute(
        f"SELECT MIN(review_cadence_days) AS cadence_days FROM ssk_control_status "
        f"WHERE control_id IN ({placeholders})",
        control_ids,
    ).fetchone()
    cadence = row["cadence_days"] if row and row["cadence_days"] is not None else 90
    return int(cadence)


def _compute_next_review_due(reviewed_at: str, cadence_days: int) -> str:
    return (datetime.fromisoformat(reviewed_at) + timedelta(days=cadence_days)).isoformat()


def _latest_same_scope_review_id(conn, control_id: str | None, control_family: str | None) -> str | None:
    if control_id is not None:
        row = conn.execute(
            "SELECT review_id FROM ssk_reviews WHERE control_id = ? ORDER BY reviewed_at DESC, review_id DESC LIMIT 1",
            (control_id,),
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT review_id FROM ssk_reviews WHERE control_family = ? ORDER BY reviewed_at DESC, review_id DESC LIMIT 1",
            (control_family,),
        ).fetchone()
    return row["review_id"] if row else None


def _latest_applicable_review(conn, control_id: str):
    control_family = _control_family_for(control_id)
    return conn.execute(
        """
        SELECT review_id, reviewed_at, outcome, quality_flag, next_review_due
        FROM ssk_reviews
        WHERE control_id = ? OR control_family = ?
        ORDER BY reviewed_at DESC, review_id DESC
        LIMIT 1
        """,
        (control_id, control_family),
    ).fetchone()


def _review_rows_for_refresh(conn, control_ids: list[str]):
    unique_control_ids = sorted(set(control_ids))
    if not unique_control_ids:
        return []
    families = sorted({_control_family_for(control_id) for control_id in unique_control_ids})
    control_placeholders = ",".join("?" for _ in unique_control_ids)
    family_placeholders = ",".join("?" for _ in families)
    return conn.execute(
        f"""
        SELECT *
        FROM ssk_reviews
        WHERE control_id IN ({control_placeholders})
           OR control_family IN ({family_placeholders})
        ORDER BY reviewed_at DESC, review_id DESC
        """,
        [*unique_control_ids, *families],
    ).fetchall()


def _recompute_review_quality(conn, review_row, effective_at: str) -> None:
    evidence_ids = json.loads(review_row["evidence_ids"]) if review_row["evidence_ids"] else []
    evidence_rows = _fetch_evidence_rows(conn, evidence_ids)
    quality_flag = _quality_flag(
        review_row["control_id"],
        review_row["control_family"],
        evidence_ids,
        evidence_rows,
        effective_at,
    )
    conn.execute(
        "UPDATE ssk_reviews SET quality_flag = ? WHERE review_id = ?",
        (quality_flag, review_row["review_id"]),
    )


def _controls_for_families(conn, families: set[str]) -> list[str]:
    if not families:
        return []
    clauses = " OR ".join("control_id LIKE ?" for _ in families)
    rows = conn.execute(
        f"SELECT control_id FROM ssk_controls WHERE {clauses} ORDER BY control_id",
        [f"{family}-%" for family in sorted(families)],
    ).fetchall()
    return [row["control_id"] for row in rows]


def _recompute_control_status(conn, control_id: str, updated_at: str) -> None:
    latest = _latest_applicable_review(conn, control_id)
    current_maturity = (
        "regularly_reviewed"
        if latest and latest["outcome"] == "ok" and latest["quality_flag"] == QUALITY_OK
        else "not_regularly_reviewed"
    )
    gap_summary = None if current_maturity == "regularly_reviewed" else NON_REGULAR_GAP_SUMMARY
    last_reviewed_at = latest["reviewed_at"] if latest else None
    next_review_due = latest["next_review_due"] if latest else None
    conn.execute(
        """
        UPDATE ssk_control_status
        SET current_maturity = ?,
            gap_summary = ?,
            last_reviewed_at = ?,
            next_review_due = ?,
            last_updated = ?
        WHERE control_id = ?
        """,
        (
            current_maturity,
            gap_summary,
            last_reviewed_at,
            next_review_due,
            updated_at,
            control_id,
        ),
    )


def refresh_review_state_for_controls(conn, control_ids: list[str], updated_at: str) -> None:
    unique_control_ids = sorted(set(control_ids))
    if not unique_control_ids:
        return
    families = {_control_family_for(control_id) for control_id in unique_control_ids}
    for review_row in _review_rows_for_refresh(conn, unique_control_ids):
        _recompute_review_quality(conn, review_row, updated_at)
    affected_control_ids = sorted(
        set(unique_control_ids) | set(_controls_for_families(conn, families))
    )
    for control_id in affected_control_ids:
        _recompute_control_status(conn, control_id, updated_at)


def ssk_record_review(
    control_id=None,
    control_family=None,
    reviewer=None,
    evidence_ids=None,
    scope_summary=None,
    outcome=None,
    findings_summary=None,
) -> str:
    review_id = str(uuid.uuid4())
    entity_id = None
    try:
        normalized_control_id, normalized_family = _normalize_scope(control_id, control_family)
        entity_id = normalized_control_id or normalized_family
        normalized_reviewer = _normalize_reviewer(reviewer)
        normalized_outcome = _normalize_outcome(outcome)
        normalized_evidence_ids = _normalize_evidence_ids_input(evidence_ids)
        reviewed_at = ssk_common.utc_now()

        with get_connection() as conn:
            control_ids = _affected_control_ids(conn, normalized_control_id, normalized_family)
            evidence_rows = _fetch_evidence_rows(conn, normalized_evidence_ids)
            _validate_evidence_scope(evidence_rows, normalized_control_id, normalized_family)
            quality_flag = _quality_flag(
                normalized_control_id,
                normalized_family,
                normalized_evidence_ids,
                evidence_rows,
                reviewed_at,
            )
            next_review_due = _compute_next_review_due(
                reviewed_at,
                _cadence_days_for_scope(conn, control_ids),
            )
            prior_review_id = _latest_same_scope_review_id(conn, normalized_control_id, normalized_family)
            conn.execute(
                """
                INSERT INTO ssk_reviews
                    (review_id, control_id, control_family, reviewer, reviewed_at, scope_summary,
                     evidence_ids, outcome, quality_flag, findings_summary, next_review_due, prior_review_id)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    review_id,
                    normalized_control_id,
                    normalized_family,
                    normalized_reviewer,
                    reviewed_at,
                    scope_summary,
                    _serialize_evidence_ids(normalized_evidence_ids),
                    normalized_outcome,
                    quality_flag,
                    findings_summary,
                    next_review_due,
                    prior_review_id,
                ),
            )
            row = conn.execute(
                "SELECT * FROM ssk_reviews WHERE review_id = ?",
                (review_id,),
            ).fetchone()
            refresh_review_state_for_controls(conn, control_ids, reviewed_at)

        append_activity(
            "ssk_record_review",
            "success",
            {
                "control_id": normalized_control_id,
                "control_family": normalized_family,
                "outcome": normalized_outcome,
                "quality_flag": quality_flag,
                "review_id": review_id,
            },
            entity_id=review_id,
        )
        payload = _row_to_payload(row)
        if quality_flag != QUALITY_OK:
            payload["warning"] = f"review recorded with quality_flag '{quality_flag}'"
        return json_ok(payload)
    except ReviewScopeError as exc:
        append_activity(
            "ssk_record_review",
            "error",
            {"entity": entity_id, "error_type": "ReviewScopeError"},
            entity_id=entity_id,
        )
        return json_error(str(exc), "ReviewScopeError")
    except UnknownControlError as exc:
        append_activity(
            "ssk_record_review",
            "error",
            {"entity": entity_id, "error_type": "UnknownControlError"},
            entity_id=entity_id,
        )
        return json_error(str(exc), "UnknownControlError")
    except ValueError as exc:
        append_activity(
            "ssk_record_review",
            "error",
            {"entity": entity_id, "error_type": "ValidationError"},
            entity_id=entity_id,
        )
        return json_error(str(exc), "ValidationError")


def ssk_review_history(control_id: str, limit: int = 10) -> str:
    normalized_control_id = _normalize_control_id(control_id)
    if limit <= 0:
        return json_error("limit must be greater than zero", "ValidationError")
    try:
        with get_connection() as conn:
            require_control(conn, normalized_control_id)
            rows = conn.execute(
                """
                SELECT *
                FROM ssk_reviews
                WHERE control_id = ? OR control_family = ?
                ORDER BY reviewed_at DESC, review_id DESC
                LIMIT ?
                """,
                (
                    normalized_control_id,
                    _control_family_for(normalized_control_id),
                    limit,
                ),
            ).fetchall()
        return json_ok([_row_to_payload(row) for row in rows])
    except UnknownControlError as exc:
        return json_error(str(exc), "UnknownControlError")


def ssk_alerts() -> str:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM ssk_reviews
            WHERE quality_flag != ?
            ORDER BY reviewed_at DESC, review_id DESC
            """,
            (QUALITY_OK,),
        ).fetchall()
    return json_ok([_row_to_payload(row) for row in rows])


def ssk_due(days_ahead: int = 30, include_never_reviewed: bool = True) -> str:
    """Return controls due for review within days_ahead, plus never-reviewed controls when include_never_reviewed is True."""
    if days_ahead < 0:
        return json_error("days_ahead must be zero or greater", "ValidationError")
    now = datetime.fromisoformat(ssk_common.utc_now())
    cutoff = (now + timedelta(days=days_ahead)).isoformat()
    with get_connection() as conn:
        if include_never_reviewed:
            rows = conn.execute(
                """
                SELECT s.control_id, s.current_maturity, s.last_reviewed_at, s.next_review_due,
                       s.review_cadence_days, s.gap_summary, c.title, c.category, c.category_name,
                       CASE WHEN s.next_review_due IS NULL THEN 'never_reviewed'
                            WHEN s.next_review_due < ? THEN 'overdue'
                            ELSE 'due_soon'
                       END AS review_status
                FROM ssk_control_status s
                JOIN ssk_controls c ON c.control_id = s.control_id
                WHERE (s.next_review_due IS NULL)
                   OR (s.next_review_due <= ?)
                ORDER BY
                    CASE WHEN s.next_review_due IS NULL THEN 1 ELSE 0 END,
                    s.next_review_due,
                    s.control_id
                """,
                (now.isoformat(), cutoff),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT s.control_id, s.current_maturity, s.last_reviewed_at, s.next_review_due,
                       s.review_cadence_days, s.gap_summary, c.title, c.category, c.category_name,
                       CASE WHEN s.next_review_due < ? THEN 'overdue' ELSE 'due_soon' END AS review_status
                FROM ssk_control_status s
                JOIN ssk_controls c ON c.control_id = s.control_id
                WHERE s.next_review_due IS NOT NULL
                  AND s.next_review_due <= ?
                ORDER BY s.next_review_due, s.control_id
                """,
                (now.isoformat(), cutoff),
            ).fetchall()
    return json_ok([dict(row) for row in rows])


def _review_notification_subject(counts: dict, generated_at: str) -> str:
    return (
        "MCNA Secure SketCH review queue "
        f"({counts['total']} controls, {generated_at[:10]})"
    )


def _review_notification_body(
    generated_at: str,
    days_ahead: int,
    counts: dict,
    rows: list[dict],
) -> str:
    def _label(row: dict) -> str:
        status = row["review_status"].replace("_", " ")
        due = row["next_review_due"][:10] if row["next_review_due"] else "none"
        reviewed = row["last_reviewed_at"][:10] if row["last_reviewed_at"] else "never"
        title = row["title"] or ""
        return (
            f"- {row['control_id']} | {status} | next due {due} | "
            f"last reviewed {reviewed} | {title}"
        )

    lines = [
        "MCNA Secure SketCH scheduled review notification",
        f"Generated: {generated_at}",
        f"Window: next {days_ahead} day(s)",
        "",
        f"Controls requiring attention: {counts['total']}",
        f"Overdue: {counts['overdue']}",
        f"Due soon: {counts['due_soon']}",
        f"Never reviewed: {counts['never_reviewed']}",
        "",
    ]
    if rows:
        lines.append("Review queue:")
        lines.extend(_label(row) for row in rows)
    else:
        lines.append("No controls currently require review.")
    return "\n".join(lines)


def ssk_review_notifications(
    days_ahead: int = 30,
    include_never_reviewed: bool = True,
    to=None,
    cc=None,
    importance: str = "normal",
    dry_run: bool = True,
) -> str:
    """Build a review digest and optionally preview/send it through mail_send_summary."""
    due_result = json.loads(
        ssk_due(days_ahead=days_ahead, include_never_reviewed=include_never_reviewed)
    )
    if isinstance(due_result, dict) and due_result.get("error_type"):
        return json.dumps(due_result)

    rows = due_result
    counts = {
        "total": len(rows),
        "overdue": sum(1 for row in rows if row["review_status"] == "overdue"),
        "due_soon": sum(1 for row in rows if row["review_status"] == "due_soon"),
        "never_reviewed": sum(1 for row in rows if row["review_status"] == "never_reviewed"),
    }
    generated_at = ssk_common.utc_now()
    subject = _review_notification_subject(counts, generated_at)
    body = _review_notification_body(generated_at, days_ahead, counts, rows)

    mail_result = None
    if to is not None:
        mail_result = json.loads(
            mail_send_summary(
                to=to,
                cc=cc,
                subject=subject,
                body=body,
                importance=importance,
                dry_run=dry_run,
            )
        )

    append_activity(
        "ssk_review_notifications",
        "success",
        {
            "days_ahead": days_ahead,
            "include_never_reviewed": include_never_reviewed,
            "control_count": counts["total"],
            "mail_requested": to is not None,
            "dry_run": dry_run,
            "mail_sent": None if mail_result is None else mail_result.get("sent"),
        },
    )
    return json_ok(
        {
            "generated_at": generated_at,
            "days_ahead": days_ahead,
            "include_never_reviewed": include_never_reviewed,
            "counts": counts,
            "controls": rows,
            "subject": subject,
            "body": body,
            "mail": mail_result,
        }
    )
