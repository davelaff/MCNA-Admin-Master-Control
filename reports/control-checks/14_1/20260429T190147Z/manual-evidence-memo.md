# 14-1 Manual Evidence Memo

Generated: 2026-04-29T19:01:47.595869+00:00
Prepared by: Dave Lafferty
Control: 14-1 Security check on incoming mail
Control-check run: `manual_required`

## Conclusion

Control `14-1` is supported by current documented policy and prior review evidence. The control-check run for `14-1` did not execute any automated tenant scan because no automated check is mapped to this control. For auditor use, the defensible evidence set is the existing policy statement, the audit-binder control page, and the family review record showing family `14` was reviewed `ok` and promoted to `regularly_reviewed` on 2026-04-27.

## Primary Evidence Set

- [docs/policies/email/email-security.md](../../../..//docs/policies/email/email-security.md)
- [reports/audit-binders/2026-04-26/14_1.md](../../../audit-binders/2026-04-26/14_1.md)
- [docs/reviews/2026-04-27-initial-ssk-review-batch-1.md](../../../..//docs/reviews/2026-04-27-initial-ssk-review-batch-1.md)
- [check.md](./check.md)
- [result.json](./result.json)

## Evidence Summary

The current inbound email security policy states that MCNA email is hosted on Exchange Online and protected by Exchange Online Protection and Microsoft Defender for Office 365 Plan 1. It also states that inbound protections include anti-spam, anti-malware, anti-phishing, Safe Links, Safe Attachments, anti-spoofing, and impersonation protection.

The same policy states that SPF, DKIM, and DMARC are configured for `nofmetalcoatings.us`, with DMARC enforced to prevent domain spoofing. Reported phishing messages are triaged through Microsoft tooling by the Director of IT & MIS.

The Secure SketCH initial review memo dated 2026-04-27 records family `14` (`14-1`, `14-2`) as reviewed `ok`, with maturity promoted to `regularly_reviewed` and next review due 2026-07-26. The audit-binder control page for `14-1` contains the control statement and the specific recommended action set that this evidence addresses.

## Control-to-Evidence Mapping

| Item | Requirement | Evidence basis | Position |
|---|---|---|---|
| 14-1-a | Define security guidance for incoming email | `email-security.md` section "Inbound email security (14-1)" | Covered |
| 14-1-b | Check and restrict incoming email as necessary | EOP and Defender for Office 365 anti-spam, anti-malware, anti-phishing, anti-spoofing, and impersonation controls documented in policy | Covered |
| 14-1-c | Perform virus scan on attached files | Safe Attachments and anti-malware protections documented in policy | Covered |
| 14-1-d | Block risky attachment extensions not required for business | Covered by documented inbound restriction posture, but exact extension block list is not enumerated in the policy artifact | Partially explicit |
| 14-1-e | Filter spam emails | EOP anti-spam filtering documented in policy | Covered |
| 14-1-f | Verify SPF, DKIM, and DMARC policies | SPF, DKIM, and enforced DMARC documented in policy | Covered |
| 14-1-g | Temporarily store emails with attachments or URLs to allow analysis updates | Safe Attachments and Safe Links detonation behavior documented in policy | Covered |
| 14-1-h | Analyze and block attachments and URLs using sandbox features | Safe Attachments and Safe Links documented in policy | Covered |
| 14-1-i | Regularly review guidance and implementation measures | Family `14` review recorded on 2026-04-27; policy review cycle is annual | Covered |

## Auditor Notes

This artifact is a manual evidence memo created because the current `ssk_run_control_check` implementation has no automated check function mapped for control `14-1`. That is a tooling gap, not an evidence gap. The evidence set above is sufficient to answer an auditor request for current control design and review coverage for inbound email security.

The narrowest residual weakness in the evidence package is that the current policy artifact does not enumerate the exact blocked attachment extension list. If an auditor asks for that implementation detail, provide the live Exchange Online or Defender policy configuration export or screenshots as supplemental evidence.

## Recommended Auditor Hand-off

Hand over these three artifacts together:

1. [docs/reviews/2026-04-27-initial-ssk-review-batch-1.md](../../../..//docs/reviews/2026-04-27-initial-ssk-review-batch-1.md)
2. [reports/audit-binders/2026-04-26/14_1.md](../../../audit-binders/2026-04-26/14_1.md)
3. [docs/policies/email/email-security.md](../../../..//docs/policies/email/email-security.md)