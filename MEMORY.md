# MEMORY.md — MCNA Admin Master Control
Version: v9 | Updated: 2026-04-21

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
   - **NOT YET BUILT** — this is the primary next build task

The old "Play" model is retired. Existing Play scripts are in `archive/`.

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

Auth and docs:
- `docs/auth/app-registrations.md` — app reg record (moved from `auth/`)
- `docs/superpowers/specs/` — design specs
- `docs/superpowers/plans/` — implementation plans

Build artifact (not yet built):
- `mcp-server/` — MCNA-AMC MCP Server

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

---

## Knowledge base schema

Five tables in `mcp-server/kb/mcna_amc.db`:

- **`tenant_snapshot`** — one row per entity, JSON properties blob, `last_scanned` timestamp
- **`findings`** — flagged items: entity type/ID, SecureSketCH control, severity, status (open/acknowledged/resolved), first/last seen
- **`baselines`** — known-good state for drift detection
- **`dismissed`** — accepted-risk items with reason and date
- **`activity_log`** — every tool invocation: timestamp, tool, entity, outcome

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
- 2026-04-21 — v9 — Platform decision: Claude Code as AMC + MCP server layers.
  Play model retired. Repo cleaned: Play scripts, task specs, session handoffs,
  AGENTS.md, dis-log, queries moved to archive/. auth/ moved to docs/auth/.
  MCNA-AMC MCP Server defined (not yet built). Domain tool surface and KB
  schema documented.
