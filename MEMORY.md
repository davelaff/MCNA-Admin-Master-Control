# MEMORY.md — MCNA Tenant Intel / Master Control
Version: v8 | Updated: 2026-04-20

## Purpose of this file

This is the living handoff and project-state file.

Use it to understand:

- what decisions have already been made
- what the repo currently contains
- what is true right now about auth, scope, and risk posture
- what important context a fresh session should not have to rediscover

Read this once at project startup.

After that:

- `CONTEXT.md` governs architecture
- `CLAUDE.md` governs operational behavior in the repo
- `ROADMAP.md` remains useful for direction and history

---

## Current architectural position

The repo started life as a set of narrow task ideas and early scripts.

Current direction:

- treat the repo as the seed of `Master Control`
- stop treating narrow `Plays` as the long-term architectural unit
- treat current scripts as prototype capabilities
- build toward domain agents plus shared schemas plus orchestration

Important working definition:

`Master Control is a Microsoft estate orchestration and governance platform. Its agents are domain authorities, not single-purpose scanners.`

This repo is still early-stage. It is not yet Master Control itself.
It is the proving ground and seed layer for it.

---

## Repo role right now

Right now this repo is:

- a local admin-intelligence workspace
- a place to prototype Microsoft estate discovery and governance logic
- a source of operational outputs and evidence-capable artifacts
- a place where durable architecture is now being defined

It is not yet:

- a fully normalized platform
- a unified data model
- a mature orchestrator
- a multi-agent domain system

---

## Durable decisions already made

### 1. Master Control is an orchestrator

The long-term target is not a single fuzzy chatbot.

It is:

- an orchestrator
- a control plane
- a governance intelligence backend

### 2. Domain agents are the architectural unit

The durable units are domain agents such as:

- Entra
- Exchange
- SharePoint and OneDrive
- Teams
- Intune
- Power Platform
- Power BI
- Security
- Purview
- Copilot and AI Governance

### 3. Existing narrow scans are prototypes, not architecture

Examples:

- app registration scanning belongs inside the future `Entra Agent`
- orphaned asset logic belongs inside the future `SharePoint and OneDrive Agent`
  and may intersect with `Teams Agent`
- Power Platform hygiene belongs inside the future `Power Platform Agent`

### 4. Read-first posture remains in force

Any write or remediation path should remain explicit, gated, and approval-bound.

### 5. Evidence production matters

Outputs should become usable in:

- Secure SketCH support
- the 2026 governance program
- leadership review
- audit readiness

---

## Current repo contents of consequence

Core docs:

- `README.md`
- `CLAUDE.md`
- `ROADMAP.md`
- `CONTEXT.md`
- `MEMORY.md`
- `activity-log.md`
- `auth/app-registrations.md`

Current scripts:

- `dis_daily_summary.py`
- `app_reg_scanner.py`
- `orphaned_asset_scanner.py`
- `power_platform_hygiene.py`
- `ms_learn_scraper.py`

Current working interpretation:

- `dis_daily_summary.py` is an operational utility task
- the other three major scanners are prototype governance capabilities
- `ms_learn_scraper.py` is a useful research utility, not part of the core
  governance model

---

## Authentication and identity realities

### Accounts in use

This repo currently uses two delegated MSAL user contexts because Exchange
Full Access delegation does not extend to Graph delegated mailbox access.

- Admin account: `nof-dlafferty@nofmetalcoatings.us`
  Used for:
  - sendMail
  - admin-scoped Graph queries
  - most admin-side work
  Cache:
  - `C:/Users/dlafferty.MCNA/.msal_token_cache_admin.json`

- Primary account: `dlafferty@nofmetalcoatings.us`
  Used for:
  - primary mailbox read
  - Power Platform queries where that account context is needed
  Cache:
  - `C:/Users/dlafferty.MCNA/.msal_token_cache_primary.json`

Important:

- `ApplicationImpersonation` in Exchange Online is deprecated and should not be
  suggested as a solution path.
- If delegated auth fails or expires, manual reauthentication is currently the
  operational recovery path.

### App registration currently in use

Primary app registration:

- `MCNA-TenantIntel-ReadOnly`

Current reality:

- public client flows enabled
- delegated permissions in use
- application permission `Tasks.Read.All` also present for Planner access

Important architectural caution:

The project principles aim for clean separation between trust models, but the
current implementation is still transitional and not perfectly aligned to the
ideal architecture yet.

### Certificate / PFX reality

Current implementation uses:

- `MCNA-TenantIntel-Planner`
- exportable PFX path outside the synced repo

This works operationally, but it does not perfectly match the aspirational
security model described elsewhere. Treat it as current reality, not final
architecture.

### .env location

Current env file:

- `C:\Users\dlafferty.MCNA\mcna-tenantintel.env`

It lives outside the OneDrive-synced repo on purpose.

Known variables in use include:

- `TENANT_ID`
- `CLIENT_ID`
- `CERT_THUMBPRINT`
- `CERT_PFX_PATH`
- `USER_EMAIL`
- `PRIMARY_MAILBOX`
- `SUMMARY_RECIPIENT`

---

## OneDrive / SharePoint sync reality

This repo is synced into the M365 Security and Governance library in the MIS
SharePoint site.

Implications:

- repo outputs become organizational content
- version history exists
- retention and Purview treatment may apply
- sloppy temp files are bad
- filenames and folder structure matter

The `.env` file is intentionally outside the synced repo.

---

## Current functional state of the repo

### `dis_daily_summary.py`

Status:

- active
- operational
- narrow and task-specific

Role in the broader architecture:

- operational utility
- proof that the end-to-end pattern works
- not a future top-level domain architecture concept

### `app_reg_scanner.py`

Status:

- active prototype

Role in the broader architecture:

- seed capability for the future `Entra Agent`

Important note:

- it is already surfacing real governance issues, including owner gaps

### `orphaned_asset_scanner.py`

Status:

- active prototype

Role in the broader architecture:

- seed capability for future `SharePoint and OneDrive Agent`
- may also intersect with `Teams Agent`

Important note:

- the orphaned-assets concept is useful, but it is only one slice of the future
  SharePoint/Teams governance surface

### `power_platform_hygiene.py`

Status:

- active prototype

Role in the broader architecture:

- seed capability for future `Power Platform Agent`

Important note:

- this domain is much broader than the current script and will eventually need
  to cover environments, makers, DLP, ALM, connections, Copilot Studio, and
  governance posture

### `ms_learn_scraper.py`

Status:

- utility

Role:

- official-doc research helper
- useful for product/domain discovery and documentation extraction

---

## Immediate architectural implications

Before adding many more narrow scripts, the system should define:

- a normalized finding schema
- a normalized evidence model
- domain-agent boundaries
- cross-domain services
- what gets treated as durable evidence versus disposable analysis

If that does not happen, the repo will grow tentacles in the bad sense:

- too many narrow scripts
- too much duplicated auth/query logic
- too many disconnected reports
- too much context that only Dave remembers

---

## Relationship to the 2026 governance program

Master Control should eventually support:

- the Secure SketCH response cycle
- evidence generation and tracking
- governance review packets
- remediation prioritization
- control-state visibility
- audit readiness

This repo is therefore not just an admin sandbox. It is becoming part of the
backend governance capability for the 2026 IT-MIS Security and Governance work.

---

## Known risks and tensions

### 1. Architecture drift

The docs may describe a cleaner future-state than the code currently implements.

### 2. Security-model drift

Read/write separation and certificate handling are not yet in their ideal final
state.

### 3. Schema debt

The repo currently has multiple useful outputs but no unified normalized model
yet.

### 4. Memory concentration risk

Too much meaning still lives in Dave's head and in ad hoc repo history rather
than in shared structures.

### 5. Tool sprawl risk

Without domain-agent framing, each new problem could become another standalone
script.

---

## Current best next moves

1. Keep `CONTEXT.md` stable as the durable architecture reference.
2. Use this file as the living operational memory.
3. Define the common finding schema before expanding too far.
4. Define the evidence model and retention expectations.
5. Recast prototype scripts under future domain-agent ownership.
6. Choose the first serious domain agents for design and build.

Recommended early serious domains:

- Entra
- SharePoint and OneDrive
- Power Platform
- Security or Purview, depending on whether evidence or security posture is the
  more urgent next use

---

## Things a fresh session should remember

- The current repo is early-stage and promising, but still transitional.
- The old `Play` framing is no longer the right top-level architecture.
- `Master Control` is the new architectural center of gravity.
- Domain agents should replace narrow task-centric thinking.
- Existing scripts are still useful and should be preserved as prototypes.
- The next foundational work is context, memory, schema, and evidence design.
  apps. Scores findings by severity (Critical/High/Medium/Low). Writes
  risk register to reports/app-reg-governance/YYYY-MM-DD.md + .csv.
  First run: 40 apps, 25 with findings (Critical: 7, High: 54, Medium: 30).
  Token cache hot -- no device code on re-run. Run on-demand.
  Key finding: 6 critical expired certs on Portals-* apps. Workflow app
  has 57 cert entries -- SharePoint Online auto-provisioned, not actionable.

- orphaned_asset_scanner.py -- Active, v1. Built and verified 2026-04-17.
  Inventories orphaned M365 groups/Teams, distribution groups, users,
  SharePoint sites, and Planner plans in orphaned groups.
  Auth: delegated token for groups/users/sites; client credentials (cert)
  for Planner (Tasks.Read.All application permission).
  First run (full): 166 assets flagged (High: 26, Medium: 105, Low: 44).
  Writes to reports/orphaned-assets/YYYY-MM-DD.md + .csv. Run on-demand.
  Key findings: 14 M365 groups with all owners disabled (lverzella, jsimonic,
  sfreeman, ariddle, lcannon, tbankole accounts). 3 disabled users holding
  licenses (cheinz x2, dschultz, skemp). Macola Project group has 3 orphaned
  Planner plans. QMS site (/sites/qualityna) had stale primary admin --
  luribe added as site collection admin 2026-04-17.
  Known limitation: SP usage report Owner Principal Name shows group email
  for Teams-backed sites, not individual users. High firing = stale primary
  admin account, not necessarily unmanaged. Verify in SP Admin Center.

- ms_learn_scraper.py -- Present in folder, built by Claude Code.
  Playwright-based scraper for learn.microsoft.com. Not yet formally
  tasked or documented in CLAUDE.md. Needs: pip install playwright +
  playwright install chromium before use.

### Folder structure (confirmed as of 2026-04-17)
```
mcna-tenant-intel/
|- CLAUDE.md
|- MEMORY.md
|- ROADMAP.md
|- README.md
|- activity-log.md
|- dis_daily_summary.py
|- app_reg_scanner.py
|- orphaned_asset_scanner.py
|- ms_learn_scraper.py
|- handoff-CA-policy-2026-04-17.md
|- auth/
|   |- app-registrations.md
|- tasks/
|   |- dis-daily-summary.md
|   |- app-reg-scanner.md
|   |- orphaned-assets.md
|- dis-log/
|   |- 2026-04-16.md
|- queries/
|- archive/
|- reports/
    |- app-reg-governance/
    |   |- 2026-04-17.md
    |   |- 2026-04-17.csv
    |- orphaned-assets/
    |   |- 2026-04-17.md
    |   |- 2026-04-17.csv
    |- secure-score/
    |- power-platform-hygiene/
```

### Governance housekeeping outstanding
IT-GOV-ENTRA-v1.0 requires a documented request record for the scope
additions made 2026-04-16 (Application.Read.All, AuditLog.Read.All,
Directory.Read.All, Policy.Read.All, Reports.Read.All,
RoleManagement.Read.Directory). Dave self-approves as IS Director but
the paper trail should exist. Not yet done.

---

## Things NOT to assume
- Dave does not use Obsidian.
- Dave is already technical and already a global admin. Do not explain
  basic Graph, Entra, or M365 concepts unless he asks.
- ApplicationImpersonation cannot be used -- deprecated. Do not suggest it.
- This project is Dave's personal workbench. Not a template for
  MCNA-wide deployment without a formal governance review.

---

## Open items

### CA policy & Entra identity (from sessions 4-5, 2026-04-17)
- Awaiting Tony response on 4 CA policy gaps (legacy auth, admin
  policy, service accounts, MCNA break-glass)
- Identify owner of admin@nofmetalcoatings.us before touching it
- Confirm cloudadmin@nofmetalcoatings.us ownership
- Decision: when to disable Security Defaults and enable CA policies
- blynn@nofmetalcoatings.us: holds custom role GUID
  d24aef57-1500-4070-84db-2666f29cf966. Unknown identity and purpose.
  Needs investigation before touching.

### Entra role remediation (session 5 -- mostly complete)
- DONE: dlafferty@ daily driver cleaned -- roles moved to nof-dlafferty@
- DONE: nof-scala@ -- removed Fabric Administrator, Power Platform Administrator
- DONE: MIS@ -- role count reduced from 24 per governance review
- IN PROGRESS: nof-dkochever@ -- User Admin and Teams Admin removed.
  Exchange Administrator on hold. Key question for meeting: is Diana
  actively managing shared mailboxes or DLs? If no ongoing use case,
  remove Exchange Administrator.

### Project infrastructure
- Governance paper trail for scope additions per IT-GOV-ENTRA-v1.0:
  2026-04-16 additions (Application.Read.All, AuditLog.Read.All,
  Directory.Read.All, Policy.Read.All, Reports.Read.All,
  RoleManagement.Read.Directory) and 2026-04-17 additions
  (Sites.Read.All delegated, Tasks.Read.All application). Self-approved
  as IS Director but paper trail not yet written.
- MCNA-TenantIntel-Writer app reg: architecture discussed 2026-04-17.
  Pattern: edited CSV queue as approval mechanism; write script executes
  approved rows; every write logged twice. Needs separate app reg with
  Group.ReadWrite.All, User.ReadWrite.All scopes + new cert.
  Deferred to a future session. DO NOT add write scopes to ReadOnly reg.
- Power Platform admin API token flow: not yet configured, needed for Play 5
- ms_learn_scraper.py: needs formal task definition in CLAUDE.md if
  it enters regular use
- Play 8 (mail/Teams forensics): gated, requires explicit risk
  sign-off before any work begins
- activity-log.md line 4 has encoding corruption (em-dashes as â€")
  from a PowerShell write. Historical, low priority. All future
  writes must use MCP FileSystem tool, not PowerShell.

### VS Code tooling
- Windows MCP Server (sbroenne.windows-mcp) requires .NET 10 Windows
  Desktop Runtime. Fixed 2026-04-17 by installing
  Microsoft.DotNet.DesktopRuntime.10 via winget. If it breaks after
  a future extension update, check the runtime version requirement first.

---

## Change log
- 2026-04-14 -- v1 -- Initial handoff from scoping session.
- 2026-04-16 -- v2 -- Full rebuild to reflect actual project state
  after build session.
- 2026-04-17 -- v3 -- Stripped content already in Claude system
  instructions (Dave identity, communication style, stack, key
  people, active initiatives). Added session 2 and session 3
  summaries. Added tasks/ disk-vs-design discrepancy note.
  Added activity-log encoding corruption to open items.
- 2026-04-17 -- v4 -- Added session 4 summary (CA policy & Entra
  role audit). Added CA/identity open items section. Saved
  handoff-CA-policy-2026-04-17.md to project root.
- 2026-04-17 -- v5 -- Added Windows MCP Server .NET dependency note.
- 2026-04-17 -- v6 -- Session 5: app_reg_scanner.py added to tasks built.
  Folder structure updated. Entra role remediation status captured.
  Session 4 outstanding actions updated (items 4+5 partially complete).
  Open items restructured to separate CA/identity from role remediation.
  Stale tasks/ disk note removed.
- 2026-04-17 -- v7 -- Session 6: Play 3 built (orphaned_asset_scanner.py).
  Sites.Read.All and Tasks.Read.All added to app reg. Certificate replaced
  (old cert non-exportable; new MCNA-TenantIntel-Planner cert created as
  exportable PFX). Planner scan operational via client credentials flow.
  First full scan: 166 assets flagged. QMS site remediated (luribe added
  as site collection admin). Write phase architecture discussed and deferred.
  Folder structure, permissions, tasks, and open items updated.
