# START_HERE.md - MCNA Admin Master Control

## Purpose

Use this file as the low-token startup point for new sessions.

This repo is Dave Lafferty's Admin Master Control workspace: a Microsoft estate
orchestration and governance platform for NOF Metal Coatings North America.
Master Control runs as Codex/Claude Code plus MCP server tools.

## Startup Rule

Fresh sessions should read only:

1. `AGENTS.md`
2. `START_HERE.md`
3. Last 40 lines of `activity-log.md`

Do not read the full brain stack unless the task needs it.

Read these only on demand:

- `MEMORY.md` - current-state details, prior decisions, unresolved findings
- `CONTEXT.md` - short architecture orientation
- `ARCHITECTURE.md` - schema, MCP server, and domain-agent design details
- `ROADMAP.md` - strategic direction and phase history
- `CLAUDE.md` - legacy Claude Code operational brain; mostly mirrors `AGENTS.md`

## Hard Rules

- Read-only by default. Writes require an explicit request.
- Use `rtk` for terminal commands.
- This folder is OneDrive-synced governance content. No scratch files left behind.
- Fail loud. Do not hide auth/API failures or empty results that should not be empty.
- If Graph returns 401/403, stop and tell Dave. Do not keep retrying.
- Every task that produces an artifact appends one line to `activity-log.md`:
  `YYYY-MM-DD HH:MM — {task name} — {outcome} — {artifact path}`
- Domain-first, not task-first. Use established domain boundaries.
- Shared schemas before new fields. Findings should conform to `ARCHITECTURE.md`.
- Do not suggest EXO ApplicationImpersonation. It is deprecated.

## Current State

As of 2026-04-25:

- Phase 3 is 9 of 9 planned work items built or partially implemented.
- Final Phase 3 domain `mcp-server/tools/mail.py` is built and registered.
- Full test suite last verified from `mcp-server/`: `rtk python -m pytest --tb=short -q` -> 231 passed.
- Phase 4 approval/closure foundation is built: remediation plans, actions, events, approval queue export, and closure evidence linkage.
- No tenant remediations are approved or executing.
- Secure SketCH catalog repaired/re-imported from `Secure_SketCH_Guidelines_2026-01-01.docx`.
- Catalog state: 75 real controls, 728 recommended actions, `02-3` and `02-4` present, no `98-*` test controls.
- KB open findings: 8 Critical, 123 High, 18 Medium, 1 Low.

Implemented Phase 3 coverage:

- `pim.py`
- `license.py`
- `sharing.py` (site staleness built; permission-based sharing expansion deferred)
- `intune.py`
- `purview.py`
- `exo.py`
- `copilot.py`
- `mail.py`

## Active Operational Items

- 30 open High EXO findings: `shared_mailbox_interactive`.
  - Remediation worksheet: `reports/exo-shared-mailbox-remediation/2026-04-25.md`
  - Execution plan: `docs/operations/exo-shared-mailbox-remediation-plan.md`
  - Approval tooling: `mcp-server/tools/remediation.py`
  - Current decision: document and stage only; no tenant action yet.
- 1 open High EXO finding: `external_forwarding_rule` on `bstraka@nofmetalcoatings.us` to `4402269019@vtext.com`; likely intentional SMS gateway, undocumented.
- 40 open High Entra findings: `missing_owner`.
- 22 open High PIM findings: `permanent_privileged_assignment`.
- Purview label scan needs `InformationProtectionPolicy.Read.All`; without it, `purview_scope_gap` is expected.
- Copilot settings scan needs `Microsoft365CopilotSettings.Read.All`; without it, settings scope gap is expected.

## Best Next Moves

If Dave gives no specific task, recommend one of these before changing files:

1. Seed the EXO shared mailbox remediation plan into the new approval queue; do not execute tenant changes.
2. bstraka SMS forwarding decision: accept/document risk or remove rule.
3. Validate EXO shared mailbox remediation batches with owners; do not execute changes without explicit approval.
4. Run Purview live scans after consenting `InformationProtectionPolicy.Read.All`.
5. Expand Secure SketCH evidence coverage for `02-3`, `02-4`, `07-2`, `06-1`, and `16-1`.

## Brain Update Check

Run this before every final response:

1. If any artifact changed, append one line to `activity-log.md`.
2. Update `START_HERE.md` only if first-screen startup facts changed.
3. Update `MEMORY.md` only if future sessions would waste time rediscovering the fact.
4. Update `ARCHITECTURE.md` only if design, schema, auth model, MCP layers, or domain boundaries changed.
5. Update `ROADMAP.md` only if priorities, phases, or strategic direction changed.
6. If unsure, leave the big brain files alone and use `activity-log.md`.

Final answers should include a short receipt:

```text
Brain update: activity-log only.
```

or:

```text
Brain update: activity-log + MEMORY.md.
```

## `mail.py` Current Scope

v1 is intentionally narrow:

- Tool: `mail_send_summary(to, subject, body, cc=None, importance="normal", save_to_sent_items=True, dry_run=True)`
- Use delegated admin-account Graph `/me/sendMail`.
- `dry_run=True` by default.
- Actual send requires `dry_run=False` and non-empty recipient, subject, and body.
- Log every attempted send to KB `activity_log` with outcome `dry_run`, `sent`, or `failed`.
- Return JSON with recipients, subject, dry_run, sent status, and Graph error detail if failed.
- Tests first, follow existing domain patterns, register in `server.py`.
- Do not add mailbox automation or broader mail read/write behavior unless Dave explicitly asks.

## Fresh-Session Prompt

```text
Start in C:\Users\dlafferty.MCNA\OneDrive - NOF\DL OneDrive\OneDrive - NOF\Management Information Systems - Governance and Security Project 2026\MCNA-Admin-Master-Control.

Read AGENTS.md, START_HERE.md, and the last 40 lines of activity-log.md.
Do not read MEMORY.md, CONTEXT.md, ROADMAP.md, ARCHITECTURE.md, or CLAUDE.md unless the task requires them.
Use rtk for terminal commands.
Then tell me the current state and recommend the next move before changing anything.
```
