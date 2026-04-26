# Password Policy

**SSK Controls:** 08-4  
**Owner:** Director of IT & MIS  
**Date:** 2026-04-26  
**Review cycle:** Annual

MCNA's password policy is enforced through Microsoft Entra ID Password Protection. The policy prohibits commonly-used passwords and a customized banned-password list specific to MCNA (organization name, product names, and derivatives). Minimum complexity requirements are enforced at the Entra ID level and synchronized to on-premises Active Directory via the Password Protection agent.

Password expiration is disabled in favor of MFA enforcement per Microsoft best practice and NIST SP 800-63B guidance. All cloud accounts are protected by Conditional Access policies requiring phishing-resistant MFA or Microsoft Authenticator for all sign-ins. Accounts without MFA enrollment trigger an alert reviewed by the Director of IT & MIS.

Local administrator passwords on domain-joined systems are managed by Microsoft LAPS (Local Administrator Password Solution), rotating automatically and storing credentials in Active Directory. LAPS is deployed to all domain-joined endpoints and servers managed by DIS.
