# AGENTS.md — MCNA Admin Master Control

## Project purpose
This is Dave Lafferty's Admin Master Control workspace — a Microsoft estate
orchestration and governance platform for NOF Metal Coatings North America (MCNA).
Dave is the Director of IT & MIS and holds global admin rights across Entra ID,
Exchange, SharePoint, Teams, and Power Platform.

Master Control runs as Codex augmented by two MCP server layers:
- **Microsoft MCP Server for Enterprise** (hosted) — Entra ID read via Graph
- **MCNA-AMC MCP Server** (local Python, `mcp-server/`) — all other domains
  plus the persistent knowledge base (SQLite)

For fresh sessions, use `START_HERE.md` first. See CONTEXT.md for architecture
orientation only when needed. See ARCHITECTURE.md for full design.

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
Sites.Read.All, DeviceManagementManagedDevices.Read.All,
DeviceManagementConfiguration.Read.All, MailboxSettings.Read,
Dynamics CRM: user_impersonation (Dataverse Web API per org),
Power Apps Service: User (BAP/PowerApps/Flow APIs)

Application scopes (admin consent granted):
Tasks.Read.All, MailboxSettings.Read — client credentials flow, cert-based

Microsoft MCP Server for Enterprise auth: separate from the above. Authenticates
as Dave's admin Entra account via delegated OAuth through Codex. No MSAL
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
See ARCHITECTURE.md for full layout. Primary build artifact: `mcp-server/`. Knowledge base: `mcp-server/kb/mcna_amc.db`. Reports: `reports/`. Design docs: `docs/`.

Low-token startup guide: `START_HERE.md`.

Report usage guide: `docs/how-to-use-reports.md`.

Audit binder note: when reusing the same binder output directory, `ssk_export_binder` now merges `index.md` and `manifest.json` rather than overwriting them with only the last single-control export.

## Current version
v2.5 — 2026-04-25

<!-- rtk-instructions v2 -->
# RTK (Rust Token Killer) - Token-Optimized Commands

## Golden Rule

**Always prefix commands with `rtk`**. If RTK has a dedicated filter, it uses it. If not, it passes through unchanged. This means RTK is always safe to use.

**Important**: Even in command chains with `&&`, use `rtk`:
```bash
# ❌ Wrong
git add . && git commit -m "msg" && git push

# ✅ Correct
rtk git add . && rtk git commit -m "msg" && rtk git push
```

## RTK Commands by Workflow

### Build & Compile (80-90% savings)
```bash
rtk cargo build         # Cargo build output
rtk cargo check         # Cargo check output
rtk cargo clippy        # Clippy warnings grouped by file (80%)
rtk tsc                 # TypeScript errors grouped by file/code (83%)
rtk lint                # ESLint/Biome violations grouped (84%)
rtk prettier --check    # Files needing format only (70%)
rtk next build          # Next.js build with route metrics (87%)
```

### Test (60-99% savings)
```bash
rtk cargo test          # Cargo test failures only (90%)
rtk go test             # Go test failures only (90%)
rtk jest                # Jest failures only (99.5%)
rtk vitest              # Vitest failures only (99.5%)
rtk playwright test     # Playwright failures only (94%)
rtk pytest              # Python test failures only (90%)
rtk rake test           # Ruby test failures only (90%)
rtk rspec               # RSpec test failures only (60%)
rtk test <cmd>          # Generic test wrapper - failures only
```

### Git (59-80% savings)
```bash
rtk git status          # Compact status
rtk git log             # Compact log (works with all git flags)
rtk git diff            # Compact diff (80%)
rtk git show            # Compact show (80%)
rtk git add             # Ultra-compact confirmations (59%)
rtk git commit          # Ultra-compact confirmations (59%)
rtk git push            # Ultra-compact confirmations
rtk git pull            # Ultra-compact confirmations
rtk git branch          # Compact branch list
rtk git fetch           # Compact fetch
rtk git stash           # Compact stash
rtk git worktree        # Compact worktree
```

Note: Git passthrough works for ALL subcommands, even those not explicitly listed.

### GitHub (26-87% savings)
```bash
rtk gh pr view <num>    # Compact PR view (87%)
rtk gh pr checks        # Compact PR checks (79%)
rtk gh run list         # Compact workflow runs (82%)
rtk gh issue list       # Compact issue list (80%)
rtk gh api              # Compact API responses (26%)
```

### JavaScript/TypeScript Tooling (70-90% savings)
```bash
rtk pnpm list           # Compact dependency tree (70%)
rtk pnpm outdated       # Compact outdated packages (80%)
rtk pnpm install        # Compact install output (90%)
rtk npm run <script>    # Compact npm script output
rtk npx <cmd>           # Compact npx command output
rtk prisma              # Prisma without ASCII art (88%)
```

### Files & Search (60-75% savings)
```bash
rtk ls <path>           # Tree format, compact (65%)
rtk read <file>         # Code reading with filtering (60%)
rtk grep <pattern>      # Search grouped by file (75%)
rtk find <pattern>      # Find grouped by directory (70%)
```

### Analysis & Debug (70-90% savings)
```bash
rtk err <cmd>           # Filter errors only from any command
rtk log <file>          # Deduplicated logs with counts
rtk json <file>         # JSON structure without values
rtk deps                # Dependency overview
rtk env                 # Environment variables compact
rtk summary <cmd>       # Smart summary of command output
rtk diff                # Ultra-compact diffs
```

### Infrastructure (85% savings)
```bash
rtk docker ps           # Compact container list
rtk docker images       # Compact image list
rtk docker logs <c>     # Deduplicated logs
rtk kubectl get         # Compact resource list
rtk kubectl logs        # Deduplicated pod logs
```

### Network (65-70% savings)
```bash
rtk curl <url>          # Compact HTTP responses (70%)
rtk wget <url>          # Compact download output (65%)
```

### Meta Commands
```bash
rtk gain                # View token savings statistics
rtk gain --history      # View command history with savings
rtk discover            # Analyze Codex sessions for missed RTK usage
rtk proxy <cmd>         # Run command without filtering (for debugging)
rtk init                # Add RTK instructions to AGENTS.md
rtk init --global       # Add RTK to ~/.Codex/AGENTS.md
```

## Token Savings Overview

| Category | Commands | Typical Savings |
|----------|----------|-----------------|
| Tests | vitest, playwright, cargo test | 90-99% |
| Build | next, tsc, lint, prettier | 70-87% |
| Git | status, log, diff, add, commit | 59-80% |
| GitHub | gh pr, gh run, gh issue | 26-87% |
| Package Managers | pnpm, npm, npx | 70-90% |
| Files | ls, read, grep, find | 60-75% |
| Infrastructure | docker, kubectl | 85% |
| Network | curl, wget | 65-70% |

Overall average: **60-90% token reduction** on common development operations.
<!-- /rtk-instructions -->
