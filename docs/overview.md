# MCNA Admin Master Control — Plain English Overview

## What is this?

Admin Master Control (AMC) is a security governance tool for MCNA's Microsoft 365 tenant. It automatically scans the M365 environment for security problems and compliance gaps, stores findings in a local database, and produces audit-ready evidence packages for the Secure SketCH framework.

It runs inside **Claude Code** — the AI assistant CLI. Claude is the interface. The MCP servers are the tools Claude uses to actually query Microsoft and maintain state.

---

## What problem does it solve?

MCNA scores well on Secure SketCH because policies are written and maturity is marked "Implemented." But there's no evidence trail proving it. If an auditor asks "show me how you manage privileged access," the answer needs to be more than "we have a policy document."

AMC closes that gap. Every scan it runs produces findings that get mapped to specific Secure SketCH controls. Those findings become evidence. Evidence gets bundled into per-control audit binders — markdown files with a findings table, linked evidence, review history, and recommended actions.

---

## How it's built

Two layers sit underneath Claude:

**Layer 1 — Microsoft MCP Server for Enterprise** (Microsoft-hosted)
Reads Entra ID: users, groups, apps, devices, directory. You don't run this; it's a remote server Microsoft operates. Claude connects to it via OAuth through your admin account.

**Layer 2 — MCNA-AMC MCP Server** (runs locally, `mcp-server/`)
Everything else: Exchange, Licensing, PIM roles, SharePoint sites, Intune devices, Purview labels, Power Platform. Also manages the local SQLite knowledge base where all findings live.

The local server is a Python process. Claude Code starts it automatically using the config in `.mcp.json`.

---

## What it scans (current domains)

| Domain | What it looks for |
|---|---|
| Entra ID | App registrations without owners, guest users without sponsors |
| Conditional Access | Policy gaps: no MFA, legacy auth not blocked, admin accounts unprotected |
| Exchange | Shared mailboxes with interactive login enabled, inbox rules that forward externally |
| Licensing | Overage on SKUs, unused prepaid seats, licensed-but-disabled accounts, productivity stacking |
| PIM / Roles | Permanent privileged assignments (no P2 = everything is permanent), privileged roles on non-admin accounts |
| SharePoint | Sites untouched for 1+ or 2+ years |
| Intune | Devices out of compliance, encryption gaps, stale enrollments |
| Purview | Sensitivity label coverage, audit log activity |
| Power Platform | Environments and apps, orphaned or ungoverned |

Each scan writes findings to the local database. Findings include: what was found, which Secure SketCH control it maps to, severity, and first/last seen timestamps.

---

## How to use it

### Starting a session

Open Claude Code in this folder. That's it. Claude loads the MCP servers automatically. Check that tools are available — you should see `mcna-amc` tools in the tool list.

If the MCP server isn't responding, restart it: open the Claude Code MCP settings and restart the `mcna-amc` server.

### Running a scan

Ask Claude to run a scan. Examples:

- "Run exo_scan_mailboxes and exo_scan_forwarding"
- "Run license_scan_skus"
- "Run pim_scan_role_assignments"

Claude calls the tool, the tool queries Microsoft Graph, findings are written to the KB automatically, and Claude summarizes what it found.

### Reviewing findings

Ask Claude to pull findings from the knowledge base:

- "What are the current High findings?"
- "Show me findings for control 08-1"
- "What's been found since last week?"

Claude uses `kb_get_findings` to query the SQLite DB and returns results directly.

### Exporting audit binders

Ask Claude to generate a binder for a control:

- "Export a binder for control 08-6"
- "Generate binders for 06-3, 08-1, and 15-4"

Binders are written to `reports/audit-binders/` as markdown files. Each binder contains:
- A findings table (pulled from the KB)
- An evidence section (linked files or SharePoint URLs)
- Review history (any attestations recorded)
- Recommended actions with status

### Linking evidence to controls

Scan findings are automatically linked. For manual evidence (policy documents, SharePoint links, attestations), ask Claude:

- "Link the CA policy document as evidence for control 08-2"
- "Record an attestation for control 15-3 — reviewed and confirmed acceptable"

---

## Authentication

The local MCP server authenticates to Microsoft Graph using an MSAL token cache. The token is cached on disk and survives across sessions — you usually don't need to re-authenticate.

**When a scan fails with a token error:**

```
python mcp-server/refresh_auth.py
```

This opens a device code flow in the terminal. Sign in with `nof-dlafferty@nofmetalcoatings.us`. The new token is written to the cache. Run the scan again.

The two accounts in use:
- `nof-dlafferty@nofmetalcoatings.us` — admin account, used for most Graph queries
- `dlafferty@nofmetalcoatings.us` — primary account, used for Power Platform queries

---

## Where things live

| Path | What's there |
|---|---|
| `mcp-server/` | The local MCP server (Python) |
| `mcp-server/kb/mcna_amc.db` | SQLite database — all findings, evidence, reviews |
| `mcp-server/tools/` | One file per domain (entra.py, exo.py, pim.py, etc.) |
| `mcp-server/refresh_auth.py` | Re-authentication script |
| `reports/audit-binders/` | Exported audit binders (markdown) |
| `reports/app-reg-governance/` | Historical Entra app reg scan outputs |
| `docs/` | Design specs, auth records, governance docs |
| `MEMORY.md` | Session handoff — what was built, what's next |
| `ARCHITECTURE.md` | Full technical design reference |
| `ROADMAP.md` | Strategic direction and version history |

---

## Current state (as of 2026-04-23)

- **201 tests passing**
- **Phase 3 in progress** — 6 domain scan tools built, all on main
- **7 of 73 Secure SketCH controls** have automated scan coverage
- **EXO live scans not yet run** — domain built, scope consented, just needs execution
- **Purview** needs one additional scope consent (`InformationProtectionPolicy.Read.All`) before label scans will work

---

## What it is not

- Not a real-time monitoring tool. It scans on demand.
- Not an automated remediation tool. It finds and documents; it does not fix.
- Not a MCNA-wide deployment template. It's Dave's workbench. Turning it into a shared platform would need a formal governance review.
