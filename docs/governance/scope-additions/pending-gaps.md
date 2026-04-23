# Scope Gap Record — Pending Consent

Scopes identified as needed but not yet added to MCNA-TenantIntel-ReadOnly.
Each entry requires explicit approval before adding. Update this file when consented.

---

## DeviceManagementManagedDevices.Read.All

| Field | Value |
|---|---|
| **Type** | Delegated |
| **Identified** | 2026-04-22 |
| **Identified by** | D. Lafferty |
| **Status** | Pending |
| **Justification** | Required for `intune_*` domain tool — device compliance, BitLocker posture, enrollment status. Gates `/deviceManagement/managedDevices` and `/deviceManagement/deviceCompliancePolicies`. Intune licensing also gates which endpoints respond — probe `/subscribedSkus` first after consent. |
| **SSK mapping** | SSK 16-x (endpoint security) |
| **Blocked by** | Admin consent not yet granted |

---

## MailboxSettings.Read

| Field | Value |
|---|---|
| **Type** | Delegated |
| **Identified** | 2026-04-22 |
| **Identified by** | D. Lafferty |
| **Status** | Pending |
| **Justification** | Required for EXO domain tool — mailbox forwarding rules, auto-reply hygiene. Alternative: EXO PowerShell (separate auth surface). Decision deferred. |
| **SSK mapping** | TBD — Exchange hygiene |
| **Blocked by** | Architecture decision pending (Graph vs EXO PowerShell) |

---

## Sites.FullControl.All

| Field | Value |
|---|---|
| **Type** | Delegated |
| **Identified** | 2026-04-22 |
| **Identified by** | D. Lafferty |
| **Status** | Pending |
| **Justification** | Required for permission-level sharing checks in `sharing_*` tools. Current `Sites.Read.All` returns site metadata but not granular permission assignments. Broad scope — add only if permission-audit depth justifies it. |
| **SSK mapping** | SSK 15-4 (external sharing) |
| **Blocked by** | Scope breadth review — may be deferrable indefinitely |

---

## How to add a scope

1. Update this file: change Status to `Approved`, add Approved-by and Date fields.
2. Add to app reg via Entra portal — API permissions → Add a permission.
3. Grant admin consent as nof-dlafferty@nofmetalcoatings.us.
4. Create a new dated record in this folder (see 2026-04-16 and 2026-04-20 as templates).
5. Update `docs/auth/app-registrations.md` permissions table.
6. Remove the entry from this file once consented and documented.
