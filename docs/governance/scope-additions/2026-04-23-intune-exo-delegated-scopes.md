# Scope Addition Record - Intune and EXO Delegated Read Scopes

**Date:** 2026-04-23
**Requested by:** D. Lafferty (nof-dlafferty@nofmetalcoatings.us)
**App registration:** MCNA-TenantIntel-ReadOnly

---

## Scopes Added

| Scope | Type | Consent Date |
|---|---|---|
| DeviceManagementManagedDevices.Read.All | Delegated | 2026-04-23 |
| DeviceManagementConfiguration.Read.All | Delegated | 2026-04-23 |
| MailboxSettings.Read | Delegated | 2026-04-23 |

---

## Justification

`DeviceManagementManagedDevices.Read.All` and
`DeviceManagementConfiguration.Read.All` unblock `intune_scan_devices` and
`intune_scan_compliance_policies` for endpoint compliance, BitLocker/encryption
posture, enrollment, and policy coverage checks.

Delegated `MailboxSettings.Read` was added for initial EXO mailbox-settings
coverage. It proved insufficient for full cross-user mailbox governance by
itself; `MailboxSettings.Read` application permission was added separately on
2026-04-24 and is documented in
`2026-04-24-exo-application-scope.md`.

---

## Consent Outcome

Admin consent granted. `docs/auth/app-registrations.md` records these scopes as
granted.

---

## Risk Notes

These are read scopes. They expand visibility into Intune device state,
configuration policy posture, and mailbox settings, but do not grant mutation
rights. EXO remediation remains outside the read-only app registration.
