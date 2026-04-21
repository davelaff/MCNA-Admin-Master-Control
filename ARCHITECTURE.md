# ARCHITECTURE.md — Master Control

## Purpose

This file holds the longer-form architectural thinking for Master Control.

`CONTEXT.md` stays short.

This file is where the detail lives:

- architectural premises
- system layers
- domain-agent responsibilities
- shared services
- schema direction
- evidence model
- relationship to Secure SketCH and the 2026 governance program

---

## Platform Architecture

Master Control runs as Claude Code augmented by two MCP server layers.

```
┌─────────────────────────────────────────────────────┐
│                  Claude Code (AMC)                  │
│            CLAUDE.md = operational brain            │
└───────────────┬──────────────────┬──────────────────┘
                │                  │
   ┌────────────▼────┐    ┌────────▼────────────────┐
   │  Microsoft MCP  │    │   MCNA-AMC MCP Server   │
   │  Server for     │    │   (local Python)        │
   │  Enterprise     │    │                         │
   │  (hosted,       │    │  Domains: pp, entra,    │
   │   read-only)    │    │  ca, exo, license, pim, │
   │                 │    │  sharing, compliance,   │
   │  Entra ID:      │    │  mail, intune, copilot, │
   │  users, groups, │    │  purview, kb            │
   │  apps, devices, │    │                         │
   │  directory      │    │  Auth: MSAL + app reg   │
   │                 │    │  KB: SQLite (OneDrive-  │
   │  Auth: Entra    │    │  synced)                │
   │  delegated via  │    └─────────────────────────┘
   │  Claude Code    │
   └─────────────────┘
```

### MCNA-AMC MCP Server structure

```
mcp-server/
├── server.py          # MCP server entry point
├── auth.py            # MSAL token management
├── graph.py           # Shared Graph HTTP client
├── tools/             # One module per domain
│   ├── pp.py
│   ├── entra.py
│   ├── ca.py
│   ├── exo.py
│   ├── license.py
│   ├── pim.py
│   ├── sharing.py
│   ├── compliance.py
│   ├── mail.py
│   ├── intune.py
│   ├── copilot.py
│   ├── purview.py
│   └── kb.py
└── kb/
    └── mcna_amc.db    # SQLite knowledge base
```

### Knowledge base schema

Five tables: `tenant_snapshot`, `findings`, `baselines`, `dismissed`,
`activity_log`. KB tools: `kb_get_findings`, `kb_update_finding`,
`kb_dismiss`, `kb_get_snapshot`, `kb_diff_snapshot`.

---

## What Master Control Is

Master Control (`MC`) is a Microsoft estate orchestration and governance
platform.

It is not:

- a single chatbot
- a pile of one-off scripts
- a narrow reporting bot
- a set of disconnected scans

It is:

- an orchestrator
- a control plane
- a governance intelligence layer
- a backend system for making the Microsoft estate legible, governable,
  auditable, and actionable

The core design idea is that the Microsoft estate is too broad and fragmented
to govern well through portals and manual spot-checking alone. Identity,
messaging, collaboration, content, devices, automation, analytics, security,
compliance, and AI all create governance obligations. MC exists to unify those
surfaces and translate technical reality into governance meaning.

---

## Core Problem

The Microsoft environment spreads truth across too many surfaces:

- Entra
- Exchange Online
- SharePoint and OneDrive
- Teams
- Intune
- Power Platform
- Power BI
- Defender / Microsoft security
- Purview
- Copilot / agents / AI governance

Each surface has:

- its own admin center
- its own object model
- its own settings and policies
- its own activity records
- its own blind spots

The portals do not think like an architect, a governance lead, or an auditor.
They do not naturally answer the questions MCNA actually needs answered:

- what exists
- who owns it
- whether it is governed
- whether it aligns to standards
- whether there is evidence for the control
- what changed
- what matters now

MC is intended to answer those questions continuously.

---

## Architectural Premises

1. The architectural unit is the domain authority agent, not the narrow scan.
2. The highest-value output is cross-domain governance reasoning, not raw data.
3. The system must be read-oriented and evidence-oriented before it becomes
   action-oriented.
4. Shared schemas matter more than adding more narrow scripts.
5. The Secure SketCH assessment is a major consumer of MC outputs, but it is
   not the only reason MC exists.
6. MC should support the full 2026 IT-MIS governance program, not just security
   hygiene.

---

## Design Principles

### 1. Domain-First Architecture

Agents are organized around durable Microsoft domains, not today's immediate
task list.

### 2. Orchestrator, Not Monolith

Master Control coordinates work, merges outputs, maps governance meaning, and
supports decisions. It should not be treated as one fuzzy general-purpose
"super-agent."

### 3. Read Before Write

Collection, inventory, posture analysis, evidence design, and governance
mapping come first. Any write/remediation path must be separate, explicit, and
approval-bound.

### 4. Common Schemas

Every domain agent should emit findings and governed objects in a common form
so outputs can be correlated across time and across domains.

### 5. Evidence by Design

MC should produce artifacts that can be used in governance reviews, project
management, and audit readiness. It should not merely observe.

### 6. Human Accountability Remains Central

MC supports human decision-making, prioritization, and evidence assembly.
Ownership, approvals, and acceptance of risk remain human responsibilities.

### 7. Memory Compounds Value

The system should get more useful over time by retaining:

- prior outputs
- known false positives
- ownership realities
- historical decisions
- accepted exceptions
- control mappings

---

## System Layers

### Layer 1 — Domain Collection

Domain agents collect:

- inventories
- settings
- policies
- ownership
- usage/activity
- posture signals
- drift indicators

### Layer 2 — Normalization

Raw outputs are converted into shared records such as:

- assets
- findings
- evidence references
- control mappings
- risk items

### Layer 3 — Correlation and Reasoning

Master Control compares outputs:

- across domains
- across time
- against standards
- against expected control state

This is where technical reality becomes governance intelligence.

### Layer 4 — Governance Mapping

Findings are mapped to:

- Secure SketCH
- MCNA standards and policies
- future procedures/protocols
- internal objectives
- risk and exception handling

### Layer 5 — Planning and Action Support

MC should produce:

- remediation queues
- evidence asks
- review agendas
- leadership summaries
- project inputs

### Layer 6 — Archive and Memory

Runs, changes, outputs, evidence pointers, and important context are retained
so the system compounds in value rather than resetting every session.

---

## Domain Agent Catalog

### Entra Agent

Mission:
Identity and access governance.

Primary scope:

- users
- groups
- roles
- admin units
- app registrations
- enterprise apps
- service principals
- guests
- MFA
- Conditional Access
- authentication posture

Example functions:

- privileged role review
- app registration governance
- guest governance
- ownership and lifecycle review
- MFA and CA posture review
- entitlement and access drift detection

### Exchange Agent

Mission:
Messaging and mailbox governance.

Primary scope:

- user mailboxes
- shared mailboxes
- resource mailboxes
- forwarding
- delegates
- transport rules
- connectors
- messaging hygiene

Example functions:

- mailbox inventory
- risky forwarding review
- delegate review
- transport governance
- shared mailbox governance
- service account mailbox review

### SharePoint and OneDrive Agent

Mission:
Content, site, storage, and sharing governance.

Primary scope:

- site inventory
- ownership
- permissions
- sharing posture
- storage
- lifecycle
- site architecture
- stale or orphaned content/surfaces

Example functions:

- site ownership review
- permission drift analysis
- external sharing analysis
- stale site detection
- orphaned asset detection
- architecture conformance
- content governance signals

### Teams Agent

Mission:
Collaboration and workspace governance.

Primary scope:

- teams
- channels
- shared channels
- guest access
- external access
- ownership
- policies
- meeting/collaboration posture

Example functions:

- team inventory
- owner validation
- external collaboration review
- lifecycle governance
- policy drift detection

### Intune Agent

Mission:
Endpoint, device, and compliance governance.

Primary scope:

- managed devices
- compliance policies
- configuration profiles
- security baselines
- enrollment posture
- app protection

Example functions:

- device inventory
- compliance posture review
- baseline conformance
- profile drift analysis
- endpoint governance reporting

### Power Platform Agent

Mission:
Low-code platform governance.

Primary scope:

- environments
- apps
- flows
- solutions
- connection references
- makers
- DLP
- ALM
- Dataverse posture
- Copilot Studio surfaces where relevant

Example functions:

- environment governance
- maker governance
- departed-owner analysis
- ALM hygiene
- DLP alignment
- connection and integration risk review

### Power BI Agent

Mission:
Analytics and reporting governance.

Primary scope:

- workspaces
- reports
- semantic models
- gateways
- admins
- tenant settings
- sharing posture

Example functions:

- workspace governance
- stale analytics detection
- gateway exposure review
- admin and sharing posture review

### Security Agent

Mission:
Threat and security operations posture.

Primary scope:

- Defender-related signals
- alerts
- incidents
- security posture
- exposure indicators
- security operations readiness

Example functions:

- security finding intake
- posture summary
- alert and incident correlation
- secure score style signals
- control-readiness signals

### Purview Agent

Mission:
Compliance, information protection, and records governance.

Primary scope:

- sensitivity labels
- retention
- DLP
- records
- audit
- eDiscovery readiness
- data governance/security signals

Example functions:

- label coverage review
- retention policy mapping
- DLP posture analysis
- records readiness
- evidence and audit readiness support

### Copilot and AI Governance Agent

Mission:
AI enablement and guardrail governance.

Primary scope:

- Microsoft 365 Copilot
- agents
- Work IQ-related governance
- Copilot Studio
- approved AI use patterns
- adoption evidence
- access and data-boundary posture

Example functions:

- AI feature inventory
- governance settings review
- approved pattern monitoring
- adoption evidence tracking
- AI readiness reporting

---

## Shared Services

### Asset Registry Service

Maintains normalized governed objects across domains.

### Finding Service

Stores normalized findings from all agents.

### Control Mapping Service

Maps findings to:

- Secure SketCH controls
- MCNA standards
- future procedures
- internal objectives

### Evidence Service

Tracks:

- what evidence should exist
- what evidence exists
- where it lives
- which controls it supports

### Risk and Exception Service

Turns findings into:

- risk items
- exceptions
- aging issues
- compensating controls
- review deadlines

### Change Detection Service

Compares runs over time and identifies meaningful deltas.

### Planning Service

Translates outputs into:

- remediation work
- project inputs
- leadership briefings
- review agendas

### Memory Service

Retains:

- known false positives
- architectural decisions
- ownership realities
- historical context
- prior findings and treatment

---

## Common Finding Schema

Every agent should eventually emit a shared finding model.

Minimum fields:

- `finding_id`
- `domain`
- `object_type`
- `object_id`
- `object_name`
- `owner`
- `finding_type`
- `severity`
- `status`
- `control_mapping`
- `recommended_action`
- `evidence_required`
- `evidence_pointer`
- `detected_at`
- `source_run`
- `notes`

This is more important than adding many more narrow scripts.

---

## Evidence Model

MC should intentionally produce evidence-capable outputs.

Core evidence families:

- inventory evidence
- configuration evidence
- activity evidence
- review evidence
- remediation evidence
- reporting evidence

MC is valuable partly because it can become an evidence-producing backend for:

- Secure SketCH
- the 2026 governance project
- audit readiness
- leadership review

---

## Relationship to Secure SketCH and the 2026 Governance Program

Secure SketCH is a major consumer of MC outputs.

MC should eventually help answer:

- what current control state actually is
- where evidence exists or does not exist
- what findings map to specific Secure SketCH controls
- what remediation actions belong in the annual plan
- what artifacts should be retained for review or audit

More broadly, MC should support the full 2026 IT-MIS Security and Governance
program by providing:

- domain visibility
- normalized findings
- evidence tracking
- risk inputs
- planning inputs
- executive-ready status views

---

## Relationship to the Current Repo

The current repo contains narrow prototype capabilities.

Those prototypes remain useful, but they should now be understood as:

- seed functions
- early probes
- proof-of-concept routines

They do not define the permanent architecture.

Example:

- `orphaned_asset_scanner.py` is not a top-level architecture concept
- it is one capability that would eventually belong inside the
  `SharePoint and OneDrive Agent` and possibly also intersect with
  `Teams Agent`

Likewise:

- app registration governance belongs inside `Entra Agent`
- Power Platform hygiene belongs inside `Power Platform Agent`
- DIS daily summary is a narrow operational task, not the long-term system model

---

## Build Direction

The right next move is not to keep multiplying narrow scans under the old
`Play` model.

The right next move is:

1. Stabilize the architecture.
2. Define durable context and memory files.
3. Define the common finding and evidence schemas.
4. Recast existing prototypes under domain-agent boundaries.
5. Build cross-domain services once shared structures are stable.

---

## Immediate Priorities

1. Build the MCNA-AMC MCP Server (`mcp-server/`) with shared auth, graph client,
   KB schema, and the first domain tools.
2. Configure Microsoft MCP Server for Enterprise in Claude Code MCP settings.
3. Define the common finding schema (see above) before expanding tool surface.
4. First domain tools to build: `entra`, `ca`, `pp`, `kb` — highest SecureSketCH
   value and most directly fed by existing prototype logic.
5. Tie every tool output to the KB so findings accumulate over time rather than
   resetting each session.
