# MEMORY.md — MCNA Tenant Intel Project
Version: v4 | Updated: 2026-04-17

## Purpose of this file
Handoff document for Claude Cowork. Covers how this project came to
exist, the current project state as of the last documented session,
and project-specific context a fresh Cowork instance needs that isn't
already in the Claude system instructions.

Read this once at project startup. After that, CLAUDE.md governs
operational behavior and ROADMAP.md governs direction.

---

## Context already in Claude system instructions
The following are fully documented in the Claude project system
instructions and do not need to be repeated here. A fresh Cowork
instance starting this project should consult those for:

- Who Dave is, how he thinks, and his communication preferences
- MCNA org context (company, NOF relationship, product line)
- The full technology stack
- Active initiatives (WorkSmart/KR-9, FIA, Governance Overhaul, etc.)
- Key MCNA personnel (Gerry Truax, Steve Cala, Chris Gayhart, etc.)
- Document naming conventions and SharePoint library structure
- DIS communication style guidelines

---

## Project-specific context

### DIS identity (project use only)
DIS is MCNA's managed service provider. These values are the source
of truth for the DIS daily summary task and should match CLAUDE.md.

Domain: discomputers.com
Known senders: nwhitelaw@discomputers.com, Tony@discomputers.com
Ticket system: support@discomputers.com
Subject markers: [DIS], [Ticket #], DIS Support

### Auth accounts
This project uses two MSAL sessions because Exchange Full Access
delegation does not extend to Graph delegated API access, and
ApplicationImpersonation is deprecated in Exchange Online as of 2026
(New-ManagementRoleAssignment throws ManagementRoleDeprecatedException).
Do not suggest ApplicationImpersonation as a solution -- it cannot be used.

- Admin account: nof-dlafferty@nofmetalcoatings.us
  Used for: sendMail + admin-scoped Graph queries
  Token cache: C:/Users/dlafferty.MCNA/.msal_token_cache_admin.json

- Primary account: dlafferty@nofmetalcoatings.us
  Used for: mail read on primary mailbox
  Token cache: C:/Users/dlafferty.MCNA/.msal_token_cache_primary.json

Both use device code flow + MFA. Refresh tokens last ~90 days.
When expired, the scheduled task fails with a 403. Fix: run the
script manually once to re-authenticate. Check activity-log.md for
FAILED entries.

### App registration: MCNA-TenantIntel-ReadOnly
Created: 2026-04-16
Type: Public client, delegated permissions, device code flow
Tenant ID: 2eb7fcc8-58b3-4f06-9cbc-77d0c178dba3
Client ID: 96587e5a-65a1-4b20-a82c-e61b2e6bc9db
Certificate: MCNA-TenantIntel-ReadOnly-2026
  Thumbprint: 3FCC406A5AC6C2913F111337407201F8F35C2F0B
  Valid: 2026-04-16 to 2028-04-16
  Store: CurrentUser\My, NonExportable
Public client flows: Enabled
Redirect URI: http://localhost (Mobile & desktop)

Permissions (all delegated, admin consent granted):
Mail.Read, Mail.Send, User.Read, Application.Read.All,
AuditLog.Read.All, Directory.Read.All, Policy.Read.All,
Reports.Read.All, RoleManagement.Read.Directory

Not yet added: Sites.Read.All (Play 7), Power Platform API (Play 5)

### .env location
C:\Users\dlafferty.MCNA\mcna-tenantintel.env
Stored outside the OneDrive sync folder -- does not sync to SharePoint.
Variables: TENANT_ID, CLIENT_ID, CERT_THUMBPRINT, CERT_STORE,
USER_EMAIL, PRIMARY_MAILBOX, SUMMARY_RECIPIENT

### OneDrive sync
This project folder is OneDrive-synced to the M365 Security and
Governance document library in the MIS SharePoint site. Every file
written here becomes organizational content with SharePoint version
history and retention applied automatically. The .env file is the
only exception -- it lives outside the synced folder deliberately.

---

## How this project came to exist

### Phase 1 -- Copilot Cowork vs Claude Cowork comparison
Dave has Copilot Cowork (Microsoft's Claude-powered M365 agent, Wave 3
/ Frontier program) and Claude Cowork (Anthropic's desktop agent).
Key conclusion: they are complementary, not competing.

- Copilot Cowork: tenant-native, governed, Work-IQ-grounded, auditable,
  org-wide deployable. Cannot reach outside M365 -- no local files,
  no computer use, no third-party connectors. Survives Dave leaving.
- Claude Cowork: local, computer use, broader MCP connectors, Dispatch,
  brain file / project pattern. Explicitly NOT for regulated workloads.
  Conversation history not in Audit Logs or Compliance API.

Strategic split:
- Claude Cowork: personal workbench, local files, Macola-adjacent work,
  tenant admin automation via Graph, FIA prototyping, anything requiring
  computer use or non-Microsoft connectors.
- Copilot Cowork: org-wide workflows, anything governed, anything that
  needs to survive Dave.
- Regulated data (EPA CDR, TSCA, SDS, customer PII): Copilot Cowork only.

### Phase 2 -- The core architectural insight
Dave is global admin across Entra, Exchange, SharePoint, Teams, and
Power Platform. Claude Cowork on his workstation + an Entra app reg
with Graph permissions = an admin automation layer over the entire
tenant. Not "AI does my email" -- architectural leverage.

Two app reg flavors to keep separate:
- Delegated (user-context): acts as Dave, inherits admin rights,
  interactive sign-in. Good for exploratory work. This is what
  MCNA-TenantIntel-ReadOnly is.
- Application (daemon): unattended, cert auth, no user context. Good
  for scheduled jobs. Higher leverage, higher risk. Not yet built.
  Requires its own app reg -- never add daemon scopes to the existing
  delegated reg.

Eight strategic plays identified, ranked by value-to-risk. Full detail
in ROADMAP.md. Starting point was deliberately delegated + read-only:
run for a month, see what it surfaces, then decide on write scopes or
daemon.

### Phase 3 -- Risk framing
Shadow governance: Graph calls appear in Entra audit logs, but Claude's
reasoning lives in local conversation history only -- not in Audit Logs,
Compliance API, or Data Exports. Dave owns this tradeoff. Not a
replication pattern for other MCNA staff without a formal review.

App reg risk posture is locked as operating principles in ROADMAP.md:
cert-based auth only, read/write split across separate regs, Application
Access Policies mandatory for mail scopes, Conditional Access to bound
where app can run, dual logging (local + SharePoint).

### Phase 4 -- First concrete task
DIS daily summary chosen as v1: tiny scope, minimal risk, exercises
the full pattern end to end (auth, Graph, analysis, artifact, delivery,
logging). Proven pattern then extends to all future tasks.

### Session 2 -- 2026-04-16 build session
Starting point: brain files only. No code, no folder structure,
no app reg, no credentials.
Ending point: fully operational DIS daily summary on a weekday schedule.

Key discoveries during build:
- Single admin token querying /users/{upn}/mailFolders fails with 403.
  Exchange Full Access delegation does not extend to Graph delegated
  API access. Two-account approach is the correct workaround.
- ApplicationImpersonation deprecated in Exchange Online 2026. Cannot
  be used. Do not suggest it.
- Script encoding: do not rewrite Python files with PowerShell
  Out-File/Set-Content. Use the MCP FileSystem tool. PowerShell
  corrupts non-ASCII characters. Em-dashes replaced with hyphens
  in source to avoid recurrence.
- First two runs failed with 403 (auth not yet settled). Third run
  at 16:07 succeeded: 4 threads, 4 messages. Script is stable.

### Session 4 -- 2026-04-17 CA policy & Entra role audit session
Full detail in handoff-CA-policy-2026-04-17.md (project root).

CA current state: Security Defaults still ON. Tony built one policy
(Require MFA for all users, all resources, dis@nofmetalcoatings.us
excluded) -- in report-only mode only. 97% of sign-ins would require
MFA. CA policy cannot go live until Security Defaults are disabled --
that decision is pending.

Four additional policies recommended and emailed to Tony. Response
pending:
1. Legacy auth block (IMAP, POP3, SMTP AUTH, ActiveSync)
2. Admin role policy (stricter MFA for directory roles)
3. Service account policy (restrict to known MCNA IP, not MFA-exempt)
4. MCNA-owned break-glass accounts (currently only DIS-owned one exists)

Entra role audit run via Microsoft Graph PowerShell. Output saved to
EntraRoleAssignments.csv on Dave's desktop. Key findings:

Global Admins (3):
- nof-dlafferty@nofmetalcoatings.us (expected)
- dis@nofmetalcoatings.us (expected)
- admin@nofmetalcoatings.us -- "admin admin" -- unknown origin.
  Last sign-in: 2025-05-30 (~11 months ago, note: handoff doc says
  2026-05-30 which is a typo). Also holds Hybrid Identity
  Administrator. Do NOT disable until Tony confirms origin and
  dependency check is done.

Other role items flagged:
- dlafferty@nofmetalcoatings.us (daily driver) holds Authentication
  Administrator, Power Platform Administrator, AI Administrator --
  should move to nof-dlafferty admin account
- cloudadmin@nofmetalcoatings.us holds Cloud Application Administrator
  and Application Administrator -- ownership unconfirmed
- NOF Diana Kochever holds User Administrator, Teams Administrator,
  Exchange Administrator -- confirm intentional

Outstanding actions from this session:
1. Tony to respond on CA policy gaps (4 policies above)
2. Identify owner of admin@nofmetalcoatings.us -- ask Tony
3. Confirm cloudadmin@nofmetalcoatings.us ownership
4. Move role assignments from dlafferty@ daily driver to nof-dlafferty@ admin account
5. Confirm Diana Kochever role assignments are intentional
6. Decision point: when to disable Security Defaults and enable CA policies

### Session 3 -- 2026-04-17 strategy session
Dave watched a "How I AI" channel tutorial (Claire Vo interviewing
JJ Englert from Tenex) on Claude Cowork best practices. Key concepts
analyzed for MCNA applicability:

Brain file strategy: most transferable idea. No direct Copilot Cowork
equivalent. Aligns with Dave's existing SKILL.md scaffolding habit.

Multi-persona advisory board: spin up sub-agents with different
personas (CFO lens, skeptical technical peer, Japanese corporate
reader) to critique work from multiple angles. Claude Cowork play,
not Copilot Cowork. Directly useful for Dave's multi-register writing.

Personalized voice: explicit brain file voice profile beats Copilot
Cowork's implicit Work IQ adaptation for Dave's strongly-held
audience-specific registers.

Progressive trust / draft-don't-send: universal principle. Must be
explicit in Claude Cowork brain file. Already documented in CLAUDE.md.

Artifacts produced in session 3: CLAUDE.md v1, ROADMAP.md v1,
MEMORY.md v1-v3, handoff-2026-04-17.md. All grounded in actual
project state from the build session.

---

## Current project state (as of 2026-04-17)

### Tasks built
- dis_daily_summary.py -- Active, v1. Stable as of 2026-04-16 16:07.
  Reads inbox/sent from both mailboxes, filters for DIS, classifies
  threads, sends HTML summary email to dlafferty@nofmetalcoatings.us,
  writes log to dis-log/YYYY-MM-DD.md.
  Scheduled task: \MCNA\MCNA-TenantIntel-DISSummary, weekdays 5:30 PM.
  Format: HTML UTF-8, monospace pre block.

- ms_learn_scraper.py -- Present in folder, built by Claude Code.
  Playwright-based scraper for learn.microsoft.com. Not yet formally
  tasked or documented in CLAUDE.md. Needs: pip install playwright +
  playwright install chromium before use.

### Folder structure (confirmed as of 2026-04-16)
```
mcna-tenant-intel/
|- CLAUDE.md
|- MEMORY.md
|- ROADMAP.md
|- README.md
|- activity-log.md
|- dis_daily_summary.py
|- ms_learn_scraper.py
|- .claude/
|   |- settings.local.json     (Claude Code permissions)
|- auth/
|   |- app-registrations.md
|- dis-log/
|   |- 2026-04-16.md           (first run log)
|- queries/
|- archive/
|- reports/
    |- app-reg-governance/
    |- secure-score/
    |- orphaned-assets/
    |- power-platform-hygiene/
```

Note: tasks/ folder is in the CLAUDE.md design but not yet created
on disk. Task specs still live inline in CLAUDE.md. Create tasks/
and migrate when building task #2.

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
- tasks/ does not yet exist on disk. Don't try to read task specs
  from tasks/ -- they're still inline in CLAUDE.md.

---

## Open items

### CA policy & Entra identity (from session 4, 2026-04-17)
- Awaiting Tony response on 4 CA policy gaps (legacy auth, admin
  policy, service accounts, MCNA break-glass)
- Identify owner of admin@nofmetalcoatings.us before touching it
- Confirm cloudadmin@nofmetalcoatings.us ownership
- Move role assignments from dlafferty@ daily driver to nof-dlafferty@ admin account
- Confirm Diana Kochever role assignments are intentional
- Decision: when to disable Security Defaults and enable CA policies

### Project infrastructure
- tasks/ folder: create on disk when building task #2, migrate
  DIS summary spec out of CLAUDE.md at that point
- Governance paper trail for 2026-04-16 scope additions per
  IT-GOV-ENTRA-v1.0
- Sites.Read.All: not yet added, needed for Play 7
- Power Platform admin API token flow: not yet configured, needed for Play 5
- ms_learn_scraper.py: needs formal task definition in CLAUDE.md if
  it enters regular use
- Sunset/decommissioning plan: not yet written
- "How to onboard a new task" section for CLAUDE.md: deferred until
  task #2-3 reveals the common shape
- Play 8 (mail/Teams forensics): gated, requires explicit risk
  sign-off before any work begins
- activity-log.md line 4 has encoding corruption (em-dashes as â€")
  from a PowerShell write. Historical, low priority. All future
  writes must use MCP FileSystem tool, not PowerShell.

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
