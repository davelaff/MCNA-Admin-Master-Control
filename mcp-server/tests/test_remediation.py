import json
from pathlib import Path

from db import get_connection
from tools.remediation import (
    remediation_add_action,
    remediation_approve_action,
    remediation_close_action,
    remediation_create_plan,
    remediation_export_queue,
    remediation_list_actions,
    remediation_reject_action,
)


def _insert_finding(finding_id="f1", domain="exo", control_id="08-2"):
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO findings
                (finding_id, domain, object_type, object_id, object_name,
                 finding_type, severity, securesketch_control, recommended_action,
                 status, first_seen, last_seen)
            VALUES (?, ?, 'mailbox', 'obj1', 'Shared Mailbox',
                    'shared_mailbox_interactive', 'High', ?, 'Disable sign-in',
                    'open', '2026-01-01', '2026-01-01')
            """,
            (finding_id, domain, control_id),
        )


def _seed_control(control_id="08-2"):
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO ssk_controls
                (control_id, source_version, category, category_name, title,
                 overview, imported_at)
            VALUES (?, '2026-01-01', '08', 'Access Control',
                    'Privileged access', 'Test control', '2026-01-01')
            """,
            (control_id,),
        )


def _create_plan_and_action():
    _insert_finding()
    plan = json.loads(remediation_create_plan(
        title="EXO shared mailbox sign-in cleanup",
        domain="exo",
        description="Disable direct sign-in on confirmed shared mailboxes.",
        source_pointer="docs/operations/exo-shared-mailbox-remediation-plan.md",
    ))
    action = json.loads(remediation_add_action(
        plan_id=plan["plan_id"],
        finding_id="f1",
        target_id="obj1",
        target_name="Shared Mailbox",
        proposed_action="Disable Entra account sign-in",
        control_id="08-2",
        risk_notes="Low dependency shared mailbox",
        batch_name="Batch 1",
    ))
    return plan, action


def test_remediation_create_plan_logs_activity_and_event(db):
    result = json.loads(remediation_create_plan(
        title="EXO shared mailbox sign-in cleanup",
        domain="exo",
        source_pointer="docs/operations/exo-shared-mailbox-remediation-plan.md",
    ))

    assert result["title"] == "EXO shared mailbox sign-in cleanup"
    assert result["domain"] == "exo"
    assert result["status"] == "open"

    with get_connection() as conn:
        activity = conn.execute(
            "SELECT tool_name, outcome, entity_id FROM activity_log WHERE entity_id = ?",
            (result["plan_id"],),
        ).fetchone()
        event = conn.execute(
            "SELECT event_type, plan_id FROM remediation_events WHERE plan_id = ?",
            (result["plan_id"],),
        ).fetchone()

    assert activity["tool_name"] == "remediation_create_plan"
    assert activity["outcome"] == "success"
    assert event["event_type"] == "plan_created"


def test_remediation_add_action_links_existing_finding(db):
    _insert_finding()
    plan = json.loads(remediation_create_plan("EXO cleanup", "exo"))

    result = json.loads(remediation_add_action(
        plan_id=plan["plan_id"],
        finding_id="f1",
        target_id="obj1",
        target_name="Shared Mailbox",
        proposed_action="Disable Entra account sign-in",
        control_id="08-2",
    ))

    assert result["finding_id"] == "f1"
    assert result["status"] == "pending"
    assert result["target_name"] == "Shared Mailbox"


def test_remediation_add_action_rejects_missing_finding(db):
    plan = json.loads(remediation_create_plan("EXO cleanup", "exo"))

    result = json.loads(remediation_add_action(
        plan_id=plan["plan_id"],
        finding_id="missing",
        target_id="obj1",
        target_name="Shared Mailbox",
        proposed_action="Disable Entra account sign-in",
    ))

    assert result["error_type"] == "NotFoundError"


def test_remediation_add_action_rejects_duplicate_finding_in_plan(db):
    _insert_finding()
    plan = json.loads(remediation_create_plan("EXO cleanup", "exo"))
    kwargs = {
        "plan_id": plan["plan_id"],
        "finding_id": "f1",
        "target_id": "obj1",
        "target_name": "Shared Mailbox",
        "proposed_action": "Disable Entra account sign-in",
    }
    remediation_add_action(**kwargs)

    result = json.loads(remediation_add_action(**kwargs))

    assert result["error_type"] == "ValidationError"


def test_remediation_approve_action_records_approval(db):
    _, action = _create_plan_and_action()

    result = json.loads(remediation_approve_action(
        action_id=action["action_id"],
        approved_by="Dave Lafferty",
        approval_note="Approved Batch 1.",
    ))

    assert result["status"] == "approved"
    assert result["approved_by"] == "Dave Lafferty"
    assert result["approval_note"] == "Approved Batch 1."


def test_remediation_reject_action_records_reason(db):
    _, action = _create_plan_and_action()

    result = json.loads(remediation_reject_action(
        action_id=action["action_id"],
        rejected_by="Dave Lafferty",
        rejection_reason="Keep enabled for device validation.",
    ))

    assert result["status"] == "rejected"
    assert result["rejected_by"] == "Dave Lafferty"
    assert result["rejection_reason"] == "Keep enabled for device validation."


def test_remediation_list_actions_filters_by_status_and_domain(db):
    _create_plan_and_action()

    result = json.loads(remediation_list_actions(status="pending", domain="exo"))

    assert len(result) == 1
    assert result[0]["domain"] == "exo"
    assert result[0]["status"] == "pending"


def test_remediation_export_queue_writes_markdown(tmp_path, db):
    plan, action = _create_plan_and_action()
    output = tmp_path / "queue.md"

    result = json.loads(remediation_export_queue(
        plan_id=plan["plan_id"],
        output_path=str(output),
    ))

    text = Path(result["output_path"]).read_text(encoding="utf-8")
    assert result["format"] == "markdown"
    assert action["action_id"] in text
    assert "Approval Note" in text
    assert "Disable Entra account sign-in" in text


def test_remediation_close_action_requires_approval(db):
    _seed_control()
    _, action = _create_plan_and_action()

    result = json.loads(remediation_close_action(
        action_id=action["action_id"],
        control_id="08-2",
        evidence_title="EXO shared mailbox sign-in disabled",
        source_pointer="activity_log:scan-run-1",
    ))

    assert result["error_type"] == "ValidationError"


def test_remediation_close_action_creates_evidence_and_resolves_finding(db):
    _seed_control()
    _, action = _create_plan_and_action()
    remediation_approve_action(action["action_id"], "Dave Lafferty", "Approved Batch 1.")

    result = json.loads(remediation_close_action(
        action_id=action["action_id"],
        control_id="08-2",
        evidence_title="EXO shared mailbox sign-in disabled",
        source_pointer="activity_log:scan-run-1",
        notes="Post-scan confirmed accountEnabled=false.",
        closed_by="Dave Lafferty",
    ))

    assert result["status"] == "closed"
    assert result["closure_evidence_id"]

    with get_connection() as conn:
        evidence = conn.execute(
            "SELECT evidence_type, source_pointer, notes FROM ssk_evidence WHERE evidence_id = ?",
            (result["closure_evidence_id"],),
        ).fetchone()
        finding = conn.execute(
            "SELECT status, closure_evidence_id FROM findings WHERE finding_id = 'f1'",
        ).fetchone()

    assert evidence["evidence_type"] == "finding_closure"
    assert evidence["source_pointer"] == "activity_log:scan-run-1"
    assert "accountEnabled=false" in evidence["notes"]
    assert finding["status"] == "resolved"
    assert finding["closure_evidence_id"] == result["closure_evidence_id"]


def test_remediation_tools_registered_in_server():
    import server
    import tools.remediation as remediation

    assert server.remediation_create_plan is remediation.remediation_create_plan
    assert server.remediation_add_action is remediation.remediation_add_action
    assert server.remediation_close_action is remediation.remediation_close_action
