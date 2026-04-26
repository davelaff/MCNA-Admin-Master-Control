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
| **Outcome** | `purview_scan_labels` returns `available: false` with `purview_scope_gap` finding and action pointing to Purview P1/P2 licensing check. The permission itself is not the gap. |

---

## Microsoft365CopilotSettings.Read.All

| Field | Value |
|---|---|
| **Type** | Delegated |
| **Identified** | 2026-04-25 |
| **Identified by** | D. Lafferty |
| **Status** | Pending |
| **Justification** | Required for `copilot_scan_settings` to inspect tenant Copilot settings. Without it, Copilot settings scans should record `copilot_scope_gap`. |
| **SSK mapping** | AI governance / Copilot governance evidence |
| **Blocked by** | Admin consent not yet granted |

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
