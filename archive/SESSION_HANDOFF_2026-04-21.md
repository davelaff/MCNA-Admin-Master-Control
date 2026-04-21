# Session Handoff — 2026-04-21

## Purpose

Use this file to resume the Master Control planning session without
reconstructing the design conversation.

Read this first, then read:

1. `CONTEXT.md`
2. `MEMORY.md`
3. `ARCHITECTURE.md`

---

## What changed in this session

The project framing shifted significantly.

Previous framing: Master Control is a governance platform built around
domain agents, shared services, and a common finding schema.

**New framing: Master Control is a Secure SketCH / Secure Score
orchestrator.**

That is the correct and more precise end product. The domain-agent model
and shared schemas are still valid architectural ingredients, but they are
means, not ends. The end is: Dave inputs a Secure SketCH standard ID, MC
routes sub-questions to the right tools, and returns a dated evidence
package that proves where MCNA stands on that standard.

---

## The core design insight from this session

A Secure SketCH standard like 02-1 (Risk Identification and Evaluation)
requires a **composite answer** — multiple sub-questions across multiple
domains, merged into one evidence package.

Example for 02-1:
- Asset inventory across M365 domains → SharePoint/Teams/Entra tools
- Threat and identity risk signals → Entra + Security tools
- Configuration gap summary → Secure Score tool
- Evidence of prior review → dated prior artifacts in reports/

The orchestrator holds:
1. The **standard-to-question mapping** — what does this standard need answered?
2. The **question-to-tool routing** — which tool answers each sub-question?

Domain tools just answer sub-questions and emit findings in a common shape.
MC assembles the evidence package.

Simple questions (one domain, one answer) and composite questions (multiple
domains, merged artifact) are both valid orchestrator inputs.

---

## The build plan agreed in this session

### Phase 1 — Foundation (design work only, no new Python)

Three files to produce before writing any new code:

**1a. Standard-question mapping**
A YAML or JSON file mapping each Secure SketCH standard to the governance
questions it requires answered. Human-maintained. This is the orchestrator's
brain — without it MC doesn't know what to ask.

**1b. Common finding schema**
A single Python dataclass (or TypedDict) that every tool emits. Minimum
fields: `finding_id`, `domain`, `object_type`, `object_id`, `object_name`,
`severity`, `finding_type`, `recommended_action`, `control_mapping`,
`detected_at`, `source`.

Retrofit the three existing scanners to emit this shape. The schema is
proven against real data before anything new is built on top of it.

**1c. Evidence package format**
What MC returns when a standard is queried: standard ID and title, date,
findings by domain, coverage summary (which sub-questions were answered,
which weren't), artifact file pointer.

---

### Phase 2 — Orchestrator shell

**2a. `master_control.py`**
Entry point. Takes a standard ID as input (`mc run 02-1`), looks it up in
the standard-question mapping, fans out sub-questions to registered tools,
collects findings, assembles the evidence package, writes it to
`reports/secure-sketch/{standard-id}/YYYY-MM-DD.md`.

Start sequential. No parallelism needed yet. Routing table is a plain dict:
question type → function to call.

**2b. Register existing tools**
The three existing scanners become registered tools in MC's routing table.
They don't need structural changes — just need to emit the common finding
schema and be callable by the orchestrator rather than only standalone.

**2c. Secure Score tool**
New thin tool (~100 lines) pulling current score and open recommendations
via Graph `/security/secureScores` and `/security/secureScoreControlProfiles`.
Maps recommendations to the standard being queried. High value for low effort.

---

### Phase 3 — Domain coverage in standard-priority order

Extend domain tools only as specific standards need them. No speculative
tool building. Likely first targets:

- Identity and access (Entra) — roles, MFA, CA, guests, app regs
- Asset and configuration (SharePoint + Exchange) — inventory, ownership
- Security posture (Security) — Secure Score, Defender signals
- Platform governance (Power Platform) — already started

---

### Phase 4 — Memory and change detection

After MC is producing dated evidence packages:

- Suppression rules — known false positives that shouldn't re-fire
- Change detection — diff this run against prior run, surface what's new/resolved
- Review cycle tracking — MC alerts when a standard is due for re-run

---

## The question Dave needs answered before Phase 1 starts

Which Secure SketCH standards are currently "Initial" or "Developing" that
need to reach "Regularly Reviewed" as the 2026 priority? That list determines
the order of standard-question mapping entries and therefore the order in
which domain tools get built.

If you have the current Secure SketCH assessment scores, bring them into
this session. That's the input that drives Phase 1.

---

## What is NOT changing

- Read-first posture remains in force.
- Write/remediation paths remain separate, explicit, approval-bound.
- Existing scripts remain active and useful as prototype tools.
- The Play model is still deprecated as the top-level architecture.
- MCNA-TenantIntel-ReadOnly app reg is still the auth foundation.

---

## Doc debt noted in this session (low priority, do not block on these)

- `CLAUDE.md` and `AGENTS.md` still use Play framing throughout — should
  be recast around domain-agent ownership.
- `AGENTS.md` is a near-duplicate of `CLAUDE.md` — needs a distinct role
  or should be deleted.
- `MEMORY.md` lines 402–463 have a structural corruption (leftover script
  inventory block mid-section).
- Folder structure in `CLAUDE.md`, `AGENTS.md`, and `MEMORY.md` is stale —
  does not reflect `CONTEXT.md`, `ARCHITECTURE.md`, `AGENTS.md`,
  `SESSION_HANDOFF_2026-04-20.md`, or `docs/superpowers/`.
- `docs/superpowers/` exists but is undocumented in MEMORY.md open items.
- `SESSION_HANDOFF_2026-04-20.md` and `handoff-CA-policy-2026-04-17.md`
  belong in `archive/` once open items from them are confirmed captured.

---

## Working definition (unchanged)

`Master Control is a Microsoft estate orchestration and governance platform.
Its agents are domain authorities, not single-purpose scanners.`

**Refined for this phase:**

`MC takes a Secure SketCH standard as input, routes sub-questions to the
right tools, and returns a dated evidence package proving where MCNA stands
on that standard.`
