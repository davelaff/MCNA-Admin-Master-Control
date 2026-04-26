# Remote Access Policy

**SSK Controls:** 12-1, 12-2  
**Owner:** Director of IT & MIS  
**Date:** 2026-04-26  
**Review cycle:** Annual

## Usage rules for remote access (12-1)

All remote access to MCNA systems requires authentication through Microsoft Entra ID with MFA enforced by Conditional Access. Company-owned or Intune-compliant devices are required for access to sensitive internal resources. Personal devices may access M365 cloud services only under MAM (Mobile Application Management) policy, which enforces app-level data protection without full device management.

Remote access is permitted only for business purposes. Employees must not allow others to use their remote session or credentials. Simultaneous connections through personal VPNs while connected to MCNA resources are prohibited. The acceptable use policy covers remote access obligations; employees acknowledge it at onboarding and annually.

## Control of remote access (12-2)

Remote access to on-premises resources is provided through site-to-site VPN (for site connectivity) and Azure AD Application Proxy for internal web application access, both managed by DIS. Direct inbound RDP, SMB, or other unencrypted protocols from the internet are blocked at the perimeter firewall. Remote administration of servers requires VPN connectivity or jump server access; direct internet-facing management interfaces are not permitted.

All remote sessions are logged at the VPN concentrator and Entra ID sign-in log level. Conditional Access policies enforce device compliance, location, and risk-based access controls. Access reviews for remote access entitlements are conducted by the Director of IT & MIS quarterly.
