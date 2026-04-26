# Incident Response Policy

**SSK Controls:** 19-1, 19-2, 19-3, 19-4  
**Owner:** Director of IT & MIS  
**Date:** 2026-04-26  
**Review cycle:** Annual

## Detection and initial response (19-1)

Security alerts from Microsoft 365 Defender, Entra ID Protection, and Exchange Online Protection are the primary detection sources. The Director of IT & MIS monitors alert queues as primary responder. Confirmed security incidents trigger immediate notification to DIS (within 2 hours). Initial containment actions — account disable, device isolation, mail quarantine, sender block — are executed by the Director of IT & MIS using M365 admin tools and Defender for Endpoint.

Incidents are classified by severity (Critical, High, Medium, Low) based on data involved, systems affected, and business impact. Critical incidents trigger immediate notification to MCNA executive management and, where the NOF escalation threshold is met, NOF Corporation IS team.

## Recovery and improvement (19-2)

Post-containment, the Director of IT & MIS leads recovery with DIS technical support. Recovery steps follow the applicable IR runbook. A post-incident review (PIR) is conducted within 5 business days of incident closure. PIR findings feed back into policy updates, control improvements, and training content revisions. PIR reports are retained in the IT & MIS SharePoint library.

## IR procedures (19-3)

IR runbooks are maintained for MCNA's primary incident types: phishing / BEC, ransomware, account compromise, data exfiltration, and endpoint malware. Runbooks specify detection indicators, initial triage steps, containment actions, eradication steps, recovery sequence, and evidence preservation requirements. Runbooks are stored in the IT & MIS SharePoint library and reviewed annually by the Director of IT & MIS and DIS.

## IR team composition (19-4)

| Role | Person / Entity |
|------|----------------|
| IR Lead | Director of IT & MIS |
| Technical Support | DIS Computers (Nate Whitelaw, primary contact) |
| Legal / HR | Engaged by executive management for regulatory or HR-impacted incidents |
| Executive Sponsor | MCNA President / GM |
| NOF Escalation | NOF Corporation IS team (for incidents meeting NOF threshold) |

IR team contact information and escalation thresholds are maintained in the IR runbook documentation.
