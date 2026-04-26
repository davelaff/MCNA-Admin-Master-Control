# Backup and Recovery

**SSK Controls:** 09-3  
**Owner:** Director of IT & MIS  
**Date:** 2026-04-26  
**Review cycle:** Annual

MCNA's backup posture combines Microsoft 365 native retention with a managed backup solution operated by DIS Computers. Microsoft 365 native retention: SharePoint versioning (minimum 500 versions), Exchange Online deleted item retention (30 days), OneDrive recycle bin (93 days). A third-party M365 backup solution (managed by DIS) provides point-in-time recovery for Exchange, SharePoint, OneDrive, and Teams data with a 30-day backup window minimum.

On-premises servers are backed up nightly to a DIS-managed backup infrastructure with offsite replication. Recovery point objective (RPO) for on-premises file servers is 24 hours; for the ERP system, 24 hours. DIS verifies backup integrity monthly via test restores. Results are reported to the Director of IT & MIS.

Backup storage is isolated from production — cloud backup uses a separate Azure tenant or vendor-managed storage inaccessible from the MCNA production tenant. On-premises backups replicate to offsite storage not directly accessible from the production network, providing ransomware isolation. Recovery procedures and RTO/RPO targets are documented in the IT-BCP.
