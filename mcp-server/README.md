# mcp-server

MCNA-AMC MCP Server — Python/FastMCP. Exposes all governance domain tools to Claude Code.

Full design: `../ARCHITECTURE.md`

## Entry points

| File | Purpose |
|---|---|
| `server.py` | FastMCP server registration, tool routing |
| `auth.py` | MSAL device-code flow, token cache management |
| `db.py` | SQLite KB access (`kb/mcna_amc.db`) |
| `graph.py` | Microsoft Graph API client wrapper |
| `refresh_auth.py` | Manual token refresh helper |

## tools/ domains

| Module | Domain |
|---|---|
| `ca.py` | Conditional Access policy scanning |
| `copilot.py` | Copilot license and settings audit |
| `entra.py` | Entra ID — users, guests, app registrations |
| `exo.py` | Exchange Online — mailboxes, forwarding |
| `intune.py` | Intune — devices, compliance policies |
| `kb.py` | Knowledge base — findings CRUD |
| `license.py` | License SKU and user assignment audit |
| `mail.py` | Mail send (admin account) |
| `pim.py` | Privileged Identity Management — roles |
| `pp.py` | Power Platform — environments, apps |
| `purview.py` | Purview — audit logs, sensitivity labels |
| `remediation.py` | Remediation plans and action queue |
| `sharing.py` | SharePoint external sharing scan |
| `ssk.py` | Secure SketCH — core controls, coverage, gaps |
| `ssk_actions.py` | SSK recommended action queue |
| `ssk_auditor.py` | SSK auditor package generation |
| `ssk_binder.py` | SSK audit binder export |
| `ssk_evidence.py` | SSK evidence linking and verification |
| `ssk_loader.py` | SSK catalog import |
| `ssk_matrix.py` | SSK control matrix and maturity dashboard |
| `ssk_registry.py` | SSK asset registry |
| `ssk_reviews.py` | SSK control review recording and history |

## kb/

SQLite knowledge base (`kb/mcna_amc.db`). Not git-tracked — preserved via OneDrive sync.
`kb/catalog-imports/` holds the SSK control catalog source JSON (git-tracked).

## tests/

271 tests covering all domain tools. Run from this directory:

```bash
rtk python -m pytest --tb=short -q
```
