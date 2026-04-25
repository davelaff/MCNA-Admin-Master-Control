# MEMORY.md — MCNA Admin Master Control
Version: v22 | Updated: 2026-04-23

## Purpose of this file

Living handoff + project-state file.

Use to understand:
- architectural decisions made and why
- what repo contains
- truth about auth, scope, open items
- what fresh session shouldn't rediscover

Read once at project startup.
After: `CONTEXT.md` governs architecture, `CLAUDE.md` governs operational behavior, `ROADMAP.md` for direction and history.

---

## ▶ Next session startup prompt

Read first. Everything below is reference; this is what to do next.

**Where we left off (2026-04-23 session, auth/graph hardening):**
Auth and Graph client hardened. `refresh_auth.py` created as standalone re-auth script. `auth.py` now raises RuntimeError instead of blocking on device code flow inline — MCP tools no longer hang waiting for device code input. `graph_batch()` added to graph.py. EXO still best next live-scan candidate.

**EXO domain (2026-04-23 built):**
- `exo_scan_mailboxes`: detects shared mailboxes with interactive sign-in enabled (High → 08-1). Uses `userPurpose` from `/users/{id}/mailboxSettings`.
- `exo_scan_forwarding`: scans inbox message rules for external forwarding/redirect (High → 06-1). Detects both `forwardTo` and `redirectTo` actions.
- Scope: `MailboxSettings.Read` delegated. Consented 2026-04-23.
- INTERNAL_DOMAINS: `nofmetalcoatings.us`, `nofmetalcoatings.onmicrosoft.com`.
- Graceful 404 (no mailbox, skip) vs 403 (scope gap, emit finding once) handling.
- 19 tests, 201/201 total.

**Purview domain (built in prior session — MEMORY was stale):**
- `purview_scan_labels` + `purview_scan_audit` built, tested, committed. 13 tests.
- Needs `InformationProtectionPolicy.Read.All` for label scan. Not yet consented — will emit `purview_scope_gap` Medium finding if run without it.
- Audit scan uses `AuditLog.Read.All` (already consented).

**Evidence + binder work completed (2026-04-23 built):**
- `ssk_evidence` populated with 15 verified `scan_snapshot` rows from existing artifacts.
- Controls now carrying evidence: `06-3`, `08-1`, `08-2`, `08-6`, `15-3`, `15-4`.
- Refreshed binder set: `reports/audit-binders/2026-04-23-204903/`.
- New operator guide: `docs/how-to-use-reports.md`.
- `ssk_export_binder` fixed so repeated single-control exports into the same `output_dir` merge `index.md` and `manifest.json` instead of clobbering them.
- Regression coverage added in `mcp-server/tests/test_ssk_binder.py`; binder test file passes `15/15` when run with `--basetemp` outside the blocked default Windows temp path.

**Recommended first move next session — pick one:**

1. **Run EXO live scans** — `exo_scan_mailboxes` + `exo_scan_forwarding`. MCP restart required first.
2. **Run Purview live scans** — consent `InformationProtectionPolicy.Read.All` first or accept scope gap finding.
3. **Expand evidence coverage** — add current artifacts for `07-2`, `06-1`, `16-1`, then regenerate their binders.
4. **Triage high-severity findings** — 22 permanent privileged assignments, 9 non-admin privileged role holders.

**Default if no preference:** run EXO live scans (domain just built, scope consented, ready to go).

**Mechanical reminders:**
- `.rtk/` and `CLAUDE.md` (rtk-section edit) intentionally uncommitted. Leave unless adding to .gitignore.
- Binder output dirs from 2026-04-23: `reports/audit-binders/2026-04-23/` (08-6), `2026-04-23-142332/` (06-3), `2026-04-23-142541/` (08-1), `2026-04-23-204903/` (06-3, 08-1, 08-2, 08-6, 15-3, 15-4). Keep for reference.
- MCP server restart required when new tools are added to server.py.
- Token cache expired → run `python mcp-server/refresh_auth.py` (standalone, does device code flow). Do NOT edit auth.py to put device code flow back inline.

---

## Current architectural position

Master Control: Microsoft estate orchestration and governance platform. Agents are domain authorities, not single-purpose scanners.

**Platform decision (2026-04-21):** Claude Code IS Master Control. Domain agent capabilities via two MCP server layers:

1. **Microsoft MCP Server for Enterprise** (hosted, Microsoft-managed, public preview)
   - Remote MCP server: `https://mcp.svc.cloud.microsoft/enterprise`
   - Entra ID read-only: users, groups, apps, devices, directory, admin reporting
   - Authenticates via Dave's Entra admin account through Claude Code OAuth flow
   - No code to write. Configure in Claude Code MCP settings.
   - App ID for Graph activity log filtering: `e8c77dc2-69b3-43f4-bc51-3213c9d915b4`

2. **MCNA-AMC MCP Server** (local Python, `mcp-server/`)
   - All domains not covered by Microsoft's server + local KB
   - Auth: MSAL device code flow with cached tokens
   - App reg: MCNA-TenantIntel-ReadOnly (see docs/auth/app-registrations.md)
   - KB: SQLite at `mcp-server/kb/mcna_amc.db` (OneDrive-synced)
   - **PARTIALLY BUILT** — FastMCP scaffold, auth, graph client, KB schema, first domain scan tools functional. See Build status below.

Old "Play" model retired. Existing Play scripts in `archive/`.

**Project purpose decision (2026-04-22):** AMC's primary product is **audit-ready Secure SketCH evidence**, not tenant hygiene. MCNA score is high (policies written, maturity "Implemented") but no evidence trail. AMC closes that gap. See ROADMAP.md v3.0 thesis.

**SSK tracking layer design (2026-04-22):** Approach A chosen — SQLite-first, conversational-only, migration-ready. 7 new tables in `ssk_*` namespace, ~17 MCP tools, audit binder exports as markdown per control.
Spec: `docs/superpowers/specs/2026-04-22-securesketch-tracking-design.md`.

---

## Repo contents (as of 2026-04-23)

Core docs:
- `CLAUDE.md` — operational brain
- `CONTEXT.md` — short architecture orientation
- `ARCHITECTURE.md` — full AMC design reference
- `MEMORY.md` — this file
- `ROADMAP.md` — strategic direction
- `README.md` — 5-line orientation
- `activity-log.md` — append-only task log
- `Secure_SketCH_Guidelines_2026-01-01.docx` — compliance target (binary, not git-tracked)
- `.mcp.json` — Claude Code MCP server config (tracked in git)
- `.claude/settings.json` — Claude Code workspace settings (tracked in git)

Auth and docs:
- `docs/auth/app-registrations.md` — app reg record (moved from `auth/`)
- `docs/how-to-use-reports.md` — operator guide for scan reports and audit binders
- `docs/superpowers/specs/` — design specs
- `docs/superpowers/plans/` — implementation plans

Build artifact:
- `mcp-server/` — MCNA-AMC MCP Server (Phase 1+2 complete, Phase 3 in progress, 201 tests passing)

Reports (historical scan outputs, still valid reference):
- `reports/app-reg-governance/` — 2026-04-17, 2026-04-20
- `reports/audit-binders/` — refreshed multi-control binder set at `2026-04-23-204903/`
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
- `tools/entra.py` — `entra_scan_app_regs`, `entra_scan_guests` verified working against live tenant (2026-04-22: 40 apps, 49 findings)
- `tools/ca.py` — `ca_scan_policies`, `ca_scan_coverage_gaps`
- `tools/pp.py` — `pp_scan_environments`, `pp_scan_apps`
- `tools/kb.py` — `kb_get_findings`, `kb_get_snapshot`, `kb_diff_snapshot`, `kb_update_finding`, `kb_dismiss`
- MCP server registered in Claude Code (commit 8d07819)

Outstanding Phase 1 work: validation all tool outputs are schema-conformant, snapshot/diff end-to-end testing.

### Phase 2a — COMPLETE (2026-04-22)

Design spec: `docs/superpowers/specs/2026-04-22-securesketch-tracking-design.md`
Implementation plan: `docs/superpowers/plans/2026-04-22-amc-phase2a-catalog-import.md`

Built and functional:
- DB schema: 7 `ssk_*` tables (controls, history, categories, recommended_actions, control_status, evidence, reviews) + actions + registries
- `tools/ssk_control_map.py` — alias normalization (canonical_control_id)
- `tools/ssk_parser.py` — docx catalog parser
- `tools/ssk_loader.py` — catalog import with idempotent upsert
- `tools/ssk.py` — ssk_import_catalog, ssk_get_control, ssk_list_controls, ssk_family_summary, ssk_search_controls
- `kb/ssk_control_aliases.json` — alias map
- `kb/catalog-imports/2026-01-01.json` — first import snapshot
- 105 tests passing (commit 32e2427)

### Phase 2b — COMPLETE (2026-04-22)

Scope: Evidence, reviews, action tracking, registries, audit binder, tool registration. All tools registered in server.py, 120/120 tests verified.

Built and functional:
- `tools/ssk_common.py` — json_ok, json_error, utc_now, shared helpers
- `tools/ssk_evidence.py` — ssk_link_evidence, ssk_list_evidence, ssk_evidence_expiring, ssk_verify_pointers
- `tools/ssk_reviews.py` — ssk_record_review, ssk_review_history, ssk_alerts, ssk_due
- `tools/ssk_actions.py` — ssk_mark_action, ssk_action_queue
- `tools/ssk_registry.py` — registry_add, registry_list, registry_get, registry_retire
- `tools/ssk_binder.py` — ssk_coverage, ssk_export_binder (markdown per-control, index.md, manifest.json)
- `tools/entra.py`, `ca.py`, `pp.py` — CONTRIBUTES_TO dicts wired to ssk_binder
- `server.py` — all 16 Phase 2b tools registered with FastMCP
- `tests/test_ssk.py` — end-to-end integration test (import → link → review → export)
- 120 tests passing, on main (branch phase2b-task0-control-map deleted)

### Phase 3 — in progress (2026-04-22/23)

Goal: broad domain coverage feeding SSK evidence layer. Every new domain tool wires CONTRIBUTES_TO to specific Secure SketCH controls.

Built:
- `tools/pim.py` — `pim_scan_role_assignments`, `pim_scan_role_definitions`.
  Detects permanent privileged assignments, privileged roles on non-admin UPNs (no `nof-` prefix), long-standing eligible assignments (>90d), unused custom roles, P2-licensing gap. Graceful fallback to `/roleAssignments` when `roleAssignmentSchedules` returns 400 (no P2).
  Uses `RoleManagement.Read.Directory` (already consented). Wired to 08-3 (access privilege) and 08-6 (privileged account process). 13 tests, 133/133 total.

**Confirmed tenant reality (2026-04-22 live scan):**
- No Azure AD Premium P2. P1 via SPB (Business Premium) only.
- PIM unavailable. All 45 active role assignments permanent.
- 22 permanent assignments on privileged roles (High).
- 9 privileged roles on non-`nof-` accounts: `admin@`, `cloudadmin@`, `MIS@`, `DIS Computers`, plus enterprise apps (Power BI Service, PowerBI-Usage-Reader). admin@ and cloudadmin@ pending owner confirmation.
- 0 custom role definitions. `blynn@` open item was false alarm — resolved.

- `tools/license.py` — `license_scan_skus`, `license_scan_users`.
  Flags over-consumed SKUs (High→06-3), unused prepaid SKUs (Low→06-3), productivity-SKU stacking (Medium→06-3), licensed-but-disabled accounts (Medium→08-1). Uses existing Directory.Read.All. 10 new tests, 143/143 total. Live findings: ATA (unused), 6 stacking, 3 disabled-with-licenses.

- `tools/sharing.py` — `sharing_scan_sites`. Enumerates /sites, flags stale (>365d, Medium) and very-stale (>730d, High). Wired to 15-4. 6 new tests, 149/149 total. Live: 29 sites, 17 very-stale, 5 stale — ~7 active.

- `tools/intune.py` — `intune_scan_devices`, `intune_scan_compliance_policies`. Device compliance (High→INTUNE-NONCOMPLIANT-01→07-2), stale device (Low→INTUNE-STALE-01→06-2), encryption gap (High→INTUNE-ENCRYPT-01→07-2), scope/no-policies findings (Medium/High→INTUNE-SCOPE-01/NOPOL-01→07-2). Both scopes consented 2026-04-23. Live: 1 device (JWEDGE-2018, not encrypted), 1 compliance policy. 20 new tests, 169/169 total.

- `tools/purview.py` — `purview_scan_labels`, `purview_scan_audit`. Label coverage (High→PURVIEW-LABEL-01→06-1), audit log activity check (High→PURVIEW-AUDIT-01→16-1), scope gap (Medium→PURVIEW-SCOPE-01→06-1). Needs `InformationProtectionPolicy.Read.All` for label scan (not yet consented). Audit scan uses existing `AuditLog.Read.All`. 13 tests, 182/182 total.

- `tools/exo.py` — `exo_scan_mailboxes`, `exo_scan_forwarding`. Shared mailbox interactive login (High→EXO-SHARED-ENABLED-01→08-1), external forwarding/redirect rules (High→EXO-FORWARD-01→06-1), scope-gap detection (Medium→EXO-SCOPE-01→08-1 when permission is missing). Scopes: `MailboxSettings.Read` delegated (consented 2026-04-23) + `MailboxSettings.Read` application (consented 2026-04-24). Application permission enables full cross-user mailbox scans via cert-based client credentials flow (`get_app_token()` in auth.py). 19 tests, 201/201 total.

  **First live scan (2026-04-25):**
  - `exo_scan_mailboxes`: 187 users, 82 user mailboxes, 68 shared, 8 resource. **30 shared mailboxes with interactive sign-in enabled (High)**. Full list in KB findings.
  - `exo_scan_forwarding`: 187 users, 441 rules scanned. **2 external forwarding rules flagged**: (1) bstraka@nofmetalcoatings.us → 4402269019@vtext.com (SMS gateway, likely intentional, undocumented); (2) wstark@nofmetalcoatings.us → X.500 legacy Exchange DNs — **false positive**, internal recipients expressed as `/o=ExchangeLabs/...` DNs.
  - **Known bug:** `_is_external()` returns True for X.500 addresses (no `@` sign → full string returned → not in INTERNAL_DOMAINS). Fix: skip or classify addresses without `@` as non-external. Walt Stark finding should be dismissed after fix.
  - Stale `exo_scope_gap` finding in KB (from before app token added) — needs `kb_dismiss`.

**Auth/graph hardening (2026-04-23):**
- `mcp-server/auth.py` — `get_token()` no longer blocks on device code flow inline. Raises RuntimeError with instructions to run `refresh_auth.py`. Prevents MCP server from hanging on expired cache.
- `mcp-server/graph.py` — `graph_batch()` added. Auto-chunks up to 20 requests per `/$batch` call, returns `{request_id: {status, body}}`. 401/403 still raises GraphError.
- `mcp-server/refresh_auth.py` — new standalone script. Runs device code flow, writes updated token cache. Run from repo root: `python mcp-server/refresh_auth.py`.

**EXO application token (2026-04-24):**
- `mcp-server/auth.py` — `get_app_token()` added. Cert-based client credentials flow using `cryptography` (pkcs12) + MSAL `ConfidentialClientApplication`. Loads PFX, computes SHA1 thumbprint, acquires token for client. Used by EXO scans for cross-user mailbox coverage.
- `MailboxSettings.Read` application permission added to MCNA-TenantIntel-ReadOnly, admin consent granted 2026-04-24. Recorded in `docs/auth/app-registrations.md` v1.6 and `docs/governance/scope-additions/2026-04-24-exo-application-scope.md`.

**Binder smell-test — PASSED (2026-04-23):**
- `ssk_coverage`: 7/73 automated, 66 uncovered.
- Findings route correctly via alias map: 08-6 (29 High pim findings), 06-3 (7 medium/low license findings), 08-1 (3 disabled-account findings via LIC-DISABLED-01 → 08-1 alias at render time).
- Evidence/reviews sections empty (expected). Actions all not_started (accurate).
- Same-day collision handling works: timestamped suffix dirs created.
- No bugs. Pipeline sound.

**Evidence backfill + binder refresh (2026-04-23):**
- `ssk_evidence` now populated for six controls from existing local artifacts; all 15 pointers resolved cleanly.
- Refreshed binder set at `reports/audit-binders/2026-04-23-204903/` now shows populated evidence tables for `06-3`, `08-1`, `08-2`, `08-6`, `15-3`, `15-4`.
- `ssk_export_binder` patched so repeated single-control exports into the same directory merge `index.md` and `manifest.json` instead of overwriting them.
- Binder regression test added and verified with `python -m pytest mcp-server/tests/test_ssk_binder.py -q --basetemp C:\Users\dlafferty.MCNA\codex-pytest-base` → 15 passed.

**Scope gaps surfaced during Phase 3:**
- EXO transport-rule/deeper Exchange admin coverage still needs EXO PowerShell or a broader Exchange-specific approach. `exo.py` mailboxSettings-based scans are built and unblocked with `MailboxSettings.Read`.
- Sharing permission findings (external sharing, guest site access) need `Sites.FullControl.All`. `/sites/{id}/permissions` returns 403 with current Sites.Read.All. Deferred.
- Intune scopes now consented: `DeviceManagementManagedDevices.Read.All` + `DeviceManagementConfiguration.Read.All` (2026-04-23).
- Purview needs `InformationProtectionPolicy.Read.All` — not yet in app reg.

Next candidates (priority order): fix `_is_external()` X.500 false-positive bug, dismiss stale EXO scope-gap finding, remediate 30 shared mailbox interactive-sign-in findings, then `purview`, `copilot`, `mail`.

**Python environment:** Python 3.14.2, `mcp` 1.26.0, `python-docx` installed.

---

## MCNA-AMC MCP Server — domain tool surface

Thirteen primary domains planned for v1, plus local support surfaces:

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

Existing (Phase 1) — five tables in `mcp-server/kb/mcna_amc.db`:

- **`tenant_snapshot`** — one row per entity, JSON properties blob, `last_scanned` timestamp
- **`findings`** — flagged items: entity type/ID, SecureSketCH control, severity, status (open/acknowledged/resolved), first/last seen
- **`baselines`** — known-good state for drift detection
- **`dismissed`** — accepted-risk items with reason and date
- **`activity_log`** — every tool invocation: timestamp, tool, entity, outcome

Built (Phase 2) — 7 new tables + 1 new column:

- **`ssk_controls`** — Secure SketCH catalog (73 controls after import)
- **`ssk_controls_history`** — superseded control rows after re-import
- **`ssk_categories`** — small lookup (category → name, ~10-20 rows)
- **`ssk_recommended_actions`** — per-action checklist rows (flat, ~600 rows)
- **`ssk_control_status`** — MCNA's current position per control
- **`ssk_evidence`** — any record supporting control (scan outputs, SharePoint pointers, reviews, attestations, policy links, registry entries)
- **`ssk_reviews`** — append-only attestation ledger
- **`ssk_registries`** — generic human-authored records (approved_software, exceptions, vendor_support, policies, nda_ledger, approved_browsers, ...)
- **`findings.closure_evidence_id`** — new column linking resolved findings to evidence row proving closure

---

## Authentication and identity realities

### Accounts in use

- Admin account: `nof-dlafferty@nofmetalcoatings.us`
  Cache: `C:/Users/dlafferty.MCNA/.msal_token_cache_admin.json`
  Used for: sendMail, admin-scoped Graph queries

- Primary account: `dlafferty@nofmetalcoatings.us`
  Cache: `C:/Users/dlafferty.MCNA/.msal_token_cache_primary.json`
  Used for: primary mailbox read, Power Platform queries

ApplicationImpersonation deprecated in EXO 2026 — do not suggest.

### App registration

- `MCNA-TenantIntel-ReadOnly` — public client, delegated + application perms
- Certificate: MCNA-TenantIntel-Planner, expires 2028-04-16
  PFX at `C:\Users\dlafferty.MCNA\mcna-tenantintel-planner.pfx`
- .env: `C:\Users\dlafferty.MCNA\mcna-tenantintel.env`
- Current scopes in `docs/auth/app-registrations.md`
- `MCNA-TenantIntel-Writer` (write-capable reg): designed, not yet created

### Governance paper trail outstanding

IT-GOV-ENTRA-v1.0 requires documented request records for scope additions.

Documented in repo:
- 2026-04-16 initial registration record exists in `docs/governance/scope-additions/2026-04-16-initial-registration.md`
- 2026-04-20 Power Platform scope record exists in `docs/governance/scope-additions/2026-04-20-power-platform.md`

Still outstanding:
- Newer 2026-04-22/23 additions and consent outcomes should be written up as dated records
- `docs/governance/scope-additions/pending-gaps.md` and `docs/auth/app-registrations.md` should be reconciled with current consent state

---

## OneDrive / SharePoint sync reality

Repo syncs to M365 Security and Governance library in MIS SharePoint site. Outputs become organizational content with version history and retention. `.env` and cert files live outside synced repo intentionally.

---

## Open items

### CA policy and Entra identity (sessions 4-5, 2026-04-17)
- Awaiting Tony response on 4 CA policy gaps (legacy auth, admin policy, service accounts, MCNA break-glass)
- Identify owner of admin@nofmetalcoatings.us before touching
- Confirm cloudadmin@nofmetalcoatings.us ownership
- Decision: when to disable Security Defaults and enable CA policies
- RESOLVED 2026-04-22: blynn@nofmetalcoatings.us is Barry Lynn (regular user). Role GUID d24aef57-1500-4070-84db-2666f29cf966 is built-in "Modern Commerce User" role (isBuiltIn=true), not custom. Benign — commerce billing role. Confirmed via pim_scan_role_definitions.

### Entra role remediation (session 5 — mostly complete)
- DONE: dlafferty@ daily driver cleaned — roles moved to nof-dlafferty@
- DONE: nof-scala@ — removed Fabric Administrator, Power Platform Administrator
- DONE: MIS@ — role count reduced per governance review
- IN PROGRESS: nof-dkochever@ — User Admin and Teams Admin removed. Exchange Administrator on hold. Key question: is Diana actively managing shared mailboxes or DLs? If no, remove Exchange Administrator.

### Infrastructure
- Governance paper trail for scope additions (see above)
- MCNA-TenantIntel-Writer app reg: designed, not yet created
- activity-log.md line 4 has encoding corruption (em-dashes as â€"). Historical, low priority. All future writes via MCP FileSystem tool, not PowerShell.

### VS Code tooling
- Windows MCP Server (sbroenne.windows-mcp) requires .NET 10 Windows Desktop Runtime. Fixed 2026-04-17. If it breaks after extension update, check runtime version first.

---

## Things NOT to assume
- Dave doesn't use Obsidian.
- Dave is technical and global admin. Don't explain Graph, Entra, M365 basics unless asked.
- ApplicationImpersonation can't be used — deprecated. Don't suggest.
- Project is Dave's personal workbench, not MCNA-wide deployment template without formal governance review.

---

## Change log
- 2026-04-25 — v23 — EXO first live scans. `get_app_token()` added to auth.py (cert/client-credentials). MailboxSettings.Read application consented 2026-04-24. exo_scan_mailboxes: 187 users, 30 shared mailboxes interactive (High). exo_scan_forwarding: 441 rules, 1 real external fwd (bstraka→SMS), 1 false positive (wstark X.500 legacy DN). Bug identified: `_is_external()` misclassifies X.500 addresses. Stale scope-gap finding needs dismissal.
- 2026-04-23 — v22 — Auth/graph hardening. `auth.py` raises RuntimeError on expired cache instead of blocking on inline device code flow. `graph_batch()` added to graph.py. `refresh_auth.py` created as standalone re-auth script. Claude memory dir MEMORY.md rebuilt.
- 2026-04-23 — v21 — Evidence/binder session. Backfilled `ssk_evidence` for six controls, regenerated binders in `reports/audit-binders/2026-04-23-204903/`, added `docs/how-to-use-reports.md`, and fixed `ssk_export_binder` so repeated single-control exports no longer clobber `index.md` and `manifest.json`.
- 2026-04-23 — v20 — MEMORY cleanup pass. Removed stray tool artifact, reconciled EXO status/scope text, updated repo snapshot date and test count, clarified governance paper-trail status, and clarified domain-count wording.
- 2026-04-23 — v19 — EXO domain built (exo_scan_mailboxes, exo_scan_forwarding). MailboxSettings.Read consented. 19 tests, 201/201. Purview domain (built in earlier session) noted as stale in MEMORY — corrected. Startup prompt updated.
- 2026-04-23 — v18 — Intune live scan session. Both scopes consented, bug fixed, two High findings (incomplete_enrollment, encryption_not_enabled on JWEDGE-2018), stale scope-gap finding dismissed. Startup prompt updated for purview.py as next task.
- 2026-04-23 — v15 — End-of-day handoff for 2026-04-22 session. Phase 3 three domains complete on main: pim (133), license (143), sharing (149 tests). 64 governance findings written to KB. Scope gaps documented: MailboxSettings.Read for exo, Sites.FullControl.All for sharing permissions. Startup prompt added.
- 2026-04-22 — v14 — Phase 3 begun. tools/pim.py built, CONTRIBUTES_TO wired to 08-3/08-6, 11 new tests (131/131 passing). No new scope required.
- 2026-04-22 — v13 — Git hygiene complete. Branch phase2b-task0-control-map deleted, stale worktrees pruned. .mcp.json and .claude/settings.json committed and pushed.
- 2026-04-22 — v12 — Phase 2b complete. Evidence, reviews, actions, registries, binder tools built, tested (120/120), registered in server.py. CONTRIBUTES_TO wired across entra/ca/pp tools.
- 2026-04-22 — v11 — Phase 2 SSK tracking layer designed (Approach A). Spec committed. ROADMAP v3.0 reframed around audit evidence as primary product.
- 2026-04-14 — v1 — Initial handoff.
- 2026-04-16 — v2 — Full rebuild after build session.
- 2026-04-17 — v3 — Session 2 and 3 summaries. Auth/scope additions.
- 2026-04-17 — v4 — CA policy and Entra role audit session notes.
- 2026-04-17 — v5 — Windows MCP Server .NET dependency note.
- 2026-04-17 — v6 — app_reg_scanner.py built. Entra role remediation status.
- 2026-04-17 — v7 — Play 3 built. Sites.Read.All, Tasks.Read.All added. Cert replaced. QMS site remediated. Write phase deferred.
- 2026-04-20 — v8 — ARCHITECTURE.md and CONTEXT.md added. Play 5 built. Power Platform scopes granted. AMC direction established.
- 2026-04-21 — v10 — Build status section added. Phase 1 plan ready.
- 2026-04-21 — v9 — Platform decision: Claude Code as AMC + MCP server layers. Play model retired. Repo cleaned. MCNA-AMC MCP Server defined (not yet built).
