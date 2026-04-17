# App Registrations — MCNA Tenant Intel

This file is the non-secret record of all app registrations used by this
project. Secrets, thumbprints, and tenant/client IDs live in the .env file
on the local workstation and are never stored here.

---

## MCNA-TenantIntel-ReadOnly

| Field | Value |
|---|---|
| **Display name** | MCNA-TenantIntel-ReadOnly |
| **Type** | Public client (delegated permissions) |
| **Auth flow** | Device code / interactive, token cached locally |
| **Public client flows** | Enabled |
| **Redirect URI** | http://localhost (Mobile & desktop) |
| **Supported account types** | Single tenant — NOF |
| **Certificate** | MCNA-TenantIntel-ReadOnly-2026, expires 2028-04-16 |
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

### Mailboxes in scope

| Mailbox | Access method |
|---|---|
| nof-dlafferty@nofmetalcoatings.us | /me (signed-in user) |
| dlafferty@nofmetalcoatings.us | /users/{upn} via Full Access delegation |

### Tasks using this registration

| Task | Script | Status |
|---|---|---|
| DIS daily summary | dis_daily_summary.py | Active — v1 |

### Roadmap plays enabled by current scopes

| Play | Description | Scopes required |
|---|---|---|
| Play 1 | Tenant-wide intelligence brief | All current scopes |
| Play 2 | Entra app reg governance scanner | Application.Read.All, AuditLog.Read.All |
| Play 3 | Orphaned asset cleanup (read phase) | Directory.Read.All |
| Play 4 | SecureSketCH / Secure Score remediation drafting | Reports.Read.All, Policy.Read.All |

### Notes

- Certificate private key is NonExportable in CurrentUser\My store.
- Full Access delegation from nof-dlafferty to dlafferty granted 2026-04-16.
- App reg governance review due: Q4 2026 (annual cycle per IT-GOV-ENTRA-v1.0).
- Sites.Read.All (Play 7 — SharePoint) not yet added. Add when Play 7 is scoped.
- Power Platform admin API requires separate token flow. Not yet configured.

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
