# CONTEXT.md — Master Control / MCNA Tenant Intel

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

Master Control sits above domain agents and shared services.

High-level model:

- domain agents collect and interpret domain state
- shared schemas normalize findings and governed objects
- MC correlates outputs across domains and across time
- outputs feed governance, evidence, risk, planning, and reporting

Current prototype scripts are useful, but they are seed capabilities only.
They do not define the permanent architecture.

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

- `CLAUDE.md`
  Repo-specific working behavior and task execution guidance.

- `ROADMAP.md`
  Strategic direction, history, and longer-range thinking.

- `ARCHITECTURE.md`
  Long-form design detail for Master Control.

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
