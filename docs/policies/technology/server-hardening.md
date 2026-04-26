# Server Hardening and Secure Configuration

**SSK Controls:** 07-1  
**Owner:** Director of IT & MIS  
**Date:** 2026-04-26  
**Review cycle:** Annual

MCNA on-premises server infrastructure is managed by DIS Computers under a hardening baseline derived from CIS Benchmark recommendations. Servers run current supported OS versions; end-of-life OS versions are not permitted on production infrastructure without a documented exception and compensating controls. Unnecessary services, ports, and features are disabled as part of the hardening baseline.

Windows servers are domain-joined and managed via Group Policy. Security configurations are enforced centrally; local administrator access on servers is restricted and managed via Microsoft LAPS. Server configuration baselines are documented by DIS and maintained in the IT & MIS SharePoint library.

Azure-hosted infrastructure is governed by Microsoft Defender for Cloud security recommendations. The Director of IT & MIS reviews Defender for Cloud secure score and recommendations monthly. Deviations from baseline require documented justification and approval by the Director of IT & MIS.
