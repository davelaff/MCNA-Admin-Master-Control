# ROADMAP.md — MCNA Tenant Intel Project

## Purpose of this document
This is the strategic roadmap for the mcna-tenant-intel Cowork project. It
captures why the project exists, the principles that govern how it grows,
the planned tasks in rough priority order, and the risk framing that
shaped those decisions.

CLAUDE.md is operational. This file is directional. Cowork should read
this when Dave asks about project direction, when a new task is being
scoped, or when a decision needs to be checked against the original
intent. It should NOT be pulled into context for routine task execution.

---

## Project thesis
Dave holds global admin across Entra, Exchange, SharePoint, Teams, and
Power Platform. Cowork running locally on his workstation, authenticated
as purpose-built app registrations, becomes an admin automation layer
over Microsoft Graph that compounds in value with every use. This is not
"AI does my email." It is architectural leverage — the kind Dave has
historically had to build through social influence and finally gets to
build through infrastructure.

The value compounds because every week the brain file gets sharper,
every investigation teaches it something about how the tenant actually
works versus how it's documented, and every false positive teaches it
where MCNA's thresholds differ from generic Microsoft baselines. In six
months this becomes something nobody else at MCNA or DIS could
reproduce, because nobody else has the combination of context and
admin rights.

---

## Operating principles (locked)
These are decisions Dave has already made. They should not be relitigated
task by task. If a future task appears to require violating one of these,
stop and escalate instead of proceeding.

### 1. Read before write, always
First version of any capability is read-only. Write scopes get added
only after the read version has been running cleanly and the use case
is proven. No task gets built with write access on day one.

### 2. Split read and write across separate app registrations
Read-only app regs and write-capable app regs are never combined. A
cert leak on a read-only app reg is an information disclosure incident.
A cert leak on a write-capable app reg is a tenant-wide change incident.
Keeping them separate bounds the blast radius.

### 3. Least privilege on every app reg
Scopes are added only when a specific task needs them, and removed if
the task is retired. No "just in case" scopes. No tenant-wide scopes
where mailbox-scoped or site-scoped would work. If a scope feels too
broad for what the task actually needs, it is too broad.

### 4. Application Access Policies are mandatory for mail scopes
Any app reg with Mail.Read or Mail.Send application permissions must be
scoped via Exchange Application Access Policy to a specific mailbox
(Dave's, during development) before first use. The app physically
cannot read or send from mailboxes outside the policy. This is
non-optional.

### 5. Certificates, not client secrets
All app reg auth uses certificates stored in the Windows certificate
store. No client secrets in .env files, no secrets in code, no secrets
in the project folder (which syncs to SharePoint and would leak them).

### 6. Conditional Access bounds where the app can run from
Where possible, app regs are restricted via Conditional Access to run
only from Dave's managed workstation. This limits the attack surface
if a cert is ever exfiltrated.

### 7. Every Graph call is logged locally AND to SharePoint
Each task appends to activity-log.md (local, synced) and writes
detailed call logs to a reports subfolder. The synced copy gives Dave
a second audit trail that survives the laptop and provides evidence
for any future conversation with NOF Corporate or an auditor about
what this thing actually does.

### 8. Fail loud
Silent failures are worse than loud failures. Any task that encounters
an unexpected state stops, writes a failure entry, and alerts Dave. No
silent retries, no papering over empty results with plausible-looking
output.

### 9. Shadow governance is a known risk, not an accepted one
This project operates outside the Copilot Cowork / Purview governance
story by design — that's the tradeoff that makes it powerful. Dave
owns the decisions and the risk. But this pattern is explicitly NOT
for replication by other MCNA staff without a formal governance
review. If anyone else wants to build something like this, it goes
through a proper process.

---

## Planned tasks (by value-to-risk ratio)

### Play 1 — Tenant-wide read-only intelligence layer (STARTED)
**Status:** DIS daily summary task in v1. More to come.
**Risk:** Low. Read-only, information disclosure only.
**App reg:** MCNA-TenantIntel-ReadOnly (delegated, user-context)
**Scopes:** Mail.Read, Mail.Send (self only, via Application Access
Policy when graduated to application perms), Directory.Read.All,
AuditLog.Read.All, Reports.Read.All, SecurityEvents.Read.All,
Policy.Read.All, Application.Read.All, RoleManagement.Read.Directory

Answers questions no dashboard answers well:
- Which app registrations have secrets expiring in the next 90 days,
  who owns them, and which haven't been used in 6 months?
- Which guest accounts were added in the last year, who invited them,
  and have they signed in since?
- Which conditional access policies reference groups that no longer
  exist, and who would be affected if fixed?
- Current tenant posture vs. SecureSketCH baseline, gaps grouped by
  effort to remediate.
- Power Platform environments with makers who left the company, and
  what apps/flows they own.

This is the M365 Security and Governance Initiative on steroids.
Target: 60% → 80% Secure Score with a weekly brief that writes itself.

### Play 2 — Entra app registration governance scanner
**Status:** Active, v1. Built 2026-04-17. app_reg_scanner.py in project root.
**Risk:** Low. Read-only.
**App reg:** Same read-only app reg as Play 1.
**Scopes:** Application.Read.All, AuditLog.Read.All

Inventories every app registration and enterprise app in the tenant.
For each, checks:
- Overprivileged Graph scopes vs. actual usage
- Expired or expiring secrets/certs
- Missing owners
- Consented-but-unused scopes (via audit log sign-in data)
- Publisher verification status
- Risky redirect URIs (localhost, wildcards, http)

Output: scored risk register with recommended actions per app reg.

Bonus task: daily Dispatch job that flags any new app reg created in
the tenant against the standard. Change detection on the identity
surface without a CASB.

This is meta — it governs the very mechanism this project runs on,
which is the right place for a control to sit. When DIS asks about
app reg controls, Dave hands them data instead of opinions.

### Play 3 — Orphaned asset cleanup (read phase)
**Status:** Active, v1. Built 2026-04-17. orphaned_asset_scanner.py in project root.
**Risk:** Low in read phase, medium when write phase is added.
**App reg:** Read phase uses existing read-only app reg. Write phase
requires a separate MCNA-TenantIntel-Writer app reg with targeted
scopes, built later and only if Dave decides it's worth the risk.

Inventories orphaned SharePoint sites, Teams, distribution groups,
shared mailboxes, and user accounts. Correlates owners against active
Entra roster. Produces a cleanup queue.

Planner plans excluded: Tasks.Read.All is application-only and requires
a confidential client — incompatible with the delegated public-client
pattern. Orphaned plans carry no license cost or auth surface risk;
not worth the architecture change. Power Platform apps, flows, and
Dataverse are Play 5.

Write phase (future, not yet approved): executes approved cleanups
via the writer app reg. Dave reviews the queue and approves items,
Cowork executes. Every write operation logged twice (local + SharePoint).

Write phase architecture (designed 2026-04-17, deferred):
- Approval mechanism: Dave edits the CSV output, adds Approved=YES to rows
- orphaned_asset_writer.py reads approved rows and executes each action
- Requires MCNA-TenantIntel-Writer app reg (separate from ReadOnly per principle 2)
- Write scopes needed: Group.ReadWrite.All, User.ReadWrite.All
- SharePoint site deletion/archiving kept manual — Sites.FullControl.All is too broad

### Play 4 — SecureSketCH / Secure Score remediation drafting
**Status:** Planned. Builds on Play 1.
**Risk:** Low. Drafting only, no execution.
**App reg:** Existing read-only app reg.

Reads current Secure Score recommendations, reads existing tenant
config for each, produces a change ticket with:
- Exactly what needs to change
- Why (Microsoft recommendation + SecureSketCH alignment)
- Estimated impact
- Which users/groups would be affected
- Rollback plan

Dave reviews and approves. Execution is manual or handed to the
future writer app reg. Compresses the 60% → 80% Secure Score project
from months of ticket-by-ticket work to weeks of review-and-approve.

### Play 5 — Power Platform environment hygiene
**Status:** Active, v1. Built 2026-04-19. power_platform_hygiene.py in project root.
**Risk:** Low. Read-only.
**App reg:** Existing read-only app reg. Two new delegated permissions required before first run:
Dynamics CRM: user_impersonation, Power Apps Service: User (admin consent granted 2026-04-20).

Inventories all environments, solutions, connection references,
environment variables, and security roles. Flags:
- Production apps built in the default environment
- Connections using service accounts belonging to departed staff
- Solutions that exist in dev but never got promoted
- Unused environments consuming capacity

This is the governance work every Power Platform admin knows they
should do and nobody has time for.

### Play 6 — FIA local prototype harness
**Status:** Planned. Supports the main FIA build.
**Risk:** Low. Read from Macola SQL, read from Graph, write to local
files only.
**App reg:** Existing read-only app reg for Graph side; SQL auth for
Macola side.

Cowork project with direct SQL access to Macola, brain file that
codifies MCNA's cost methodology (Material COGS, Mfg OH batch-count
allocation against annual budget divided by projected sales volume,
Freight OH per-lb rolled through BOM, OpEx flat percent of sales),
and Graph read access to post findings to SharePoint or Teams.

Purpose: prototype FIA's analytical logic 10x faster locally than in
Dataverse, port stable logic into the production path (Dataverse +
Power BI dataflows) once proven. Classic "prototype where it's fast,
productionize where it's governed."

### Play 7 — SharePoint content intelligence
**Status:** Planned.
**Risk:** Low. Read-only.
**App reg:** Existing read-only app reg.
**Scopes:** Sites.Read.All

Crawls specified site collections, extracts text, builds a topic map.
Front half of a proper information architecture project. Near-term
practical uses:
- Find every doc referencing an old product code and flag for review
- List SharePoint sites with no activity in 12 months, grouped by owner
- Surface duplicate or near-duplicate content across the tenant

### Play 8 — Mailbox and Teams forensics
**Status:** PLANNED BUT GATED. Not to be built without explicit risk
sign-off and documented purpose.
**Risk:** Medium-high. Crown-jewels permissions.
**App reg:** Would require a dedicated MCNA-TenantIntel-Forensics app
reg with Mail.Read and Chat.Read.All application permissions, scoped
via Application Access Policy to a specific mailbox/team during any
use. Never given broad tenant scope even temporarily.

Use cases:
- Vendor contract reconstruction from historical email
- "Your guy told me X" claim verification
- Technical decision archaeology — when exactly did we decide Y

Why gated: Mail.Read and Chat.Read.All at application scope are the
kind of permissions auditors ask pointed questions about. Building
this requires documented business justification, Application Access
Policy from day one, and a clear retention/deletion plan for whatever
Cowork extracts. Not worth doing casually.

---

## Where Dave started and why
Play 1 (DIS daily summary) was chosen as the first concrete task
because:
- Scope is tiny (one mailbox, one sender class)
- Risk is minimal (read-only on Dave's own mail, one Mail.Send to
  himself)
- It exercises the full pattern end to end: auth, Graph query,
  analysis, artifact generation, delivery, logging
- It has real daily value independent of the broader project
- If it works, the pattern for every future task is proven; if it
  breaks, the failure mode is "Dave's email summary is wrong" not
  "tenant-wide incident"

Plays 1 (full) and 2 are the next build priorities after DIS summary
is stable. The tenant intelligence brief + app reg governance scanner
pair justify the project to anyone who asks and produce the highest
leverage for the Secure Score initiative.

---

## What this project is NOT
- Not a replacement for Copilot Cowork on org-wide workflows. Anything
  other MCNA staff will touch belongs in the Copilot/governance path.
- Not a replacement for formal IT governance tooling. It's a personal
  admin force multiplier, not a CASB, not a SIEM, not a GRC platform.
- Not a pattern for other MCNA staff to replicate without review. The
  shadow governance tradeoff is acceptable because Dave owns the
  decisions. It is not acceptable as an unreviewed template.
- Not a production system. It lives on Dave's workstation. If Dave
  leaves, the institutional knowledge survives in the synced brain
  file and roadmap, but the execution capability does not transfer
  without a new owner taking on the risk posture explicitly.

---

## Change log
- 2026-04-14 — v1 — Initial roadmap. Eight plays documented. Principles
  locked. Play 1 (DIS daily summary) is the only task built so far.
- 2026-04-17 — v1.1 — Play 3 (orphaned asset scanner) built. Status updated to Active.
- 2026-04-17 — v1.2 — Play 3 write phase architecture documented. Planner excluded
  from Play 3 scope (Tasks.Read.All is application-only, workaround implemented via
  client credentials). Write phase deferred pending writer app reg creation.
- 2026-04-19 — v1.3 — Play 5 (Power Platform hygiene) built. Status updated to Active.
  Requires Dynamics CRM and Power Apps Service user_impersonation on app reg before first run.
