# Secure SketCH Review Batch 4

Date: 2026-04-29
Reviewer: Dave Lafferty
Cadence: 90 days
Review scope: Remaining never-reviewed controls `15-1`, `15-2`, `15-4`, plus families `16`, `17`, `18`, `20`

## Objective

Close the initial Secure SketCH review queue by recording first-pass reviews for the last 15 never-reviewed controls using current local evidence already linked in the KB.

## Executive Conclusion

Seven review records were entered for this batch. All seven were reviewed as `ok`. This batch reduced the never-reviewed queue from 15 to 0.

MCNA now has an initial review record for all 75 Secure SketCH controls. This does not mean every control family is fully clean. Control `15-3` remains `action_required` from the earlier cloud-security review because the Copilot settings scope gap is still unresolved, but it is no longer part of the never-reviewed queue.

## Review Summary

| Scope | Controls covered | Review result | Next review due |
| --- | --- | --- | --- |
| Control `15-1` | `15-1` | `ok` | 2026-07-28 |
| Control `15-2` | `15-2` | `ok` | 2026-07-28 |
| Control `15-4` | `15-4` | `ok` | 2026-07-28 |
| Family `16` | `16-1`, `16-2`, `16-3`, `16-4` | `ok` | 2026-07-28 |
| Family `17` | `17-1`, `17-2`, `17-3`, `17-4`, `17-5` | `ok` | 2026-07-28 |
| Family `18` | `18-1` | `ok` | 2026-07-28 |
| Family `20` | `20-1`, `20-2` | `ok` | 2026-07-28 |

## Scope 15-1 — Cloud Service Policy Rules

Review record: `b45cdffe-418c-4b73-b93a-3a06a55bea01`

Control covered:

- `15-1` Establishing and communicating policies or rules addressing use of cloud services

Conclusion:
Cloud-service governance rules are documented and reviewable. The Power Platform scope approval record and binder evidence are current enough to support an `ok` review for the policy-and-rules control itself. No open mapped findings were present at review time.

Evidence basis:

- Power Platform scope approval record
- Audit binder control page for `15-1`

Next action:
Maintain cadence. Re-review by 2026-07-28.

## Scope 15-2 — Cloud Service Usage Process

Review record: `a559aa0f-ac7b-4232-8bb6-4c0f72108810`

Control covered:

- `15-2` Development of processes for the use of cloud services

Conclusion:
Operational process evidence exists for how MCNA reviews cloud-service usage in practice. The Power Platform hygiene review artifact and binder page are sufficient to support an `ok` review. No open mapped findings were present at review time.

Evidence basis:

- Power Platform hygiene review report
- Audit binder control page for `15-2`

Next action:
Maintain cadence. Re-review by 2026-07-28.

## Scope 15-4 — Cloud Service Visibility and Control

Review record: `06a14819-a16b-410b-b903-de44780158fc`

Control covered:

- `15-4` Visualization and control of cloud services usage

Conclusion:
Current Power Platform hygiene evidence is sufficient to show visibility into cloud-service usage and configuration risk. This control was reviewed as `ok`. No open mapped findings were present at review time.

Evidence basis:

- Power Platform hygiene report (markdown)
- Power Platform hygiene data export (CSV)

Next action:
Maintain cadence. Re-review by 2026-07-28.

## Scope 16 — Logging and Monitoring

Review record: `6bfd646f-c82f-449c-934e-353f9c8d0fc8`

Controls covered:

- `16-1` Enabling logging of systems and acquired logs
- `16-2` Storing, retaining, and protecting logs
- `16-3` Enabling analysis of acquired systems logs
- `16-4` Enabling log correlation and analyzing logs across sources

Conclusion:
Logging policy, retention requirements, and cross-source analysis expectations are documented. Purview audit evidence exists in the KB for active logging capability. No open mapped findings were present at review time, so this family was reviewed as `ok`.

Evidence basis:

- `purview_scan_audit` scan snapshot evidence in the KB
- Log management policy

Next action:
Maintain cadence. Re-review by 2026-07-28.

## Scope 17 — Secure System Development Lifecycle

Review record: `3f3e024d-5bc9-44a0-8330-9009af1d9760`

Controls covered:

- `17-1` Establishing and communicating policies or rules for the system development lifecycle
- `17-2` Security-conscious system design
- `17-3` Security-conscious system installation
- `17-4` Security-conscious system operation
- `17-5` Conducting vulnerability scans

Conclusion:
The Admin Master Control codebase has documented design, implementation, operating, and vulnerability-management artifacts sufficient to support an initial SDL review. No open mapped findings were present at review time, so this family was reviewed as `ok`.

Evidence basis:

- Secure SketCH tracking layer design spec
- Admin Master Control design spec
- Phase 4 approval and closure implementation plan
- Report and audit binder operating guide
- Vulnerability management policy

Next action:
Maintain cadence. Re-review by 2026-07-28.

## Scope 18 — IT Business Continuity

Review record: `ecd166aa-3a23-477a-a01d-1beb1856c585`

Controls covered:

- `18-1` Planning for business continuity with IT considerations (IT-BCP, etc.)

Conclusion:
Business continuity planning is documented with explicit IT recovery scenarios, RTO/RPO expectations, and annual testing language. The control was reviewed as `ok`. No open mapped findings were present at review time.

Evidence basis:

- IT Business Continuity Plan
- Backup and recovery policy

Next action:
Maintain cadence. Re-review by 2026-07-28.

## Scope 20 — Incident Response Training and Exercises

Review record: `c66dde41-a99e-4559-a69a-fc469c995fa0`

Controls covered:

- `20-1` Training the incident response teams
- `20-2` Cross-functional incident response training

Conclusion:
IR training and exercise expectations are documented, including annual tabletop cadence and cross-functional participation. No open mapped findings were present at review time, so this family was reviewed as `ok`.

Evidence basis:

- Incident response training policy
- Cross-functional exercise participation requirements in the same policy

Next action:
Maintain cadence. Re-review by 2026-07-28.

## Auditor Use

For any control in this batch, provide:

- This review memo
- The matching control page from the current audit binder (`reports/audit-binders/2026-04-26/`)
- The cited policy, spec, or report artifact

Examples:

- `15-4`: this memo + `reports/audit-binders/2026-04-26/15_4.md` + Power Platform hygiene report/data export
- `16-2`: this memo + `reports/audit-binders/2026-04-26/16_2.md` + log management policy
- `17-5`: this memo + `reports/audit-binders/2026-04-26/17_5.md` + vulnerability management policy
- `18-1`: this memo + `reports/audit-binders/2026-04-26/18_1.md` + IT Business Continuity Plan
- `20-2`: this memo + `reports/audit-binders/2026-04-26/20_2.md` + incident response training policy
