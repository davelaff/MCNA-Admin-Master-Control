# EXO Shared Mailbox Batch 1 Execution Packet

Status: validation-ready, not executed
Created: 2026-04-29
Plan ID: `d5d91bf4-9ca7-49cd-98b7-d2ea0e11e8d9`
Finding type: `shared_mailbox_interactive`
Batch: `Batch 1: active operational shared mailboxes`

## Objective

Prepare the first EXO shared-mailbox validation batch for explicit approval and controlled follow-up. No tenant changes were made while preparing this packet.

## Scope

These eight targets are active operational shared mailboxes. They are not low-risk disable candidates. The first pass is to document current business use, confirm delegated-access readiness, and identify any direct sign-in, device, vendor, rule, or workflow dependency before any tenant change is approved.

Default target state: keep the shared mailbox in place and move usage to delegated access only. A group-backed address is a separate redesign decision, not the default remediation path for this packet.

| Action ID | Finding ID | Target | UPN | Proposed Action |
| --- | --- | --- | --- | --- |
| `f2a27f39-fbef-401d-856f-70216db05dde` | `8d9fa479-edd3-51c7-8ad9-b75c0d2b222a` | Accounts Payable | `ap@nofmetalcoatings.us` | Validate workflow, delegates, and direct sign-in dependency before any sign-in change |
| `bc63cfe0-dd49-4901-b91b-8c924fff9421` | `b7041292-2dc5-5797-9e09-5b91242e3c12` | MCNA Careers | `careers@nofmetalcoatings.us` | Validate workflow, delegates, and direct sign-in dependency before any sign-in change |
| `e1e496a0-95f7-4954-a780-8829ab9ba5ce` | `41140720-51b5-5a48-b616-1fee3dd3ba5e` | MCNA Human Resources | `humanresources@nofmetalcoatings.us` | Validate workflow, delegates, and direct sign-in dependency before any sign-in change |
| `a23af0ab-ed3f-4c1f-a8d8-52c768909aba` | `0ed90736-04cf-563e-8258-7a3dfd24031a` | MCNA Inquiries | `Contact@metal-coatings.com` | Validate workflow, delegates, and direct sign-in dependency before any sign-in change |
| `b33fe092-a763-4328-be9d-cea0663f40b6` | `3d607b26-11de-5834-95c3-5751ba3e5647` | Marketing | `marketing@nofmetalcoatings.us` | Validate workflow, delegates, and direct sign-in dependency before any sign-in change |
| `39c5511a-0a2f-4953-8acb-8f95a26dcd76` | `5a339e7b-9451-546a-b878-10e67e5da8b6` | Monthly Flash Report | `monthlyflashreport@nofmetalcoatings.us` | Validate workflow, delegates, and direct sign-in dependency before any sign-in change |
| `f3fc8de2-7a69-47a1-87dc-864d26a16882` | `27939408-479f-5f29-bb19-9f7705618ddf` | Orders | `orders@nofmetalcoatings.us` | Validate workflow, delegates, and direct sign-in dependency before any sign-in change |
| `a12cf224-e544-4a0f-bc81-a798497c800d` | `d61c8feb-dd37-5d7b-9f14-5bb93783b3bb` | Production | `production@nofmetalcoatings.us` | Validate workflow, delegates, and direct sign-in dependency before any sign-in change |

## Preconditions

1. Dave explicitly approves Batch 1 as a validation pass, not as a blind disable batch.
2. Business owners or delegates can confirm how each mailbox is actually used.
3. The operator has enough Exchange/Entra visibility to inspect delegates, mailbox rules, and sign-in context.
4. No tenant change is made in this packet unless a target is separately approved after validation.

## Operator Steps

Work each mailbox one target at a time, in the listed order.

1. Confirm the mailbox is still an active operational inbox and identify the business owner.
2. Confirm who currently has Full Access / Send As / Send on Behalf rights.
3. Check for mailbox rules, forwarding, device sign-in, vendor workflow, SMTP relay, or application dependency that would break if direct sign-in were disabled.
4. Classify the target state:
   - keep shared mailbox and move to delegated access only
   - redesign later to group-backed address or alias model
   - keep direct sign-in temporarily because a dependency still exists
5. Record the result in the validation log below before moving to the next target.
6. If a mailbox is proven ready for sign-in disable, create or update a separate approved execution packet before changing tenant state.

Suggested inspection surfaces:

`Entra admin center > Users > select user`

`Exchange admin center > Recipients > Mailboxes > select mailbox`

## Validation Log

Record validation inline for each target:

- Accounts Payable — Owner: ______ — Delegates confirmed: ______ — Direct sign-in dependency: Yes / No — Recommended target state: ______ — Operator: ______ — Notes: ______
- MCNA Careers — Owner: ______ — Delegates confirmed: ______ — Direct sign-in dependency: Yes / No — Recommended target state: ______ — Operator: ______ — Notes: ______
- MCNA Human Resources — Owner: ______ — Delegates confirmed: ______ — Direct sign-in dependency: Yes / No — Recommended target state: ______ — Operator: ______ — Notes: ______
- MCNA Inquiries — Owner: ______ — Delegates confirmed: ______ — Direct sign-in dependency: Yes / No — Recommended target state: ______ — Operator: ______ — Notes: ______
- Marketing — Owner: ______ — Delegates confirmed: ______ — Direct sign-in dependency: Yes / No — Recommended target state: ______ — Operator: ______ — Notes: ______
- Monthly Flash Report — Owner: ______ — Delegates confirmed: ______ — Direct sign-in dependency: Yes / No — Recommended target state: ______ — Operator: ______ — Notes: ______
- Orders — Owner: ______ — Delegates confirmed: ______ — Direct sign-in dependency: Yes / No — Recommended target state: ______ — Operator: ______ — Notes: ______
- Production — Owner: ______ — Delegates confirmed: ______ — Direct sign-in dependency: Yes / No — Recommended target state: ______ — Operator: ______ — Notes: ______

## Stop Rule

If validation shows a mailbox still depends on direct sign-in, stop remediation for that target immediately.

Do not disable sign-in for that mailbox in this batch. Record the dependency and move the target to a redesign or validate-first path.

If validation uncovers a pattern that likely applies to the remaining Batch 1 mailboxes, stop the batch and re-scope the plan before proceeding.

## Post-Validation Gate

After all targets in this batch are validated:

1. Separate the eight mailboxes into:
   - ready for delegated-access-only execution
   - redesign later to group/alias model
   - blocked by a current direct sign-in dependency
2. For any mailbox marked ready for delegated-access-only execution, prepare a separate approval packet for sign-in disable.
3. If any target is actually changed later, run `exo_scan_mailboxes` and confirm `userPurpose=shared` plus `accountEnabled=false` before closing findings.
4. Do not authorize Batch 2 based on assumption alone; carry forward the validated classification model.

## Closure Evidence Checklist

For each target, closure evidence should include:

1. The worksheet row from `reports/exo-shared-mailbox-remediation/2026-04-25.md`.
2. This batch packet with completed validation log.
3. The approval note naming approver and date.
4. Delegate and dependency evidence supporting the recommended target state.
5. Post-change `exo_scan_mailboxes` evidence confirming `accountEnabled=false` for any mailbox later approved for disable.
6. The KB finding ID resolved after verification.

## Approval Block

Validation approved by:

Date:

Approval note:

## Next Gate

If Batch 1 validation completes cleanly, update the queue and create mailbox-specific or sub-batch execution packets only for targets proven ready. Do not proceed to Batch 2 as a disable batch until the same validation model is applied.

`reports/remediation-queues/exo-shared-mailbox-interactive-sign-in-2026-04-25.md`
