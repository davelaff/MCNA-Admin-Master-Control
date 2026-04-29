# EXO Shared Mailbox Batch 1 Execution Packet

Status: approval-ready, not executed
Created: 2026-04-29
Plan ID: `d5d91bf4-9ca7-49cd-98b7-d2ea0e11e8d9`
Finding type: `shared_mailbox_interactive`
Batch: `Batch 1: low-dependency shared/function mailboxes`

## Objective

Prepare the first EXO shared-mailbox remediation batch for explicit approval and controlled execution. No tenant changes were made while preparing this packet.

## Scope

These eight targets are the lowest-risk disable candidates in the current queue. The intended change is the same for all eight entries: disable Entra account sign-in only. Do not delete the user object. Do not remove Exchange mailbox delegation.

| Action ID | Finding ID | Target | UPN | Proposed Action |
| --- | --- | --- | --- | --- |
| `f2a27f39-fbef-401d-856f-70216db05dde` | `8d9fa479-edd3-51c7-8ad9-b75c0d2b222a` | Accounts Payable | `ap@nofmetalcoatings.us` | Disable Entra account sign-in only |
| `bc63cfe0-dd49-4901-b91b-8c924fff9421` | `b7041292-2dc5-5797-9e09-5b91242e3c12` | MCNA Careers | `careers@nofmetalcoatings.us` | Disable Entra account sign-in only |
| `e1e496a0-95f7-4954-a780-8829ab9ba5ce` | `41140720-51b5-5a48-b616-1fee3dd3ba5e` | MCNA Human Resources | `humanresources@nofmetalcoatings.us` | Disable Entra account sign-in only |
| `a23af0ab-ed3f-4c1f-a8d8-52c768909aba` | `0ed90736-04cf-563e-8258-7a3dfd24031a` | MCNA Inquiries | `Contact@metal-coatings.com` | Disable Entra account sign-in only |
| `b33fe092-a763-4328-be9d-cea0663f40b6` | `3d607b26-11de-5834-95c3-5751ba3e5647` | Marketing | `marketing@nofmetalcoatings.us` | Disable Entra account sign-in only |
| `39c5511a-0a2f-4953-8acb-8f95a26dcd76` | `5a339e7b-9451-546a-b878-10e67e5da8b6` | Monthly Flash Report | `monthlyflashreport@nofmetalcoatings.us` | Disable Entra account sign-in only |
| `f3fc8de2-7a69-47a1-87dc-864d26a16882` | `27939408-479f-5f29-bb19-9f7705618ddf` | Orders | `orders@nofmetalcoatings.us` | Disable Entra account sign-in only |
| `a12cf224-e544-4a0f-bc81-a798497c800d` | `d61c8feb-dd37-5d7b-9f14-5bb93783b3bb` | Production | `production@nofmetalcoatings.us` | Disable Entra account sign-in only |

## Preconditions

1. Dave explicitly approves Batch 1.
2. Change window is business-safe and mailbox delegates are available if something unexpected surfaces.
3. No target in this batch is still being used for direct sign-in by a device, vendor workflow, or application.
4. The operator performing the change has Entra permissions to disable sign-in state.

## Operator Steps

Perform the change one target at a time, in the listed order.

1. Open Entra admin center.
2. Navigate to Users.
3. Open the target user object by UPN.
4. Edit properties.
5. Set `Account enabled = No`.
6. Save.
7. Record timestamp and operator initials in the execution log below before moving to the next target.

Suggested portal path:

`Entra admin center > Users > select user > Edit properties > Account enabled = No`

## Execution Log

Record completion inline for each target:

- Accounts Payable — Disabled at: ______ — Operator: ______ — Notes: ______
- MCNA Careers — Disabled at: ______ — Operator: ______ — Notes: ______
- MCNA Human Resources — Disabled at: ______ — Operator: ______ — Notes: ______
- MCNA Inquiries — Disabled at: ______ — Operator: ______ — Notes: ______
- Marketing — Disabled at: ______ — Operator: ______ — Notes: ______
- Monthly Flash Report — Disabled at: ______ — Operator: ______ — Notes: ______
- Orders — Disabled at: ______ — Operator: ______ — Notes: ______
- Production — Disabled at: ______ — Operator: ______ — Notes: ______

## Rollback Rule

If any mailbox or workflow breaks unexpectedly after disabling sign-in for a target, stop the batch immediately.

Rollback for the affected target only:

1. Re-open the target user object in Entra.
2. Set `Account enabled = Yes`.
3. Record the reason for rollback.
4. Do not proceed with remaining targets until the dependency is understood.

## Post-Change Verification

After all approved targets in this batch are changed:

1. Run `exo_scan_mailboxes`.
2. Confirm each target still reports `userPurpose=shared`.
3. Confirm each target now reports `accountEnabled=false`.
4. Confirm no user-reported access breakage before authorizing Batch 2.
5. Resolve each matching KB finding only after scan evidence confirms the new state.

## Closure Evidence Checklist

For each target, closure evidence should include:

1. The worksheet row from `reports/exo-shared-mailbox-remediation/2026-04-25.md`.
2. This batch packet with completed execution log.
3. The approval note naming approver and date.
4. Post-change `exo_scan_mailboxes` evidence confirming `accountEnabled=false`.
5. The KB finding ID resolved after verification.

## Approval Block

Approved by:

Date:

Approval note:

## Next Gate

If Batch 1 completes cleanly, proceed to Batch 2 from the existing queue artifact:

`reports/remediation-queues/exo-shared-mailbox-interactive-sign-in-2026-04-25.md`
