# ROADMAP.md — MCNA Admin Master Control

## Purpose of this document
Strategic direction for the Admin Master Control project. Read when scoping
new work, when a decision needs to be checked against original intent, or when
a new session needs directional context. Not for routine task execution.

AGENTS.md is operational for Codex. CLAUDE.md is the legacy Claude Code mirror.
CONTEXT.md is architectural. This file is directional.

---

## Governance document layer

The 2026 Security and Governance program has two parallel tracks that complement each other:

**Track A — AMC (this project):** Continuous measurement, live tenant scanning, KB-accumulated findings, evidence production. Machine-sourced. Authoritative on what is actually true in the tenant at scan time.

**Track B — Cowork governance package:** Structured policy and evidence documents produced by Copilot Cowork sessions. Covers Secure SketCH workstreams W1–W6 (inventories, periodic reports, training records, technical configuration evidence, policies, operational plans). Human-authored structure with AI-generated scaffolding. Authoritative on what MCNA has committed to in governance terms.

The relationship:
- Track B documents define the standard and the evidence schema (what *should* be true, what evidence *should* exist).
- Track A produces the live data that validates or invalidates Track B's placeholder statuses.
- The integration point is the evidence write-back layer (see Phase 3, Phase 4 below): KB findings populate Track B workbooks, replacing AI-generated placeholders with verified, timestamped, scan-sourced data.

Track B document location: `02_Policy_and_Standards/Copilot_Cowork_Generated_Materials/` (OneDrive-synced to the MIS SharePoint governance library).

Key Track B workbooks AMC writes to:
- `MIS_Technical_Configuration_Evidence.xlsx` (W4) — per-domain control rows with Covered/Partial/Gap status
- `MIS_Periodic_Reports_Master.xlsx` and standalone report templates (W2) — recurring evidence cadence
- `Security_Evidence_Artifacts.xlsx` (W1) — master control-to-artifact mapping

---

## Project thesis

Dave is overhauling MCNA's information systems governance and security
framework for 2026. The Secure SketCH guidelines (75 controls as of the
2026-04-25 catalog refresh) are the
measuring stick. MCNA's Secure SketCH score is currently high because the
standards and policies are written — maturity level "Implemented." The score
cannot be defended in an audit because there is no evidence or artifact
trail. An auditor asking "prove it" would find a gap on almost every control.

Master Control exists to close that gap. It is an **evidence-producing
governance backend** for the 2026 IT-MIS Security and Governance program.
Its primary job is to:

1. Take continuous measure of MCNA's IT/MIS control state against the Secure
   SketCH catalog.
2. Surface what needs to be overhauled, reconfigured, or newly implemented.
3. Monitor the things that need monitoring.
4. Produce the evidence and artifacts that would satisfy a Secure SketCH audit.

Running as Claude Code with two MCP server layers on Dave's workstation, MC
compounds in value every session. The knowledge base grows. Domain coverage
expands. The control-to-evidence mapping gets more complete. In six months
this becomes something nobody else at MCNA or DIS could reproduce — because
nobody else has the combination of access, context, and institutional
knowledge.

This is not "AI does my admin work." It is a measurement, monitoring, and
evidence layer for a governance program Dave owns personally.

---

## Operating principles (locked)
These are decisions already made. Do not relitigate task by task.

1. **Read before write, always.** First version of any capability is read-only.
   Write scopes get added only after the read version is clean and the use case
   is proven.

2. **Split read and write across separate app registrations.** A cert leak on a
   read-only app reg is an information disclosure incident. A cert leak on a
   write-capable app reg is a tenant-wide change incident. Separate app regs
   bound the blast radius.

3. **Least privilege on every app reg.** Scopes added only when a specific
   capability needs them. No "just in case" scopes.

4. **Application Access Policies are mandatory for mail scopes.** Any app reg
   with Mail.Read or Mail.Send application permissions must be scoped via
   Exchange Application Access Policy before first use.

5. **Certificates, not client secrets.** All app reg auth uses certificates in
   the Windows certificate store. No secrets in .env files or in the project
   folder.

6. **Conditional Access bounds where the app can run from.** App regs should be
   restricted via CA to Dave's managed workstation where possible.

7. **Every operation is logged.** Each tool invocation writes to the KB
   activity_log. Generated reports write to reports/ and sync to SharePoint.

8. **Fail loud.** Silent failures are worse than loud failures. Any tool that
   encounters unexpected state stops and alerts Dave. No silent retries.

9. **Evidence is never duplicated; it is pointed to.** Artifacts that already
   live in SharePoint, OneDrive, or elsewhere in the M365 estate are referenced
   by URL + identifier triple `{site_id, drive_id, item_id}`, not copied into
   the KB. The KB stores structured metadata and a resolvable pointer.

10. **Reviews are append-only attestations.** The `ssk_reviews` ledger is how
    a control moves from "Implemented" to "Regularly Reviewed." Every row is
    an immutable, timestamped attestation that a named reviewer examined a
    named set of evidence on a specific date. No updates to review rows —
    only new ones.

11. **Shadow governance is a known risk, not an accepted one.** This operates
    outside the Copilot governance story by design. Dave owns the decisions and
    the risk. Not a pattern for replication by other MCNA staff without a formal
    governance review.

---

## Design decisions (locked)

### Platform: Codex/Claude Code + two MCP server layers
Decided 2026-04-21. Documented in CONTEXT.md and ARCHITECTURE.md.

### Secure SketCH tracking: Approach A (SQLite-first, conversational-only)
Decided 2026-04-22.

- Control catalog, status, evidence, reviews, and registries live in the
  existing `mcna_amc.db` SQLite KB under `ssk_*` tables.
- All interaction is through MCP tools — no UI, no separate app.
- Audit binders export to `reports/audit-binders/<control-id>/` as
  markdown/HTML and inherit M365 retention + Purview labels automatically via
  OneDrive sync into the governance SharePoint library.
- Evidence that already lives in SharePoint is pointed to, not duplicated.
- Schema is designed so a future migration to SharePoint Lists or Dataverse is
  a mechanical export — the `ssk_*` namespace moves as a unit.

Approaches B (SharePoint Lists for registries) and C (Dataverse-backed)
were considered and rejected for year one as YAGNI. Dave is the sole
operator. Build collaboration surfaces when collaboration is required, not
before.

### Secure SketCH data model (7 tables)
Decided 2026-04-22. Design spec:
`docs/superpowers/specs/2026-04-22-securesketch-tracking-design.md` (pending).

- `ssk_controls` — the catalog (75 rows after the 2026-04-25 refresh)
- `ssk_recommended_actions` — per-action line items under each control
- `ssk_control_status` — current maturity, target maturity, review cadence
- `ssk_evidence` — any record supporting a control (scan output, SharePoint
  pointer, review minutes, attestation, policy link, registry entry)
- `ssk_reviews` — immutable attestation ledger
- `ssk_registries` — generic authoring surface for human records
  (approved software, exceptions, vendor support, policies, NDA ledger, etc.)
- `findings` — existing table, extended with `closure_evidence_id` to link
  finding closure to the evidence that proves it

---

## Build phases

### Phase 1 — Platform foundation (in progress)
**Goal:** MCNA-AMC MCP Server running with core infrastructure and the
highest-value domain scan tools operational.

**Status (2026-04-22):** Partially built. FastMCP scaffold, auth, graph
client, KB schema, and first domain scan tools exist. `entra_scan_app_regs`,
`entra_scan_guests`, `ca_scan_policies`, `ca_scan_coverage_gaps`,
`pp_scan_environments`, `pp_scan_apps` functional. `kb_*` read tools
functional. Server registered in Claude Code MCP settings.
All Phase 1 tools have CONTRIBUTES_TO dicts wired to the ssk_binder.

**Remaining Phase 1 work:**
- Validation that all existing tools write conformant findings to the KB
- Snapshot/diff flow end-to-end tested
- `.env`-free auth validated against new scopes as added

---

### Phase 2 — Secure SketCH alignment layer (COMPLETE 2026-04-22)
**Goal:** Turn AMC into a measurement, monitoring, and evidence-production
layer mapped to the Secure SketCH catalog.

**Deliverables:**
- Catalog import tool (`ssk_import_catalog`) — one-shot parser that reads
  `Secure_SketCH_Guidelines_2026-01-01.docx` and populates `ssk_controls`
  and `ssk_recommended_actions`
- `ssk_*` tables created in `mcna_amc.db`
- MCP tool surface for the SSK layer:
  - `ssk_status` / `ssk_status_all` — current maturity per control
  - `ssk_record_review` — append to the attestation ledger
  - `ssk_link_evidence` — attach evidence records to a control
  - `ssk_list_evidence` — query evidence by control, type, or date
  - `ssk_mark_action` — set implementation_status on a recommended action
  - `ssk_gaps` — roll-up of controls below target maturity
  - `ssk_export_binder` — generate audit binder for a control or family
  - `registry_add` / `registry_list` / `registry_retire` — generic registry CRUD
- First generated audit binder for one control (proof-of-concept end-to-end)
- Finding → control → evidence linkage working: a finding closure writes a
  `finding_closure` evidence row automatically

**Status (2026-04-22): COMPLETE.** All deliverables built across Phase 2a
(catalog import, ssk_* tables, ssk.py tools) and Phase 2b (evidence, reviews,
actions, registries, binder, server registration). 120 tests passing.
All code on main. Branch phase2b-task0-control-map deleted.

**Operational follow-through (2026-04-23):**
- `ssk_evidence` was backfilled from existing artifacts for controls `06-3`,
  `08-1`, `08-2`, `08-6`, `15-3`, and `15-4`.
- Audit binders were regenerated into `reports/audit-binders/2026-04-23-204903/`
  so those controls now render evidence tables instead of empty placeholders.
- `docs/how-to-use-reports.md` was added as the operator guide for report and
  binder usage.
- `ssk_export_binder` was patched so repeated single-control exports into the
  same output directory merge `index.md` and `manifest.json` instead of
  clobbering them.

**Why this is Phase 2:** Without the SSK layer, AMC is a hygiene-scanning
tool. With it, AMC is the governance intelligence layer described in
CONTEXT.md and ARCHITECTURE.md.

---

### Phase 3 — Broad domain coverage feeding the evidence layer (COMPLETE 2026-04-25)
**Goal:** Cover the remaining Microsoft domains, with every new tool
registering itself as an evidence contributor to specific Secure SketCH
controls.

**Status (2026-04-25):** Nine planned work items built or partially implemented and tested (219/219 tests).
`tools/pim.py`, `tools/license.py`, `tools/sharing.py`, `tools/intune.py`,
`tools/purview.py`, `tools/exo.py`, `tools/copilot.py`, and `tools/mail.py`
are built. Sharing posture expansion remains deferred (needs `Sites.FullControl.All`).

**Deliverables:**
- `tools/license.py` — unassigned licenses, duplicate stacking, service plan
  conflicts → evidence for software asset management controls **(BUILT)**
- `tools/pim.py` — privileged role review, permanent vs. eligible **(BUILT)**
- `tools/sharing.py` — site staleness inventory; permission-based external
  sharing checks deferred (need Sites.FullControl.All) **(PARTIAL)**
- `tools/sharing.py` — external sharing posture across SharePoint, OneDrive,
  Teams
- `tools/exo.py` — Exchange hygiene: forwarding rules and shared mailboxes.
  Transport-rule depth still needs EXO PowerShell or a broader Exchange-specific
  approach. **(BUILT + LIVE-SCANNED 2026-04-25)** — 30 shared mailbox
  interactive sign-in findings (High), 1 external forwarding rule (High).
  X.500 false-positive handling was fixed 2026-04-25.
- `tools/intune.py` — device compliance, BitLocker, enrollment posture,
  baseline drift. Feeds asset-management and endpoint controls heavily. **(BUILT 2026-04-23)**
- `tools/purview.py` — sensitivity label coverage, DLP policy inventory,
  audit log queries. Feeds information protection controls. **(BUILT 2026-04-23)**
- `tools/copilot.py` — Copilot license utilization, label coverage
  readiness, oversharing risk **(BUILT 2026-04-25)**
- `tools/mail.py` — sendMail for summaries and alerts (read scopes pre-Phase
  4; send from admin account) **(BUILT 2026-04-25)**

Each domain tool declares which controls it contributes evidence to. The
contribution manifest is read by `ssk_status` to compute coverage.

**Evidence write-back (concept, unfleshed):**
Every domain scan produces KB findings that validate or invalidate rows in
the Track B Cowork workbooks — primarily W4 (`MIS_Technical_Configuration_Evidence.xlsx`)
and W2 periodic report templates. Today this is a manual step (human reads
findings, updates workbook). The natural next capability is an AMC write-back
layer: KB findings → openpyxl → W4/W2 rows updated (Status, Notes, Last
Verified fields) automatically after each scan run. Row matching uses the
control ID columns already present in W4. This closes the loop from live
tenant state to audit-ready evidence doc without manual transcription.
This is a local file write (OneDrive path), not a tenant write — separate
from Phase 4 write scopes. Needs design before build.

---

### Phase 4 — Control coverage, evidence expansion, and remediation closure
**Goal:** Prove control-by-control Secure SketCH coverage, expand real evidence pointers, and convert KB findings into approved remediation plans with closure evidence. Tenant writes remain gated and are not automatic.

**Status (2026-04-26):** Phase 4A-4B coverage/evidence foundation built. The current matrix classifies all 75 controls:
6 evidenced, 69 gaps, 11 controls with mapped automated tools, and 64 controls currently manual/policy evidence required. Latest reports:
`reports/ssk-control-coverage/coverage-2026-04-26.md` and
`reports/ssk-evidence-gaps/gaps-2026-04-26.md`.

The earlier approval/closure foundation also remains built. First operational plan exists for EXO shared mailbox interactive sign-in findings:
`docs/operations/exo-shared-mailbox-remediation-plan.md`.

No tenant remediations are approved or executing. The current mode is evidence coverage, planning, validation, approval queueing, and closure readiness.

**Phase 4A-4B built coverage/evidence layer:**
- `ssk_control_coverage_snapshots` KB table for durable matrix runs
- `mcp-server/tools/ssk_matrix.py` MCP tools for control matrix, gap report, coverage detail, and scan-evidence backfill
- `ssk_coverage()` expanded to include Intune, Purview, EXO, and Copilot automated mappings
- Audit-defensible coverage rule: only active, verified evidence pointers count as evidenced
- No Copilot Cowork workbook write-back and no placeholder evidence rows

**Built foundation:**
- `remediation_plans`, `remediation_actions`, and `remediation_events` KB tables
- `mcp-server/tools/remediation.py` MCP tools for plan/action creation, approval, rejection, queue export, and closure
- finding closure through `ssk_evidence(evidence_type='finding_closure')` plus `findings.closure_evidence_id`

**Requirements before tenant-write build:**
- Phase 2 Secure SketCH layer functional — remediations must be tracked as
  closure evidence against controls, not as blind tenant writes
- MCNA-TenantIntel-Writer app reg created with targeted write scopes
- Approval mechanism defined (CSV queue, Dave edits and approves rows)
- Write operations logged three ways: KB activity_log, `ssk_evidence`
  (type = finding_closure), and SharePoint report
- Every write action gated on explicit Dave approval
- Every write action produces an evidence row linked to the relevant control(s)

**Current Phase 4 operating rule:**
Manual or automated remediation can be planned, but execution requires Dave's explicit approval per batch. Evidence work must use real pointers only. The EXO shared mailbox plan uses four batches: immediate shared/function mailboxes, remaining shared/function mailboxes, former-user validation, and device/automation validation.

---

### Phase 5 — Review cadence and leadership reporting
**Goal:** Make AMC drive the periodic review process, not just record it.

**Deliverables:**
- Scheduled review notifications (controls past `next_review_due`)
- Quarterly governance packet generator (auto-assembled from KB)
- Leadership summary view (maturity dashboard by category)
- Secure SketCH portal submission workflow — re-score with MCNA's current
  evidence trail after each quarterly review

---

## What this project is NOT
- Not a replacement for formal IT governance tooling (CASB, SIEM, GRC platform).
- Not a pattern for other MCNA staff to replicate without review. The shadow
  governance tradeoff is acceptable because Dave owns the decisions. It is not
  acceptable as an unreviewed template.
- Not a production system. It lives on Dave's workstation. Institutional
  knowledge survives in the synced docs. Execution capability does not transfer
  without a new owner taking on the risk posture explicitly.
- Not a Secure SketCH scoring engine. AMC does not compute the MCNA score;
  Secure SketCH does. AMC produces the evidence trail that justifies the score
  and makes it defensible.

---

## Change log
- 2026-04-26 — v4.1 — Phase 4A-4B coverage/evidence foundation built: all 75 controls classified, durable coverage snapshots added, evidence/gap reports generated, and automated coverage expanded to Intune/Purview/EXO/Copilot.
- 2026-04-25 — v4.0 — Phase 4 approval/closure foundation built: remediation plans/actions/events, exported approval queues, and closure evidence linkage without tenant writes.
- 2026-04-25 — v3.9 — Phase 3 marked complete at 9/9 planned work items and 219-test baseline. Phase 4 recast as remediation planning and evidence closure; EXO shared mailbox remediation plan added as first Phase 4 artifact.
- 2026-04-25 — v3.8 — Cross-document alignment pass. Current-state docs now agree on low-token startup, 75-control catalog, 214-test baseline, Phase 3 work-item wording, EXO false-positive fix, and granted vs pending scopes.
- 2026-04-25 — v3.7 — Cleanup pass: stale auth and SSK alias tests fixed, Secure SketCH catalog re-imported from updated docx (75 controls, 728 actions), test-pollution controls 98-1/98-2 removed, Copilot marked built, Phase 3 moved to 8/9 planned work items built or partially implemented.
- 2026-04-25 — v3.6 — Intermediate brain sync: intune.py and purview.py marked built. Superseded by v3.7/v3.8 for current Phase 3 count, test count, and catalog state.
- 2026-04-25 — v3.5 — Governance document layer section added (Track A/B relationship, Cowork package integration, evidence write-back concept). Phase 3 write-back note added.
- 2026-04-25 — v3.4 — Phase 3 EXO live scans complete. `get_app_token()` cert-credentials flow. MailboxSettings.Read application consented. 30 High findings (shared mailbox interactive). False-positive bug in `_is_external()` identified.
- 2026-04-23 — v3.3 — Phase 3 progress noted: pim, license, sharing built
  (149 tests). EXO pivot recorded. Two scope-add candidates documented:
  MailboxSettings.Read, Sites.FullControl.All.
- 2026-04-14 — v1 — Initial roadmap. Eight Plays documented.
- 2026-04-17 — v1.1 — Play 3 (orphaned assets) built.
- 2026-04-17 — v1.2 — Play 3 write phase architecture documented.
- 2026-04-19 — v1.3 — Play 5 (Power Platform hygiene) built.
- 2026-04-21 — v2.0 — Play model retired. Roadmap rewritten around AMC platform
  architecture and domain agent build phases. MCP server approach adopted.
- 2026-04-22 — v3.1 — Phase 2 marked COMPLETE. Phase 1 CONTRIBUTES_TO note
  added. Phase 3 is next.
- 2026-04-22 — v3.2 — Phase 2 branch merge noted. Git hygiene complete.
  .mcp.json and .claude/settings.json committed and pushed to main.
- 2026-04-22 — v3.0 — Project thesis rewritten around Secure SketCH audit
  evidence as the primary product. Phase 2 recast as the Secure SketCH
  alignment layer with the `ssk_*` data model (Approach A). Phase 5 added for
  review cadence and leadership reporting. Operating principles 10 and 11
  added (evidence pointers; immutable review attestations). Phase 1 status
  updated to reflect partial build completion.
