# Secure SketCH Review Batch 3

Date: 2026-04-29
Reviewer: Dave Lafferty
Cadence: 90 days
Review scope: Families `05`, `06`, `07`, `10`, `11`, `12`, `13` — Physical Security, Asset Management, Endpoint/Server Security, Malware Defense, Network Security, Remote Access, Wireless Security

## Objective

Establish the first auditor-defensible review record for operational and technical security controls. This batch surfaces two families with open findings requiring action (06, 07) and clears five families as satisfactory.

## Executive Conclusion

Seven family reviews recorded. Five reviewed as `ok`; two reviewed as `action_required`. This batch reduced the never-reviewed queue from 42 to 15. Open action items: license/Purview findings in family 06, and JWEDGE-2018 encryption gap in family 07.

## Review Summary

| Scope | Controls covered | Review result | Next review due |
|---|---|---|---|
| Family `05` | `05-1`, `05-2`, `05-3` | `ok` | 2026-07-28 |
| Family `06` | `06-1`, `06-2`, `06-3`, `06-4`, `06-5` | `action_required` | 2026-07-28 |
| Family `07` | `07-1`, `07-2`, `07-3`, `07-4`, `07-5`, `07-6` | `action_required` | 2026-07-28 |
| Family `10` | `10-1`, `10-2` | `ok` | 2026-07-28 |
| Family `11` | `11-1`, `11-2`, `11-3`, `11-4`, `11-5`, `11-6`, `11-7` | `ok` | 2026-07-28 |
| Family `12` | `12-1`, `12-2` | `ok` | 2026-07-28 |
| Family `13` | `13-1`, `13-2` | `ok` | 2026-07-28 |

## Scope 05 — Physical Security

Review record: `2f5c48f0-e390-43d4-bdd0-7ee84e443c10`

Controls covered:
- `05-1` Implementing physical security zoning by asset sensitivity
- `05-2` Implementing physical access and entry control
- `05-3` Physical management of endpoints

Conclusion:
MCNA facilities managed by plant operations. IT assets housed in secured server room with controlled access. Physical security policy in place. Endpoint physical controls backed by Intune device management and Windows Hello/BitLocker policies.

Evidence basis:
- IT-PHYS-SEC-v1.0 — Physical security policy
- Intune device management (device compliance + enrollment evidence in KB)

Next action:
Maintain cadence. Re-review by 2026-07-28.

## Scope 06 — Asset Management

Review record: `0311a210-ddb2-42c2-b6c6-59ac535d5769`

Controls covered:
- `06-1` Management of information assets
- `06-2` Management of hardware assets
- `06-3` Management of software assets
- `06-4` Managing internal and external information systems
- `06-5` Understand network configuration

Conclusion:
Asset management policy framework is in place. Open scanner findings require resolution before this family can be reviewed as `ok`.

Evidence basis:
- IT-ASSET-INFO-v1.0, IT-ASSET-HW-v1.0, IT-ASSET-SW-v1.0, IT-ASSET-SYS-v1.0, IT-ASSET-NET-v1.0

Open findings:
- `06-3` (High): 6 license stacking findings — users with redundant productivity SKUs
- `06-3` (Medium): 3 disabled-accounts-with-licenses findings — licenses not reclaimed after user disable
- `06-1` (Medium/High): Purview label scan blocked by Microsoft-Azure-Application-Gateway 403 — MS support ticket needed; no label taxonomy deployed org-wide

Next action:
- Open MS support ticket for Purview Graph API access (see `docs/governance/scope-additions/pending-gaps.md`).
- Reclaim licenses from 3 disabled accounts.
- Triage 6 license stacking findings — likely require per-user SKU review.
- Re-review family 06 after above resolved.

## Scope 07 — Endpoint and Server Security

Review record: `ea50dd24-6c72-449d-82d2-c94fed62552d`

Controls covered:
- `07-1` Standardizing secure configuration sets for servers, and server hardening
- `07-2` Standardizing secure configuration sets for endpoints, and endpoint hardening
- `07-3` Restriction of unauthorized software
- `07-4` Understand network configuration
- `07-5` Vulnerability management process
- `07-6` Conducting penetration tests

Conclusion:
Intune compliance policy is in place. One device (JWEDGE-2018) is flagged noncompliant due to encryption not enabled. Vulnerability management process is documented. Penetration test cadence to be established at organizational level.

Evidence basis:
- IT-VULN-MGMT-v1.0 — Vulnerability management process
- Intune compliance policy (KB scan snapshot evidence)
- IT-CONFIG-STD-v1.0 — Configuration standards

Open findings:
- `07-2` (High): JWEDGE-2018 encryption not enabled (`INTUNE-ENCRYPT-01`)
- `07-2` (Medium): Intune enrollment incomplete finding

Next action:
- Remediate JWEDGE-2018 — enable BitLocker encryption.
- Confirm Intune enrollment status for remaining devices.
- Establish pen test cadence (annual or biennial for SMB scope).
- Re-review family 07 after encryption and enrollment issues resolved.

## Scope 10 — Malware Defense

Review record: `fbb45eb8-e6fa-4ecf-b573-89323a5bdaf5`

Controls covered:
- `10-1` Protecting endpoints and servers from malware
- `10-2` Implementation of endpoint log collection and immediate response to malware infection (EDR)

Conclusion:
Microsoft Defender for Endpoint is active via M365 Business Premium across managed endpoints. Real-time protection and EDR capability present. Policy in place.

Evidence basis:
- IT-MALWARE-DEF-v1.0 — Malware defense policy
- Microsoft 365 Business Premium — Defender for Endpoint (real-time, EDR)

Next action:
Maintain cadence. Re-review by 2026-07-28.

## Scope 11 — Network Security

Review record: `c5dbc869-14fc-4c8d-b96b-fbc99cc90a73`

Controls covered:
- `11-1` Network segmentation
- `11-2` Denying communication which is not permitted
- `11-3` Detection of unauthorized communication from outside
- `11-4` Logging internet access and activity
- `11-5` Web access restriction (web content filtering)
- `11-6` Attack detection and response to web application (WAF etc.)
- `11-7` Response to abnormal increase in traffic

Conclusion:
Network perimeter managed by DIS. M365 Defender for Office 365 provides email and web threat protection. SMB scope acknowledged — no full SIEM or WAF required at current maturity level. Network security policy in place.

Evidence basis:
- IT-NET-SEC-v1.0 — Network security policy
- DIS MSP network management (firewall, perimeter)
- Microsoft 365 Business Premium — Defender for Office 365

Next action:
Maintain cadence. Re-review by 2026-07-28.

## Scope 12 — Remote Access

Review record: `889e0c10-b057-4597-a46a-c8aae6ddef52`

Controls covered:
- `12-1` Establishing and disseminating usage rules for remote access
- `12-2` Control of remote access

Conclusion:
Remote access governed through Entra ID Conditional Access policies requiring MFA for all remote access scenarios. Remote access policy in place.

Evidence basis:
- IT-REMOTE-ACCESS-v1.0 — Remote access policy
- Entra ID Conditional Access policies (CA scan evidence in KB)

Next action:
Maintain cadence. Re-review by 2026-07-28.

## Scope 13 — Wireless Security

Review record: `5925a4de-47a0-4416-afd0-0da6b8acb1a3`

Controls covered:
- `13-1` Wireless communication management
- `13-2` Management of wireless access points

Conclusion:
Wireless infrastructure managed by DIS at facility level. Corporate wireless uses enterprise-grade authentication. Policy in place.

Evidence basis:
- IT-WIRELESS-v1.0 — Wireless security policy
- DIS MSP wireless infrastructure management

Next action:
Maintain cadence. Re-review by 2026-07-28.

## Auditor Use

For any control in this batch, provide:
- This review memo
- The matching control page from the current audit binder (`reports/audit-binders/2026-04-26/`)
- The cited policy document from `docs/policies/`

Priority controls an auditor is likely to ask about:
- `07-2` (endpoint hardening): this memo + Intune compliance scan evidence + open JWEDGE-2018 finding
- `06-3` (software asset management): this memo + license scan findings in KB + IT-ASSET-SW-v1.0
- `11-1` (network segmentation): this memo + IT-NET-SEC-v1.0 + DIS network management documentation
- `10-2` (EDR): this memo + M365 Business Premium license evidence (copilot scan output)
