# Scope Gap Record - Pending Consent

Scopes identified as needed but not yet added to MCNA-TenantIntel-ReadOnly.
Each entry requires explicit approval before adding. Update this file when consented.

---

## InformationProtectionPolicy.Read.All

| Field | Value |
|---|---|
| **Type** | Application (only form available; Delegated `.Read.All` does not exist in Graph) |
| **Identified** | 2026-04-23 |
| **Identified by** | D. Lafferty |
| **Status** | **Consented — 2026-04-26** |
| **Consented by** | D. Lafferty (global admin) |
| **Justification** | Added to support `purview_scan_labels`. Application credential present and consented. However, the Graph beta endpoint (`/beta/security/informationProtection/sensitivityLabels`) returns HTTP 403 from Microsoft-Azure-Application-Gateway for both delegated and application callers. This is an API availability block, not a permission issue — the endpoint requires Purview/AIP to be licensed and activated in the tenant. The tool correctly uses delegated auth (`InformationProtectionPolicy.Read`) per Microsoft docs; the Application permission is also present but does not unblock the endpoint. |
| **SSK mapping** | SSK 06-1 |
| **Outcome** | Root cause corrected 2026-04-26: NOT a licensing gap. SPB (Business Premium) includes `RMS_S_ENTERPRISE` + `RMS_S_PREMIUM` (AIP P1/P2). NOT a permissions gap — both delegated and application credentials are consented. The 403 from Microsoft-Azure-Application-Gateway indicates the **Purview unified labeling store has not been provisioned/activated** in this tenant. Action: [purview.microsoft.com/informationprotection/informationprotectionlabels/sensitivitylabels](https://purview.microsoft.com/informationprotection/informationprotectionlabels/sensitivitylabels) > activate unified labeling service. Note: compliance.microsoft.com is **retired**; use purview.microsoft.com. Re-run `purview_scan_labels` after activation (provisioning can take up to 24h). **2026-04-29 UPDATE:** Still 403 App Gateway 3+ days after first sensitivity label was published (2026-04-26). Both org-wide (application token) and `/me/` (delegated) endpoints blocked identically. This is no longer consistent with a propagation delay. **Action: Open MS support ticket** from nof-dlafferty@nofmetalcoatings.us — Product: Microsoft Purview / Information Protection; Issue: `GET /beta/security/informationProtection/sensitivityLabels` returns HTTP 403 from Microsoft-Azure-Application-Gateway/v2 on both paths; scopes consented, label published, store initialized. |

---

## CopilotSettings-LimitedMode.Read

| Field | Value |
|---|---|
| **Type** | Delegated |
| **Identified** | 2026-04-25 |
| **Identified by** | D. Lafferty |
| **Status** | Resolved / validated 2026-04-29 |
| **Justification** | `copilot_scan_settings` uses `CopilotSettings-LimitedMode.Read` against `/copilot/admin/settings/limitedMode` (v1.0), not `Microsoft365CopilotSettings.Read.All`. Live validation on 2026-04-29 returned `available:true`, `findings:0`; the stale `copilot_scope_gap` finding was resolved and control `15-3` was re-reviewed to `regularly_reviewed`. |
| **SSK mapping** | AI governance / Copilot governance evidence |
| **Blocked by** | None |

---

## Sites.FullControl.All

| Field | Value |
|---|---|
| **Type** | Delegated |
| **Identified** | 2026-04-22 |
| **Identified by** | D. Lafferty |
| **Status** | Pending / Deferred |
| **Justification** | Required for permission-level sharing checks in `sharing_*` tools. Current `Sites.Read.All` returns site metadata but not granular permission assignments. Broad scope; add only if permission-audit depth justifies it. |
| **SSK mapping** | SSK 15-4 |
| **Blocked by** | Scope breadth review; may be deferred indefinitely |

---

## How to add a scope

1. Update this file: change Status to `Approved`, add Approved-by and Date fields.
2. Add to app reg via Entra portal: API permissions -> Add a permission.
3. Grant admin consent as nof-dlafferty@nofmetalcoatings.us.
4. Create a new dated record in this folder.
5. Update `docs/auth/app-registrations.md` permissions table.
6. Remove the entry from this file once consented and documented.
