# Secure SketCH Initial Review Batch 1

Date: 2026-04-27
Reviewer: Dave Lafferty
Cadence: 90 days
Review scope: Initial Secure SketCH review batch covering family `08`, family `09`, family `14`, control `15-3`, and family `19`

## Objective

Establish the first auditor-defensible review record for a focused set of high-value Secure SketCH controls using current local evidence, scan outputs, and existing remediation context.

## Executive Conclusion

Five review records were entered for this batch. Three scopes were reviewed as satisfactory and now count as `regularly_reviewed`: family `09`, family `14`, and family `19`. Two scopes were reviewed with `action_required`: family `08` and control `15-3`.

This batch reduced the notification queue from 75 never-reviewed controls to 58. The remaining gap is not missing evidence for the reviewed scopes. The remaining gap is unresolved control findings in IAM/privileged access and the open Copilot settings scope gap for cloud-security settings.

## Review Summary

| Scope | Controls covered | Review result | Maturity result | Next review due |
|---|---|---|---|---|
| Family `08` | `08-1`, `08-2`, `08-3`, `08-4`, `08-5`, `08-6`, `08-7` | `action_required` | `not_regularly_reviewed` | 2026-07-26 |
| Family `09` | `09-1`, `09-2`, `09-3` | `ok` | `regularly_reviewed` | 2026-07-26 |
| Family `14` | `14-1`, `14-2` | `ok` | `regularly_reviewed` | 2026-07-26 |
| Control `15-3` | `15-3` | `action_required` | `not_regularly_reviewed` | 2026-07-26 |
| Family `19` | `19-1`, `19-2`, `19-3`, `19-4` | `ok` | `regularly_reviewed` | 2026-07-26 |

## Scope 08

Review record: `f9591107-060e-4b29-8cb9-8d58c7b99dbb`

Controls covered:
- `08-1` Creating and provisioning access and accounts, and conducting access inventory
- `08-2` Authenticating accounts
- `08-3` Managing access privilege
- `08-4` Establishing and adopting password policies
- `08-5` Monitoring and responding to unusual access
- `08-6` Implementing a process governing the use of privileged accounts
- `08-7` Prior approval for privileged access, and reconciling activity logs against approved scope

Conclusion:
Current evidence is sufficient to support review activity, but the scope remains open because material IAM and privileged-access findings are still active. This family was reviewed with `action_required`, not `ok`.

Evidence reviewed:
- [08_1.md](</c:/Users/dlafferty.MCNA/OneDrive%20-%20NOF/DL%20OneDrive/OneDrive%20-%20NOF/Management%20Information%20Systems%20-%20Governance%20and%20Security%20Project%202026/MCNA-Admin-Master-Control/reports/audit-binders/2026-04-23-142541/08_1.md>)
- [2026-04-20.md](</c:/Users/dlafferty.MCNA/OneDrive%20-%20NOF/DL%20OneDrive/OneDrive%20-%20NOF/Management%20Information%20Systems%20-%20Governance%20and%20Security%20Project%202026/MCNA-Admin-Master-Control/reports/app-reg-governance/2026-04-20.md>)
- [2026-04-25.md](</c:/Users/dlafferty.MCNA/OneDrive%20-%20NOF/DL%20OneDrive/OneDrive%20-%20NOF/Management%20Information%20Systems%20-%20Governance%20and%20Security%20Project%202026/MCNA-Admin-Master-Control/reports/exo-shared-mailbox-remediation/2026-04-25.md>)
- [08_6.md](</c:/Users/dlafferty.MCNA/OneDrive%20-%20NOF/DL%20OneDrive/OneDrive%20-%20NOF/Management%20Information%20Systems%20-%20Governance%20and%20Security%20Project%202026/MCNA-Admin-Master-Control/reports/audit-binders/2026-04-23/08_6.md>)

Open findings and exceptions:
- Open `missing_owner` findings remain in app registration governance.
- Open privileged-access findings remain for DIS Global Admin account handling.
- Open PIM licensing gap remains.

Next action:
Close or formally accept the IAM/PIM findings, then re-review family `08` and promote it to `regularly_reviewed`.

## Scope 09

Review record: `93a8f495-2079-4da5-b385-5053393a5919`

Controls covered:
- `09-1` Encryption of data in transit
- `09-2` Encryption of data at rest
- `09-3` Acquiring and protecting backups

Conclusion:
Evidence is current and no open family findings were present at review time. This family was reviewed as `ok` and is now `regularly_reviewed`.

Evidence reviewed:
- [encryption-in-transit.md](</c:/Users/dlafferty.MCNA/OneDrive%20-%20NOF/DL%20OneDrive/OneDrive%20-%20NOF/Management%20Information%20Systems%20-%20Governance%20and%20Security%20Project%202026/MCNA-Admin-Master-Control/docs/policies/data/encryption-in-transit.md>)
- [backup-and-recovery.md](</c:/Users/dlafferty.MCNA/OneDrive%20-%20NOF/DL%20OneDrive/OneDrive%20-%20NOF/Management%20Information%20Systems%20-%20Governance%20and%20Security%20Project%202026/MCNA-Admin-Master-Control/docs/policies/data/backup-and-recovery.md>)
- Linked resolved scan snapshot for `09-2` stored in KB evidence `9504a9d6-cf08-4c54-b810-33c6111fb7b2`

Next action:
Maintain cadence. Re-review by 2026-07-26 unless material architectural change occurs earlier.

## Scope 14

Review record: `1417f344-9c31-4a1d-92d5-95ff2c62d8a7`

Controls covered:
- `14-1` Security check on incoming mail
- `14-2` Enabling security of outbound email communication

Conclusion:
Evidence is current and no open family findings were present at review time. This family was reviewed as `ok` and is now `regularly_reviewed`.

Evidence reviewed:
- [email-security.md](</c:/Users/dlafferty.MCNA/OneDrive%20-%20NOF/DL%20OneDrive/OneDrive%20-%20NOF/Management%20Information%20Systems%20-%20Governance%20and%20Security%20Project%202026/MCNA-Admin-Master-Control/docs/policies/email/email-security.md>)

Next action:
Maintain cadence. Re-review by 2026-07-26.

## Scope 15-3

Review record: `f8a7b4b2-1c44-46d0-b7f6-a5692b3a654f`

Control covered:
- `15-3` Security settings for cloud services

Conclusion:
Evidence is current for Power Platform cloud-service settings, but this control remains open because the Copilot settings scope gap is unresolved. This control was reviewed with `action_required`, not `ok`.

Evidence reviewed:
- [2026-04-20.md](</c:/Users/dlafferty.MCNA/OneDrive%20-%20NOF/DL%20OneDrive/OneDrive%20-%20NOF/Management%20Information%20Systems%20-%20Governance%20and%20Security%20Project%202026/MCNA-Admin-Master-Control/reports/power-platform-hygiene/2026-04-20.md>)
- [2026-04-20.csv](</c:/Users/dlafferty.MCNA/OneDrive%20-%20NOF/DL%20OneDrive/OneDrive%20-%20NOF/Management%20Information%20Systems%20-%20Governance%20and%20Security%20Project%202026/MCNA-Admin-Master-Control/reports/power-platform-hygiene/2026-04-20.csv>)

Open findings and exceptions:
- Open `copilot_scope_gap` finding remains. Cloud-service settings evidence is not yet complete across the full intended scope.

Next action:
Resolve the Copilot settings scope gap, rerun the settings scan as needed, then re-review control `15-3`.

## Scope 19

Review record: `b264db1c-58f0-4e0c-b35f-d3f37381125d`

Controls covered:
- `19-1` Establishing and disseminating incident response policy - detection and initial response
- `19-2` Establishing and disseminating incident response policy - recovery and improvement
- `19-3` Establishing and disseminating incident response procedures or operating guidance
- `19-4` Formation of incident response teams

Conclusion:
Evidence is current and no open family findings were present at review time. This family was reviewed as `ok` and is now `regularly_reviewed`.

Evidence reviewed:
- [ir-policy.md](</c:/Users/dlafferty.MCNA/OneDrive%20-%20NOF/DL%20OneDrive/OneDrive%20-%20NOF/Management%20Information%20Systems%20-%20Governance%20and%20Security%20Project%202026/MCNA-Admin-Master-Control/docs/policies/incident-response/ir-policy.md>)

Next action:
Maintain cadence. Re-review by 2026-07-26.

## Auditor Use

If an auditor asks to "show the thing" for a control in this batch, hand them:
- this review memo
- the matching control page from the audit binder
- the cited source evidence file or report

Examples:
- `14-1`: this memo + [14_1.md](</c:/Users/dlafferty.MCNA/OneDrive%20-%20NOF/DL%20OneDrive/OneDrive%20-%20NOF/Management%20Information%20Systems%20-%20Governance%20and%20Security%20Project%202026/MCNA-Admin-Master-Control/reports/audit-binders/2026-04-26/14_1.md>) + [email-security.md](</c:/Users/dlafferty.MCNA/OneDrive%20-%20NOF/DL%20OneDrive/OneDrive%20-%20NOF/Management%20Information%20Systems%20-%20Governance%20and%20Security%20Project%202026/MCNA-Admin-Master-Control/docs/policies/email/email-security.md>)
- `08-6`: this memo + [08_6.md](</c:/Users/dlafferty.MCNA/OneDrive%20-%20NOF/DL%20OneDrive/OneDrive%20-%20NOF/Management%20Information%20Systems%20-%20Governance%20and%20Security%20Project%202026/MCNA-Admin-Master-Control/reports/audit-binders/2026-04-26/08_6.md>) + the family `08` evidence listed above
- `19-1`: this memo + [19_1.md](</c:/Users/dlafferty.MCNA/OneDrive%20-%20NOF/DL%20OneDrive/OneDrive%20-%20NOF/Management%20Information%20Systems%20-%20Governance%20and%20Security%20Project%202026/MCNA-Admin-Master-Control/reports/audit-binders/2026-04-26/19_1.md>) + [ir-policy.md](</c:/Users/dlafferty.MCNA/OneDrive%20-%20NOF/DL%20OneDrive/OneDrive%20-%20NOF/Management%20Information%20Systems%20-%20Governance%20and%20Security%20Project%202026/MCNA-Admin-Master-Control/docs/policies/incident-response/ir-policy.md>)
