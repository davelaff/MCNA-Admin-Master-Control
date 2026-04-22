# Secure SketCH Tracking Layer — Design Spec

**Project:** MCNA Admin Master Control
**Spec date:** 2026-04-22
**Author:** Dave Lafferty (with Claude Code, brainstorming session)
**Target phase:** Phase 2 of the AMC build roadmap
**Status:** Approved design, pending implementation plan

---

## Goal

Turn AMC from a tenant-hygiene scanning tool into an **audit-ready evidence
production layer** mapped to the Secure SketCH 2026-01-01 catalog (76 controls).

MCNA's Secure SketCH score is currently high because policies are written —
the implicit maturity of "Implemented." The score cannot be defended to an
auditor because there is no evidence trail. This spec closes that gap.

The goal for every Secure SketCH control at MCNA is maturity "Regularly
Reviewed." Everything below that is a fail. This is a binary bar.

---

## Scope

In scope:

- A new `ssk_*` namespace of tables in the existing `mcna_amc.db` SQLite KB.
- MCP tools for catalog management, status tracking, evidence linking,
  review attestation, recommended-action tracking, registry CRUD, and
  audit binder export.
- A catalog import pipeline that parses
  `Secure_SketCH_Guidelines_2026-01-01.docx` into structured rows.
- An audit binder output format rendered as per-control markdown files in
  `reports/audit-binders/<date>/<scope>/`.
- An evidence-contribution manifest convention on each existing domain tool.

Out of scope:

- Any UI beyond Claude Code conversation.
- Migration to SharePoint Lists or Dataverse (designed to be future-easy,
  not built now — see Approach B/C rejection in ROADMAP.md).
- Write-path tools that remediate findings in the Microsoft estate. Those
  are Phase 4.
- Computing the Secure SketCH score. AMC produces evidence; Secure SketCH
  keeps the score.

---

## Design decisions (locked before implementation)

1. **Approach A** — SQLite-first, conversational-only, migration-ready.
2. **Target maturity is globally "Regularly Reviewed."** No per-control
   target authoring surface. Binary pass/fail.
3. **Bullets are flat.** Recommended actions in the source `.docx` are
   preserved as a single ordered list per control. No sub-bullet structure.
   Escape hatch: add `parent_action_id` later only if one specific control
   demonstrably needs grouping.
4. **Evidence is pointed to, never duplicated.** SharePoint-hosted
   artifacts are referenced by `{site_id, drive_id, item_id}` + URL.
5. **Reviews are append-only at the tool layer.** No `ssk_update_review`
   tool exists. Corrections are new rows referencing prior review IDs.
6. **`ssk_record_review` with empty or stale evidence is allowed** with
   a prominent `quality_flag` value — not rejected. An honest "I reviewed
   without evidence" attestation is more auditor-defensible than a gap.
7. **Two-stage catalog import.** Parser writes a JSON intermediate for
   inspection before any DB write. DB import is all-or-nothing.
8. **`ssk_*` namespace** for all tables in this layer. Entire namespace
   is a clean migration unit if SharePoint Lists or Dataverse is ever
   adopted.

---

## Data model

Six new tables plus one column added to `findings`.

### `ssk_controls`

The catalog. One row per control — this is the current version. Prior
versions move to `ssk_controls_history` on re-import.

| Column | Type | Notes |
|---|---|---|
| `control_id` | TEXT PK | e.g., `"06-3"` |
| `source_version` | TEXT | e.g., `"2026-01-01"` (tracks which catalog this reflects) |
| `category` | TEXT | `"06"` (first hyphen-separated segment) |
| `category_name` | TEXT | `"Asset Management"` (populated from `ssk_categories`) |
| `title` | TEXT | `"Management of software assets"` |
| `overview` | TEXT | Full overview paragraph from the doc |
| `status_descriptions` | JSON | `{"Regularly Reviewed": "Inventory of software assets is taken periodically."}` (one key at MCNA, JSON kept for forward-compat) |
| `insufficient_measures_risks` | TEXT | Full risk text blob |
| `imported_at` | TIMESTAMP | |

### `ssk_controls_history`

Mirror of `ssk_controls` populated on re-import. Same columns plus
`superseded_at`. Enables diff queries: "did control 06-3's overview change
between 2026-01-01 and 2026-07-01?"

### `ssk_categories`

Small lookup table, 10–20 rows. Populated manually from the doc's category
headings.

| Column | Type | Notes |
|---|---|---|
| `category` | TEXT PK | `"06"` |
| `category_name` | TEXT | `"Asset Management"` |
| `display_order` | INT | |

### `ssk_recommended_actions`

Per-action checklist rows, flat.

| Column | Type | Notes |
|---|---|---|
| `action_id` | TEXT PK | `"06-3-a"`, `"06-3-b"`, ... (synthetic, document order) |
| `control_id` | TEXT FK → `ssk_controls.control_id` | |
| `source_version` | TEXT | Tracks which catalog version this action came from |
| `sequence` | INT | 0-indexed position |
| `action_text` | TEXT | |
| `implementation_status` | ENUM | `not_started | in_progress | complete | n_a` |
| `implementation_notes` | TEXT | |
| `owner` | TEXT | |
| `last_updated` | TIMESTAMP | |

### `ssk_control_status`

Current MCNA position per control. One row per control.

| Column | Type | Notes |
|---|---|---|
| `control_id` | TEXT PK/FK | |
| `current_maturity` | ENUM | `regularly_reviewed | not_regularly_reviewed` (binary) |
| `target_maturity` | TEXT | Always `"Regularly Reviewed"`. Denormalized constant. |
| `gap_summary` | TEXT | Human-authored narrative if current != target |
| `owner` | TEXT | Default `nof-dlafferty@nofmetalcoatings.us` |
| `review_cadence_days` | INT | Default 90 |
| `last_reviewed_at` | TIMESTAMP | Derived from most recent `ssk_reviews` row |
| `next_review_due` | TIMESTAMP | `last_reviewed_at + review_cadence_days` |
| `last_updated` | TIMESTAMP | |

### `ssk_evidence`

Any record supporting a control.

| Column | Type | Notes |
|---|---|---|
| `evidence_id` | TEXT PK | UUID |
| `control_id` | TEXT FK | |
| `evidence_type` | ENUM | `scan_snapshot | review_minutes | signed_document | attestation | policy_link | registry_entry | external_link | finding_closure` |
| `title` | TEXT | Human-readable label |
| `source_kind` | ENUM | `local_file | sharepoint | url | kb_row | scan_run` |
| `source_pointer` | TEXT | Path, URL, or identifier |
| `source_metadata` | JSON | `{site_id, drive_id, item_id}` for SharePoint |
| `produced_at` | TIMESTAMP | |
| `validity_window_days` | INT NULL | Null = point-in-time; integer = auto-computed `expires_at` |
| `expires_at` | TIMESTAMP NULL | |
| `verification_status` | ENUM | `unverified | resolved | unresolvable` |
| `verification_checked_at` | TIMESTAMP NULL | |
| `recorded_by` | TEXT | |
| `notes` | TEXT | |

### `ssk_reviews`

The attestation ledger. Append-only by convention.

| Column | Type | Notes |
|---|---|---|
| `review_id` | TEXT PK | UUID |
| `control_id` | TEXT FK NULL | Nullable if reviewing a family or whole program |
| `control_family` | TEXT NULL | e.g., `"06"` |
| `reviewer` | TEXT | |
| `reviewed_at` | TIMESTAMP | |
| `scope_summary` | TEXT | What the review covered |
| `evidence_ids` | JSON | Array of `ssk_evidence.evidence_id` values examined |
| `outcome` | ENUM | `ok | gaps_identified | action_required` |
| `quality_flag` | ENUM | `ok | no_evidence | stale_evidence | low_evidence_count` |
| `findings_summary` | TEXT | Narrative of what was found |
| `next_review_due` | TIMESTAMP | Computed from `reviewed_at + cadence` |
| `prior_review_id` | TEXT NULL | If this row corrects a prior review, points to it |

### `ssk_registries`

Generic authoring surface for human-authored records. No per-registry
schema enforced at the DB level.

| Column | Type | Notes |
|---|---|---|
| `registry_entry_id` | TEXT PK | UUID |
| `registry_name` | TEXT | `approved_software | exceptions | vendor_support | policies | nda_ledger | approved_browsers | ...` |
| `control_ids` | JSON | Array of controls this entry contributes evidence to |
| `entry_key` | TEXT | Natural key within registry |
| `entry_data` | JSON | Free-form payload — convention documented per registry in `docs/registries/` |
| `entry_pointer` | TEXT NULL | Optional SharePoint URL or file path |
| `status` | ENUM | `active | retired | superseded` |
| `effective_from` | TIMESTAMP | |
| `effective_to` | TIMESTAMP NULL | |
| `recorded_by` | TEXT | |
| `recorded_at` | TIMESTAMP | |

Uniqueness: `(registry_name, entry_key, status='active')` — only one active
entry per key per registry at a time.

### `findings` (existing table — one new column)

| Column | Type | Notes |
|---|---|---|
| `closure_evidence_id` | TEXT FK NULL | When a finding is resolved, link to the `ssk_evidence` row that proves closure |

---

## MCP tool surface

~17 new tools. All writes append to existing `activity_log`.

### Catalog

- `ssk_import_catalog(docx_path, version, dry_run=False)` — parse and upsert.
  Returns `{parsed_controls, written_controls, written_actions, parse_failures, warnings, intermediate_json_path}`. Idempotent by `(control_id, source_version)`.
- `ssk_list_controls(category=None)` — list catalog entries.
- `ssk_get_control(control_id)` — full detail including recommended actions.

### Status & gaps

- `ssk_status(control_id)` — current state for one control.
- `ssk_status_all(below_target=False, due_before=None)` — roll-up.
- `ssk_gaps()` — one-shot "what's below target and why."
- `ssk_due(days_ahead=30)` — reviews coming due or past due.

(No `ssk_set_target` — target is globally fixed.)

### Evidence

- `ssk_link_evidence(control_id, evidence_type, source_kind, source_pointer, source_metadata=None, validity_window_days=None, title=None, notes=None)`
- `ssk_list_evidence(control_id, type=None, active_only=True)`
- `ssk_evidence_expiring(days_ahead=30)`
- `ssk_verify_pointers(control_id=None)` — walks SharePoint pointers, updates
  `verification_status`, emits `pointer_broken` findings for unresolvable items.

### Reviews (append-only attestation ledger)

- `ssk_record_review(control_id=None, control_family=None, reviewer, evidence_ids, scope_summary, outcome, findings_summary)`
  — appends one row. **Exactly one of `control_id` or `control_family` must
  be set; passing both or neither raises `ReviewScopeError`.** Computes
  `quality_flag` and `next_review_due`. Returns prominent warning if
  `quality_flag != ok`.
- `ssk_review_history(control_id, limit=10)` — timeline.
- `ssk_alerts()` — lists review rows with non-`ok` `quality_flag`.

### Recommended actions

- `ssk_mark_action(action_id, status, notes=None, owner=None)`
- `ssk_action_queue(owner=None, status='in_progress')`

### Registries

- `registry_add(registry_name, entry_key, entry_data, control_ids, pointer=None, effective_from=None)` — rejects with `RegistryConflictError` if
  an active entry already exists for `(registry_name, entry_key)`. To replace
  an active entry, call `registry_retire` first, then `registry_add` (the new
  row gets `supersedes = <prior_id>` wired via `entry_data.supersedes` by convention).
- `registry_list(registry_name=None, status='active')` — if no name, lists
  all registry names with counts (drift detection).
- `registry_get(registry_name, entry_key)`
- `registry_retire(registry_name, entry_key, reason)`

### Audit binder export

- `ssk_export_binder(scope, output_dir=None)` where `scope` is a single
  control ID, a category (`"06"`), or `"all"`.
- `ssk_coverage()` — which controls have automated evidence contributors
  vs. rely entirely on human-authored records.

### Evidence-contribution manifest (convention, not a tool)

Each existing domain tool module declares:

```python
CONTRIBUTES_TO = {
    # finding_type OR tool-level → control IDs
    "__tool__": ["IAM-APP-01", "IAM-APP-02"],     # tool-level baseline
    "expired_secret": ["IAM-APP-02"],             # per-finding-type refinement
    "missing_owner": ["IAM-APP-01"],
}
```

`ssk_coverage()` reads these manifests at startup.

---

## Audit binder format

Output shape:

```
reports/audit-binders/YYYY-MM-DD/
├── index.md
├── manifest.json
└── <NN-category-slug>/
    └── <control-id>.md
```

- One markdown file per control, grouped by category.
- One directory per export run, dated. Never overwrite.
- `manifest.json` mirrors the binder in structured form for future re-ingestion.
- Markdown is the canonical format. PDF conversion via `pandoc` on demand.

### Per-control `.md` sections (in order)

1. Header — control ID, title, export timestamp, exported-by, source version.
2. **MCNA position** — summary table (current maturity, owner, last review,
   reviewer, outcome, cadence, next due, evidence count, open findings,
   recommended actions complete). This is the auditor's 5-second answer.
3. Control statement — Overview and "Regularly Reviewed status" quoted
   verbatim from the catalog.
4. Evidence table — type, title, source, produced date, valid-until,
   last-verified timestamp.
5. Recommended actions table — 1:1 with catalog, showing implementation
   status + notes + owner.
6. Review history — last N rows from `ssk_reviews`, including `quality_flag`.
7. Findings — open findings + findings closed since last review (with
   closure evidence link).
8. Risk — "Insufficient Measures Risks" quoted verbatim from the catalog.

### Index page content

- Catalog version, controls total, controls at target, controls below target,
  reviews overdue, broken pointers, exported by.
- Maturity matrix across all 76 (binary pass/fail view per MCNA's bar).
- Table of controls below target.
- Table of overdue reviews.
- Table of broken evidence pointers (if any).
- Category index with links into each control `.md`.

### What's excluded

- No AMC-internal IDs except as evidence provenance.
- No architecture notes.
- No maturity self-scoring math.

---

## Catalog import pipeline

Library: `python-docx` (add to `mcp-server/requirements.txt`).

Two-stage:

1. **Parse** → write `mcp-server/kb/catalog-imports/<version>.json`.
2. **Load** → upsert into DB from the JSON.

### Parser state machine

Walk the `.docx` paragraph by paragraph. States:

- `LOOKING_FOR_CONTROL` — waiting for the next `^\d{2}-\d+` line.
- `AFTER_HEADER` — after control ID line, waiting for `"Overview"` heading.
- `IN_OVERVIEW` — accumulating overview text.
- `IN_STATUS` — accumulating the single "Regularly Reviewed status" text.
- `IN_ACTIONS` — accumulating recommended-action bullets (flat, document order).
- `IN_RISKS` — accumulating insufficient-measures-risk text.

Control boundaries reset state to `AFTER_HEADER`. Document-level headers
(`"Introduction"`, the main title) are recognized and ignored.

### Error behavior

- Missing expected section on a control → log control_id + reason, skip,
  continue. Final `parse_failures` list returned to caller.
- DB write is atomic — either all successfully parsed controls commit or none.
- Re-running with same version = no-op with row counts.
- Re-running with newer version inserts new rows; old rows retained.

### First real run

Run with `dry_run=True`. Inspect JSON intermediate. Tune parser if needed.
Re-run with `dry_run=False` to commit.

---

## Error handling rules

| Situation | Behavior |
|---|---|
| Parser failure on one control | Skip with reported reason, continue |
| Re-import same version | No-op, report already-imported counts |
| Re-import newer version | Insert fresh rows under new version, retain old |
| Graph error on pointer verify | Mark evidence `unresolvable`, emit `pointer_broken` finding, no exception |
| `ssk_link_evidence` unknown control_id | Reject with `UnknownControlError` |
| `registry_add` unknown control_ids | Warn, don't reject |
| `ssk_record_review` empty evidence_ids | Accept, `quality_flag = no_evidence`, warning in response |
| `ssk_record_review` stale evidence_ids | Accept, `quality_flag = stale_evidence`, warning |
| Graph 401/403 | Stop, surface to Dave, no retry (existing operating principle) |
| SQLite constraint violation | Surface the specific constraint name |
| `ssk_export_binder` empty scope | Empty manifest, warning, no empty directory |
| `.docx` missing or unreadable | `CatalogSourceError`, no silent fallback |

### Invariants enforced in tool layer (not DB schema)

- No `ssk_update_review` tool exists. Review correction = new row with
  `prior_review_id` set.
- Every write tool appends to `activity_log`.
- Pointer verification does not run on every read. Runs via `ssk_verify_pointers`
  or implicitly at the start of `ssk_export_binder`.

---

## Testing strategy

Follows the Phase 1 plan's pytest + TDD approach.

### Fixtures

- `tests/fixtures/catalogs/minimal.docx` — 3 well-formed controls.
- `tests/fixtures/catalogs/with_gaps.docx` — one control missing a section.
- `tests/fixtures/catalogs/multi_version.docx` — idempotency test.
- In-memory SQLite per test with `ssk_*` schema pre-seeded.
- Mocked Graph responses for pointer verification (200, 404, 401, 403).

### Test requirements

- Every `ssk_*` and `registry_*` tool: one happy-path test, one error-path test minimum.
- `ssk_record_review` tested per `quality_flag` value.
- Parser gets highest test density (most silent-failure surface).
- Audit binder tested via golden-file comparison (`tests/fixtures/golden/`).
- One end-to-end integration test: `import_catalog → link_evidence →
  record_review → export_binder → assert binder content`.
- No live Graph calls in tests.

No coverage percentage target. Tests are judged by whether they catch real
regressions.

---

## Out of scope (explicit)

- SharePoint Lists or Dataverse backend. Future migration is enabled by the
  `ssk_*` namespace but not built.
- Any UI beyond Claude Code.
- Bulk CSV import for registries (YAGNI — Dave has no such source spreadsheets
  today; add if the need appears).
- Remediation writes to the Microsoft estate (Phase 4).
- Automated computation of Secure SketCH score (Secure SketCH owns that).
- Evidence-pointer verification on every evidence read (expensive; runs on
  cadence or at binder export time).

---

## Migration readiness notes (for a future Approach B or C)

The `ssk_*` namespace is designed to move as a unit. When/if MCNA outgrows
the SQLite-only model:

- `ssk_registries` rows map cleanly to SharePoint List items.
- `ssk_evidence.source_metadata` already carries the SharePoint triple.
- `ssk_controls` and `ssk_recommended_actions` are reference data — ship as
  a SharePoint list seeded from the JSON intermediate.
- `ssk_reviews` append-only semantics align with SharePoint List versioning.

The hard part (modeling) is done now. The mechanical part (export/import)
is the future work.

---

## Next steps after this spec is approved

1. Invoke `superpowers:writing-plans` to produce an implementation plan
   for Phase 2.
2. Plan will be TDD, following the Phase 1 pattern.
3. First implementation task: schema migration adding `ssk_*` tables to
   `mcna_amc.db`.
4. Second task: `ssk_import_catalog` tool + parser + dry-run against the
   real 2026-01-01 `.docx`.
5. Review the JSON intermediate together before any DB commit.
