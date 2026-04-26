# Secure SketCH Missing Policy and Process Evidence Worklist

Generated: 2026-04-26 08:18 America/New_York

Scope: the 49 controls still listed as gaps in `reports/ssk-evidence-gaps/gaps-2026-04-26.md`.

Result: parallel read-only discovery found no additional defensible existing local evidence to link. The weak partial candidates should not be linked because they would overstate what the artifact proves. Coverage remains 26 of 75.

## Do Not Link

These artifacts were reviewed as partial candidates but do not close the stated controls:

| Control | Artifact | Reason |
|---|---|---|
| 01-2 | `docs/superpowers/specs/2026-04-22-securesketch-tracking-design.md` | Shows adoption of Secure SketCH tracking, not legal/regulatory compliance awareness. |
| 05-3 | `reports/audit-binders/2026-04-26/06_2.md`, `reports/audit-binders/2026-04-26/07_2.md`, `mcp-server/kb/mcna_amc.db` | Shows managed endpoint inventory/hardening posture, not physical endpoint handling, loss/theft, or workspace controls. |
| 06-1 | `reports/orphaned-assets/2026-04-20.md` | Shows M365 object ownership/activity hygiene, not information classification, retention, or lifecycle governance. |

## Required Evidence Packs

### Governance and Policy

Needed controls: `01-2`, `01-3`, `02-3`, `03-1`, `03-2`, `03-3`, `03-4`.

Required artifacts:

- MCNA information security policy with scope, ownership, review cadence, and dissemination evidence.
- Legal/regulatory/security guideline compliance register covering applicable laws, NOF group requirements, and Secure SketCH.
- Threat intelligence operating procedure or register identifying sources, review cadence, triage, and communication path.
- Third-party security risk procedure covering pre-contract assessment, contractual security obligations, periodic review, and exception handling.
- Evidence of at least one completed supplier/MSP security review, preferably DIS if that is the primary operational dependency.

### Workforce Training and Readiness

Needed controls: `04-1`, `04-3`, `04-4`.

Required artifacts:

- Cybersecurity role/skill matrix or training roadmap for IT/security staff.
- Employee security awareness program record: curriculum, audience, completion evidence, and review date.
- Phishing readiness evidence: simulation results, email-attack training records, or documented tabletop/remedial training.

### Physical Security

Needed controls: `05-1`, `05-2`, `05-3`.

Required artifacts:

- Facility security zoning or sensitive-area classification record.
- Physical access procedure and evidence of badge/key/access review.
- Endpoint physical handling procedure covering laptop/desktop placement, loss/theft handling, storage, disposal handoff, and workspace checks.

### Asset, Configuration, Vulnerability, and Backup

Needed controls: `06-1`, `06-5`, `07-1`, `07-3`, `07-4`, `07-5`, `07-6`, `09-1`, `09-3`, `10-1`, `10-2`, `17-5`.

Required artifacts:

- Information asset management procedure with classification, ownership, lifecycle, and retention rules.
- Purview label scan once `InformationProtectionPolicy.Read.All` is granted for `06-1`.
- Network diagram or network configuration inventory showing key segments, systems, and flows.
- Server hardening baseline and evidence of server configuration review.
- Authorized software/application-control procedure and exception process.
- Network device inventory and secure configuration/firmware review.
- Vulnerability management procedure plus scan or patch-status evidence.
- Penetration test authorization, report, or formal exception explaining why none exists.
- Encryption-in-transit standard and validation evidence for remote access, admin access, and sensitive data paths.
- Backup inventory, backup job evidence, retention settings, and restore-test evidence.
- Defender/AV/EDR deployment and policy evidence for endpoints and servers.
- Vulnerability scan evidence distinct from normal build/test records.

### Network, Remote Access, and Wireless

Needed controls: `11-1`, `11-2`, `11-3`, `11-4`, `11-5`, `11-6`, `11-7`, `12-1`, `12-2`, `13-1`, `13-2`.

Required artifacts:

- Network segmentation design and validation record.
- Firewall/traffic allow-deny rule review.
- IDS/IPS/NDR, firewall alert, or external-communication detection evidence.
- Internet access logging, DNS/proxy/SWG logging, or review evidence.
- Web content filtering configuration and category/block-list review.
- WAF or web-application attack detection evidence, or a documented non-applicability decision.
- Traffic baseline/threshold alerting or abnormal traffic/DDoS response procedure.
- Remote access usage policy, authorized-user/process evidence, and control validation.
- Wireless usage policy, encryption/authentication standard, authorized AP inventory, and rogue AP review.

### Email Security

Needed controls: `14-1`, `14-2`.

Required artifacts:

- Inbound email security policy and Microsoft Defender for Office 365/Exchange Online Protection settings export or review.
- Outbound email security evidence covering SPF/DKIM/DMARC, outbound spam/phishing controls, forwarding controls, and exception handling.

### Logging, BCP, and Incident Response

Needed controls: `16-2`, `16-3`, `16-4`, `18-1`, `19-1`, `19-2`, `19-3`, `19-4`, `20-1`, `20-2`.

Required artifacts:

- Log retention policy and evidence of retained M365/endpoint/server/network logs.
- Log analysis procedure and evidence of regular review.
- Cross-source log correlation/SIEM procedure or documented current-state gap.
- IT business continuity plan, system recovery priorities, and test/review evidence.
- Incident response policy covering detection, initial response, recovery, improvement, and communications.
- Incident response runbooks/playbooks and team roster with roles.
- Incident response team training and cross-functional tabletop/exercise evidence.

## Immediate Next Actions

1. Do not link partial evidence from this pass.
2. Create or collect the missing evidence packs above, prioritizing artifacts that can evidence multiple controls.
3. After each real artifact exists, link it with `ssk_link_evidence`, run `ssk_verify_pointers`, regenerate the coverage matrix, gap report, and binder.
4. For `06-1`, grant `InformationProtectionPolicy.Read.All` before rerunning the Purview label scan.
