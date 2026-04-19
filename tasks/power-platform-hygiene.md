# Task: Power Platform Hygiene Scanner
Last updated: 2026-04-19

## Implementation
Script: `power_platform_hygiene.py`
Schedule: On demand (run weekly or after PP environment changes)
Status: Active, v1. Built 2026-04-19. Read phase only.
Output: `reports/power-platform-hygiene/YYYY-MM-DD.md` + `YYYY-MM-DD.csv`

---

## What it does
Inventories all Power Platform environments, canvas apps, flows, solutions,
and connection references. Flags production workloads in the wrong environment,
connections owned by departed staff, solutions that were never promoted, and
unused environments consuming capacity. Produces a prioritized findings report.

Write phase is NOT built. Every item in the output is a recommended action
for Dave to review. Nothing is modified automatically.

## Auth
Primary account (`dlafferty@nofmetalcoatings.us`).
Cache: `C:/Users/dlafferty.MCNA/.msal_token_cache_primary.json`

Three token audiences — all acquired via the same MSAL PublicClientApplication:

| Token | Scope | Used for |
|-------|-------|---------|
| `graph_token` | `https://graph.microsoft.com/.default` | Active user roster |
| `pp_token` | `https://api.bap.microsoft.com/.default` | Environment list, apps, flows |
| `dv_token` (per env) | `https://{org_url}/.default` | Solutions, connection references |

Scopes required on MCNA-TenantIntel-ReadOnly (must be granted before first run):
- `Directory.Read.All` — already granted (user roster cross-reference)
- `Dynamics CRM: user_impersonation` — **new, must be added** (Dataverse Web API)
- `Power Apps Service: user_impersonation` — **new, must be added** (BAP, PowerApps, Flow APIs)

## API endpoints (in order)

### 1. Graph — active user roster
```
GET https://graph.microsoft.com/v1.0/users
  ?$select=id,displayName,userPrincipalName,mail,accountEnabled,userType
  &$top=999
```
Builds `active_upns: set[str]` of lowercased UPNs where `accountEnabled = true`.

### 2. Power Platform — all environments
```
GET https://api.bap.microsoft.com/providers/Microsoft.BusinessAppPlatform/environments
  ?api-version=2016-11-01
  &$expand=properties/linkedEnvironmentMetadata
```
Returns all environments with type, display name, location, Dataverse org URL (if any),
created date.

### 3. PowerApps — canvas apps per environment
```
GET https://api.powerapps.com/providers/Microsoft.PowerApps/apps
  ?$filter=environment.name eq '{env_name}'
  &api-version=2016-11-01
  &$top=250
```
Returns: displayName, environment ref, createdTime, lastModifiedTime, owner UPN,
sharedWith count. Paginated via `@odata.nextLink`.

### 4. Power Automate — flows per environment
```
GET https://api.flow.microsoft.com/providers/Microsoft.ProcessSimple/environments/{env_name}/flows
  ?api-version=2016-11-01
  &$top=250
```
Returns: displayName, state (Started/Stopped), createdTime, lastModifiedTime,
creator UPN. Paginated.

### 5. Dataverse — solutions (per org URL, if environment has Dataverse)
```
GET https://{org_url}/api/data/v9.2/solutions
  ?$select=uniquename,friendlyname,version,ismanaged,createdon,modifiedon
  &$filter=isvisible eq true
```
Returns all solutions visible in the customization UI. Used for promotion check.

### 6. Dataverse — connection references (per org URL)
```
GET https://{org_url}/api/data/v9.2/connectionreferences
  ?$select=connectionreferencedisplayname,connectorid,connectionid,createdon
  &$expand=createdby($select=fullname,internalemailaddress,isdisabled)
```
Returns connection references with creating user details.

## Analysis logic

### Flag 1 — Canvas apps in Default environment
Default environment is identified by `type == "Default"` in the BAP API response.
For each canvas app in the Default environment:

| Condition | Severity |
|-----------|----------|
| sharedWith > 5 users | High — looks like production workload in wrong env |
| sharedWith 1–5 users | Medium — shared but not clearly production |
| sharedWith = 0 | Low — personal app, normal for developers |

Recommended action (High): Move to a dedicated Production environment.

### Flag 2 — Connection references owned by departed/disabled staff
For each connection reference:

| Condition | Severity |
|-----------|----------|
| `createdby.isdisabled = true` OR email not in `active_upns` | High |

Rationale: the underlying connection credential belongs to an account the owner
can no longer manage. Connection may be silently broken; apps/flows depending on
it could fail without warning.

### Flag 3 — Solutions not promoted to production
1. Collect all solution `uniquename` values from environments of type `Production`.
2. For each solution in Sandbox or Developer environments:
   - If `uniquename` not found in any Production environment → flag.

| Condition | Severity |
|-----------|----------|
| Unmanaged solution in dev/sandbox with no prod counterpart | Medium |

Managed solutions (ismanaged = true) are excluded — those are installed packages,
not developer artifacts awaiting promotion.

### Flag 4 — Unused environments
An environment is flagged if ALL of:
- Type is not Default or Production
- Zero canvas apps AND zero flows
- Created more than 90 days ago

| Condition | Severity |
|-----------|----------|
| Unused non-production environment (see above) | Medium |
| Trial environment (any) | Low — auto-expires, track for renewal |
| Developer environment owned by departed user | Low |

## Output files
- `reports/power-platform-hygiene/YYYY-MM-DD.md` — findings grouped by severity
- `reports/power-platform-hygiene/YYYY-MM-DD.csv` — flat file, UTF-8 BOM (Excel-compatible)
- Append to `activity-log.md`

## Output columns (CSV)
Type, Display Name, Environment, Owner, Created, Last Modified, Max Severity, Findings, Recommended Action

Sorted by Max Severity (High → Medium → Low), then Display Name alphabetically.

## Activity log entry
Success: `YYYY-MM-DD HH:MM — Power Platform hygiene scan — {N} environments, {M} findings (High: n, Medium: n, Low: n) — reports/power-platform-hygiene/YYYY-MM-DD.md`
Failure: `YYYY-MM-DD HH:MM — Power Platform hygiene scan — FAILED — {reason}`

## Guardrails
- Read-only throughout — no writes to Power Platform, no modification of any environment, app, flow, or solution
- 401/403 on any API call: stop immediately, write FAILED to activity-log.md
- Dataverse endpoints returning 404 (env has no Dataverse): skip gracefully, note in output
- No email delivery — output is local files only
- Do not include full app/flow descriptions — display names and metadata only

## Change log
- 2026-04-19 — v1 — Initial spec. Read phase only.
