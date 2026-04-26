# EXO Shared Mailbox Remediation Plan

Status: planned, not executing  
Created: 2026-04-25  
Primary worksheet: `reports/exo-shared-mailbox-remediation/2026-04-25.md`  
Finding type: `shared_mailbox_interactive`  
Severity: High

## Decision

MCNA is not taking tenant action yet. The current stage is planning and evidence readiness.

The remediation target is clear: shared mailboxes should not have enabled Entra accounts for direct interactive sign-in. Access should come through mailbox delegation, not shared credentials.

## Source State

The KB has 30 open High EXO findings for `shared_mailbox_interactive`.

The worksheet groups them into:

- 16 immediate disable candidates
- 7 former-user style mailboxes to validate, then disable
- 7 device, automation, infrastructure, or workflow candidates to validate first

## Execution Model When Approved

Do not use a broad write run. Use small, reversible batches.

### Batch 1: low-dependency shared/function mailboxes

- Accounts Payable
- MCNA Careers
- MCNA Inquiries
- MCNA Human Resources
- Marketing
- Monthly Flash Report
- Orders
- Production

Action when approved: disable Entra account sign-in only. Do not delete the user object. Do not remove mailbox delegation.

### Batch 2: remaining shared/function mailboxes

- MCNA Export Group
- MCNA Import Group
- MCNA IT Support
- MCNA Safety
- NOF Quality
- Sales
- Shipping
- Supply Chain

Action when approved: disable Entra account sign-in only after Batch 1 verifies cleanly.

### Batch 3: former-user style mailboxes

- Bob Bellow
- Cassandra Gosche
- Chris Riddle
- Erik Larson
- Jason Lestock
- Jason Zmijewski
- Kelli Leonetti

Action when approved: validate business owner or retention need first. If the mailbox is only a delegated shared/departed-user mailbox, disable Entra account sign-in.

### Batch 4: validate-first dependencies

- DIS No Reply
- Visitor iPad
- NOF iPad
- Manufacturing
- Manufacturing2
- Network Services
- Ring

Action when approved: validate direct sign-in, SMTP, device, vendor, shop-floor, or automation dependencies one at a time. These are the only entries with obvious operational breakage risk.

## Verification

After each approved batch:

1. Run `exo_scan_mailboxes`.
2. Confirm each remediated mailbox snapshot remains `userPurpose=shared`.
3. Confirm each remediated mailbox snapshot has `accountEnabled=false`.
4. Check for user-reported access or workflow breakage before moving to the next batch.
5. Resolve matching KB findings only after scan evidence confirms the account state.

## Evidence Handling

Closure evidence should include:

- the pre-change worksheet row
- the batch approval note
- the post-change `exo_scan_mailboxes` result
- KB finding IDs resolved after verification

The closure evidence should be linked to `EXO-SHARED-ENABLED-01`.

## Stage Gate

This plan is ready for execution only after Dave explicitly approves a batch. Until then, it remains a planning artifact.
