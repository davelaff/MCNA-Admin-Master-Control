# Wireless Security

**SSK Controls:** 13-1, 13-2  
**Owner:** Director of IT & MIS  
**Date:** 2026-04-26  
**Review cycle:** Annual

MCNA wireless infrastructure is managed by DIS Computers. Corporate wireless uses WPA2-Enterprise (or WPA3-Enterprise where hardware supports it) with Entra ID authentication via RADIUS. Employees authenticate to corporate wireless using their Entra ID credentials; personal devices require MAM enrollment to access corporate wireless and may be limited to guest VLAN access by policy.

Guest wireless is provided on a separate SSID isolated on its own VLAN with no access to internal resources. Guest network traffic is subject to the same content filtering and logging as corporate traffic.

Wireless access points are inventoried and managed centrally through the wireless controller managed by DIS. Rogue access point detection is enabled; alerts are reviewed by DIS and escalated to the Director of IT & MIS. AP firmware is kept current by DIS as part of the managed service. DIS reviews wireless configuration and AP inventory annually and after facility changes.
