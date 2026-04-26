# Log Management

**SSK Controls:** 16-2, 16-3, 16-4  
**Owner:** Director of IT & MIS  
**Date:** 2026-04-26  
**Review cycle:** Annual

## Log storage, retention, and protection (16-2)

MCNA's log management is anchored in Microsoft Purview Audit (Standard). M365 audit logs — Entra ID sign-in and audit events, Exchange admin and mailbox access, SharePoint and OneDrive file operations, Teams activity — are retained for 90 days standard, with high-value operations (admin actions, privileged role use, bulk downloads) retained for 180 days under the Audit Standard plan. Purview audit logs are immutable within the Microsoft service and protected from modification by tenant administrators.

Firewall and network device logs are retained by DIS for a minimum of 90 days in the MSP's logging infrastructure. Endpoint detection logs are retained in Microsoft Defender for Endpoint for 180 days. Log storage integrity is Microsoft's responsibility for cloud logs; DIS is responsible for on-premises log retention per their managed service commitments.

## Log analysis (16-3)

The Director of IT & MIS analyzes M365 audit logs using Microsoft Purview Audit search and Defender for Endpoint Advanced Hunting (KQL). Exchange message trace and Entra ID sign-in logs are used for investigating mail flow anomalies and authentication events respectively. DIS performs log analysis for on-premises infrastructure and network events.

Alert rules in Microsoft Defender XDR automate detection of high-priority events (impossible travel, mass file download, admin role assignment outside change window). Alerts are reviewed by the Director of IT & MIS and triaged with DIS as needed.

## Log correlation (16-4)

Cross-source log correlation is performed using Microsoft Sentinel where deployed, or manually across Entra sign-in logs, Defender incidents, Exchange message trace, and Purview audit search for significant investigations. Defender XDR provides automated incident correlation across endpoint, identity, email, and cloud signals. The Director of IT & MIS evaluates the business case for a formal SIEM deployment as part of the annual IT roadmap review.
