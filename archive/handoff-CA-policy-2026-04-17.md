<!-- markdownlint-disable -->
# Session Handoff - 2026-04-17
## Conditional Access Policy & M365 Licensing Session

---

## Context

MCNA tenant is in the process of disabling Security Defaults and moving to custom Conditional Access policies. Business Premium pilot rollout is complete. DIS (managed service provider) is handling technical execution; Tony (Tony@discomputers.com) is the primary DIS contact.

---

## Licensing

- 60 total users
- 29 upgraded to M365 Business Premium (pilot group)
- 31 remaining on Business Standard — full rollout deferred
- 14 standalone AIP P1 licenses were removed (Business Premium includes AIP P1) and returned to reseller
- Business Standard licenses for pilot users also returned
- Licensing is clean — no action outstanding

---

## Conditional Access — Current State

Tony built one CA policy:

**Policy: Require MFA for every login**
- Scope: All users, all resources
- Excluded: dis@nofmetalcoatings.us (DIS break-glass account)
- Mode: Report-only (not yet enabled)
- Report-only result: 97% of sign-ins would require MFA, 3% excluded (DIS account)

Security Defaults are still ON. Tony cannot enable the CA policy until Security Defaults are disabled. Decision to disable has not yet been made — pending policy review completion.

---

## Recommended CA Policy Set (not yet built)

Four policies recommended beyond Tony's existing one:

1. **Legacy auth block** — Block all legacy auth protocols (IMAP, POP3, SMTP AUTH, ActiveSync). These bypass MFA entirely. Should run in report-only first.

2. **Admin role policy** — Separate policy targeting directory roles (Global Admin, etc.) with stricter controls: MFA on every sign-in, no persistent session exemptions.

3. **Service account policy** — Service accounts that can't do interactive MFA should be restricted to known MCNA IP ranges, not globally excluded from MFA.

4. **MCNA-owned break-glass accounts** — Currently the only break-glass exclusion is dis@nofmetalcoatings.us, a DIS-owned account. MCNA needs its own break-glass accounts with credentials stored offline by Dave, independent of DIS.

Email sent to Tony requesting all four. Response pending.

---

## Entra Role Audit

Ran Get-MgDirectoryRole / Get-MgDirectoryRoleMember via Microsoft Graph PowerShell. Full output saved to EntraRoleAssignments.csv.

**Global Administrators (3):**
- nof-dlafferty@nofmetalcoatings.us — Dave's dedicated admin account (expected)
- dis@nofmetalcoatings.us — DIS account (expected)
- admin@nofmetalcoatings.us — "admin admin" — origin unknown, needs investigation

**admin@nofmetalcoatings.us findings:**
- Account enabled: True
- Last sign-in: 2025-05-30 (~11 months ago)
- Also holds: Hybrid Identity Administrator
- Action: Ask Tony who created it and what it was used for before touching it. Do not disable until origin is confirmed and dependency check is done.

**Other items flagged for cleanup:**
- dlafferty@nofmetalcoatings.us (daily driver) holds Authentication Administrator, Power Platform Administrator, AI Administrator — these should move to nof-dlafferty admin account
- cloudadmin@nofmetalcoatings.us holds Cloud Application Administrator and Application Administrator — ownership unconfirmed
- NOF Diana Kochever holds User Administrator, Teams Administrator, Exchange Administrator — confirm this is intentional

---

## Outstanding Actions

1. Tony to respond on CA policy gaps (legacy auth, admin policy, service accounts, MCNA break-glass)
2. Identify owner of admin@nofmetalcoatings.us — ask Tony
3. Confirm cloudadmin@nofmetalcoatings.us ownership
4. Review role assignments on dlafferty@nofmetalcoatings.us and move to admin account
5. Confirm Diana Kochever role assignments are intentional
6. Decision point: when to disable Security Defaults and go live with CA policies

---

## PowerShell Notes

Microsoft Graph PowerShell required for Entra queries. Connect with:

```powershell
Disconnect-MgGraph
Connect-MgGraph -Scopes "RoleManagement.Read.Directory","Directory.Read.All","AuditLog.Read.All"
```

Script used for role audit:

```powershell
Get-MgDirectoryRole | ForEach-Object {
    $role = $_
    Get-MgDirectoryRoleMember -DirectoryRoleId $role.Id | ForEach-Object {
        [PSCustomObject]@{
            Role        = $role.DisplayName
            DisplayName = $_.AdditionalProperties["displayName"]
            UPN         = $_.AdditionalProperties["userPrincipalName"]
            Type        = $_.AdditionalProperties["@odata.type"]
        }
    }
} | Export-Csv -Path "C:\Users\dlafferty.MCNA\Desktop\EntraRoleAssignments.csv" -NoTypeInformation
```
