# App Registrations — MCNA Admin Master Control

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

| Scope | Type | Admin consent | AMC domain |
|---|---|---|---|
| Mail.Read | Delegated | Granted | `mail_*` |
| Mail.Send | Delegated | Granted | `mail_*` |
| User.Read | Delegated | Granted | auth |
| Application.Read.All | Delegated | Granted | `entra_*` |
| AuditLog.Read.All | Delegated | Granted | `entra_*`, `purview_*` |
| Directory.Read.All | Delegated | Granted | `entra_*`, `ca_*`, `sharing_*` |
| Policy.Read.All | Delegated | Granted | `ca_*`, `compliance_*` |
| Reports.Read.All | Delegated | Granted | `compliance_*`, `copilot_*`, `license_*` |
| RoleManagement.Read.Directory | Delegated | Granted | `pim_*` |
| Sites.Read.All | Delegated | Granted | `sharing_*`, `copilot_*` |
| DeviceManagementManagedDevices.Read.All | Delegated | Granted | `intune_*` |
| DeviceManagementConfiguration.Read.All | Delegated | Granted | `intune_*` |
| MailboxSettings.Read | Delegated | Granted | `exo_*` |
| MailboxSettings.Read | Application | Granted | `exo_*` |
| Tasks.Read.All | Application | Granted | `entra_*` (Planner orphan detection) |
| Dynamics CRM: user_impersonation | Delegated | Granted | `pp_*` (Dataverse Web API) |
| Power Apps Service: User | Delegated | Granted | `pp_*` (BAP/PowerApps/Flow) |

### Mailboxes in scope

| Mailbox | Access method |
|---|---|
| nof-dlafferty@nofmetalcoatings.us | /me (signed-in user) |
| dlafferty@nofmetalcoatings.us | Separate MSAL device code session (primary account) |

### AMC domains enabled by current scopes

| Domain | Tools | Status |
|---|---|---|
| `entra_*` | App reg governance, guest review, orphaned assets | Scopes ready, tools not yet built |
| `ca_*` | CA policy audit, coverage gap detection | Scopes ready, tools not yet built |
| `pp_*` | PP environments, apps, flows, connections | Scopes ready, tools not yet built |
| `pim_*` | Privileged role review | Scopes ready, tools not yet built |
| `license_*` | Unassigned licenses, duplicate stacking | Scopes ready, tools not yet built |
| `sharing_*` | External sharing posture | Scopes ready, tools not yet built |
| `compliance_*` | Secure Score, SecureSketCH mapping | Scopes ready, tools not yet built |
| `copilot_*` | Copilot readiness, label coverage | Scopes ready, tools not yet built |
| `mail_*` | Send summary emails | Scopes ready, tools not yet built |
| `intune_*` | Device compliance, BitLocker | Scopes granted — tools functional |
| `exo_*` | Exchange hygiene, forwarding rules | MailboxSettings.Read delegated + application granted — tools functional |
| `purview_*` | Sensitivity labels, DLP, audit | Partial — AuditLog.Read.All granted; InformationProtectionPolicy.Read.All needed for purview_scan_labels |
| `kb_*` | Knowledge base (SQLite) | No scopes required — local only |

### Notes

- Full Access delegation from nof-dlafferty to dlafferty granted 2026-04-16.
- App reg governance review due: Q4 2026 (annual cycle per IT-GOV-ENTRA-v1.0).
- Old cert (MCNA-TenantIntel-ReadOnly-2026, thumbprint 3FCC406A...) was NonExportable.
  Replaced 2026-04-17 with MCNA-TenantIntel-Planner (thumbprint 8E2A295C...),
  exportable PFX at C:\Users\dlafferty.MCNA\mcna-tenantintel-planner.pfx.
- Power Platform scopes added and admin consent granted 2026-04-20.
- Governance paper trail for scope additions per IT-GOV-ENTRA-v1.0 not yet written.
  Dave self-approves as IS Director but the record should exist.
- MCNA-TenantIntel-Writer (write-capable reg): architecture designed, not yet created.
  Requires separate approval per operating principles. Deferred.

---

## Planned registrations

| Name | Purpose | Status |
|---|---|---|
| MCNA-TenantIntel-Writer | Write-capable app reg for Phase 4 remediation tools | Not yet created — requires separate approval |

---

## Change log

- 2026-04-16 — v1 — Initial record. MCNA-TenantIntel-ReadOnly created and configured.
- 2026-04-16 — v1.1 — Added six scopes. Admin consent granted.
- 2026-04-17 — v1.2 — Added Sites.Read.All and Tasks.Read.All. Cert replaced.
- 2026-04-20 — v1.3 — Added Dynamics CRM and Power Apps Service scopes.
- 2026-04-21 — v1.4 — File moved from auth/ to docs/auth/. Permissions table
  updated to reflect AMC domain mapping instead of Play references. Tasks table
  replaced with AMC domains table. File renamed to reflect AMC project name.
- 2026-04-23 — v1.5 — Added DeviceManagementManagedDevices.Read.All and
  DeviceManagementConfiguration.Read.All (both delegated). Admin consent granted.
  Enables intune_scan_devices and intune_scan_compliance_policies.
- 2026-04-24 — v1.6 — Added MailboxSettings.Read delegated (consented 2026-04-23) and
  MailboxSettings.Read application (consented 2026-04-24). Application permission enables
  full cross-user EXO scans via cert-based client credentials flow.
