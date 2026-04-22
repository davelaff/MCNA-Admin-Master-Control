# CLAUDE.md — MCNA Admin Master Control

## Project purpose
This is Dave Lafferty's Admin Master Control workspace — a Microsoft estate
orchestration and governance platform for NOF Metal Coatings North America (MCNA).
Dave is the Director of IT & MIS and holds global admin rights across Entra ID,
Exchange, SharePoint, Teams, and Power Platform.

Master Control runs as Claude Code augmented by two MCP server layers:
- **Microsoft MCP Server for Enterprise** (hosted) — Entra ID read via Graph
- **MCNA-AMC MCP Server** (local Python, `mcp-server/`) — all other domains
  plus the persistent knowledge base (SQLite)

See CONTEXT.md for architecture orientation. See ARCHITECTURE.md for full design.

This folder is OneDrive-synced to the M365 Security and Governance document
library in the Management Information Systems SharePoint site. Anything written
here becomes organizational content with version history, retention, and Purview
labels applied automatically. Deliberate filenames, clean structure, no scratch
files left behind.

## Operating principles
- Read-only by default. Any write action must be explicitly requested.
- Fail loud, not silent. If auth breaks, an API returns an error, or a query
  comes back empty when it shouldn't, stop and tell Dave. Do not retry silently,
  do not paper over the failure with a plausible-looking output.
- Preserve Dave's voice. No corporate boilerplate, no sycophantic openers,
  no closing pleasantries.
- Match depth to the task. Short tasks get short outputs. Don't pad.
- When uncertain, label uncertainty. Don't estimate loosely and present it as fact.
- Every task that produces an artifact also appends one line to activity-log.md
  at the project root: `YYYY-MM-DD HH:MM — {task name} — {outcome} — {artifact path}`
- Domain-first, not task-first. Work inside established domain boundaries.
- Shared schemas before new fields. Every finding should conform to the common
  finding schema in ARCHITECTURE.md.

## Authentication
App registration: MCNA-TenantIntel-ReadOnly (delegated permissions, public client)
Auth method: MSAL device code flow, token cached locally
Tenant: {tenant-id from .env}
Client ID: {client-id from .env}
.env location: C:\Users\dlafferty.MCNA\mcna-tenantintel.env (outside synced repo)

Two accounts in use (Exchange Full Access delegation does not extend to Graph;
ApplicationImpersonation is deprecated in EXO 2026 — do NOT suggest it):
- Admin account: nof-dlafferty@nofmetalcoatings.us
  Cache: C:/Users/dlafferty.MCNA/.msal_token_cache_admin.json
  Used for: sendMail, admin-scoped Graph queries
- Primary account: dlafferty@nofmetalcoatings.us
  Cache: C:/Users/dlafferty.MCNA/.msal_token_cache_primary.json
  Used for: mail read on primary mailbox, Power Platform queries

Delegated scopes (admin consent granted):
Mail.Read, Mail.Send, User.Read, Application.Read.All, AuditLog.Read.All,
Directory.Read.All, Policy.Read.All, Reports.Read.All, RoleManagement.Read.Directory,
Sites.Read.All,
Dynamics CRM: user_impersonation (Dataverse Web API per org),
Power Apps Service: User (BAP/PowerApps/Flow APIs)

Application scopes (admin consent granted):
Tasks.Read.All — client credentials flow, cert-based

Microsoft MCP Server for Enterprise auth: separate from the above. Authenticates
as Dave's admin Entra account via delegated OAuth through Claude Code. No MSAL
token cache. Read-only, Entra ID scope only.

If any Graph call returns 401/403, stop immediately. Do not attempt to
re-acquire tokens more than once. Alert Dave and wait for instruction.

## DIS identity
DIS is MCNA's managed service provider. Dave works with them regularly on
infrastructure, Entra, and Microsoft 365 matters.

Primary contact: Nate Whitelaw
Domains: discomputers.com
Known senders: nwhitelaw@discomputers.com, Tony@discomputers.com
Ticket system sender: support@discomputers.com
Subject markers: [DIS], [Ticket #], "DIS Support"

When identifying DIS communication, match on any of:
1. Sender or recipient domain in the domains list
2. Sender address in the known senders list
3. Sender address matching the ticket system sender
4. Subject line containing any subject marker
5. Thread where any prior message matches the above (use conversationId)

Update this section as new DIS contacts appear.

## Writing to Dave
Audience: Dave himself. He is a systems architect, global admin, deeply
technical. Full context, no throat-clearing, no hedging language used to
avoid taking a position. Strong opinions welcome. Quick humor when it fits.

What Dave does NOT want:
- Sycophantic openers ("Great question!", "Happy to help with this!")
- Filler ("I'll go ahead and...", "Just to confirm...")
- Unsolicited disclaimers
- "Would you like me to..." closers
- Passive voice used to dodge a position
- Bullet points as a substitute for reasoning
- Corporate boilerplate of any kind

What Dave wants:
- Usable artifacts, not drafts of drafts
- Direct statements of what you found and what you think it means
- Honest labeling of uncertainty when it exists
- Preservation of his voice in anything written on his behalf

---

## Project folder structure
```
MCNA-Admin-Master-Control/
│
├── CLAUDE.md                    # Operational brain — read every session
├── CONTEXT.md                   # Short architecture orientation
├── ARCHITECTURE.md              # Full AMC design reference
├── MEMORY.md                    # Living handoff — current state, open items
├── ROADMAP.md                   # Strategic direction
├── README.md                    # 5-line orientation
├── activity-log.md              # Append-only task run log
├── Secure_SketCH_Guidelines_2026-01-01.docx  # Compliance target (binary, not tracked)
│
├── .mcp.json                    # Claude Code MCP server configuration
├── .claude/
│   └── settings.json            # Claude Code workspace settings
│
├── mcp-server/                  # MCNA-AMC MCP Server (primary build artifact)
│   ├── server.py
│   ├── auth.py
│   ├── db.py
│   ├── graph.py
│   ├── requirements.txt
│   ├── tools/                   # One module per domain
│   │   ├── __init__.py
│   │   ├── entra.py, ca.py, pp.py, kb.py
│   │   ├── ssk.py, ssk_common.py, ssk_parser.py, ssk_loader.py
│   │   ├── ssk_control_map.py, ssk_evidence.py, ssk_reviews.py
│   │   ├── ssk_actions.py, ssk_registry.py, ssk_binder.py
│   │   └── (planned: exo.py, license.py, pim.py, sharing.py,
│   │       compliance.py, mail.py, intune.py, copilot.py, purview.py)
│   ├── tests/                   # 120 tests (all passing)
│   │   ├── __init__.py, conftest.py
│   │   └── test_auth.py, test_ca.py, test_db.py, test_entra.py,
│   │       test_graph.py, test_kb.py, test_pp.py, test_ssk*.py
│   └── kb/
│       ├── mcna_amc.db          # SQLite knowledge base (OneDrive-synced)
│       ├── ssk_control_aliases.json
│       └── catalog-imports/     # Versioned catalog import snapshots
│           └── 2026-01-01.json
│
├── reports/                     # Scan outputs and governance artifacts
│   ├── app-reg-governance/
│   ├── orphaned-assets/
│   ├── power-platform-hygiene/
│   └── secure-score/
│
├── docs/                        # Design docs, specs, auth metadata
│   ├── auth/
│   │   └── app-registrations.md
│   └── superpowers/
│       ├── plans/
│       └── specs/
│
└── archive/                     # Retired scripts, session artifacts, old task specs
```

## Change log
- 2026-04-14 — v1 — Initial brain file. DIS daily summary task defined.
- 2026-04-16 — v1.1 — Added admin account. Hardcoded sendMail recipient.
- 2026-04-16 — v1.2 — Filled DIS identity section.
- 2026-04-17 — v1.3 — Two-account auth pattern, full scope list, task specs added.
- 2026-04-17 — v1.4 — Play scripts and handoff file added to structure.
- 2026-04-17 — v1.5 — Play 3 built.
- 2026-04-17 — v1.6 — Sites.Read.All added.
- 2026-04-19 — v1.7 — Play 5 built. Dynamics CRM and Power Apps Service scopes added.
- 2026-04-21 — v2.0 — Redesigned as Admin Master Control orchestrator-agent platform.
  Play model retired. MCP server architecture adopted: Microsoft MCP Server for
  Enterprise (Entra read) + MCNA-AMC MCP Server (all other domains + KB).
  Old Play scripts, task specs, session artifacts, and AGENTS.md moved to archive/.
  auth/ moved to docs/auth/. DIS daily summary task spec removed from this file.
  Folder structure updated to reflect mcp-server/ as primary build artifact.
- 2026-04-22 — v2.1 — Folder structure updated: db.py, tests/, ssk_* tools, kb aliases
  and catalog-imports added. .mcp.json and .claude/settings.json added to root.
