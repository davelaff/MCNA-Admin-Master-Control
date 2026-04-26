# Network Security Controls

**SSK Controls:** 11-1, 11-2, 11-3, 11-4, 11-5, 11-6, 11-7  
**Owner:** Director of IT & MIS  
**Date:** 2026-04-26  
**Review cycle:** Annual

MCNA network security is managed by DIS Computers with oversight from the Director of IT & MIS. DIS is responsible for firewall management, VLAN configuration, IDS/IPS monitoring, and network device patching.

**Network segmentation (11-1):** VLANs separate production systems, corporate endpoints, guest access, and network management traffic. Inter-VLAN routing is governed by firewall policy; lateral movement between zones requires explicit permit rules.

**Permitted traffic enforcement (11-2):** The perimeter firewall operates under a default-deny posture. All inbound and outbound traffic flows are explicitly permitted or blocked by rule. Firewall rule sets are reviewed by DIS and the Director of IT & MIS quarterly; orphaned or overly permissive rules are removed.

**Intrusion detection (11-3):** The perimeter firewall includes IDS/IPS functionality. Signatures are kept current by DIS. Alerts are reviewed by DIS and escalated to the Director of IT & MIS for confirmed intrusion attempts or anomalous traffic patterns.

**Internet access logging (11-4):** Outbound internet access is logged at the firewall. Logs are retained per the log management policy (90 days minimum) and are available to the Director of IT & MIS and DIS for investigation.

**Web content filtering (11-5):** Outbound web access is filtered by category and reputation using the perimeter firewall's URL filtering capability. High-risk categories — malware distribution, phishing, anonymizers, illegal content — are blocked by default. Business-justified exceptions require approval by the Director of IT & MIS.

**Web application protection (11-6):** MCNA does not host public-facing web applications on owned infrastructure. Cloud workloads in Azure are protected by Microsoft-managed DDoS Protection and Azure Web Application Firewall where applicable. Exchange Online Protection provides inbound email-based web attack protection.

**DDoS response (11-7):** DIS's ISP provides upstream DDoS mitigation at the network edge. Azure services are covered by Azure DDoS Protection. Anomalous traffic volume triggering ISP or firewall thresholds is escalated by DIS to the Director of IT & MIS immediately.
