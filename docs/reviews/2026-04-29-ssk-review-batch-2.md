# Secure SketCH Review Batch 2

Date: 2026-04-29
Reviewer: Dave Lafferty
Cadence: 90 days
Review scope: Families `01`, `02`, `03`, `04` — Governance, Risk Management, Third-Party, Human Resources Security

## Objective

Establish the first auditor-defensible review record for foundational governance and people-security controls. All four families have policy documents under `docs/policies/` and no open KB scanner findings.

## Executive Conclusion

Four family reviews recorded. All four reviewed as `ok`. This batch reduced the never-reviewed queue from 58 to 42. Policy framework is in place for all covered families. No open scanner findings in any of these families at review time.

## Review Summary

| Scope | Controls covered | Review result | Next review due |
|---|---|---|---|
| Family `01` | `01-1`, `01-2`, `01-3`, `01-4` | `ok` | 2026-07-28 |
| Family `02` | `02-1`, `02-2`, `02-3`, `02-4` | `ok` | 2026-07-28 |
| Family `03` | `03-1`, `03-2`, `03-3`, `03-4` | `ok` | 2026-07-28 |
| Family `04` | `04-1`, `04-2`, `04-3`, `04-4` | `ok` | 2026-07-28 |

## Scope 01 — Security Governance

Review record: `e523c151-b0ea-4b57-9694-a803e367c3db`

Controls covered:
- `01-1` Building Security Risk Management Systems
- `01-2` Awareness and Compliance with Laws and Guidelines
- `01-3` Establishing and Disseminating the Basic and Overarching Security Policy
- `01-4` Establishing and Maintaining Documented Policies and Procedures

Conclusion:
MCNA security governance framework is established. Policy documents are current and in place. The 2026 IT-MIS Security and Governance program provides the organizational structure. No open KB findings in this family.

Evidence basis:
- IT-GOV-RISK-v1.0 — Risk management systems policy
- IT-GOV-LEGAL-v1.0 — Legal/regulatory compliance awareness
- IT-GOV-SEC-v1.0 — Overarching security policy
- IT-GOV-POL-v1.0 — Policy and procedures framework

Next action:
Maintain cadence. Re-review by 2026-07-28.

## Scope 02 — Risk Management

Review record: `abd42e26-2a14-4358-8b1d-f26d5821e6dc`

Controls covered:
- `02-1` Identification and evaluation of security risk
- `02-2` Planning and management for security risk response
- `02-3` Leveraging threat intelligence
- `02-4` Establishing protocol for proper disclosure and communication of cybersecurity- and information security-related information

Conclusion:
Risk management processes are documented. Policy framework covers identification, response, threat intelligence, and disclosure protocols. Control `02-4` has linked scan evidence in the KB. No open findings in this family.

Evidence basis:
- IT-GOV-RISK-v1.0 — Risk identification and evaluation
- IT-RISK-INTEL-v1.0 — Threat intelligence policy
- IT-RISK-DISC-v1.0 — Disclosure and communication protocol
- KB evidence linked for `02-4` (scan snapshot from operational artifact)

Next action:
Maintain cadence. Re-review by 2026-07-28.

## Scope 03 — Third-Party / Supply Chain Security

Review record: `f91f4e2e-6821-4b54-87e1-2573fa505468`

Controls covered:
- `03-1` Enforcing cybersecurity- and information security controls across all group companies
- `03-2` Security assessments before contracting with third parties
- `03-3` Specifying security obligations within third party contracts
- `03-4` Managing third party security risks

Conclusion:
Third-party governance is documented. DIS (managed service provider) is the primary third party and is governed under established IT-GOV-DIS framework. Vendor NDA ledger maintained in the registry. DIS privileged access is being normalized (separate active work — findings `b41b2c01` and `9ca3da77`). No open KB findings specifically in the family 03 control scope.

Evidence basis:
- IT-3P-MGMT-v1.0 — Third-party security management policy
- Vendor NDA ledger in registry
- DIS MSP governance framework (IT-GOV-DIS)

Open findings / exceptions:
- DIS Global Admin account normalization in progress (`dis@` repurpose to admin-only identity). Not a family 03 finding gap — tracked under family 08 IAM findings.

Next action:
Maintain cadence. Re-review by 2026-07-28. Close DIS account normalization before next 08 review.

## Scope 04 — Human Resources / People Security

Review record: `13199394-5726-48ac-8a19-60ad0f6fd36b`

Controls covered:
- `04-1` Developing cybersecurity talent
- `04-2` Integrating security throughout workers' and users' lifecycle
- `04-3` Security education for employees
- `04-4` Improving response and readiness to email-based cyberattacks

Conclusion:
HR security policy is in place. Employee security awareness is addressed at the organizational level. Email-based attack readiness relies on Microsoft 365 Defender platform controls (anti-phishing, safe links, Defender for Office 365) active via Business Premium. No open KB findings in this family.

Evidence basis:
- IT-HR-SEC-v1.0 — HR security policy
- Microsoft 365 Business Premium — Defender for Office 365 (anti-phishing, safe links)

Next action:
Maintain cadence. Re-review by 2026-07-28. Consider adding formal security awareness training documentation before next review cycle.

## Auditor Use

For any control in this batch, provide:
- This review memo
- The matching control page from the current audit binder (`reports/audit-binders/2026-04-26/`)
- The cited policy document from `docs/policies/`

Examples:
- `01-3`: this memo + `reports/audit-binders/2026-04-26/01_3.md` + IT-GOV-SEC-v1.0
- `03-4`: this memo + `reports/audit-binders/2026-04-26/03_4.md` + IT-3P-MGMT-v1.0
- `04-4`: this memo + `reports/audit-binders/2026-04-26/04_4.md` + M365 Defender configuration evidence
