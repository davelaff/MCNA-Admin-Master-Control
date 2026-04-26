# Physical Management of Endpoints

**SSK Controls:** 05-3  
**Owner:** Director of IT & MIS  
**Date:** 2026-04-26  
**Review cycle:** Annual

All MCNA company-owned endpoints are enrolled in Microsoft Intune, assigned to specific users, and tracked in the Intune device inventory. Device assignment is updated when devices change hands. Lost or stolen devices must be reported to the Director of IT & MIS immediately; the Director of IT & MIS triggers a remote wipe via Intune and disables the associated Entra ID account pending investigation.

Employees are prohibited from leaving company devices unattended in public spaces and from allowing personal use by non-employees. Devices must be locked when unattended (enforced via Intune screen lock policies). Laptops transported offsite are required to use full-disk encryption (BitLocker, enforced via Intune compliance policy).

Retired devices undergo a verified wipe (BitLocker encryption key discarded or full factory reset) before disposal. Physical destruction or certified data destruction is used for devices where software wipe is not feasible. Disposal records are maintained in the IT & MIS SharePoint library.
