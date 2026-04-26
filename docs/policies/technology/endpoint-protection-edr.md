# Endpoint Protection and EDR

**SSK Controls:** 10-1, 10-2  
**Owner:** Director of IT & MIS  
**Date:** 2026-04-26  
**Review cycle:** Annual

All MCNA endpoints are protected by Microsoft Defender Antivirus with real-time protection, cloud-delivered protection, and automatic sample submission enabled. Defender configuration is enforced through Intune compliance and configuration policies; endpoints out of compliance are flagged and may be blocked from accessing company resources via Conditional Access.

Microsoft Defender for Endpoint (Plan 2) provides EDR capability across MCNA endpoints: behavioral detection, automated investigation, device isolation, and integration with Microsoft 365 Defender. Endpoint telemetry flows to the M365 Defender portal, where the Director of IT & MIS monitors the alert and incident queues. DIS provides Tier 2 investigation support for incidents escalated by the Director of IT & MIS.

On confirmed high-severity detections, Defender for Endpoint is configured to automatically isolate the affected device from the network while preserving cloud connectivity for investigation. Malware incident response follows the IR runbook maintained in the IT & MIS SharePoint library. Incident timelines, containment actions, and outcomes are logged per the IR policy.
