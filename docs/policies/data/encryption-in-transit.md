# Encryption in Transit

**SSK Controls:** 09-1  
**Owner:** Director of IT & MIS  
**Date:** 2026-04-26  
**Review cycle:** Annual

MCNA enforces encryption in transit across all Microsoft 365 services. Exchange Online, SharePoint Online, Teams, and OneDrive enforce TLS 1.2 minimum by Microsoft's service configuration. SMTP transport to external mail servers uses Opportunistic TLS with STARTTLS; inbound mail from known partners may be configured for enforced TLS connectors where required.

Internal network segments carrying sensitive traffic (ERP database connections, file server SMB traffic, management interfaces) use IPsec or application-layer TLS where supported by the platform. DIS manages IPsec tunnel configurations for site-to-site connectivity. Unencrypted protocols — FTP, Telnet, HTTP for internal services — are prohibited on MCNA-managed infrastructure; exceptions require documented approval by the Director of IT & MIS.

The Director of IT & MIS reviews Exchange Online TLS configuration and Defender for Cloud network encryption recommendations annually. TLS 1.0 and 1.1 are disabled on all MCNA-managed infrastructure.
