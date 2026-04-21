# ROADMAP.md — MCNA Admin Master Control

## Purpose of this document
Strategic direction for the Admin Master Control project. Read when scoping
new work, when a decision needs to be checked against original intent, or when
a new session needs directional context. Not for routine task execution.

CLAUDE.md is operational. CONTEXT.md is architectural. This file is directional.

---

## Project thesis
Dave holds global admin across Entra, Exchange, SharePoint, Teams, and Power
Platform. Master Control, running as Claude Code with MCP server tools on his
workstation, becomes a governance intelligence layer over the full Microsoft
estate that compounds in value with every session. Every scan sharpens the
knowledge base. Every finding answered teaches it where MCNA's thresholds
differ from generic Microsoft baselines. Every dismissed false positive is
remembered. In six months this becomes something nobody else at MCNA or DIS
could reproduce — because nobody else has the combination of access, context,
and institutional knowledge.

The value compounds because the KB grows, the domain coverage expands, and
the SecureSketCH control mapping gets more complete. This is not "AI does
my admin work." It is an evidence-producing governance backend.

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

9. **Shadow governance is a known risk, not an accepted one.** This operates
   outside the Copilot governance story by design. Dave owns the decisions and
   the risk. Not a pattern for replication by other MCNA staff without a formal
   governance review.

---

## Build phases

### Phase 1 — Platform foundation (current)
**Goal:** Get the MCNA-AMC MCP Server running with core infrastructure and the
highest-value domains operational.

**Status:** Design complete. Build not yet started.

**Deliverables:**
- `mcp-server/server.py` — MCP server entry point
- `mcp-server/auth.py` — shared MSAL token management
- `mcp-server/graph.py` — shared Graph HTTP client
- `mcp-server/kb/` — SQLite schema with five tables
- `tools/kb.py` — KB CRUD tools
- `tools/entra.py` — app reg governance, guest review, orphaned assets
- `tools/ca.py` — CA policy audit and coverage gap detection
- `tools/pp.py` — Power Platform environment, app, flow, and connection governance
- Microsoft MCP Server for Enterprise configured in Claude Code MCP settings

**Why these first:** Entra and CA directly support SecureSketCH compliance work.
Power Platform directly replaces the retired power_platform_hygiene.py prototype.
These three domains produce the highest governance value per build hour.

---

### Phase 2 — SecureSketCH alignment layer
**Goal:** Systematic control gap detection mapped to the SecureSketCH assessment.

**Deliverables:**
- `tools/compliance.py` — Secure Score reader + SecureSketCH control mapper
- `tools/pim.py` — privileged role review, permanent vs. eligible assignments
- `tools/license.py` — unassigned licenses, duplicate stacking, service plan conflicts
- `tools/sharing.py` — external sharing posture across SharePoint, OneDrive, Teams
- KB control mapping table linking findings to SecureSketCH control IDs
- First governance review packet generated from KB findings

---

### Phase 3 — Broad domain coverage
**Goal:** Full Microsoft estate visibility.

**Deliverables:**
- `tools/exo.py` — Exchange hygiene: forwarding rules, shared mailboxes, transport rules
- `tools/intune.py` — device compliance, BitLocker, enrollment posture, baseline drift
- `tools/purview.py` — sensitivity label coverage, DLP policy inventory, audit log queries
- `tools/copilot.py` — Copilot license utilization, label coverage readiness, oversharing risk
- `tools/mail.py` — sendMail for summaries and alerts

---

### Phase 4 — Write phase
**Goal:** Execute approved remediations via a separate write-capable app reg.

**Status:** Architecture designed (see MEMORY.md). Not yet approved for build.

**Requirements before build:**
- MCNA-TenantIntel-Writer app reg created with targeted write scopes
- Approval mechanism defined (CSV queue, Dave edits and approves rows)
- Write operations logged twice: KB activity_log + SharePoint report
- Every write action gated on explicit Dave approval

---

## What this project is NOT
- Not a replacement for formal IT governance tooling (CASB, SIEM, GRC platform).
- Not a pattern for other MCNA staff to replicate without review. The shadow
  governance tradeoff is acceptable because Dave owns the decisions. It is not
  acceptable as an unreviewed template.
- Not a production system. It lives on Dave's workstation. Institutional knowledge
  survives in the synced docs. Execution capability does not transfer without a
  new owner taking on the risk posture explicitly.

---

## Change log
- 2026-04-14 — v1 — Initial roadmap. Eight Plays documented.
- 2026-04-17 — v1.1 — Play 3 (orphaned assets) built.
- 2026-04-17 — v1.2 — Play 3 write phase architecture documented.
- 2026-04-19 — v1.3 — Play 5 (Power Platform hygiene) built.
- 2026-04-21 — v2.0 — Play model retired. Roadmap rewritten around AMC platform
  architecture and domain agent build phases. MCP server approach adopted.
  Operating principles carried forward unchanged.
