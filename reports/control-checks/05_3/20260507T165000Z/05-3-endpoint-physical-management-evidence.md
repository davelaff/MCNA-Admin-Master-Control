# SSK 05-3 Endpoint Physical Management Evidence

**Control:** 05-3 - Physical management of endpoints  
**Prepared:** 2026-05-07 12:50 America/New_York  
**Prepared by:** Dave Lafferty, Director of IT & MIS  
**Evidence status:** Partial / auditor-ready with residual validation item  
**Next review due:** 2026-07-28

## Control Requirement

SSK 05-3 requires MCNA to define rules for managing endpoints, including PCs, smartphones, and tablets, and to confirm that endpoints are appropriately managed. For audit purposes, this means MCNA must show both documented physical custody rules and operational evidence that endpoints are assigned, managed, protected from unattended access, and handled correctly when lost, stolen, reassigned, or retired.

This control is physical and operational. It does not require a full CMDB by itself, but it does require enough endpoint inventory and assignment evidence to prove custody.

## Evidence Summary

| Evidence | Source | Date | Result |
|---|---|---:|---|
| Endpoint physical management policy | `docs/policies/physical/endpoint-physical-management.md` | 2026-04-26 | Rules documented |
| Family 05 review memo | `docs/reviews/2026-04-29-ssk-review-batch-3.md` | 2026-04-29 | Family 05 reviewed `ok` |
| Intune device scan | KB `activity_log:e4dbc83f-bb90-4dbc-be0e-68339f0c4905` | 2026-05-01 | Intune available; 1 scanned device; 1 not encrypted |
| Intune compliance policy scan | KB `activity_log:37fe9b14-c38d-4560-8e35-010a988fa0b8` | 2026-05-01 | Intune available; 1 compliance policy found; 0 findings |
| Stored SSK evidence link | KB `ssk_evidence:28dae352-4b83-4209-a5d4-ff4235068642` | 2026-04-26 | Policy linked to 05-3 |

## Current Operating Position

MCNA company-owned endpoints are governed through Microsoft Intune, assigned to specific users, and tracked in the Intune device inventory. Device assignment is updated when devices change hands.

Users must not leave company devices unattended in public spaces and must not allow non-employees to use company devices. Devices must be locked when unattended. Lost or stolen devices must be reported immediately to the Director of IT & MIS, who initiates remote wipe through Intune and disables or contains the associated Entra ID account when needed.

Laptops transported offsite are required to use full-disk encryption. Retired devices must be wiped, factory reset, physically destroyed, or sent through certified destruction when software wipe is not feasible. Disposal records are retained in the IT & MIS SharePoint library.

## Technical Enforcement Evidence

The local KB contains successful Intune scan evidence from 2026-05-01:

```json
{
  "tool_name": "intune_scan_devices",
  "outcome": "success",
  "detail": {
    "intune_available": true,
    "scanned": 1,
    "not_compliant": 0,
    "not_encrypted": 1,
    "stale": 0,
    "findings": 1
  }
}
```

The local KB also contains successful Intune compliance-policy scan evidence from 2026-05-01:

```json
{
  "tool_name": "intune_scan_compliance_policies",
  "outcome": "success",
  "detail": {
    "intune_available": true,
    "policies_found": 1,
    "findings": 0
  }
}
```

These scans prove Intune visibility and at least one active compliance policy. They do not fully prove that all company endpoints are encrypted or enrolled.

## Residual Validation Item

The latest available local Intune device scan shows one visible device and reports that device as `not_encrypted`. The related system inventory verification file also states: "The 1 enrolled Intune device is `not_encrypted`. Compliance policy exists but BitLocker not verified on the visible device. May be admin/test device - unclear."

This does not invalidate the documented SSK 05-3 process, but it means the current evidence packet should be presented as partially supported unless MCNA can add one of the following:

- A current Intune export showing all active company endpoints with user assignment, compliance state, encryption state, and last check-in.
- A scoped exception record confirming the one visible not-encrypted device is a test/admin device and does not hold business data.
- Remediation evidence showing the visible device is now encrypted.

## Auditor Minimal Evidence Statement

Based on currently available local evidence, MCNA can support SSK 05-3 at the policy/process level and can show Intune management capability. The minimum auditor packet consists of:

1. This memo.
2. The endpoint physical management policy.
3. The 2026-04-29 Family 05 review memo.
4. The Intune device and compliance-policy scan records cited above.
5. Follow-up evidence resolving or explaining the `not_encrypted` device.

## Attestation

I reviewed MCNA's documented endpoint physical management process and available local Intune evidence for SSK 05-3. The control is documented and has supporting management-system evidence. Before presenting this as a clean operating-control pass, MCNA should attach current endpoint inventory evidence or resolve the visible encryption discrepancy.

Reviewer: Dave Lafferty  
Role: Director of IT & MIS  
Date: 2026-05-07
