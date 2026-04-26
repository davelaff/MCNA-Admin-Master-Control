# IT Business Continuity Plan

**SSK Controls:** 18-1  
**Owner:** Director of IT & MIS  
**Date:** 2026-04-26  
**Review cycle:** Annual

MCNA's IT Business Continuity Plan (IT-BCP) identifies critical IT systems, their dependencies, recovery time objectives (RTO), and recovery point objectives (RPO).

**Critical systems and recovery targets:**

| System | RTO | RPO |
|--------|-----|-----|
| Exchange Online / M365 | 4 hours | 24 hours |
| SharePoint / OneDrive | 4 hours | 24 hours |
| ERP (Dynamics / on-prem) | 8 hours | 24 hours |
| On-premises file servers | 8 hours | 24 hours |
| Network infrastructure | 4 hours | N/A (config backup) |
| Entra ID / identity | 4 hours | N/A (Microsoft-managed) |

BCP scenarios covered: M365 service outage, on-premises server failure, ransomware, loss of internet connectivity, and loss of key IT personnel. Runbooks for infrastructure recovery scenarios are maintained by DIS. Recovery procedures are tested annually through tabletop exercises and, for on-premises systems, through backup restore verification.

The IT-BCP is reviewed annually by the Director of IT & MIS and signed off by executive management. Updates are made after any significant incident, major infrastructure change, or annual review cycle. A copy of the IT-BCP is stored in the IT & MIS SharePoint library and a printed copy is held offsite for access during total system outage scenarios.
