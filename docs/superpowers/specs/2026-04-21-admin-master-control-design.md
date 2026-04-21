# MCNA Admin Master Control — Design Spec
Date: 2026-04-21
Status: Approved

---

## 1. Architecture Overview

Master Control runs as Claude Code augmented by two MCP server layers. Claude Code IS the orchestrator — no separate Python application, no custom conversation loop.

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

**Microsoft MCP Server for Enterprise** — remote hosted server at
`https://mcp.svc.cloud.microsoft/enterprise`. Translates natural language
into Graph API calls. Three tools: `microsoft_graph_suggest_queries`,
`microsoft_graph_get`, `microsoft_graph_list_properties`. Read-only, public
preview. Configured as a remote MCP server in Claude Code settings. No auth
code required — authenticates via Dave's Entra admin account through Claude
Code's OAuth flow.

**MCNA-AMC MCP Server** — local Python process (`mcp-server/`). Covers all
domains not provided by Microsoft's server, plus the persistent knowledge base.
Authenticates via MSAL device code flow with cached tokens. Registered as a
local MCP server in Claude Code settings.

**Claude Code MCP configuration (`.claude/settings.json`):**
```json
{
  "mcpServers": {
    "microsoft-enterprise": {
      "type": "remote",
      "url": "https://mcp.svc.cloud.microsoft/enterprise"
    },
    "mcna-amc": {
      "type": "stdio",
      "command": "python",
      "args": ["mcp-server/server.py"]
    }
  }
}
```

**Interaction modes:**
- Interactive: open-ended conversation in Claude Code, AMC reasons across
  domains, queries tools as needed, synthesizes findings
- One-shot: invoked with a specific task argument, executes, exits

**No scheduling in v1.** Interactive and on-demand only.

---

## 2. Knowledge Base

SQLite database at `mcp-server/kb/mcna_amc.db`. Lives inside the OneDrive-synced
project folder — gets version history and retention labels automatically.
Owned exclusively by the custom MCP server. Claude Code accesses it only via
`kb_*` tools, never directly.

### Schema

**`tenant_snapshot`**
One row per entity. Updated each scan. Enables drift detection.
```
entity_type    TEXT    -- user, app_reg, pp_environment, ca_policy, device, etc.
entity_id      TEXT    -- Graph object ID or equivalent
entity_name    TEXT
domain         TEXT    -- which AMC domain owns this entity
properties     TEXT    -- JSON blob of current state
last_scanned   TEXT    -- ISO 8601 timestamp
```

**`findings`**
Every flagged item from any domain scan.
```
finding_id          TEXT PRIMARY KEY
domain              TEXT
object_type         TEXT
object_id           TEXT
object_name         TEXT
owner               TEXT
finding_type        TEXT
severity            TEXT    -- Critical / High / Medium / Low
securesketch_control TEXT   -- control ID if mapped, NULL otherwise
recommended_action  TEXT
evidence_pointer    TEXT    -- path to report artifact if any
status              TEXT    -- open / acknowledged / resolved
first_seen          TEXT
last_seen           TEXT
source_run          TEXT
notes               TEXT
```

**`baselines`**
Known-good state for drift detection.
```
entity_type    TEXT
entity_id      TEXT
baseline_json  TEXT    -- expected property state
set_by         TEXT
set_at         TEXT
notes          TEXT
```

**`dismissed`**
Accepted-risk items with reason and date. Prevents re-flagging noise Dave
has explicitly evaluated.
```
finding_id     TEXT
dismissed_at   TEXT
reason         TEXT
```

**`activity_log`**
Every tool invocation. Replaces the append-to-markdown pattern with something
queryable. `activity-log.md` at the project root can be generated from this.
```
run_id         TEXT PRIMARY KEY
timestamp      TEXT
tool_name      TEXT
domain         TEXT
entity_id      TEXT
outcome        TEXT    -- success / error / empty
detail         TEXT
```

### KB tools exposed to Claude Code

| Tool | Purpose |
|---|---|
| `kb_get_findings` | Query open findings, filterable by domain / severity / control |
| `kb_update_finding` | Acknowledge or resolve a finding |
| `kb_dismiss` | Move a finding to dismissed with a reason |
| `kb_get_snapshot` | Retrieve current snapshot state for one or more entities |
| `kb_diff_snapshot` | Compare current scan results against last snapshot, return only deltas |

---

## 3. MCNA-AMC MCP Server — Tool Surface

Thirteen domains. Each domain is a module in `mcp-server/tools/`. Tools are
named `{domain}_{verb}` and always write scan results to the KB before returning.

| Domain | Module | Key tools |
|---|---|---|
| Power Platform | `pp.py` | `pp_scan_environments`, `pp_scan_apps`, `pp_scan_flows`, `pp_scan_connections`, `pp_scan_solutions` |
| Entra governance | `entra.py` | `entra_scan_app_regs`, `entra_scan_guests`, `entra_scan_orphaned_assets` |
| Conditional Access | `ca.py` | `ca_scan_policies`, `ca_scan_coverage_gaps` |
| Exchange hygiene | `exo.py` | `exo_scan_forwarding`, `exo_scan_shared_mailboxes`, `exo_scan_transport_rules` |
| Licensing | `license.py` | `license_scan_unassigned`, `license_scan_duplicates` |
| PIM | `pim.py` | `pim_scan_permanent_assignments`, `pim_scan_stale_eligible` |
| External sharing | `sharing.py` | `sharing_scan_sites`, `sharing_scan_drives`, `sharing_scan_teams` |
| Compliance | `compliance.py` | `compliance_get_secure_score`, `compliance_map_to_securesketch`, `compliance_draft_remediation` |
| Mail | `mail.py` | `mail_send_summary` |
| Intune | `intune.py` | `intune_scan_devices`, `intune_scan_compliance`, `intune_scan_bitlocker` |
| Copilot | `copilot.py` | `copilot_scan_license_utilization`, `copilot_scan_label_coverage`, `copilot_scan_oversharing` |
| Purview | `purview.py` | `purview_scan_label_coverage`, `purview_scan_dlp_policies`, `purview_query_audit_log` |
| Knowledge base | `kb.py` | `kb_get_findings`, `kb_update_finding`, `kb_dismiss`, `kb_get_snapshot`, `kb_diff_snapshot` |

---

## 4. Project Structure

```
MCNA-Admin-Master-Control/
│
├── CLAUDE.md                    # Operational brain
├── CONTEXT.md                   # Short architecture orientation
├── ARCHITECTURE.md              # Full AMC design reference
├── MEMORY.md                    # Living handoff and current state
├── ROADMAP.md                   # Strategic direction and build phases
├── README.md                    # 5-line orientation
├── activity-log.md              # Append-only task log (generated from KB)
├── Secure_SketCH_Guidelines_2026-01-01.docx
│
├── mcp-server/                  # Primary build artifact
│   ├── server.py                # MCP server entry point
│   ├── auth.py                  # MSAL token management (single account)
│   ├── graph.py                 # Shared Graph HTTP client
│   ├── tools/
│   │   ├── pp.py
│   │   ├── entra.py
│   │   ├── ca.py
│   │   ├── exo.py
│   │   ├── license.py
│   │   ├── pim.py
│   │   ├── sharing.py
│   │   ├── compliance.py
│   │   ├── mail.py
│   │   ├── intune.py
│   │   ├── copilot.py
│   │   ├── purview.py
│   │   └── kb.py
│   ├── kb/
│   │   └── mcna_amc.db          # SQLite (OneDrive-synced)
│   └── requirements.txt
│
├── reports/                     # Scan outputs and governance artifacts
├── docs/
│   ├── auth/
│   │   └── app-registrations.md
│   └── superpowers/
│       ├── plans/
│       └── specs/
│
└── archive/                     # Retired scripts, session artifacts
```

---

## 5. Authentication

Single account for all MCP server domains: `nof-dlafferty@nofmetalcoatings.us`.

**`auth.py`** loads `.env` from `C:\Users\dlafferty.MCNA\mcna-tenantintel.env`
and initializes one MSAL public client application pointing at
`C:/Users/dlafferty.MCNA/.msal_token_cache_admin.json`. Tokens are reused
if valid; device code flow fires only when expired or missing.

**Device code prompt** appears in the Claude Code terminal. Dave authenticates,
token caches, server continues. Fires only on first use or after token expiry.

**Microsoft MCP Server for Enterprise** authenticates separately via Claude
Code's OAuth flow. No shared auth infrastructure with the custom server.

**App registration:** MCNA-TenantIntel-ReadOnly. Current scopes documented in
`docs/auth/app-registrations.md`. Additional scopes needed for `intune_*` and
`exo_*` domains before those tools are built (see Phase 2/3 in ROADMAP.md).

---

## 6. Error Handling

| Failure mode | Behavior |
|---|---|
| 401 / 403 from Graph | Raise immediately. Structured error: domain, endpoint, status. No retry. Log to `activity_log`. |
| 429 throttling | Respect `Retry-After`, retry once. If second attempt also 429s, raise as tool error. Log throttle event. |
| Unexpectedly empty result | Flag explicitly rather than returning clean empty. Each tool specifies what "suspiciously empty" looks like for its domain. |
| SQLite write failure | Roll back transaction, raise. No partial KB updates. |
| MCP server crash | Claude Code surfaces tool unavailability. Dave investigates and restarts. KB is durable — no state lost. |

---

## 7. Build Priority

Phase 1 (first build): shared infrastructure + `kb.py`, `entra.py`, `ca.py`, `pp.py`.
These provide the highest SecureSketCH value and most directly replace existing
prototype logic from the archived Play scripts.

Full phase roadmap in `ROADMAP.md`.

---

## Decisions recorded

| Decision | Rationale |
|---|---|
| Claude Code as AMC, not standalone Python app | Orchestration layer already exists; build the tools, not the framework |
| Microsoft MCP Server for Enterprise for Entra reads | No Graph code to write; free, already built, logs to Graph activity logs |
| Custom MCP server for all other domains | Covers PP, Intune, Purview, CA, etc. + local KB that Microsoft's server can't provide |
| SQLite for KB | Local, queryable, OneDrive-synced, no infrastructure to provision |
| Single auth account (admin) for all domains | Simpler, cleaner; primary account no longer needed by MCP server |
| No scheduling in v1 | Interactive and on-demand first; get the tool surface right before automating |
| Graph REST only (no PowerShell in the server) | Avoids subprocess spawning complexity and second auth surface; PS remains useful for Dave's own ad-hoc queries |
