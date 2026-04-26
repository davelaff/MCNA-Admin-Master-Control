import json
import uuid
from pathlib import Path

from db import get_connection
from tools.ssk_common import UnknownControlError, json_error, json_ok, utc_now


DOMAIN = "remediation"


def _log_activity(tool_name: str, outcome: str, detail: dict, entity_id: str | None = None) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO activity_log (run_id, timestamp, tool_name, domain, entity_id, outcome, detail)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                utc_now(),
                tool_name,
                DOMAIN,
                entity_id,
                outcome,
                json.dumps(detail, separators=(",", ":"), sort_keys=True),
            ),
        )


def _record_event(
    conn,
    event_type: str,
    detail: dict,
    plan_id: str | None = None,
    action_id: str | None = None,
    actor: str | None = None,
) -> None:
    conn.execute(
        """
        INSERT INTO remediation_events
            (event_id, plan_id, action_id, event_type, actor, timestamp, detail)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            str(uuid.uuid4()),
            plan_id,
            action_id,
            event_type,
            actor,
            utc_now(),
            json.dumps(detail, separators=(",", ":"), sort_keys=True),
        ),
    )


def _row_payload(row) -> dict:
    return dict(row)


def _get_plan(conn, plan_id: str):
    return conn.execute(
        "SELECT * FROM remediation_plans WHERE plan_id = ?",
        (plan_id,),
    ).fetchone()


def _get_action(conn, action_id: str):
    return conn.execute(
        """
        SELECT a.*, p.domain, p.title AS plan_title
        FROM remediation_actions a
        JOIN remediation_plans p ON p.plan_id = a.plan_id
        WHERE a.action_id = ?
        """,
        (action_id,),
    ).fetchone()


def _get_finding(conn, finding_id: str):
    return conn.execute(
        "SELECT * FROM findings WHERE finding_id = ?",
        (finding_id,),
    ).fetchone()


def _require_control(conn, control_id: str) -> None:
    row = conn.execute(
        "SELECT control_id FROM ssk_controls WHERE control_id = ?",
        (control_id,),
    ).fetchone()
    if row is None:
        raise UnknownControlError(f"control '{control_id}' not found")


def remediation_create_plan(
    title: str,
    domain: str,
    description: str | None = None,
    source_pointer: str | None = None,
    owner: str = "Dave Lafferty",
) -> str:
    if not title or not str(title).strip():
        return json_error("title must not be blank", "ValidationError")
    if not domain or not str(domain).strip():
        return json_error("domain must not be blank", "ValidationError")

    plan_id = str(uuid.uuid4())
    now = utc_now()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO remediation_plans
                (plan_id, title, domain, description, source_pointer, owner, status,
                 created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, 'open', ?, ?)
            """,
            (
                plan_id,
                str(title).strip(),
                str(domain).strip(),
                description,
                source_pointer,
                owner,
                now,
                now,
            ),
        )
        _record_event(
            conn,
            "plan_created",
            {"title": title, "domain": domain, "source_pointer": source_pointer},
            plan_id=plan_id,
            actor=owner,
        )
        row = conn.execute(
            "SELECT * FROM remediation_plans WHERE plan_id = ?",
            (plan_id,),
        ).fetchone()

    _log_activity(
        "remediation_create_plan",
        "success",
        {"plan_id": plan_id, "domain": domain},
        entity_id=plan_id,
    )
    return json_ok(_row_payload(row))


def remediation_add_action(
    plan_id: str,
    finding_id: str,
    target_id: str,
    target_name: str,
    proposed_action: str,
    control_id: str | None = None,
    risk_notes: str | None = None,
    batch_name: str | None = None,
) -> str:
    if not proposed_action or not str(proposed_action).strip():
        return json_error("proposed_action must not be blank", "ValidationError")
    action_id = str(uuid.uuid4())
    now = utc_now()
    try:
        with get_connection() as conn:
            if _get_plan(conn, plan_id) is None:
                return json_error(f"plan '{plan_id}' not found", "NotFoundError")
            finding = _get_finding(conn, finding_id)
            if finding is None:
                return json_error(f"finding '{finding_id}' not found", "NotFoundError")
            duplicate = conn.execute(
                """
                SELECT action_id FROM remediation_actions
                WHERE plan_id = ? AND finding_id = ?
                """,
                (plan_id, finding_id),
            ).fetchone()
            if duplicate:
                return json_error(
                    f"finding '{finding_id}' already has an action in plan '{plan_id}'",
                    "ValidationError",
                )
            conn.execute(
                """
                INSERT INTO remediation_actions
                    (action_id, plan_id, finding_id, target_id, target_name,
                     proposed_action, control_id, risk_notes, batch_name, status,
                     created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)
                """,
                (
                    action_id,
                    plan_id,
                    finding_id,
                    target_id,
                    target_name,
                    proposed_action,
                    control_id,
                    risk_notes,
                    batch_name,
                    now,
                    now,
                ),
            )
            conn.execute(
                "UPDATE remediation_plans SET updated_at = ? WHERE plan_id = ?",
                (now, plan_id),
            )
            _record_event(
                conn,
                "action_created",
                {"finding_id": finding_id, "target_id": target_id},
                plan_id=plan_id,
                action_id=action_id,
            )
            row = conn.execute(
                "SELECT * FROM remediation_actions WHERE action_id = ?",
                (action_id,),
            ).fetchone()
    except Exception as exc:
        return json_error(str(exc), type(exc).__name__)

    _log_activity(
        "remediation_add_action",
        "success",
        {"plan_id": plan_id, "finding_id": finding_id},
        entity_id=action_id,
    )
    return json_ok(_row_payload(row))


def remediation_list_actions(
    plan_id: str | None = None,
    status: str | None = None,
    domain: str | None = None,
) -> str:
    clauses = []
    params: list[object] = []
    if plan_id:
        clauses.append("a.plan_id = ?")
        params.append(plan_id)
    if status:
        clauses.append("a.status = ?")
        params.append(status)
    if domain:
        clauses.append("p.domain = ?")
        params.append(domain)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    with get_connection() as conn:
        rows = conn.execute(
            f"""
            SELECT a.*, p.domain, p.title AS plan_title
            FROM remediation_actions a
            JOIN remediation_plans p ON p.plan_id = a.plan_id
            {where}
            ORDER BY p.domain, p.title, a.batch_name, a.target_name
            """,
            params,
        ).fetchall()
    return json_ok([_row_payload(row) for row in rows])


def remediation_approve_action(
    action_id: str,
    approved_by: str,
    approval_note: str,
) -> str:
    if not approved_by or not str(approved_by).strip():
        return json_error("approved_by must not be blank", "ValidationError")
    if not approval_note or not str(approval_note).strip():
        return json_error("approval_note must not be blank", "ValidationError")
    now = utc_now()
    with get_connection() as conn:
        action = _get_action(conn, action_id)
        if action is None:
            return json_error(f"action '{action_id}' not found", "NotFoundError")
        if action["status"] != "pending":
            return json_error(
                f"action '{action_id}' is {action['status']}, not pending",
                "ValidationError",
            )
        conn.execute(
            """
            UPDATE remediation_actions
            SET status = 'approved',
                approved_by = ?,
                approved_at = ?,
                approval_note = ?,
                updated_at = ?
            WHERE action_id = ?
            """,
            (approved_by, now, approval_note, now, action_id),
        )
        _record_event(
            conn,
            "action_approved",
            {"approval_note": approval_note},
            plan_id=action["plan_id"],
            action_id=action_id,
            actor=approved_by,
        )
        row = _get_action(conn, action_id)

    _log_activity(
        "remediation_approve_action",
        "success",
        {"action_id": action_id, "approved_by": approved_by},
        entity_id=action_id,
    )
    return json_ok(_row_payload(row))


def remediation_reject_action(
    action_id: str,
    rejected_by: str,
    rejection_reason: str,
) -> str:
    if not rejected_by or not str(rejected_by).strip():
        return json_error("rejected_by must not be blank", "ValidationError")
    if not rejection_reason or not str(rejection_reason).strip():
        return json_error("rejection_reason must not be blank", "ValidationError")
    now = utc_now()
    with get_connection() as conn:
        action = _get_action(conn, action_id)
        if action is None:
            return json_error(f"action '{action_id}' not found", "NotFoundError")
        if action["status"] != "pending":
            return json_error(
                f"action '{action_id}' is {action['status']}, not pending",
                "ValidationError",
            )
        conn.execute(
            """
            UPDATE remediation_actions
            SET status = 'rejected',
                rejected_by = ?,
                rejected_at = ?,
                rejection_reason = ?,
                updated_at = ?
            WHERE action_id = ?
            """,
            (rejected_by, now, rejection_reason, now, action_id),
        )
        _record_event(
            conn,
            "action_rejected",
            {"rejection_reason": rejection_reason},
            plan_id=action["plan_id"],
            action_id=action_id,
            actor=rejected_by,
        )
        row = _get_action(conn, action_id)

    _log_activity(
        "remediation_reject_action",
        "success",
        {"action_id": action_id, "rejected_by": rejected_by},
        entity_id=action_id,
    )
    return json_ok(_row_payload(row))


def _markdown_queue(plan, rows) -> str:
    lines = [
        f"# Remediation Approval Queue: {plan['title']}",
        "",
        f"Plan ID: `{plan['plan_id']}`  ",
        f"Domain: `{plan['domain']}`  ",
        f"Status: `{plan['status']}`",
        "",
        "| Action ID | Finding ID | Target | Proposed Action | Status | Batch | Risk Notes | Approved By | Approval Note | Closure Evidence |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    row["action_id"],
                    row["finding_id"],
                    row["target_name"] or row["target_id"],
                    row["proposed_action"],
                    row["status"],
                    row["batch_name"] or "",
                    row["risk_notes"] or "",
                    row["approved_by"] or "",
                    row["approval_note"] or "",
                    row["closure_evidence_id"] or "",
                ]
            )
            + " |"
        )
    lines.append("")
    return "\n".join(lines)


def remediation_export_queue(
    plan_id: str,
    output_path: str | None = None,
    format: str = "markdown",
) -> str:
    if format != "markdown":
        return json_error("only markdown export is currently supported", "ValidationError")
    with get_connection() as conn:
        plan = _get_plan(conn, plan_id)
        if plan is None:
            return json_error(f"plan '{plan_id}' not found", "NotFoundError")
        rows = conn.execute(
            """
            SELECT * FROM remediation_actions
            WHERE plan_id = ?
            ORDER BY batch_name, target_name
            """,
            (plan_id,),
        ).fetchall()
        path = Path(output_path) if output_path else Path("reports") / "remediation-queues" / f"{plan_id}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_markdown_queue(plan, rows), encoding="utf-8")
        _record_event(
            conn,
            "queue_exported",
            {"output_path": str(path), "format": format, "action_count": len(rows)},
            plan_id=plan_id,
        )

    _log_activity(
        "remediation_export_queue",
        "success",
        {"plan_id": plan_id, "output_path": str(path)},
        entity_id=plan_id,
    )
    return json_ok(
        {
            "plan_id": plan_id,
            "format": format,
            "output_path": str(path),
            "action_count": len(rows),
        }
    )


def remediation_close_action(
    action_id: str,
    control_id: str,
    evidence_title: str,
    source_pointer: str,
    notes: str | None = None,
    closed_by: str = "Dave Lafferty",
) -> str:
    if not evidence_title or not str(evidence_title).strip():
        return json_error("evidence_title must not be blank", "ValidationError")
    if not source_pointer or not str(source_pointer).strip():
        return json_error("source_pointer must not be blank", "ValidationError")

    evidence_id = str(uuid.uuid4())
    now = utc_now()
    try:
        with get_connection() as conn:
            action = _get_action(conn, action_id)
            if action is None:
                return json_error(f"action '{action_id}' not found", "NotFoundError")
            if action["status"] != "approved":
                return json_error(
                    f"action '{action_id}' is {action['status']}, not approved",
                    "ValidationError",
                )
            finding = _get_finding(conn, action["finding_id"])
            if finding is None:
                return json_error(
                    f"finding '{action['finding_id']}' not found",
                    "NotFoundError",
                )
            _require_control(conn, control_id)
            conn.execute(
                """
                INSERT INTO ssk_evidence
                    (evidence_id, control_id, evidence_type, title, source_kind,
                     source_pointer, source_metadata, produced_at,
                     verification_status, recorded_by, notes)
                VALUES (?, ?, 'finding_closure', ?, 'scan_run',
                        ?, ?, ?, 'unverified', ?, ?)
                """,
                (
                    evidence_id,
                    control_id,
                    evidence_title,
                    source_pointer,
                    json.dumps(
                        {
                            "action_id": action_id,
                            "finding_id": action["finding_id"],
                            "plan_id": action["plan_id"],
                        },
                        separators=(",", ":"),
                        sort_keys=True,
                    ),
                    now,
                    closed_by,
                    notes,
                ),
            )
            conn.execute(
                """
                UPDATE findings
                SET status = 'resolved',
                    closure_evidence_id = ?,
                    notes = COALESCE(?, notes),
                    last_seen = ?
                WHERE finding_id = ?
                """,
                (evidence_id, notes, now, action["finding_id"]),
            )
            conn.execute(
                """
                UPDATE remediation_actions
                SET status = 'closed',
                    closure_evidence_id = ?,
                    closed_by = ?,
                    closed_at = ?,
                    updated_at = ?
                WHERE action_id = ?
                """,
                (evidence_id, closed_by, now, now, action_id),
            )
            _record_event(
                conn,
                "action_closed",
                {
                    "closure_evidence_id": evidence_id,
                    "finding_id": action["finding_id"],
                    "control_id": control_id,
                },
                plan_id=action["plan_id"],
                action_id=action_id,
                actor=closed_by,
            )
            row = _get_action(conn, action_id)
    except UnknownControlError as exc:
        return json_error(str(exc), "UnknownControlError")

    _log_activity(
        "remediation_close_action",
        "success",
        {"action_id": action_id, "closure_evidence_id": evidence_id},
        entity_id=action_id,
    )
    return json_ok(_row_payload(row))
