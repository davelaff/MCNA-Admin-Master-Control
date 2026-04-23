# Scope Addition Record — Power Platform Scopes

| Field | Value |
|---|---|
| **Date** | 2026-04-20 |
| **App registration** | MCNA-TenantIntel-ReadOnly |
| **Requested by** | D. Lafferty (nof-dlafferty@nofmetalcoatings.us) |
| **Approved by** | D. Lafferty — IS Director, global admin |
| **Policy reference** | IT-GOV-ENTRA-v1.0 (self-approval authorized for IS Director) |

## Scopes added

| Scope | Type | Justification |
|---|---|---|
| Dynamics CRM: user_impersonation | Delegated | Dataverse Web API per org — required for `pp_*` tools reading environment/app/flow data |
| Power Apps Service: User | Delegated | BAP/PowerApps/Flow APIs — required for Power Platform hygiene scanner |

## Context

Added to support `mcp-server/tools/pp.py` (Power Platform domain tool).
First live scan same day: 12 environments, 3 findings (Medium).
Admin consent granted by nof-dlafferty@nofmetalcoatings.us.
