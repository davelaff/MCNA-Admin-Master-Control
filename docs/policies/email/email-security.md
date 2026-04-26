# Email Security

**SSK Controls:** 14-1, 14-2  
**Owner:** Director of IT & MIS  
**Date:** 2026-04-26  
**Review cycle:** Annual

## Inbound email security (14-1)

MCNA email is hosted on Exchange Online and protected by Exchange Online Protection (EOP) and Microsoft Defender for Office 365 Plan 1. EOP provides anti-spam, anti-malware, and anti-phishing filtering for all inbound mail. Defender for Office 365 adds Safe Links (URL rewriting and real-time detonation) and Safe Attachments (sandboxed attachment detonation) enforced tenant-wide.

SPF, DKIM, and DMARC are configured for the nofmetalcoatings.us domain. DMARC policy is set to enforce (p=reject or p=quarantine) to prevent spoofing of MCNA's domain in inbound mail. Anti-spoofing and impersonation protection policies are enabled in Defender for Office 365.

Employees report suspected phishing via the Microsoft Report Message add-in. Reported messages are triaged by the Director of IT & MIS using Threat Explorer.

## Outbound email security (14-2)

All outbound email flows through Exchange Online. SMTP relay from on-premises applications uses an authenticated Exchange Online connector. DKIM signing is enforced for all outbound mail from the nofmetalcoatings.us domain. Outbound spam filtering prevents MCNA sending infrastructure from being used for bulk mail or malware distribution.

The Director of IT & MIS reviews EOP and Defender for Office 365 policy settings quarterly. DMARC aggregate reports are reviewed by the Director of IT & MIS to identify unauthorized sending sources.
