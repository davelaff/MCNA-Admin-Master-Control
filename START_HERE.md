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

As of 2026-04-27:

- Phase 3 is 9 of 9 planned work items built or partially implemented.
- Final Phase 3 domain `mcp-server/tools/mail.py` is built and registered.
- Full test suite last verified from `mcp-server/`: `rtk python -m pytest --tb=short -q` -> 271 passed.
- Phase 4 approval/closure foundation is built: remediation plans, actions, events, approval queue export, and closure evidence linkage.
- Phase 4A-4B coverage/evidence foundation is built: control matrix, evidence gap report, scan-evidence backfill tool, and durable coverage snapshots.
- Phase 5 kicked off: review cadence and leadership reporting tools built and registered.
- Tenant remediations executed 2026-04-26: 7 abandoned Entra app regs deleted; Workflow cert finding closed as false positive (Power Platform system app, PP suppression added to scanner).
- Secure SketCH catalog repaired/re-imported from `Secure_SketCH_Guidelines_2026-01-01.docx`.
- Catalog state: 75 real controls, 728 recommended actions, `02-3` and `02-4` present, no `98-*` test controls.
- Audit-defensible evidence coverage: 75 of 75 controls evidenced; 0 gaps remain. 27 policy docs created under `docs/policies/` on 2026-04-26 to close all 49 manual_required gaps.
- Automated tool mapping coverage: 11 of 75 controls have mapped domain tools.
- Latest matrix report: `reports/ssk-control-coverage/coverage-2026-04-26.md`.
- Latest gap report: `reports/ssk-evidence-gaps/gaps-2026-04-26.md`.
- Latest full audit binder: `reports/audit-binders/2026-04-26/`.
- KB open findings: 0 Critical, ~113 High (10 MIS acknowledged, bstraka resolved), 18 Medium, 1 Low.

Implemented Phase 3 coverage:

- `pim.py`
- `license.py`
- `sharing.py` (site staleness built; permission-based sharing expansion deferred)
- `intune.py`
- `purview.py`
- `exo.py`
- `copilot.py`
- `mail.py`

Implemented Phase 5 tools (COMPLETE as of 2026-04-29):

- `ssk_due` — controls past or approaching `next_review_due`; `include_never_reviewed` param added
- `ssk_review_notifications` — scheduled review digest generator with optional `mail_send_summary` dry-run/send handoff
- `ssk_maturity_dashboard` — per-category maturity rollup (review status, evidence coverage, maturity levels)
- `ssk_quarterly_packet` — auto-assembled quarterly governance review packet
- `ssk_portal_submission_packet` — Secure SketCH portal re-score submission packet generator; markdown + JSON per control family at `reports/ssk-submissions/<quarter>/`
- Live Q2 2026 packet: `reports/governance-packets/2026-Q2.md`
- Review batches recorded (never-reviewed queue: 75 → 0):
  - Batch 1 (2026-04-27): families `08`, `09`, `14`, `19`, control `15-3`
  - Batch 2 (2026-04-29): families `01`, `02`, `03`, `04` — all `ok`; memos at `docs/reviews/2026-04-29-ssk-review-batch-2.md`
  - Batch 3 (2026-04-29): families `05`, `10`, `11`, `12`, `13` → `ok`; families `06`, `07` → `action_required` (license/Purview findings, JWEDGE-2018 encryption gap); memo at `docs/reviews/2026-04-29-ssk-review-batch-3.md`
  - Batch 4 (2026-04-29): controls `15-1`, `15-2`, `15-4`, families `16`, `17`, `18`, `20` → all `ok`; memo at `docs/reviews/2026-04-29-ssk-review-batch-4.md`
  - Remaining never-reviewed: 0. All 75 Secure SketCH controls now have an initial review record.
- Test count: 284/284 passing

## Active Operational Items

- 30 open High EXO findings: `shared_mailbox_interactive`.
  - Remediation worksheet: `reports/exo-shared-mailbox-remediation/2026-04-25.md`
  - Execution plan: `docs/operations/exo-shared-mailbox-remediation-plan.md`
  - Approval tooling: `mcp-server/tools/remediation.py`
  - Approval queue: `reports/remediation-queues/exo-shared-mailbox-interactive-sign-in-2026-04-25.md`
  - Batch 1 execution packet: `reports/remediation-queues/exo-shared-mailbox-batch-1-execution-2026-04-29.md`
  - KB remediation plan: `d5d91bf4-9ca7-49cd-98b7-d2ea0e11e8d9`, 30 pending actions
  - Current decision: document and stage only; no tenant action yet.
- 1 EXO finding `external_forwarding_rule` on `bstraka@nofmetalcoatings.us` → `4402269019@vtext.com` (Verizon SMS): resolved 2026-04-26 as intentional SMS gateway, documented.
- Entra app registration ownership cleanup changed materially on 2026-04-29:
  - `entra_scan_app_regs` was corrected to hydrate owners from Graph before evaluating `missing_owner`
  - live post-fix scan reduced the real active `missing_owner` set to 7 items
  - Dave assigned owners to the 4 MCNA-owned apps that still lacked owners: `CopilotGraphConnector`, `CI Project Tracker`, `PowerBI-Usage-Reader`, `P2P Server`
  - `MCNA_GPT` was deleted as dead/unused; do not rotate its secret
  - the 3 remaining non-MCNA identities from the corrected scan are suppression/routing items, not owner-assignment work: `Report Message`, `MessageCenterFeedBot`, `ConnectSyncProvisioning_MCNA-DC_04a43dcfcd20`
- PIM triage 2026-04-26 (pending follow-up next week):
  - `cloudadmin@nofmetalcoatings.us` — unknown owner, App Admin + Cloud App Admin, created 2026-03-12, signed in once, never again. Waiting on DIS (Nate/Tony) to confirm if break-glass.
  - Diana Kochever — keeps existing admin roles; no remediation needed.
  - `admin@nofmetalcoatings.us` — confirmed break-glass. Acknowledge when ready.
  - DIS Global Admin (`dis@nofmetalcoatings.us`) — permanent Global Admin on non-dedicated account. Decision: have DIS repurpose the existing account into a dedicated admin-only identity (`DIS Admin`, no mailbox/general routing, MFA enforced, privileged use only). Dave emailed Nate Whitelaw on 2026-04-27 and is waiting on written confirmation before verification/closure.
  - MIS service account — 10 findings acknowledged as intentional.
  - Your own roles + PowerBI service principals — structural (no P2); acknowledge when ready.
- Purview label scan: `InformationProtectionPolicy.Read.All` consented 2026-04-26. A real `Public` sensitivity label and published policy now exist in the tenant. Live `purview_scan_labels` still returns `available:false`, but now correctly reports dual 403 Microsoft-Azure-Application-Gateway blocks on both the org-wide and `/me` sensitivity-label endpoints. This is a scanner-access/platform issue, not evidence that labels are absent. Full label taxonomy (Public / Internal / Confidential / Highly Confidential) still to be designed and published org-wide once the platform path is usable.
- Copilot settings scan: fixed 2026-04-26. Uses `CopilotSettings-LimitedMode.Read` via `/copilot/admin/settings/limitedMode` (v1.0). Last run returned `available:true`, 0 findings.

## DIS Privileged Access Decision

DIS privileged access will run through `dis@nofmetalcoatings.us` repurposed as an admin-only identity.

Required characteristics:

- Account: `dis@nofmetalcoatings.us`
- Purpose: dedicated DIS admin-only account
- No mailbox or general mail-routing behavior
- MFA enforced with strong, independent authentication
- Display name: `DIS Admin` or similar
- Used only for privileged actions in the MCNA tenant

Ownership:

- DIS executes the change
- Dave verifies after completion

Completion criteria:

- DIS confirms the change in writing by email reply
- Global Admin remains assigned only after the account is admin-only
- Evidence captured: account properties screenshot/export, role assignment evidence, and Nate confirmation
- Re-run `pim_scan_role_assignments` after completion and attach the result
- Findings `b41b2c01` and `9ca3da77` remain open until Dave verifies

## Best Next Moves

If Dave gives no specific task, recommend one of these before changing files:

1. **Open MS support ticket** for Purview Graph API (`GET /beta/security/informationProtection/sensitivityLabels` returning 403 from Azure App Gateway for 3+ days post-label-publish). Details in `docs/governance/scope-additions/pending-gaps.md`. Once resolved: design and publish full label taxonomy (Public / Internal / Confidential / Highly Confidential).
2. **EXO shared mailbox Batch 1 approval** — execution packet ready for the first 8 low-risk disables at `reports/remediation-queues/exo-shared-mailbox-batch-1-execution-2026-04-29.md`. Remaining queue stays at `reports/remediation-queues/exo-shared-mailbox-interactive-sign-in-2026-04-25.md`.
3. Follow up with DIS on `cloudadmin@nofmetalcoatings.us` — disable if not a break-glass account.
4. After Diana Kochever meeting — remove excess roles (Teams Admin, Exchange Admin), close PIM findings.
5. Wait for Nate Whitelaw to confirm `dis@nofmetalcoatings.us` repurpose in writing, then verify account properties and re-run `pim_scan_role_assignments` before closing `b41b2c01` and `9ca3da77`.
6. Acknowledge remaining structural PIM findings (admin@ break-glass, Dave's own roles, PowerBI SPNs).
7. Revisit control `15-3` after the Copilot settings scope gap is resolved so family `15` can be fully promoted from mixed status.

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
