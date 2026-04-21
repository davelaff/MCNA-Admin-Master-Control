# Task: App Registration Governance Scanner
Last updated: 2026-04-17

## Implementation
Script: `app_reg_scanner.py`
Schedule: On demand (run manually, weekly or after Entra change events)
Status: Active, v1. Built 2026-04-17.
Output: `reports/app-reg-governance/YYYY-MM-DD.md` + `YYYY-MM-DD.csv`

---

## What it does
Inventories every app registration and enterprise app in the tenant. Scores findings
by severity. Writes a risk register to `reports/app-reg-governance/`. No email
delivery — this is a run-on-demand report, not a daily summary.

## Auth
Admin account only (`nof-dlafferty@nofmetalcoatings.us`).
Cache: `C:/Users/dlafferty.MCNA/.msal_token_cache_admin.json`
No second account needed — no mail read required.

Scopes required (all already granted on MCNA-TenantIntel-ReadOnly):
- Application.Read.All
- AuditLog.Read.All
- Directory.Read.All
- Reports.Read.All
- User.Read

## Graph queries (in order)

1. App registrations (MCNA-owned):
```
GET /v1.0/applications
  ?$select=id,appId,displayName,createdDateTime,signInAudience,
           requiredResourceAccess,passwordCredentials,keyCredentials,web,publicClient,spa
  &$expand=owners($select=id,displayName,userPrincipalName)
  &$top=999
```

2. Service principals (enterprise apps + first-party SP entries):
```
GET /v1.0/servicePrincipals
  ?$select=id,appId,displayName,appOwnerOrganizationId,verifiedPublisher,
           tags,servicePrincipalType,accountEnabled
  &$top=999
```

3. Sign-in activity per service principal:
```
GET /v1.0/reports/servicePrincipalSignInActivities
```
Falls back to /beta/ if v1.0 returns 404. Skips check gracefully if neither is available.

## Checks per app registration

| Check | Severity |
|---|---|
| Secret or cert expired | Critical |
| Secret/cert expiring in <= 30 days | High |
| No owners assigned | High |
| Insecure redirect URI (http:// non-localhost) | High |
| Wildcard redirect URI | High |
| Secret/cert expiring in 31-90 days | Medium |
| Multi-tenant signInAudience | Medium |
| Active creds but no sign-in activity | Medium |
| Active creds, last sign-in > 90 days ago | Medium |

## Checks per enterprise app (3rd party, service principals without owned app reg)
| Check | Severity |
|---|---|
| Publisher unverified | Low |

Microsoft-owned apps (appOwnerOrganizationId = f8cdef31-...) and managed identities
are excluded from enterprise app findings to reduce noise.

## Output files
- `reports/app-reg-governance/YYYY-MM-DD.md` — risk register, findings grouped by severity
- `reports/app-reg-governance/YYYY-MM-DD.csv` — flat file, UTF-8 BOM (Excel-compatible), sorted by severity
- Append to `activity-log.md`

## Activity log entry
Success: `YYYY-MM-DD HH:MM - App reg scan - {N} apps scanned, {M} with findings (Critical: X, High: Y) - reports/app-reg-governance/YYYY-MM-DD.md`
Failure: `YYYY-MM-DD HH:MM - App reg scan - FAILED - {reason}`

## Guardrails
- Read-only throughout — no writes to Entra, no modification of any app reg
- 401/403 on any Graph call: stop immediately, write FAILED to activity-log.md
- No email delivery — output is local files only

## Self-check
On each run, verify MCNA-TenantIntel-ReadOnly appears in output and its findings
are accurate (no expired creds, 1 owner = Dave, no risky redirect URIs).

## Future plays
- Change detection: compare today's output to previous run, flag new app regs
  that don't meet the standard (Play 2 bonus task from ROADMAP.md)
- Scheduled daily dispatch variant once manual output format proves stable
