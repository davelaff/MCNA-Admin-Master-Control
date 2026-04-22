# ROADMAP.md — MCNA Admin Master Control

## Purpose of this document
Strategic direction for the Admin Master Control project. Read when scoping
new work, when a decision needs to be checked against original intent, or when
a new session needs directional context. Not for routine task execution.

CLAUDE.md is operational. CONTEXT.md is architectural. This file is directional.

---

## Project thesis

Dave is overhauling MCNA's information systems governance and security
framework for 2026. The Secure SketCH guidelines (76 controls) are the
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

### Platform: Claude Code + two MCP server layers
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

- `ssk_controls` — the catalog (76 rows after import)
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

**Remaining Phase 1 work:**
- Validation that all existing tools write conformant findings to the KB
- Snapshot/diff flow end-to-end tested
- `.env`-free auth validated against new scopes as added

---

### Phase 2 — Secure SketCH alignment layer (next)
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

**Why this is Phase 2:** Without the SSK layer, AMC is a hygiene-scanning
tool. With it, AMC is the governance intelligence layer described in
CONTEXT.md and ARCHITECTURE.md.

---

### Phase 3 — Broad domain coverage feeding the evidence layer
**Goal:** Cover the remaining Microsoft domains, with every new tool
registering itself as an evidence contributor to specific Secure SketCH
controls.

**Deliverables:**
- `tools/license.py` — unassigned licenses, duplicate stacking, service plan
  conflicts → evidence for software asset management controls
- `tools/pim.py` — privileged role review, permanent vs. eligible
- `tools/sharing.py` — external sharing posture across SharePoint, OneDrive,
  Teams
- `tools/exo.py` — Exchange hygiene: forwarding rules, shared mailboxes,
  transport rules
- `tools/intune.py` — device compliance, BitLocker, enrollment posture,
  baseline drift. Feeds asset-management and endpoint controls heavily.
- `tools/purview.py` — sensitivity label coverage, DLP policy inventory,
  audit log queries. Feeds information protection controls.
- `tools/copilot.py` — Copilot license utilization, label coverage
  readiness, oversharing risk
- `tools/mail.py` — sendMail for summaries and alerts (read scopes pre-Phase
  4; send from admin account)

Each domain tool declares which controls it contributes evidence to. The
contribution manifest is read by `ssk_status` to compute coverage.

---

### Phase 4 — Write phase
**Goal:** Execute approved remediations via a separate write-capable app reg.

**Status:** Architecture designed (see MEMORY.md). Not yet approved for build.

**Requirements before build:**
- Phase 2 Secure SketCH layer functional — remediations must be tracked as
  closure evidence against controls, not as blind tenant writes
- MCNA-TenantIntel-Writer app reg created with targeted write scopes
- Approval mechanism defined (CSV queue, Dave edits and approves rows)
- Write operations logged three ways: KB activity_log, `ssk_evidence`
  (type = finding_closure), and SharePoint report
- Every write action gated on explicit Dave approval
- Every write action produces an evidence row linked to the relevant control(s)

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
- 2026-04-14 — v1 — Initial roadmap. Eight Plays documented.
- 2026-04-17 — v1.1 — Play 3 (orphaned assets) built.
- 2026-04-17 — v1.2 — Play 3 write phase architecture documented.
- 2026-04-19 — v1.3 — Play 5 (Power Platform hygiene) built.
- 2026-04-21 — v2.0 — Play model retired. Roadmap rewritten around AMC platform
  architecture and domain agent build phases. MCP server approach adopted.
- 2026-04-22 — v3.0 — Project thesis rewritten around Secure SketCH audit
  evidence as the primary product. Phase 2 recast as the Secure SketCH
  alignment layer with the `ssk_*` data model (Approach A). Phase 5 added for
  review cadence and leadership reporting. Operating principles 10 and 11
  added (evidence pointers; immutable review attestations). Phase 1 status
  updated to reflect partial build completion.
