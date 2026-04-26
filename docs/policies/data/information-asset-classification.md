# Information Asset Classification and Sensitivity Labels

**SSK Controls:** 06-1  
**Owner:** Director of IT & MIS  
**Date:** 2026-04-26  
**Review cycle:** Annual

MCNA manages information assets through Microsoft 365 and Entra ID. Asset inventory is maintained via the Intune device registry (hardware assets), the Microsoft 365 license assignment (user accounts and entitlements), and the SharePoint document library structure (information repositories).

**Sensitivity label status (scan: 2026-04-26):** Microsoft Purview sensitivity labels are not yet configured in the MCNA tenant. The `InformationProtectionPolicy.Read.All` scope is granted and verified. A live scan confirms the tenant has 0 published sensitivity labels. Configuring sensitivity labels is a planned control improvement — this document represents the current baseline state and initiates the record of intent.

Information classification at MCNA is currently implemented through SharePoint site access controls and Entra ID group-based permissions rather than label-based classification. The planned improvement is to define and publish a sensitivity label taxonomy (Public, Internal, Confidential, Highly Confidential) aligned with NOF Corporation's information classification requirements and apply auto-labeling policies for M365 content.

The Director of IT & MIS owns this improvement item and will track progress against the annual IT roadmap.
