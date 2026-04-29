# Entra App Registration Missing Owner Assignment Plan

Status: planned, not executing  
Created: 2026-04-29  
Primary worksheet: `reports/entra-missing-owner-remediation/2026-04-29.md`  
Finding type: `missing_owner`  
Severity: High

## 2026-04-29 Update

This plan is now mostly historical.

- `MCNA_GPT` was deleted as dead/unused, so it left the owner-assignment scope entirely.
- `entra_scan_app_regs` was corrected on 2026-04-29 to hydrate owners from Graph before evaluating `missing_owner`.
- The corrected live scan reduced the real active owner-gap set to 7 items.
- Dave assigned owners to the 4 MCNA-owned apps that still needed them:
	- `CopilotGraphConnector`
	- `CI Project Tracker`
	- `PowerBI-Usage-Reader`
	- `P2P Server`
- The remaining 3 active findings from that rescan were non-MCNA items and should be handled by scanner suppression / routing, not by MCNA owner assignment:
	- `Report Message`
	- `MessageCenterFeedBot`
	- `ConnectSyncProvisioning_MCNA-DC_04a43dcfcd20`

No broad MCNA-owned owner-assignment batch remains open from this worksheet after those actions.

## Decision

MCNA-owned app registrations should get an explicit human owner.

Default owner target is `nof-dlafferty@nofmetalcoatings.us` unless a specific app already has a better long-term operational owner. This plan originally covered the 26 `MCNA-OWNED` app registrations from the triage worksheet.

This artifact is execution planning only. No tenant write action is approved by this document.

## Source State

Current triage state from the worksheet:

- 26 `MCNA-OWNED` app registrations need an owner assigned
- 5 `MS-SYSTEM` app registrations should be suppressed, not assigned
- 3 `PP-SYSTEM` app registrations need separate Power Platform ownership review
- 1 `DIS-MANAGED` app registration should be routed to Nate Whitelaw
- 3 `REVIEW` app registrations need identification before any owner action

Out of scope for this execution run:

- `MCNA_GPT` secret rotation
- Power Platform system identities
- Microsoft system app suppressions
- DIS-managed ownership assignment
- review-only portal identities pending investigation

## Execution Model When Approved

Do not mix all 26 into one blind bulk action.

Use two small, auditable batches with a verification pause between them.

Preferred execution path: Entra portal if Dave wants maximum visibility and low scripting risk.

Alternate execution path: Microsoft Graph batch if the portal run becomes too slow or error-prone. If Graph is used later, keep the same batches and collect pre/post evidence the same way.

## Pre-Flight

Before any owner assignment:

1. Confirm `nof-dlafferty@nofmetalcoatings.us` is the intended owner for all 26 `MCNA-OWNED` entries that do not already have a more appropriate delegate.
2. Confirm no app in the batch is actually a retirement candidate that should be deleted instead of assigned.
3. Capture pre-change evidence for each app: display name, application ID, current owners pane showing none, and the matching finding ID from the worksheet.
4. Keep `MCNA_GPT` in the first batch because it is operationally important, but treat secret rotation as a separate change.

## Batch 1: High Priority MCNA-Owned Apps

Assign `nof-dlafferty@nofmetalcoatings.us` as owner for:

- MCNA-TenantIntel-ReadOnly
- MCNA Sales BI API
- MCNA Power Apps
- MCNA_GPT
- MCNA Financial Insights (Copilot Studio)
- MCNA WiSys Agent (Copilot Studio)
- Claude MCP
- AR Collections Agent (Copilot Studio)
- Competitor Product Profiles (Copilot Studio)
- Corporate Intercept Agent (Copilot Studio)
- CDR SDS Information Agent (Copilot Studio)
- NOF Corporate Email Watcher (Copilot Studio)
- Price Approvals Assistant (Copilot Studio)
- SDS Expert (Copilot Studio)

Reason: these are the clearest current-production or governance-relevant MCNA apps and agents.

## Batch 2: Medium and Low Priority MCNA-Owned Apps

Assign `nof-dlafferty@nofmetalcoatings.us` as owner, or a named delegate if decided before execution, for:

- CI Project Tracker
- PowerBI-Usage-Reader
- PBIService
- P2P Server
- CoE Command Center
- TestCopilot
- CopilotGraphConnector
- Agent 1 (Copilot Studio)
- Agent (Copilot Studio) — a882b07e
- Agent (Copilot Studio) — d83c45dd
- Portals-DaveLafferty
- Portals-Customer Order Status
- Products-test-agent (Copilot Studio)

Reason: lower immediate risk, more likely to include test or owner-refinement cases.

## Special Handling Inside Scope

These entries stay inside the 26-app owner run but deserve explicit notes:

- `TestCopilot` and `Products-test-agent (Copilot Studio)`: before assigning owner, decide whether they are still worth keeping. If they are not, convert them into deletion candidates instead of assigning owner.
- `P2P Server`, `MCNA Sales BI API`, `CI Project Tracker`, and `Portals-Customer Order Status`: if a stable business or IT delegate exists now, assign that owner instead of using Dave as placeholder.
- generic-name Copilot Studio agents: keep a small alias note with the object ID or finding ID so future cleanup does not lose track of which agent is which.

## Verification

After Batch 1 and again after Batch 2:

1. Re-open each app registration and confirm `nof-dlafferty@nofmetalcoatings.us` appears in Owners.
2. Re-run `entra_scan_app_regs`.
3. Confirm each assigned app no longer produces `missing_owner` findings.
4. Confirm non-batch findings remain unchanged: `MS-SYSTEM`, `PP-SYSTEM`, `DIS-MANAGED`, and `REVIEW` should not be accidentally altered.
5. Resolve only the findings verified clean by the post-change scan.

## Evidence Handling

For each remediated app, retain:

- pre-change owner screenshot or export
- post-change owner screenshot or export
- finding ID from the worksheet
- post-change `entra_scan_app_regs` result showing the finding cleared

If execution happens in the portal, capture one batch summary screenshot plus per-app evidence only where needed.

## Follow-On Work After Owner Assignment

These are adjacent but separate actions:

1. Rotate `MCNA_GPT` secret before 2026-07-10.
2. Add suppression rules for the 5 `MS-SYSTEM` entries.
3. Decide treatment for the 3 `PP-SYSTEM` entries: suppress vs assign to Power Platform owner.
4. Send `ConnectSyncProvisioning_*` to Nate Whitelaw for DIS-side ownership.
5. Investigate the 3 `REVIEW` portal identities before assigning or deleting anything.

## Stage Gate

This plan is ready for execution only after Dave explicitly approves a batch.

Until then, it remains a planning artifact and no owner assignments should be made.