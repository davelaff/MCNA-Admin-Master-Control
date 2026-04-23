# How To Use Reports

## Purpose

This document explains how to use the report outputs in this repo.

Use it to answer:

- which report to open first
- what each report type is for
- how to move from finding to remediation to evidence
- how audit binders differ from operational scan reports

---

## Report Locations

Primary output folders live under `reports/`:

- `reports/app-reg-governance/`
- `reports/orphaned-assets/`
- `reports/power-platform-hygiene/`
- `reports/audit-binders/`
- `reports/secure-score/`

Typical file types:

- `.md` = human-readable report
- `.csv` = raw or tabular export for filtering, sorting, and follow-up analysis
- `manifest.json` = machine-readable summary for a binder export

---

## Start Here

Use this order:

1. Open the latest `.md` report for the domain you care about.
2. Read the `Summary` section first.
3. Identify `Critical` and `High` findings before anything else.
4. Use the matching `.csv` file when you need filtering, pivoting, or bulk follow-up.
5. After remediation or review, use the binder output under `reports/audit-binders/` as the audit-facing package.

If your goal is operational cleanup, start with the domain scan reports.

If your goal is audit defense or evidence review, start with the audit binders.

---

## Report Types

### App Registration Governance

Folder: `reports/app-reg-governance/`

Use this when reviewing:

- missing app owners
- expired or expiring secrets
- expired certificates
- app registration hygiene and accountability

Read the markdown report for:

- scan date
- total apps scanned
- counts by severity
- named apps with specific findings

Use the CSV when you need to:

- sort by owner
- filter by severity
- group by app or finding type
- prepare a remediation worklist

This is primarily an operational governance report. It can also support Secure SketCH controls around account inventory and authentication when linked as evidence.

### Orphaned Assets

Folder: `reports/orphaned-assets/`

Use this when reviewing:

- groups with no owners
- owners with disabled accounts
- stale collaboration assets
- potentially abandoned M365 objects

This report is best used for cleanup and ownership confirmation, not as a final audit binder by itself.

### Power Platform Hygiene

Folder: `reports/power-platform-hygiene/`

Use this when reviewing:

- unused environments
- unpromoted solutions
- Power Platform governance drift

This is both an operational report and a source artifact for cloud-service governance evidence.

### Audit Binders

Folder: `reports/audit-binders/`

Use this when you need:

- a per-control evidence package
- a review packet for Secure SketCH controls
- a clean auditor-facing artifact instead of a raw domain scan

Each binder folder contains:

- `index.md` = list of included controls
- `manifest.json` = structured export metadata
- one markdown file per control

Each control file is organized as:

1. header
2. MCNA position
3. control statement
4. evidence
5. recommended actions
6. review history
7. active findings
8. risk

The binder is the report you use to show:

- what the control is
- what evidence exists
- what findings remain open
- whether reviews have been performed

### Secure Score

Folder: `reports/secure-score/`

Treat this as reserved unless populated later. It is not currently the primary evidence product of AMC.

---

## How To Read A Report

### For operational work

Use this sequence:

1. Read the summary counts.
2. Focus on `Critical` and `High`.
3. Confirm whether the finding is real, stale, or already addressed.
4. Assign an owner and remediation path.
5. Re-run the relevant scan after changes.

### For audit or compliance work

Use this sequence:

1. Open the relevant control binder.
2. Check the `Evidence` section first.
3. Check whether evidence is current and verified.
4. Review `Active Findings`.
5. Review `Review History`.
6. Decide whether the control is defensible today.

If there is no evidence, the control is not audit-ready even if the environment may be technically acceptable.

---

## From Finding To Evidence

The intended workflow is:

1. Domain scan finds the issue.
2. Report documents the issue.
3. Remediation or review happens.
4. Supporting artifacts are linked into `ssk_evidence`.
5. Binder is regenerated.
6. Binder becomes the control-level evidence package.

In short:

- scan reports tell you what is wrong
- binders tell you what you can defend

---

## Practical Rules

- Do not treat a single old report as current truth without checking its date.
- Prefer the newest report in each folder unless you are comparing drift over time.
- Use markdown for reading and briefing.
- Use CSV for analysis and work tracking.
- Use binders for control reviews, audits, and evidence conversations.
- If a binder says `_No evidence linked._`, the control is not yet evidence-backed even if findings exist elsewhere.

---

## Suggested Workflow By Need

### Need to clean up the tenant

- Start with `app-reg-governance`, `orphaned-assets`, or `power-platform-hygiene`
- Fix the highest-severity issues
- Re-run the scan

### Need to defend a Secure SketCH control

- Open the relevant binder under `reports/audit-binders/`
- Confirm evidence, findings, and review history
- Add missing evidence if the control is still thin
- Re-export the binder

### Need to prepare for a review meeting

- Bring the markdown report for the domain problem
- Bring the corresponding binder for the mapped control
- Use the report for operational detail
- Use the binder for the governance and evidence story

---

## Current Limitation

Single-control binder exports written into the same output directory can overwrite that folder's `index.md` and `manifest.json`.

If building a multi-control binder set, verify that:

- all expected control markdown files are present
- `index.md` lists all included controls
- `manifest.json` matches the actual contents of the folder

---

## Bottom Line

Use scan reports to discover and triage.

Use audit binders to prove and defend.
