# Session Handoff — 2026-04-20

## Purpose

Use this file to resume the project without reconstructing the last design
conversation.

Read this first, then read:

1. `CONTEXT.md`
2. `MEMORY.md`
3. `ARCHITECTURE.md` if deeper design detail is needed

---

## Current position

This repo is no longer being treated as just a collection of narrow admin
scripts.

It is now being treated as the seed workspace for `Master Control` (`MC`), a
Microsoft estate orchestration and governance platform for MCNA.

The earlier `Play` framing is deprecated.

Current scripts remain useful, but they are now understood as prototype
capabilities rather than long-term architectural units.

---

## Core architectural decisions already made

### 1. Master Control is an orchestrator, not a single agent

MC is intended to act as:

- an orchestrator
- a control plane
- a governance intelligence backend
- an evidence-producing support layer for the 2026 IT-MIS governance program

### 2. Domain agents are the durable architectural units

The intended domain-agent model is:

- `Entra Agent`
- `Exchange Agent`
- `SharePoint and OneDrive Agent`
- `Teams Agent`
- `Intune Agent`
- `Power Platform Agent`
- `Power BI Agent`
- `Security Agent`
- `Purview Agent`
- `Copilot and AI Governance Agent`

### 3. Shared services matter more than more narrow scripts

The architecture assumes shared services for:

- findings
- evidence
- control mapping
- risk and exceptions
- change detection
- planning
- memory

### 4. Shared schemas are a first-class requirement

The most important technical design constraint identified so far:

do not keep multiplying narrow workers before defining common schemas.

The common finding model matters more than adding more one-off scans.

### 5. Read-first posture remains in force

The system should stay read-oriented and evidence-oriented before it becomes
write-capable.

Any future remediation path should be explicit, approval-bound, and separate
from read-side collection.

---

## What the current scripts now represent

These are prototypes, not top-level architecture:

- `app_reg_scanner.py` -> future `Entra Agent` capability
- `orphaned_asset_scanner.py` -> future `SharePoint and OneDrive Agent`
  capability, possibly intersecting with `Teams Agent`
- `power_platform_hygiene.py` -> future `Power Platform Agent` capability
- `dis_daily_summary.py` -> narrow operational task, not long-term architecture
- `ms_learn_scraper.py` -> research/support utility

---

## Important repo-document decisions

- `CONTEXT.md` is now intentionally short and should remain short.
- `ARCHITECTURE.md` contains the long-form design model.
- `MEMORY.md` is the living current-state and handoff file.
- `ROADMAP.md` still has historical value, but the old narrow `Play` model is
  no longer the governing architecture.

---

## Known design debt and tensions

These should be treated as real design debt, not ignored:

- authentication model drift between stated principles and current
  implementation
- certificate handling posture needs reconciliation
- doc-to-reality drift in parts of the repo
- duplicated auth/http/logging patterns across scripts
- current repo mixes operational utilities with future-platform architecture

---

## Recommended next decision

Decide whether to split this work into two repos now.

Recommended split:

### Repo A: Master Control

Keep here:

- `CONTEXT.md`
- `ARCHITECTURE.md`
- `MEMORY.md`
- schema specs
- orchestrator design
- domain-agent definitions
- governance mapping and planning docs

### Repo B: operational worker toolkit

Move or recreate there:

- `app_reg_scanner.py`
- `orphaned_asset_scanner.py`
- `power_platform_hygiene.py`
- `dis_daily_summary.py`
- `ms_learn_scraper.py`
- `auth/`
- `tasks/`
- `reports/`
- `activity-log.md`
- runtime-focused support docs

Rationale:

the repo currently contains two valid but different systems:

- a functional operational toolkit
- an emerging orchestration platform

Trying to force both identities into one repo will keep the project muddy.

---

## If resuming work immediately

The most defensible next steps are:

1. decide on repo split vs in-place restructure
2. define the common finding schema as a real spec file
3. define the evidence model as a real spec file
4. choose the first 3-4 domain agents to formalize
5. only then decide how current prototype capabilities should be recast

---

## Working definition

`Master Control is a Microsoft estate orchestration and governance platform. Its agents are domain authorities, not single-purpose scanners.`
