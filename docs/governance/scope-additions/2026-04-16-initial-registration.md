# Scope Addition Record — MCNA-TenantIntel-ReadOnly Initial Registration

| Field | Value |
|---|---|
| **Date** | 2026-04-16 |
| **App registration** | MCNA-TenantIntel-ReadOnly |
| **Requested by** | D. Lafferty (nof-dlafferty@nofmetalcoatings.us) |
| **Approved by** | D. Lafferty — IS Director, global admin |
| **Policy reference** | IT-GOV-ENTRA-v1.0 (self-approval authorized for IS Director) |

## Scopes added

| Scope | Type | Justification |
|---|---|---|
| Mail.Read | Delegated | Read DIS and vendor communications for daily summary tooling |
| Mail.Send | Delegated | Send governance summary emails from admin account |
| User.Read | Delegated | Required for MSAL device code flow authentication |
| Application.Read.All | Delegated | App registration governance — enumerate apps, credentials, owners |
| AuditLog.Read.All | Delegated | Entra audit log access for governance and Purview domain tools |
| Directory.Read.All | Delegated | Full directory read — users, groups, devices, CA policies, sharing |
| Policy.Read.All | Delegated | Conditional Access policy audit and coverage gap detection |
| Reports.Read.All | Delegated | Compliance reports, Secure Score, license and Copilot readiness signals |
| RoleManagement.Read.Directory | Delegated | PIM and permanent role assignment review |
| Sites.Read.All | Delegated | SharePoint site enumeration for sharing posture and Copilot governance |
| Tasks.Read.All | Application | Planner orphan detection via client credentials (cert-based) |

## Certificate

New cert created same day: MCNA-TenantIntel-Planner, exportable PFX.
Replaces prior NonExportable cert (MCNA-TenantIntel-ReadOnly-2026, thumbprint 3FCC406A).
New thumbprint: 8E2A295C. PFX at C:\Users\dlafferty.MCNA\mcna-tenantintel-planner.pfx.

## Notes

Admin consent granted by nof-dlafferty@nofmetalcoatings.us at registration.
Full Access delegation from nof-dlafferty to dlafferty also established 2026-04-16.
