# App Registrations — MCNA Tenant Intel

This file is the non-secret record of all app registrations used by this
project. Secrets, thumbprints, and tenant/client IDs live in the .env file
on the local workstation and are never stored here.

---

## MCNA-TenantIntel-ReadOnly

| Field | Value |
|---|---|
| **Display name** | MCNA-TenantIntel-ReadOnly |
| **Type** | Public client (delegated) + application permissions (client credentials) |
| **Auth flow** | Device code for delegated; client credentials + cert for application perms |
| **Public client flows** | Enabled |
| **Redirect URI** | http://localhost (Mobile & desktop) |
| **Supported account types** | Single tenant — NOF |
| **Certificate** | MCNA-TenantIntel-Planner, expires 2028-04-16 (PFX at C:\Users\dlafferty.MCNA\) |
| **Client secrets** | None |
| **Created** | 2026-04-16 |
| **Created by** | D. Lafferty (nof-dlafferty@nofmetalcoatings.us) |

### Permissions

| Scope | Type | Admin consent | Purpose |
|---|---|---|---|
| Mail.Read | Delegated | Granted | Read inbox/sent items (admin + primary mailbox) |
| Mail.Send | Delegated | Granted | Send summary email to Dave |
| User.Read | Delegated | Granted | Sign in, read user profile |
| Application.Read.All | Delegated | Granted | Read app registrations and enterprise apps |
| AuditLog.Read.All | Delegated | Granted | Read sign-in logs, consent grants, app usage |
| Directory.Read.All | Delegated | Granted | Read users, groups, guest accounts, roles |
| Policy.Read.All | Delegated | Granted | Read Conditional Access policies |
| Reports.Read.All | Delegated | Granted | Read M365 usage reports |
| RoleManagement.Read.Directory | Delegated | Granted | Read PIM and role assignments |
| Sites.Read.All | Delegated | Granted | Read SharePoint sites tenant-wide (Play 3 + Play 7) |
| Tasks.Read.All | Application | Granted | Read Planner plans tenant-wide (Play 3, client credentials) |

### Mailboxes in scope

| Mailbox | Access method |
|---|---|
| nof-dlafferty@nofmetalcoatings.us | /me (signed-in user) |
| dlafferty@nofmetalcoatings.us | Separate MSAL device code session (primary account) |

### Tasks using this registration

| Task | Script | Status |
|---|---|---|
| DIS daily summary | dis_daily_summary.py | Active — v1 |
| App reg governance scanner | app_reg_scanner.py | Active — v1 |
| Orphaned asset scanner | orphaned_asset_scanner.py | Active — v1 |

### Roadmap plays enabled by current scopes

| Play | Description | Status | Scopes used |
|---|---|---|---|
| Play 1 | Tenant-wide intelligence brief | Partial — DIS summary active | All delegated scopes |
| Play 2 | Entra app reg governance scanner | Active | Application.Read.All, AuditLog.Read.All |
| Play 3 | Orphaned asset cleanup (read phase) | Active | Directory.Read.All, Reports.Read.All, Sites.Read.All, Tasks.Read.All |
| Play 4 | SecureSketCH / Secure Score remediation drafting | Planned | Reports.Read.All, Policy.Read.All |
| Play 5 | Power Platform hygiene | Planned | Requires Power Platform API (not yet configured) |
| Play 7 | SharePoint content intelligence | Planned | Sites.Read.All (already granted) |

### Notes

- Full Access delegation from nof-dlafferty to dlafferty granted 2026-04-16.
- App reg governance review due: Q4 2026 (annual cycle per IT-GOV-ENTRA-v1.0).
- Old cert (MCNA-TenantIntel-ReadOnly-2026, thumbprint 3FCC406A...) was NonExportable
  and could not be used for client credentials flow. Replaced 2026-04-17 with
  MCNA-TenantIntel-Planner (thumbprint 8E2A295C...), exportable PFX at
  C:\Users\dlafferty.MCNA\mcna-tenantintel-planner.pfx.
- Power Platform admin API requires separate token flow. Not yet configured.
- MCNA-TenantIntel-Writer (write-capable reg): architecture designed, not yet created.
  Requires separate approval per operating principles. Deferred.

---

## Planned registrations

| Name | Purpose | Status |
|---|---|---|
| MCNA-TenantIntel-Writer | Write-capable app reg for future cleanup/remediation tasks | Not yet created — requires separate approval per operating principles |

---

## Change log

- 2026-04-16 — v1 — Initial record. MCNA-TenantIntel-ReadOnly created and configured.
- 2026-04-16 — v1.1 — Added six scopes: Application.Read.All, AuditLog.Read.All,
  Directory.Read.All, Policy.Read.All, Reports.Read.All, RoleManagement.Read.Directory.
  Admin consent granted for all. Enables Plays 1-4.
- 2026-04-17 — v1.2 — Added Sites.Read.All (delegated) and Tasks.Read.All (application).
  Replaced non-exportable cert with MCNA-TenantIntel-Planner PFX for client credentials
  flow. Added orphaned_asset_scanner.py to tasks. Updated plays table.
