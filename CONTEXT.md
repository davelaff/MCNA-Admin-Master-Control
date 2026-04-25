# CONTEXT.md — MCNA Admin Master Control

## Purpose

This file is the short, durable orientation for the repo.

Use it to answer, quickly:

- what this project is
- what it is trying to become
- what architectural model we are using
- what belongs here versus in other files

This file should stay short.

---

## What This Project Is

This repo is the seed workspace for `Master Control` (`MC`), a Microsoft estate
orchestration and governance platform for MCNA.

It is not a chatbot and not a pile of unrelated admin scripts.

It is intended to become:

- an orchestrator
- a control plane
- a governance intelligence backend
- an evidence-producing support layer for the 2026 IT-MIS governance program

---

## Problem It Solves

The Microsoft environment is too fragmented to govern well through portals and
manual checks alone.

Truth is spread across:

- Entra
- Exchange
- SharePoint and OneDrive
- Teams
- Intune
- Power Platform
- Power BI
- Security / Defender
- Purview
- Copilot / AI governance

MC exists to unify those surfaces and answer the questions MCNA actually needs:

- what exists
- who owns it
- whether it is governed
- whether it aligns to standards
- whether evidence exists
- what changed
- what matters now

---

## Architectural Model

The architectural unit is the `domain agent`, not the narrow scan.

**Platform:** Codex/Claude Code is Master Control. Domain agent capabilities are
exposed as MCP server tools. Two MCP server layers:

1. **Microsoft MCP Server for Enterprise** (hosted, Microsoft-managed) —
   Entra ID read-only via natural language over Microsoft Graph. Configured
   as a remote MCP server in the local MCP client settings. No auth code required.

2. **MCNA-AMC MCP Server** (local Python) — Power Platform, Intune, Exchange
   hygiene, Purview, Copilot governance, licensing, PIM, sharing posture,
   Conditional Access, the local knowledge base (SQLite), and eventual write
   operations. Uses existing MSAL auth pattern and app reg.

High-level model:

- domain agents collect and interpret domain state
- shared schemas normalize findings and governed objects across domains
- MC (Claude Code) correlates outputs across domains and across time
- outputs feed governance, evidence, risk, planning, and reporting

Prior prototype scripts are archived. They are seed capabilities only and
do not define the permanent architecture.

---

## Intended Domain Agents

- Entra Agent
- Exchange Agent
- SharePoint and OneDrive Agent
- Teams Agent
- Intune Agent
- Power Platform Agent
- Power BI Agent
- Security Agent
- Purview Agent
- Copilot and AI Governance Agent

These are the durable domain boundaries unless there is a strong reason to
change them.

---

## Core Rules

1. Domain-first, not task-first.
2. Read before write.
3. Shared schemas before major expansion.
4. Evidence matters as much as findings.
5. Cross-domain reasoning is the real value.
6. Human ownership and approval remain central.

---

## File Roles

- `CONTEXT.md`
  Short durable orientation and architectural center of gravity.

- `MEMORY.md`
  Living handoff, current-state facts, decisions made, and operational reality.

- `AGENTS.md`
  Codex-facing repo-specific working behavior and task execution guidance.

- `CLAUDE.md`
  Legacy Claude Code working behavior; should mirror `AGENTS.md` where possible.

- `ROADMAP.md`
  Strategic direction, history, and longer-range thinking.

- `ARCHITECTURE.md`
  Long-form design detail for Master Control.

- `docs/how-to-use-reports.md`
  Operator guide for interpreting domain scan reports, CSV exports, and audit binders.

---

## Relationship to the 2026 Governance Program

MC should eventually support:

- Secure SketCH work
- governance evidence production
- control-state visibility
- remediation planning
- leadership reporting
- audit readiness

It is broader than Secure SketCH, but Secure SketCH is one major consumer of
its outputs.

---

## Working Definition

Master Control is a Microsoft estate orchestration and governance platform.
Its agents are domain authorities, not single-purpose scanners.
