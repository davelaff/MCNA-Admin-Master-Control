# Software Restriction and Application Control

**SSK Controls:** 07-3  
**Owner:** Director of IT & MIS  
**Date:** 2026-04-26  
**Review cycle:** Annual

MCNA controls software installation on company endpoints through Microsoft Intune application deployment policies. Employees do not have local administrator rights on managed endpoints and cannot install arbitrary software without IT approval. All business applications are deployed via Intune or require a formal request to the Director of IT & MIS for evaluation and deployment.

Application allow/deny decisions are made by the Director of IT & MIS in coordination with department managers based on business need and security assessment. The Intune application inventory provides the authoritative list of approved and deployed software. Applications identified as unauthorized are removed via Intune remediation.

Microsoft Defender Antivirus blocks known malicious software at the endpoint. Defender Application Control (WDAC) or AppLocker policies are evaluated for production servers requiring stricter application control. DIS manages application control policy for server infrastructure.
