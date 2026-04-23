# MCNA Admin Master Control — Copilot Instructions

## What this is
Microsoft estate governance platform for NOF Metal Coatings NA. Primary artifact: `mcp-server/` — a Python MCP server exposing Graph/M365 domain tools + SQLite knowledge base.

Owner: Dave Lafferty, Director IT & MIS, global admin on Entra/Exchange/SharePoint/Teams/Power Platform.

## Code conventions
- Python, no type stubs required but type hints preferred
- One tool module per domain in `mcp-server/tools/` — don't combine domains
- All findings conform to shared schema in ARCHITECTURE.md
- Tests live in `mcp-server/tests/` — pytest, ~120 tests, all must pass
- No silent failures. Raise, don't swallow exceptions
- Read-only by default. Write operations must be explicit

## Key paths
- `mcp-server/server.py` — MCP server entry
- `mcp-server/tools/` — domain tool modules (entra, ca, pp, kb, ssk_*, license, pim, sharing)
- `mcp-server/kb/mcna_amc.db` — SQLite KB
- `mcp-server/auth.py` — MSAL token cache, two accounts (admin + primary)
- `mcp-server/graph.py` — Graph API wrapper

## Auth pattern
Two MSAL accounts. Admin: `nof-dlafferty@nofmetalcoatings.us`. Primary: `dlafferty@nofmetalcoatings.us`. Token caches at `~/.msal_token_cache_admin.json` and `~/.msal_token_cache_primary.json`. On 401/403: stop, don't retry.

## Writing style
Direct. No filler. No hedging. No corporate boilerplate. If uncertain, say so explicitly.
