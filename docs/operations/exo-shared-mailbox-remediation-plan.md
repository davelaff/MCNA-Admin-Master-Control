# EXO Shared Mailbox Remediation Plan

Status: planned, not executing  
Created: 2026-04-25  
Primary worksheet: `reports/exo-shared-mailbox-remediation/2026-04-25.md`  
Finding type: `shared_mailbox_interactive`  
Severity: High

## Decision

MCNA is not taking tenant action yet. The current stage is planning and evidence readiness.

The remediation target is still clear: shared mailboxes should not rely on direct interactive sign-in. Access should come through mailbox delegation, not shared credentials.

What changed on 2026-04-29 is the classification of Batch 1. Those eight mailboxes are active operational team inboxes, not low-risk disable candidates. They need a validation pass first, not a blind sign-in disable.

## Source State

The KB has 30 open High EXO findings for `shared_mailbox_interactive`.

The worksheet groups them into:

- 16 immediate disable candidates
- 7 former-user style mailboxes to validate, then disable
- 7 device, automation, infrastructure, or workflow candidates to validate first

## Execution Model When Approved

Do not use a broad write run. First validate mailbox purpose and access model, then use small, reversible batches only where direct sign-in is proven unnecessary.

### Batch 1: active operational shared mailboxes

- Accounts Payable
- MCNA Careers
- MCNA Inquiries
- MCNA Human Resources
- Marketing
- Monthly Flash Report
- Orders
- Production

Action when approved: validate business use, current delegates, mailbox rules, automation, direct sign-in dependency, and whether a group-backed address would actually satisfy the workflow. Default target state is to keep the shared mailbox and move usage to delegated access only. Do not delete the user object. Do not remove mailbox delegation. Do not disable sign-in until the validation pass proves there is no remaining direct sign-in dependency.

### Batch 2: remaining shared/function mailboxes

- MCNA Export Group
- MCNA Import Group
- MCNA IT Support
- MCNA Safety
- NOF Quality
- Sales
- Shipping
- Supply Chain

Action when approved: apply the same validation model used in Batch 1 before scheduling any sign-in disable. Do not assume these are clean disable candidates until mailbox purpose and access pattern are confirmed.

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

After each validation batch or approved change batch:

1. Confirm mailbox purpose, delegate model, and any direct sign-in dependency are documented for each target.
2. If sign-in is disabled for a validated target, run `exo_scan_mailboxes`.
3. Confirm each remediated mailbox snapshot remains `userPurpose=shared`.
4. Confirm each remediated mailbox snapshot has `accountEnabled=false`.
5. Check for user-reported access or workflow breakage before moving to the next batch.
6. Resolve matching KB findings only after scan evidence confirms the account state.

## Evidence Handling

Closure evidence should include:

- the pre-change worksheet row
- the validation notes for business use, delegates, and dependency classification
- the batch approval note
- the post-change `exo_scan_mailboxes` result where a sign-in disable is actually executed
- KB finding IDs resolved after verification

The closure evidence should be linked to `EXO-SHARED-ENABLED-01`.

## Stage Gate

This plan is ready for validation immediately. It is ready for execution only after Dave explicitly approves a mailbox or batch that has already passed validation. Until then, it remains a planning artifact.
