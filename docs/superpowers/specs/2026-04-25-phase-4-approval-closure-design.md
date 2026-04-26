# Phase 4 Approval and Closure Layer Design

## Goal

Build the first Phase 4 capability as an approval and evidence closure layer.
This slice converts open KB findings into explicit, reviewable remediation
actions, records Dave's approval decisions, and closes findings only after
closure evidence exists.

No tenant write operation is part of this design.

## Architecture

The KB remains the source of truth. Markdown and CSV exports are the human
approval surface. MCP tools create, list, approve, reject, export, and close
remediation actions, but they do not call Graph write endpoints or change
tenant state.

The implementation adds two SQLite tables:

- `remediation_plans`: plan-level metadata, such as plan ID, domain, title,
  source artifact, owner, status, and timestamps.
- `remediation_actions`: one row per proposed action, linked to a finding and
  a plan. Each row stores target identity, proposed action, risk notes,
  approval state, approval metadata, closure evidence, and timestamps.

Existing tables stay authoritative for evidence and findings:

- `ssk_evidence` stores closure evidence with `evidence_type='finding_closure'`.
- `findings.closure_evidence_id` links a resolved finding to the closure
  evidence row.
- `activity_log` records every approval-layer operation.

## Approval Model

Approval is row-based, not plan-wide. A plan can contain a mix of pending,
approved, rejected, and closed actions. That matches real remediation work:
low-risk shared mailbox accounts can move first, while device or automation
mailboxes stay pending until validated.

Allowed action statuses:

- `pending`: proposed but not approved.
- `approved`: explicitly approved by Dave for later execution.
- `rejected`: not approved for execution.
- `closed`: verified and linked to closure evidence.

Approval requires:

- action ID
- approver name
- approval note

Rejection requires:

- action ID
- rejected-by name
- rejection reason

Closure requires:

- action ID
- control ID
- evidence title
- evidence source pointer
- evidence notes
- finding ID linked to the action

The closure function creates one `ssk_evidence` row, updates the matching
finding to `resolved`, stores `closure_evidence_id`, and marks the remediation
action `closed`.

## Export Model

The export tool writes a Markdown approval queue under `reports/` by default.
It includes one table row per action with the action ID, finding ID, target,
proposed action, status, risk notes, approval fields, and closure fields.

CSV export can be added in the same tool if the caller requests
`format='csv'`. The first implementation should support Markdown first because
the current EXO remediation worksheet and operations plan are Markdown.

Exports are reports, not source-of-truth files. Editing an exported file does
not mutate the KB. The KB mutates only through MCP tools so approvals and
closures are logged consistently.

## Initial Use Case

The first live consumer is the EXO shared mailbox interactive sign-in plan:

- source worksheet:
  `reports/exo-shared-mailbox-remediation/2026-04-25.md`
- source operations plan:
  `docs/operations/exo-shared-mailbox-remediation-plan.md`
- finding type: `shared_mailbox_interactive`
- domain: `exo`
- expected action: disable Entra sign-in for confirmed shared mailbox accounts
- tenant execution: outside this slice and gated by separate explicit approval

The approval layer should be generic enough for later findings, but the tests
should prove the EXO flow because that is the known Phase 4 entry point.

## MCP Tool Surface

Create `mcp-server/tools/remediation.py` and register these tools in
`mcp-server/server.py`:

- `remediation_create_plan(title, domain, description=None, source_pointer=None, owner='Dave Lafferty')`
- `remediation_add_action(plan_id, finding_id, target_id, target_name, proposed_action, control_id=None, risk_notes=None, batch_name=None)`
- `remediation_list_actions(plan_id=None, status=None, domain=None)`
- `remediation_approve_action(action_id, approved_by, approval_note)`
- `remediation_reject_action(action_id, rejected_by, rejection_reason)`
- `remediation_export_queue(plan_id, output_path=None, format='markdown')`
- `remediation_close_action(action_id, control_id, evidence_title, source_pointer, notes=None, closed_by='Dave Lafferty')`

The tool names use the `remediation_` prefix so Phase 4 stays separate from
domain scanners and from Secure SketCH catalog tools.

## Error Handling

The tools return JSON payloads. Validation errors return JSON objects with
`error` and `error_type`, matching `ssk_common.json_error`.

Required validations:

- missing plan or action returns `NotFoundError`
- invalid status transition returns `ValidationError`
- approving an already closed action returns `ValidationError`
- closing an action that is not approved returns `ValidationError`
- closing an action without a linked finding returns `ValidationError`
- closing an action with an unknown control returns `UnknownControlError`
- unsupported export format returns `ValidationError`

Graph 401/403 handling is not relevant in this slice because no Graph write or
read call is made.

## Testing

Use TDD and the existing temp SQLite test fixture.

Tests must cover:

- database schema includes the two remediation tables
- plan creation logs activity
- action creation links to an existing finding
- approval records approver, note, timestamp, and activity log
- rejection records reason and activity log
- invalid close before approval is rejected
- close creates `ssk_evidence(type='finding_closure')`
- close resolves the finding and stores `closure_evidence_id`
- export writes a Markdown queue with action IDs and approval fields
- server registration exposes the remediation tools

The full suite remains the verification gate:

```powershell
rtk python -m pytest --tb=short -q
```

## Non-Goals

- No Graph writes.
- No Entra account disable operation.
- No automatic execution from approved rows.
- No parsing edited CSV or Markdown approval files back into the KB.
- No scheduled jobs.
- No tenant remediation batching engine.

Those belong after the approval and closure evidence contract is working.
