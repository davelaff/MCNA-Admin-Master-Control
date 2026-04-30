# reports/ — Retention Policy

## General rule

Keep the **3 most recent runs** per scan type. Delete older runs manually or via cleanup agent.
Exception: quarterly governance packets and audit binders — keep all (governance immutability requirement).

## By subdirectory

| Directory | Retain | Rationale |
|---|---|---|
| `audit-binders/` | All | Immutable governance artifact; no pruning. |
| `governance-packets/` | All | Quarterly records; no pruning. |
| `ssk-submissions/` | All | Portal submission packets; no pruning. |
| `control-checks/` | Latest 3 runs per control | High churn; old runs have no audit value. |
| `app-reg-governance/` | Latest 3 | Weekly scan; keep recent trend only. |
| `orphaned-assets/` | Latest 3 | Monthly scan; keep recent trend only. |
| `entra-missing-owner-remediation/` | Latest 3 | Remediation snapshots; latest 3 sufficient. |
| `exo-shared-mailbox-remediation/` | Latest 3 | Same. |
| `power-platform-hygiene/` | Latest 3 | Same. |
| `remediation-queues/` | Latest 3 | Action queue exports; latest 3 sufficient. |
| `secure-score/` | Latest 3 | Score snapshots; keep recent trend. |
| `ssk-control-coverage/` | Latest 3 | Coverage matrix exports. |
| `ssk-evidence-gaps/` | Latest 3 | Gap analysis exports. |

## Empty run directories

Directories created by a failed or cancelled scan run with no output files should be deleted promptly.
Pattern: `reports/<type>/<timestamp>/` with no files inside.

## Pruning

No automated pruning exists today. When a directory accumulates more than 3 runs,
delete the oldest manually before or after the next scan run.
