# MEMORY.md — MCNA Admin Master Control
Version: v13 | Updated: 2026-04-22

## Purpose of this file

Living handoff and project-state file.

Use it to understand:
- what architectural decisions have been made and why
- what the repo currently contains
- what is true right now about auth, scope, and open items
- what a fresh session should not have to rediscover

Read this once at project startup.
After that: `CONTEXT.md` governs architecture, `CLAUDE.md` governs operational
behavior, `ROADMAP.md` is for direction and history.

---

## Current architectural position

Master Control is a Microsoft estate orchestration and governance platform.
Its agents are domain authorities, not single-purpose scanners.

**Platform decision (2026-04-21):** Claude Code IS Master Control. Domain agent
capabilities are delivered via two MCP server layers:

1. **Microsoft MCP Server for Enterprise** (hosted, Microsoft-managed, public preview)
   - Remote MCP server: `https://mcp.svc.cloud.microsoft/enterprise`
   - Entra ID read-only: users, groups, apps, devices, directory, admin reporting
   - Authenticates via Dave's Entra admin account through Claude Code's OAuth flow
   - No code to write. Configure in Claude Code MCP settings.
   - App ID for Graph activity log filtering: `e8c77dc2-69b3-43f4-bc51-3213c9d915b4`

2. **MCNA-AMC MCP Server** (local Python, `mcp-server/`)
   - All domains not covered by Microsoft's server + local knowledge base
   - Auth: MSAL device code flow with cached tokens (existing pattern)
   - App reg: MCNA-TenantIntel-ReadOnly (see docs/auth/app-registrations.md)
   - KB: SQLite at `mcp-server/kb/mcna_amc.db` (OneDrive-synced)
   - **PARTIALLY BUILT** — FastMCP scaffold, auth, graph client, KB schema,
     and first domain scan tools are functional. See Build status below.

The old "Play" model is retired. Existing Play scripts are in `archive/`.

**Project purpose decision (2026-04-22):** AMC's primary product is
**audit-ready Secure SketCH evidence**, not tenant hygiene. MCNA's score
is high because policies are written (maturity "Implemented") but has no
evidence trail. AMC exists to close that gap. See ROADMAP.md v3.0 thesis.

**SSK tracking layer design (2026-04-22):** Approach A chosen — SQLite-first,
conversational-only, migration-ready. 7 new tables in `ssk_*` namespace,
~17 MCP tools, audit binder exports as markdown files per control.
Spec: `docs/superpowers/specs/2026-04-22-securesketch-tracking-design.md`.

---

## Repo contents (as of 2026-04-21)

Core docs:
- `CLAUDE.md` — operational brain
- `CONTEXT.md` — short architecture orientation
- `ARCHITECTURE.md` — full AMC design reference
- `MEMORY.md` — this file
- `ROADMAP.md` — strategic direction
- `README.md` — 5-line orientation
- `activity-log.md` — append-only task log
- `Secure_SketCH_Guidelines_2026-01-01.docx` — compliance target (binary, not git-tracked)
- `.mcp.json` — Claude Code MCP server configuration (tracked in git)
- `.claude/settings.json` — Claude Code workspace settings (tracked in git)

Auth and docs:
- `docs/auth/app-registrations.md` — app reg record (moved from `auth/`)
- `docs/superpowers/specs/` — design specs
- `docs/superpowers/plans/` — implementation plans

Build artifact:
- `mcp-server/` — MCNA-AMC MCP Server (Phase 1+2 complete, 120 tests passing)

Reports (historical scan outputs, still valid reference):
- `reports/app-reg-governance/` — 2026-04-17, 2026-04-20
- `reports/orphaned-assets/` — 2026-04-17, 2026-04-20
- `reports/power-platform-hygiene/` — 2026-04-20
- `reports/secure-score/` — empty

Archive (reference implementations, session artifacts):
- `archive/*.py` — old Play scripts (useful as Graph query reference)
- `archive/tasks/` — old Play task specs
- `archive/dis-log/` — old DIS mail log
- `archive/AGENTS.md` — old duplicate brain file
- `archive/SESSION_HANDOFF_*.md` — old session handoffs
- `archive/handoff-CA-policy-2026-04-17.md` — CA policy session notes

---

## Build status

### Phase 1 — partially complete (2026-04-22)

Design spec: `docs/superpowers/specs/2026-04-21-admin-master-control-design.md`
Implementation plan: `docs/superpowers/plans/2026-04-21-amc-phase1.md`

Built and functional:
- `mcp-server/` scaffold (Task 1)
- `mcp-server/db.py` KB schema (Task 2)
- `mcp-server/auth.py` MSAL auth (Task 3)
- `mcp-server/graph.py` HTTP client (Task 4)
- `tools/entra.py` — `entra_scan_app_regs`, `entra_scan_guests` verified
  working against live tenant (2026-04-22 run: 40 apps, 49 findings)
- `tools/ca.py` — `ca_scan_policies`, `ca_scan_coverage_gaps`
- `tools/pp.py` — `pp_scan_environments`, `pp_scan_apps`
- `tools/kb.py` — `kb_get_findings`, `kb_get_snapshot`, `kb_diff_snapshot`,
  `kb_update_finding`, `kb_dismiss`
- MCP server registered in Claude Code (commit 8d07819)

Outstanding Phase 1 work: validation that all tool outputs are schema-conformant,
snapshot/diff end-to-end testing.

### Phase 2a — COMPLETE (2026-04-22)

Design spec: `docs/superpowers/specs/2026-04-22-securesketch-tracking-design.md`
Implementation plan: `docs/superpowers/plans/2026-04-22-amc-phase2a-catalog-import.md`

Built and functional:
- DB schema: 7 `ssk_*` tables (controls, history, categories, recommended_actions,
  control_status, evidence, reviews) + actions + registries
- `tools/ssk_control_map.py` — alias normalization (canonical_control_id)
- `tools/ssk_parser.py` — docx catalog parser
- `tools/ssk_loader.py` — catalog import with idempotent upsert
- `tools/ssk.py` — ssk_import_catalog, ssk_get_control, ssk_list_controls,
  ssk_family_summary, ssk_search_controls
- `kb/ssk_control_aliases.json` — alias map
- `kb/catalog-imports/2026-01-01.json` — first import snapshot
- 105 tests passing (commit 32e2427)

### Phase 2b — COMPLETE (2026-04-22)

Scope: Evidence, reviews, action tracking, registries, audit binder, and tool
registration. All tools registered in server.py and verified 120/120 tests.

Built and functional:
- `tools/ssk_common.py` — json_ok, json_error, utc_now, shared helpers
- `tools/ssk_evidence.py` — ssk_link_evidence, ssk_list_evidence,
  ssk_evidence_expiring, ssk_verify_pointers
- `tools/ssk_reviews.py` — ssk_record_review, ssk_review_history, ssk_alerts, ssk_due
- `tools/ssk_actions.py` — ssk_mark_action, ssk_action_queue
- `tools/ssk_registry.py` — registry_add, registry_list, registry_get, registry_retire
- `tools/ssk_binder.py` — ssk_coverage, ssk_export_binder (markdown per-control,
  index.md, manifest.json)
- `tools/entra.py`, `ca.py`, `pp.py` — CONTRIBUTES_TO dicts wired to ssk_binder
- `server.py` — all 16 Phase 2b tools registered with FastMCP
- `tests/test_ssk.py` — end-to-end integration test (import → link → review → export)
- 120 tests passing, on main (branch phase2b-task0-control-map deleted)

**Next:** Phase 3 — live Graph evidence ingestion.

**Python environment:** Python 3.14.2, `mcp` 1.26.0, `python-docx` installed.

---

## MCNA-AMC MCP Server — domain tool surface

Thirteen domains planned for v1:

| Prefix | Domain | Primary Graph endpoints |
|---|---|---|
| `pp_*` | Power Platform | BAP, Dataverse, PAD |
| `entra_*` | Entra governance (gaps + future writes) | /applications, /servicePrincipals, /users |
| `ca_*` | Conditional Access | /identity/conditionalAccess/policies |
| `exo_*` | Exchange hygiene | /users/{id}/mailboxSettings, /admin/serviceAnnouncement |
| `license_*` | Licensing | /subscribedSkus, /users/{id}/licenseDetails |
| `pim_*` | Privileged Identity Management | /roleManagement/directory |
| `sharing_*` | External sharing posture | /sites, /drives |
| `compliance_*` | SecureSketCH mapping, Secure Score | /security/secureScores |
| `mail_*` | Send summary emails | /me/sendMail |
| `intune_*` | Device and endpoint governance | /deviceManagement |
| `copilot_*` | Copilot readiness and governance | /reports, /sites (label coverage) |
| `purview_*` | Sensitivity labels, DLP, audit | /security/informationProtection, /auditLogs |
| `kb_*` | Knowledge base (SQLite) | local only |
| `ssk_*` | Secure SketCH tracking | local only |
| `registry_*` | Generic human-authored record registries | local only |

---

## Knowledge base schema

Existing (Phase 1, built) — five tables in `mcp-server/kb/mcna_amc.db`:

- **`tenant_snapshot`** — one row per entity, JSON properties blob, `last_scanned` timestamp
- **`findings`** — flagged items: entity type/ID, SecureSketCH control, severity, status (open/acknowledged/resolved), first/last seen
- **`baselines`** — known-good state for drift detection
- **`dismissed`** — accepted-risk items with reason and date
- **`activity_log`** — every tool invocation: timestamp, tool, entity, outcome

Built (Phase 2, complete) — 7 new tables + 1 new column:

- **`ssk_controls`** — the Secure SketCH catalog (73 controls after import)
- **`ssk_controls_history`** — superseded control rows after re-import
- **`ssk_categories`** — small lookup (category → name, ~10-20 rows)
- **`ssk_recommended_actions`** — per-action checklist rows (flat, ~600 rows)
- **`ssk_control_status`** — MCNA's current position per control
- **`ssk_evidence`** — any record supporting a control (scan outputs,
  SharePoint pointers, reviews, attestations, policy links, registry entries)
- **`ssk_reviews`** — append-only attestation ledger
- **`ssk_registries`** — generic human-authored records (approved_software,
  exceptions, vendor_support, policies, nda_ledger, approved_browsers, ...)
- **`findings.closure_evidence_id`** — new column linking resolved findings
  to the evidence row that proves closure

---

## Authentication and identity realities

### Accounts in use

- Admin account: `nof-dlafferty@nofmetalcoatings.us`
  Cache: `C:/Users/dlafferty.MCNA/.msal_token_cache_admin.json`
  Used for: sendMail, admin-scoped Graph queries

- Primary account: `dlafferty@nofmetalcoatings.us`
  Cache: `C:/Users/dlafferty.MCNA/.msal_token_cache_primary.json`
  Used for: primary mailbox read, Power Platform queries

ApplicationImpersonation is deprecated in EXO 2026 — do not suggest it.

### App registration

- `MCNA-TenantIntel-ReadOnly` — public client, delegated + application perms
- Certificate: MCNA-TenantIntel-Planner, expires 2028-04-16
  PFX at `C:\Users\dlafferty.MCNA\mcna-tenantintel-planner.pfx`
- .env: `C:\Users\dlafferty.MCNA\mcna-tenantintel.env`
- Current scopes documented in `docs/auth/app-registrations.md`
- `MCNA-TenantIntel-Writer` (write-capable reg): designed, not yet created

### Governance paper trail outstanding

IT-GOV-ENTRA-v1.0 requires a documented request record for scope additions:
- 2026-04-16: Application.Read.All, AuditLog.Read.All, Directory.Read.All,
  Policy.Read.All, Reports.Read.All, RoleManagement.Read.Directory
- 2026-04-17: Sites.Read.All (delegated), Tasks.Read.All (application)
Dave self-approves as IS Director but the paper trail has not been written.

---

## OneDrive / SharePoint sync reality

This repo syncs to the M365 Security and Governance library in the MIS SharePoint
site. Outputs become organizational content with version history and retention.
The `.env` and cert files live outside the synced repo intentionally.

---

## Open items

### CA policy and Entra identity (from sessions 4-5, 2026-04-17)
- Awaiting Tony response on 4 CA policy gaps (legacy auth, admin policy,
  service accounts, MCNA break-glass)
- Identify owner of admin@nofmetalcoatings.us before touching it
- Confirm cloudadmin@nofmetalcoatings.us ownership
- Decision: when to disable Security Defaults and enable CA policies
- blynn@nofmetalcoatings.us: holds custom role GUID
  d24aef57-1500-4070-84db-2666f29cf966. Unknown identity and purpose.
  Needs investigation before touching.

### Entra role remediation (session 5 — mostly complete)
- DONE: dlafferty@ daily driver cleaned — roles moved to nof-dlafferty@
- DONE: nof-scala@ — removed Fabric Administrator, Power Platform Administrator
- DONE: MIS@ — role count reduced from 24 per governance review
- IN PROGRESS: nof-dkochever@ — User Admin and Teams Admin removed.
  Exchange Administrator on hold. Key question: is Diana actively managing
  shared mailboxes or DLs? If no ongoing use case, remove Exchange Administrator.

### Infrastructure
- Governance paper trail for scope additions (see above)
- MCNA-TenantIntel-Writer app reg: architecture designed, not yet created
- activity-log.md line 4 has encoding corruption (em-dashes as â€"). Historical,
  low priority. All future writes via MCP FileSystem tool, not PowerShell.

### VS Code tooling
- Windows MCP Server (sbroenne.windows-mcp) requires .NET 10 Windows Desktop
  Runtime. Fixed 2026-04-17. If it breaks after an extension update, check the
  runtime version requirement first.

---

## Things NOT to assume
- Dave does not use Obsidian.
- Dave is already technical and already a global admin. Do not explain basic
  Graph, Entra, or M365 concepts unless he asks.
- ApplicationImpersonation cannot be used — deprecated. Do not suggest it.
- This project is Dave's personal workbench, not a template for MCNA-wide
  deployment without a formal governance review.

---

## Change log
- 2026-04-22 — v13 — Git hygiene complete. Branch phase2b-task0-control-map deleted,
  stale worktrees pruned. .mcp.json and .claude/settings.json committed and pushed.
  Repo contents, build status, domain tool table, and KB schema sections updated.
- 2026-04-22 — v12 — Phase 2b complete. Evidence, reviews, actions, registries, and
  audit binder tools built, tested (120/120), and registered in server.py.
  CONTRIBUTES_TO wired across entra/ca/pp scan tools. Branch phase2b-task0-control-map
  merged to main and deleted.
- 2026-04-22 — v11 — Phase 2 Secure SketCH tracking layer designed (Approach A).
  Spec committed. ROADMAP v3.0 reframed around audit evidence as primary product.
  Phase 1 status corrected to reflect partial completion (scan tools working
  against live tenant). Domain tool surface extended with `ssk_*` and
  `registry_*` namespaces. KB schema extended with 7 new tables.
- 2026-04-14 — v1 — Initial handoff.
- 2026-04-16 — v2 — Full rebuild after build session.
- 2026-04-17 — v3 — Session 2 and 3 summaries. Auth/scope additions.
- 2026-04-17 — v4 — CA policy and Entra role audit session notes.
- 2026-04-17 — v5 — Windows MCP Server .NET dependency note.
- 2026-04-17 — v6 — app_reg_scanner.py built. Entra role remediation status.
- 2026-04-17 — v7 — Play 3 built. Sites.Read.All, Tasks.Read.All added.
  Cert replaced. QMS site remediated. Write phase deferred.
- 2026-04-20 — v8 — ARCHITECTURE.md and CONTEXT.md added. Play 5 built.
  Power Platform scopes granted. AMC direction established.
- 2026-04-21 — v10 — Build status section added. Phase 1 plan ready for execution.
- 2026-04-21 — v9 — Platform decision: Claude Code as AMC + MCP server layers.
  Play model retired. Repo cleaned: Play scripts, task specs, session handoffs,
  AGENTS.md, dis-log, queries moved to archive/. auth/ moved to docs/auth/.
  MCNA-AMC MCP Server defined (not yet built). Domain tool surface and KB
  schema documented.
