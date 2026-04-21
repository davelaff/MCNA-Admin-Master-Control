# Task: Orphaned Asset Scanner
Last updated: 2026-04-17

## Implementation
Script: `orphaned_asset_scanner.py`
Schedule: On demand (run manually, weekly or after HR offboarding events)
Status: Active, v1. Built 2026-04-17. Read phase only.
Output: `reports/orphaned-assets/YYYY-MM-DD.md` + `YYYY-MM-DD.csv`

---

## What it does
Inventories groups, teams, distribution lists, and user accounts that are
orphaned — no active owner, no recent activity, or consuming licenses for
departed/disabled users. Correlates against active Entra user roster.
Produces a prioritized cleanup queue.

Write phase is NOT built. Every item in the output is a recommended action
for Dave to review. Nothing is modified automatically.

## Auth
Admin account only (`nof-dlafferty@nofmetalcoatings.us`).
Cache: `C:/Users/dlafferty.MCNA/.msal_token_cache_admin.json`

Scopes required (all granted on MCNA-TenantIntel-ReadOnly):
- Directory.Read.All — groups, users, owners, members
- AuditLog.Read.All — user sign-in activity (signInActivity property)
- Reports.Read.All — M365 group activity report, SharePoint usage report
- Sites.Read.All — SharePoint site enumeration

All required scopes are granted on MCNA-TenantIntel-ReadOnly.

## Graph queries (in order)

1. All groups (M365 Groups, Teams, DLs, mail-enabled security groups):
```
GET /v1.0/groups
  ?$select=id,displayName,mail,groupTypes,mailEnabled,securityEnabled,
           visibility,createdDateTime,description
  &$expand=owners($select=id,displayName,userPrincipalName,accountEnabled)
  &$top=999
```

2. Group members count (for empty group detection):
```
GET /v1.0/groups/{id}/members/$count
  ConsistencyLevel: eventual
```
Batched per group, sampled for groups flagged as potentially empty.

3. All users (for active roster + license/mailbox checks):
```
GET /v1.0/users
  ?$select=id,displayName,userPrincipalName,accountEnabled,assignedLicenses,
           mail,createdDateTime,jobTitle,department,signInActivity
  &$top=999
```
signInActivity requires AuditLog.Read.All and Entra ID P1+.
Falls back gracefully if property is unavailable (older license SKU).

4. M365 group activity report (last 180 days):
```
GET /v1.0/reports/getOffice365GroupsActivityDetail(period='D180')
```
Returns CSV. Parsed to build groupId → lastActivityDate map.
Falls back gracefully if Reports.Read.All doesn't return this endpoint.

## Asset types and orphan criteria

### M365 Groups and Teams
| Condition | Severity |
|---|---|
| No owners assigned | High |
| All owners have accountEnabled = false | High |
| Created > 180 days ago, no activity in last 180 days | Medium |
| No members (empty group) | Medium |
| Single owner who is disabled | Medium |

### Distribution Groups and Mail-Enabled Security Groups
(groupTypes does NOT include "Unified"; mailEnabled = true)

| Condition | Severity |
|---|---|
| No owners assigned | High |
| All owners have accountEnabled = false | High |
| Created > 365 days ago | Low |

### User accounts
| Condition | Severity |
|---|---|
| accountEnabled = false AND assignedLicenses not empty | High |
| accountEnabled = true AND no sign-in in 365+ days | Medium |
| accountEnabled = false AND mail present (possible orphaned mailbox) | Medium |
| accountEnabled = true AND created > 90 days ago AND never signed in | Low |

### SharePoint sites
`GET /v1.0/sites?search=*` — all sites tenant-wide (excludes personal OneDrive).
`GET /v1.0/reports/getSharePointSiteUsageDetail(period='D180')` — owner UPN, last activity,
storage used per site. Cross-referenced to find sites with zero activity in 180 days.

| Condition | Severity |
|---|---|
| Owner UPN not found in active Entra accounts (disabled or departed) | High |
| No owner UPN in usage report | Medium |
| No activity in last 180 days (site age > 90 days) | Medium |
| Last activity >= 180 days ago | Medium |

**Known limitation:** The usage report's `Owner Principal Name` field is the primary site collection admin account — often the original creator. It does not enumerate all current site owners or admins. A site can appear as "owner not found" while still having active owners with full permissions. When this fires, the correct action is to verify current owners in SharePoint Admin Center and assign one as the primary site collection admin so the report reflects a real person.

Example confirmed: MCNA QMS Team (`/sites/qualityna`) flagged High on 2026-04-17 because the primary admin account `qualityna` is gone. The site has two active owners (Linda R Gazdak, Luis Guillermo Uribe). Action: assign one as primary site collection admin.

### Power Platform / Dataverse
Out of scope for Play 3. Addressed in Play 5.

## Output files
- `reports/orphaned-assets/YYYY-MM-DD.md` — cleanup queue grouped by severity and asset type
- `reports/orphaned-assets/YYYY-MM-DD.csv` — flat file, UTF-8 BOM (Excel-compatible)
- Append to `activity-log.md`

## Output columns (CSV)
Type, Display Name, ID/Email, Owners, Created, Last Activity, Severity, Finding, Recommended Action

## Activity log entry
Success: `YYYY-MM-DD HH:MM - Orphaned asset scan - {N} assets flagged (High: X, Medium: Y, Low: Z) - reports/orphaned-assets/YYYY-MM-DD.md`
Failure: `YYYY-MM-DD HH:MM - Orphaned asset scan - FAILED - {reason}`

## Guardrails
- Read-only throughout — no writes to Entra, no modification of any group or user
- 401/403 on any Graph call: stop immediately, write FAILED to activity-log.md
- Group member count calls: skip gracefully if throttled (429) — note in output
- signInActivity unavailable: continue without it, note in output summary
- No email delivery — output is local files only

## Future (write phase, NOT YET APPROVED)
When the write phase is added via MCNA-TenantIntel-Writer app reg:
- Remove license from disabled users after Dave approves
- Delete empty groups after 30-day confirmation window
- Disable stale service accounts after IT review
Each write operation logged twice (local + SharePoint) per ROADMAP.md principle 7.

## Change log
- 2026-04-17 — v1 — Initial read-phase spec. SharePoint stubbed pending Sites.Read.All grant.
- 2026-04-17 — v1.1 — Sites.Read.All granted. SharePoint enumeration implemented.
