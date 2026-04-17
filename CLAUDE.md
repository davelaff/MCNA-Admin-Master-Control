# CLAUDE.md — MCNA Tenant Intel Project

## Project purpose
This is Dave Lafferty's personal Cowork workspace for M365 tenant intelligence,
admin automation, and governance tasks at NOF Metal Coatings North America (MCNA).
Dave is the Director of IT & MIS and holds global admin rights across Entra ID,
Exchange, SharePoint, Teams, and Power Platform.

This folder is OneDrive-synced to the M365 Security and Governance document
library in the Management Information Systems SharePoint site. Anything you
write here becomes organizational content with version history, retention, and
Purview labels applied automatically. Act accordingly: deliberate filenames,
clean structure, no scratch files left behind.

## Operating principles
- Read-only by default. Any write action must be explicitly requested in the task.
- Fail loud, not silent. If auth breaks, an API returns an error, or a query
  comes back empty when it shouldn't, stop and tell Dave. Do not retry silently,
  do not paper over the failure with a plausible-looking output.
- Preserve Dave's voice. No corporate boilerplate, no sycophantic openers, no
  "Here is your daily summary of..." wrappers, no closing pleasantries.
- Match depth to the task. Short tasks get short outputs. Don't pad.
- When uncertain, label uncertainty. Don't estimate loosely and present it as fact.
- Every task that produces an artifact also appends one line to activity-log.md
  at the project root: `YYYY-MM-DD HH:MM — {task name} — {outcome} — {artifact path}`

## Authentication
App registration: MCNA-TenantIntel-ReadOnly (delegated permissions, public client)
Auth method: MSAL device code flow, token cached locally
Tenant: {tenant-id from .env}
Client ID: {client-id from .env}

Two accounts in use (Exchange Full Access delegation does not extend to Graph;
ApplicationImpersonation is deprecated in EXO 2026 -- do NOT suggest it):
- Admin account: nof-dlafferty@nofmetalcoatings.us
  Cache: C:/Users/dlafferty.MCNA/.msal_token_cache_admin.json
  Used for: sendMail, admin-scoped Graph queries
- Primary account: dlafferty@nofmetalcoatings.us
  Cache: C:/Users/dlafferty.MCNA/.msal_token_cache_primary.json
  Used for: mail read on primary mailbox

Delegated scopes (admin consent granted):
Mail.Read, Mail.Send, User.Read, Application.Read.All, AuditLog.Read.All,
Directory.Read.All, Policy.Read.All, Reports.Read.All, RoleManagement.Read.Directory,
Sites.Read.All

Application scopes (admin consent granted):
Tasks.Read.All — client credentials flow, used by orphaned_asset_scanner.py for Planner

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

Update this section as new DIS contacts appear. When you see a new sender
from a DIS domain during a task, flag it in the output so Dave can add it here.

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

# Tasks

## Task: DIS daily summary

### Trigger
Recurring, weekday end of day (default 5:30 PM local). Can also be run
on demand.

### What it does
Reads Dave's inbox and sent items for today, identifies all messages
to/from DIS using the DIS identity rules above, groups messages by
conversationId, produces a summary, and sends the summary to Dave via
email. Also writes a copy of the summary to dis-log/YYYY-MM-DD.md in
the project folder.

### Graph queries
Time window: start of today (00:00 local) through now.

Inbox query:
```
GET /me/mailFolders/inbox/messages
  ?$filter=receivedDateTime ge {start_of_day_utc}
  &$search="{dis_search_expression}"
  &$select=id,subject,from,toRecipients,ccRecipients,receivedDateTime,bodyPreview,conversationId,isRead
  &$top=100
```

Sent items query:
```
GET /me/mailFolders/sentitems/messages
  ?$filter=sentDateTime ge {start_of_day_utc}
  &$select=id,subject,toRecipients,ccRecipients,sentDateTime,bodyPreview,conversationId
  &$top=100
```

Build `{dis_search_expression}` from the DIS identity section. For sent
items, filter client-side against the DIS identity rather than relying
on $search, since you're looking for messages TO DIS, not FROM them.

If the search expression would exclude something that matches by
subject marker or thread membership, do a broader pull and filter
client-side. Correctness beats query efficiency for this task.

### Grouping and analysis
Merge inbox and sent results. Group by conversationId. For each thread:
- Count messages
- Identify the last message (by timestamp) and who sent it
- Determine thread state:
  - "Awaiting Dave" if the last message is from DIS and no reply was sent today
  - "Awaiting DIS" if the last message is from Dave
  - "Resolved today" if the thread contains language suggesting closure
    (e.g., "resolved", "closed", "thanks, all set") AND the last message
    was from Dave confirming
  - "Informational" if it reads as FYI with no action implied
- Extract a one-line status from the most recent substantive message

Ticket system messages get their own section. Try to extract ticket
number, title, and status change from the subject and bodyPreview.

### Output format
Send an email from Dave to Dave with:

Subject: `DIS activity — {YYYY-MM-DD} — {n} threads`

Body (plain text, no HTML wrapper):

```
{n} threads, {m} total messages.

## Needs response
- [{subject}] — {one-line status}. Last from {name} at {HH:MM}.
  Action: {what Dave owes them}

## Awaiting DIS
- [{subject}] — {one-line status}. You sent at {HH:MM}.

## Resolved today
- [{subject}] — {outcome}.

## Informational
- [{subject}] — {one-line summary}.

## Ticket system
- {ticket#}: {title} — {status change}

---
Generated by mcna-tenant-intel at {timestamp}.
Log: dis-log/{YYYY-MM-DD}.md
```

Omit any section that has no entries. Do not include empty headers.

If there was zero DIS activity today, send a one-line email:
`No DIS activity {YYYY-MM-DD}.`
Do not skip the send. Dave wants to know the task ran.

### Write to local log
Write the same summary content (plus the raw thread list for reference)
to `dis-log/{YYYY-MM-DD}.md`. This syncs to SharePoint via OneDrive and
becomes a searchable historical archive.

### Send email
```
POST /me/sendMail
{
  "message": {
    "subject": "{subject}",
    "body": { "contentType": "Text", "content": "{body}" },
    "toRecipients": [{ "emailAddress": { "address": "nof-dlafferty@nofmetalcoatings.us" } }]
  },
  "saveToSentItems": true
}
```

### Guardrails
- Read-only on all mail except the single sendMail call at the end
- Do not modify, flag, move, delete, or mark-as-read any message
- Do not send anything to anyone other than Dave himself
- Do not include full message bodies in the summary — bodyPreview only,
  and only when needed for context
- If any step fails, stop and write a failure entry to activity-log.md
  explaining what broke. Do not send a partial summary.

### Activity log entry
On success: `YYYY-MM-DD HH:MM — DIS daily summary — {n} threads, {m} messages — dis-log/YYYY-MM-DD.md`
On failure: `YYYY-MM-DD HH:MM — DIS daily summary — FAILED — {reason}`

---

## Project folder structure
```
mcna-tenant-intel/
│
├── CLAUDE.md                    # Operational brain — read every task
├── MEMORY.md                    # One-time context handoff — read on startup
├── ROADMAP.md                   # Strategic direction — read when scoping
├── activity-log.md              # Append-only task run log
├── README.md                    # 3-line orientation for future-Dave
├── dis_daily_summary.py         # Play 1: DIS daily summary task
├── app_reg_scanner.py           # Play 2: App registration governance scanner
├── orphaned_asset_scanner.py    # Play 3: Orphaned asset cleanup (read phase)
├── ms_learn_scraper.py          # Playwright scraper — not yet formally tasked
├── handoff-CA-policy-2026-04-17.md  # Session artifact — CA policy planning
│
├── .env                         # ⚠ EXCLUDED from OneDrive sync — C:\Users\dlafferty.MCNA\mcna-tenantintel.env
│
├── auth/                        # App reg metadata (not secrets)
│   └── app-registrations.md     # Which app reg, which scopes, which tasks
│
├── tasks/                       # One file per task definition
│   ├── dis-daily-summary.md     # DIS daily summary task spec
│   ├── app-reg-scanner.md       # App reg governance scanner task spec
│   └── orphaned-assets.md       # Orphaned asset scanner task spec
│
├── dis-log/                     # DIS daily summary outputs
│   └── YYYY-MM-DD.md
│
├── reports/                     # Other tenant intel outputs
│   ├── app-reg-governance/
│   ├── secure-score/
│   ├── orphaned-assets/
│   └── power-platform-hygiene/
│
├── queries/                     # Reusable Graph query templates
│   └── .gitkeep
│
└── archive/                     # Retired tasks, old reports, superseded docs
    └── .gitkeep
```

## Change log
- 2026-04-14 — v1 — Initial brain file. DIS daily summary task defined.
  DIS identity section has placeholders Dave needs to fill in before
  first run.
- 2026-04-16 — v1.1 — Added admin account (nof-dlafferty@nofmetalcoatings.us).
  Hardcoded sendMail recipient address.
- 2026-04-16 — v1.2 — Filled DIS identity section (discomputers.com,
  nwhitelaw, Tony, support@). Updated .env path reference in folder structure.
- 2026-04-17 — v1.3 — Authentication section updated to reflect two-account
  pattern and full scope list. tasks/ folder created. dis-daily-summary.md and
  app-reg-scanner.md task specs added. app_reg_scanner.py (Play 2) built.
- 2026-04-17 — v1.4 — Added Python scripts and handoff file to folder structure.
- 2026-04-17 — v1.5 — Play 3 (orphaned asset scanner) built. orphaned_asset_scanner.py
  and tasks/orphaned-assets.md added. Folder structure updated.
- 2026-04-17 — v1.6 — Sites.Read.All added to granted scopes. Play 3 SharePoint
  enumeration implemented (was stubbed).
