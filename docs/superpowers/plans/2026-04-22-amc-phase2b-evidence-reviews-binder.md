# AMC Phase 2b — Secure SketCH Evidence, Reviews, Registries, and Binder Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the Phase 2b Secure SketCH tool surface so MCNA can link evidence, record review attestations, manage registry-backed evidence, track action execution, and export audit-ready binders from the existing catalog/status database.

**Architecture:** Keep the Phase 2a catalog/status tools in `mcp-server/tools/ssk.py`, and add focused Phase 2b sibling modules for shared helpers, evidence, reviews, registries, actions, and binder export. Compute rollups from the existing `ssk_*` tables already present in `mcna_amc.db`, and expose them through new MCP tools registered in `mcp-server/server.py`.

**Tech Stack:** Python 3.14, FastMCP, SQLite, pytest, requests, pathlib, json, datetime

**Execution note (2026-04-22):** Phase 2b is being executed from a global git worktree under `~/.config/superpowers/worktrees/MCNA-Admin-Master-Control/` to avoid repo-local worktree noise and to leave local config files in the main workspace untouched.

---

## File map

- `mcp-server/tools/ssk_common.py`
  Shared Secure SketCH helpers: JSON/error responses, timestamp helpers, enum validation, activity-log append helpers, status/review/evidence query helpers reused by Phase 2b modules.
- `mcp-server/tools/ssk_control_map.py`
  Canonical control-id normalization for legacy semantic codes already emitted by scan tools and findings rows.
- `mcp-server/tools/ssk_evidence.py`
  `ssk_link_evidence`, `ssk_list_evidence`, `ssk_evidence_expiring`, `ssk_verify_pointers`.
- `mcp-server/tools/ssk_reviews.py`
  `ssk_record_review`, `ssk_review_history`, `ssk_alerts`, `ssk_due`, plus control-status recomputation after reviews land.
- `mcp-server/tools/ssk_actions.py`
  `ssk_mark_action`, `ssk_action_queue`.
- `mcp-server/tools/ssk_registry.py`
  `registry_add`, `registry_list`, `registry_get`, `registry_retire`.
- `mcp-server/tools/ssk_binder.py`
  `ssk_export_binder`, `ssk_coverage`, binder markdown rendering helpers.
- `mcp-server/tools/kb.py`
  Extend `kb_update_finding` so resolving a finding can optionally persist `closure_evidence_id`.
- `mcp-server/tools/entra.py`
  Add `CONTRIBUTES_TO` manifest for Entra findings.
- `mcp-server/tools/ca.py`
  Add `CONTRIBUTES_TO` manifest for Conditional Access findings.
- `mcp-server/tools/pp.py`
  Add `CONTRIBUTES_TO` manifest for Power Platform findings.
- `mcp-server/server.py`
  Register all new Phase 2b MCP tools.
- `mcp-server/tests/test_ssk_evidence.py`
  Evidence happy-path, validation, expiry, and pointer-verification tests.
- `mcp-server/tests/test_ssk_control_map.py`
  Control-alias coverage tests so legacy finding codes always normalize to one of the 73 imported catalog ids.
- `mcp-server/tests/test_ssk_reviews.py`
  Review-scope validation, quality-flag computation, due/alerts, and status-rollup tests.
- `mcp-server/tests/test_ssk_actions.py`
  Recommended-action update and queue tests.
- `mcp-server/tests/test_ssk_registry.py`
  Registry add/list/get/retire tests including active-key conflict cases.
- `mcp-server/tests/test_ssk_binder.py`
  Binder export and coverage tests using golden markdown fixtures.
- `mcp-server/tests/test_kb.py`
  Add closure-evidence resolution coverage.
- `mcp-server/tests/fixtures/golden/binder/`
  Golden binder outputs for one control and one category export.
- `mcp-server/kb/ssk_control_aliases.json`
  Versioned alias map from legacy semantic control codes to canonical imported numeric control ids.
- `activity-log.md`
  Append factual Phase 2b completion note only after implementation and verification are complete.

## Required implementation choices

Make these decisions explicit in code and tests. Do not re-litigate them while implementing:

1. **Review quality flags**
   - `no_evidence`: `evidence_ids == []`
   - `stale_evidence`: any referenced evidence row has `expires_at < reviewed_at` or `verification_status = 'unresolvable'`
   - `low_evidence_count`: `control_id` review has exactly 1 evidence row, or `control_family` review has fewer than 2 evidence rows
   - `ok`: none of the above
2. **Pointer verification rules**
   - `local_file`: `Path(source_pointer).exists()`
   - `url`: `requests.head(..., allow_redirects=True)` with `GET` fallback on `405`
   - `sharepoint`: require `source_metadata.site_id`, `source_metadata.drive_id`, `source_metadata.item_id`; verify with `GET /sites/{site_id}/drives/{drive_id}/items/{item_id}`
   - `kb_row`: `source_pointer` format is `table_name:key_column:key_value`; verify via exact `SELECT 1`
   - `scan_run`: `source_pointer` format is `activity_log:run_id`; verify matching `activity_log.run_id`
3. **Binder output directory**
   - Default base path is `reports/audit-binders`
   - First export of a day uses `YYYY-MM-DD`
   - If that directory already exists, append `-HHMMSS` to avoid overwrite
4. **Review status rollup**
   - After `ssk_record_review`, recompute `ssk_control_status.last_reviewed_at`, `next_review_due`, `current_maturity`, and `gap_summary` for the affected control(s)
   - `current_maturity = regularly_reviewed` only when the latest applicable review has `outcome = 'ok'` and `quality_flag = 'ok'`
   - Otherwise leave `current_maturity = not_regularly_reviewed`
5. **Write-tool activity logging**
   - Every Phase 2b write tool appends one row to `activity_log`
   - `tool_name` is the MCP tool name
   - `outcome` is `success` or `error`
   - `detail` is compact JSON summarizing the affected ids and any warning flags
6. **Canonical control ids**
   - Imported numeric ids like `06-3` are the only canonical Secure SketCH ids in Phase 2b outputs
   - Legacy semantic ids already present in `findings.securesketch_control` must be normalized through `mcp-server/kb/ssk_control_aliases.json`
   - `ssk_coverage()` and binder export must normalize legacy ids before grouping findings or contributor manifests

---

### Task 0: Add canonical control-id normalization for legacy findings

**Files:**
- Create: `mcp-server/tools/ssk_control_map.py`
- Create: `mcp-server/tests/test_ssk_control_map.py`
- Create: `mcp-server/kb/ssk_control_aliases.json`

- [ ] **Step 1: Write the failing control-map tests**

```python
from tools.ssk_control_map import canonical_control_id, all_aliases

def test_every_alias_resolves_to_imported_control_id(db, tmp_path):
    _seed_catalog(db, tmp_path)
    imported_ids = {row["control_id"] for row in json.loads(ssk_list_controls())}
    for legacy_code, canonical in all_aliases().items():
        assert canonical in imported_ids, f"{legacy_code} -> {canonical} is not in imported catalog"

def test_unknown_control_id_passes_through_unchanged():
    assert canonical_control_id("06-3") == "06-3"
```

- [ ] **Step 2: Run the control-map tests to verify they fail**

Run: `python -m pytest mcp-server/tests/test_ssk_control_map.py -q`

Expected: FAIL with `ModuleNotFoundError` for `tools.ssk_control_map`.

- [ ] **Step 3: Implement the control-alias helper**

Create `mcp-server/tools/ssk_control_map.py`:

```python
import json
from pathlib import Path

ALIAS_PATH = Path(__file__).resolve().parent.parent / "kb" / "ssk_control_aliases.json"

def all_aliases() -> dict[str, str]:
    return json.loads(ALIAS_PATH.read_text(encoding="utf-8"))

def canonical_control_id(control_ref: str | None) -> str | None:
    if control_ref is None:
        return None
    return all_aliases().get(control_ref, control_ref)
```

- [ ] **Step 4: Build the alias file from the currently emitted legacy codes**

Use the existing scan-tool references as the source set:

```bash
rg -o 'securesketch_control=\"[^\"]+\"' mcp-server/tools | % { $_.ToString().Split('"')[1] } | Sort-Object -Unique
```

Create `mcp-server/kb/ssk_control_aliases.json` so every emitted legacy code above maps to one imported numeric catalog control id. Do not leave any emitted code unmapped. Validate the file immediately with:

```bash
python -m pytest mcp-server/tests/test_ssk_control_map.py -q
```

- [ ] **Step 5: Commit control normalization**

```bash
git add mcp-server/tools/ssk_control_map.py mcp-server/tests/test_ssk_control_map.py mcp-server/kb/ssk_control_aliases.json
git commit -m "feat: add Secure SketCH control alias normalization"
```

---

### Task 1: Build shared helpers and the evidence tool surface

**Files:**
- Create: `mcp-server/tools/ssk_common.py`
- Create: `mcp-server/tools/ssk_evidence.py`
- Test: `mcp-server/tests/test_ssk_evidence.py`

- [ ] **Step 1: Write the failing evidence tests**

```python
import json
from tools.ssk_evidence import (
    ssk_link_evidence, ssk_list_evidence,
    ssk_evidence_expiring, ssk_verify_pointers,
)
from tools.ssk import ssk_import_catalog

def test_ssk_link_evidence_persists_row_and_sets_expiry(db, tmp_path):
    _seed_catalog(db, tmp_path)
    result = json.loads(ssk_link_evidence(
        control_id="06-3",
        evidence_type="policy_link",
        source_kind="local_file",
        source_pointer=str(tmp_path / "policy.docx"),
        validity_window_days=30,
        title="Asset policy",
        notes="Quarterly review input",
    ))
    assert result["control_id"] == "06-3"
    assert result["verification_status"] == "unverified"
    assert result["expires_at"] is not None

def test_ssk_link_evidence_rejects_unknown_control(db):
    result = json.loads(ssk_link_evidence(
        control_id="99-9",
        evidence_type="policy_link",
        source_kind="local_file",
        source_pointer="C:/temp/missing.txt",
    ))
    assert result["error_type"] == "UnknownControlError"

def test_ssk_verify_pointers_marks_missing_local_file_unresolvable(db, tmp_path):
    _seed_catalog(db, tmp_path)
    json.loads(ssk_link_evidence(
        control_id="06-3",
        evidence_type="policy_link",
        source_kind="local_file",
        source_pointer=str(tmp_path / "missing.docx"),
    ))
    result = json.loads(ssk_verify_pointers(control_id="06-3"))
    assert result["broken"] == 1
```

- [ ] **Step 2: Run the evidence tests to verify they fail**

Run: `python -m pytest mcp-server/tests/test_ssk_evidence.py -q`

Expected: FAIL with `ModuleNotFoundError` for `tools.ssk_evidence` and missing helper imports.

- [ ] **Step 3: Implement shared Secure SketCH helpers**

Create `mcp-server/tools/ssk_common.py` with these building blocks:

```python
import json
import uuid
from datetime import datetime, timedelta, timezone
from db import get_connection

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

def json_ok(payload: dict | list) -> str:
    return json.dumps(payload, indent=2)

def json_error(message: str, error_type: str) -> str:
    return json.dumps({"error": message, "error_type": error_type}, indent=2)

def append_activity(tool_name: str, outcome: str, detail: dict, entity_id: str | None = None) -> None:
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO activity_log VALUES (?,?,?,?,?,?,?)",
            (str(uuid.uuid4()), utc_now(), tool_name, "ssk", entity_id, outcome, json.dumps(detail, sort_keys=True)),
        )
```

Also add:

```python
EVIDENCE_TYPES = {
    "scan_snapshot", "review_minutes", "signed_document", "attestation",
    "policy_link", "registry_entry", "external_link", "finding_closure",
}
SOURCE_KINDS = {"local_file", "sharepoint", "url", "kb_row", "scan_run"}

class UnknownControlError(ValueError): ...
class ReviewScopeError(ValueError): ...
class RegistryConflictError(ValueError): ...

def require_control(conn, control_id: str) -> None:
    row = conn.execute("SELECT 1 FROM ssk_controls WHERE control_id=?", (control_id,)).fetchone()
    if row is None:
        raise UnknownControlError(f"control '{control_id}' not found")
```

- [ ] **Step 4: Implement evidence linking, listing, expiry, and pointer verification**

Create `mcp-server/tools/ssk_evidence.py` with:

```python
def ssk_link_evidence(control_id, evidence_type, source_kind, source_pointer,
                      source_metadata=None, validity_window_days=None,
                      title=None, notes=None) -> str:
    ...

def ssk_list_evidence(control_id: str, type: str | None = None, active_only: bool = True) -> str:
    ...

def ssk_evidence_expiring(days_ahead: int = 30) -> str:
    ...

def ssk_verify_pointers(control_id: str | None = None) -> str:
    ...
```

Implementation rules:

```python
produced_at = utc_now()
expires_at = (
    (datetime.fromisoformat(produced_at) + timedelta(days=validity_window_days)).isoformat()
    if validity_window_days is not None else None
)
```

For `ssk_verify_pointers`:

```python
if source_kind == "local_file":
    ok = Path(source_pointer).exists()
elif source_kind == "url":
    resp = requests.head(source_pointer, allow_redirects=True, timeout=15)
    if resp.status_code == 405:
        resp = requests.get(source_pointer, allow_redirects=True, timeout=15)
    ok = resp.ok
elif source_kind == "sharepoint":
    token = get_token()
    graph_get(f"/sites/{site_id}/drives/{drive_id}/items/{item_id}", token)
    ok = True
```

On failure:

```python
conn.execute(
    "UPDATE ssk_evidence SET verification_status='unresolvable', verification_checked_at=? WHERE evidence_id=?",
    (checked_at, evidence_id),
)
_upsert_pointer_broken_finding(conn, control_id, evidence_id, source_pointer)
```

On success:

```python
conn.execute(
    "UPDATE ssk_evidence SET verification_status='resolved', verification_checked_at=? WHERE evidence_id=?",
    (checked_at, evidence_id),
)
```

- [ ] **Step 5: Re-run the evidence tests**

Run: `python -m pytest mcp-server/tests/test_ssk_evidence.py -q`

Expected: PASS

- [ ] **Step 6: Commit the evidence layer**

```bash
git add mcp-server/tools/ssk_common.py mcp-server/tools/ssk_evidence.py mcp-server/tests/test_ssk_evidence.py
git commit -m "feat: add Secure SketCH evidence tools"
```

---

### Task 2: Add review ledger, alerts, due tracking, and control-status recomputation

**Files:**
- Create: `mcp-server/tools/ssk_reviews.py`
- Modify: `mcp-server/tools/ssk.py`
- Test: `mcp-server/tests/test_ssk_reviews.py`
- Test: `mcp-server/tests/test_ssk.py`

- [ ] **Step 1: Write the failing review tests**

```python
import json
from tools.ssk_reviews import ssk_record_review, ssk_review_history, ssk_alerts, ssk_due

def test_ssk_record_review_requires_exactly_one_scope(db, tmp_path):
    _seed_catalog_and_evidence(db, tmp_path)
    result = json.loads(ssk_record_review(
        control_id="06-3",
        control_family="06",
        reviewer="nof-dlafferty@nofmetalcoatings.us",
        evidence_ids=[],
        scope_summary="Bad call",
        outcome="action_required",
        findings_summary="Too broad",
    ))
    assert result["error_type"] == "ReviewScopeError"

def test_ssk_record_review_sets_no_evidence_flag(db, tmp_path):
    _seed_catalog(db, tmp_path)
    result = json.loads(ssk_record_review(
        control_id="06-3",
        reviewer="nof-dlafferty@nofmetalcoatings.us",
        evidence_ids=[],
        scope_summary="Quarterly review",
        outcome="action_required",
        findings_summary="No supporting artifacts yet",
    ))
    assert result["quality_flag"] == "no_evidence"
    assert "warning" in result

def test_ssk_record_review_updates_status_rollup(db, tmp_path):
    evidence_ids = _seed_two_valid_evidence_ids(db, tmp_path, "06-3")
    json.loads(ssk_record_review(
        control_id="06-3",
        reviewer="nof-dlafferty@nofmetalcoatings.us",
        evidence_ids=evidence_ids,
        scope_summary="Control review",
        outcome="ok",
        findings_summary="Evidence current",
    ))
    status = json.loads(ssk_status("06-3"))
    assert status["current_maturity"] == "regularly_reviewed"
    assert status["last_reviewed_at"] is not None
```

- [ ] **Step 2: Run the review tests to verify they fail**

Run: `python -m pytest mcp-server/tests/test_ssk_reviews.py -q`

Expected: FAIL with `ModuleNotFoundError` for `tools.ssk_reviews`.

- [ ] **Step 3: Implement review tool module**

Create `mcp-server/tools/ssk_reviews.py` with:

```python
QUALITY_OK = "ok"
QUALITY_NO_EVIDENCE = "no_evidence"
QUALITY_STALE = "stale_evidence"
QUALITY_LOW = "low_evidence_count"

def ssk_record_review(control_id=None, control_family=None, reviewer=None,
                      evidence_ids=None, scope_summary=None, outcome=None,
                      findings_summary=None) -> str:
    ...

def ssk_review_history(control_id: str, limit: int = 10) -> str:
    ...

def ssk_alerts() -> str:
    ...

def ssk_due(days_ahead: int = 30) -> str:
    ...
```

Quality-flag logic must exactly match the plan-level rules:

```python
if not evidence_ids:
    quality_flag = QUALITY_NO_EVIDENCE
elif any(row["verification_status"] == "unresolvable" or _is_expired(row["expires_at"], reviewed_at) for row in evidence_rows):
    quality_flag = QUALITY_STALE
elif control_family and len(evidence_rows) < 2:
    quality_flag = QUALITY_LOW
elif control_id and len(evidence_rows) == 1:
    quality_flag = QUALITY_LOW
else:
    quality_flag = QUALITY_OK
```

Add `_recompute_control_status(conn, control_id)`:

```python
latest = conn.execute(
    "SELECT reviewed_at, outcome, quality_flag, next_review_due FROM ssk_reviews WHERE control_id=? ORDER BY reviewed_at DESC LIMIT 1",
    (control_id,),
).fetchone()
current_maturity = "regularly_reviewed" if latest and latest["outcome"] == "ok" and latest["quality_flag"] == "ok" else "not_regularly_reviewed"
gap_summary = None if current_maturity == "regularly_reviewed" else "Latest review is missing current, sufficient evidence or still reports action-required gaps."
```

If `control_family` is passed, call `_recompute_control_status` for every control whose id starts with `f"{control_family}-"`.

- [ ] **Step 4: Extend the Phase 2a status module only where needed**

Leave `mcp-server/tools/ssk.py` unchanged unless a shared query helper clearly belongs there. Register `ssk_due` directly from `ssk_reviews.py` in `server.py` rather than creating a passthrough wrapper.

Preferred registration pattern:

```python
from tools.ssk_reviews import ssk_record_review, ssk_review_history, ssk_alerts, ssk_due
```

- [ ] **Step 5: Re-run review and status tests**

Run:

```bash
python -m pytest mcp-server/tests/test_ssk_reviews.py -q
python -m pytest mcp-server/tests/test_ssk.py -q
```

Expected: PASS

- [ ] **Step 6: Commit the review layer**

```bash
git add mcp-server/tools/ssk_reviews.py mcp-server/tests/test_ssk_reviews.py mcp-server/tests/test_ssk.py
git commit -m "feat: add Secure SketCH review and due tools"
```

---

### Task 3: Add recommended-action management and finding-closure evidence linkage

**Files:**
- Create: `mcp-server/tools/ssk_actions.py`
- Modify: `mcp-server/tools/kb.py`
- Test: `mcp-server/tests/test_ssk_actions.py`
- Test: `mcp-server/tests/test_kb.py`

- [ ] **Step 1: Write the failing action and closure-evidence tests**

```python
import json
from tools.ssk_actions import ssk_mark_action, ssk_action_queue
from tools.kb import kb_update_finding

def test_ssk_mark_action_updates_status_notes_and_owner(db, tmp_path):
    _seed_catalog(db, tmp_path)
    result = json.loads(ssk_mark_action("06-3-a", "complete", notes="Procedure updated", owner="Security"))
    assert result["action_id"] == "06-3-a"
    assert result["implementation_status"] == "complete"

def test_ssk_action_queue_filters_by_status(db, tmp_path):
    _seed_catalog(db, tmp_path)
    result = json.loads(ssk_action_queue(status="not_started"))
    assert any(item["action_id"] == "06-3-a" for item in result)

def test_kb_update_finding_records_closure_evidence_on_resolve(db):
    _insert_finding(db, "f1")
    result = json.loads(kb_update_finding("f1", "resolved", closure_evidence_id="ev-123"))
    assert result["closure_evidence_id"] == "ev-123"
```

- [ ] **Step 2: Run the action-focused tests to verify they fail**

Run:

```bash
python -m pytest mcp-server/tests/test_ssk_actions.py -q
python -m pytest mcp-server/tests/test_kb.py -q
```

Expected: FAIL with missing module/function signatures.

- [ ] **Step 3: Implement the action tools**

Create `mcp-server/tools/ssk_actions.py`:

```python
VALID_ACTION_STATUSES = {"not_started", "in_progress", "complete", "n_a"}

def ssk_mark_action(action_id: str, status: str, notes: str | None = None, owner: str | None = None) -> str:
    ...

def ssk_action_queue(owner: str | None = None, status: str = "in_progress") -> str:
    ...
```

Use this update shape:

```python
conn.execute(
    "UPDATE ssk_recommended_actions SET implementation_status=?, implementation_notes=COALESCE(?, implementation_notes), owner=COALESCE(?, owner), last_updated=? WHERE action_id=?",
    (status, notes, owner, utc_now(), action_id),
)
```

- [ ] **Step 4: Extend `kb_update_finding` for closure evidence**

Modify `mcp-server/tools/kb.py`:

```python
def kb_update_finding(finding_id: str, status: str, notes: str = None, closure_evidence_id: str = None) -> str:
    ...
```

Only allow `closure_evidence_id` when `status == "resolved"`:

```python
if closure_evidence_id and status != "resolved":
    return json.dumps({"error": "closure_evidence_id is only valid when status='resolved'"})
```

Persist it on update:

```python
conn.execute(
    "UPDATE findings SET status=?, notes=?, closure_evidence_id=?, last_seen=? WHERE finding_id=?",
    (status, notes, closure_evidence_id, _now(), finding_id),
)
```

- [ ] **Step 5: Re-run the action and KB tests**

Run:

```bash
python -m pytest mcp-server/tests/test_ssk_actions.py -q
python -m pytest mcp-server/tests/test_kb.py -q
```

Expected: PASS

- [ ] **Step 6: Commit action and closure-evidence support**

```bash
git add mcp-server/tools/ssk_actions.py mcp-server/tools/kb.py mcp-server/tests/test_ssk_actions.py mcp-server/tests/test_kb.py
git commit -m "feat: add Secure SketCH action tracking tools"
```

---

### Task 4: Add registry CRUD and registry-backed evidence conventions

**Files:**
- Create: `mcp-server/tools/ssk_registry.py`
- Test: `mcp-server/tests/test_ssk_registry.py`

- [ ] **Step 1: Write the failing registry tests**

```python
import json
from tools.ssk_registry import registry_add, registry_list, registry_get, registry_retire

def test_registry_add_persists_active_entry(db):
    result = json.loads(registry_add(
        registry_name="approved_software",
        entry_key="7zip",
        entry_data={"publisher": "7-Zip", "approved": True},
        control_ids=["06-3"],
        pointer="https://sharepoint.example/item",
        effective_from="2026-04-22T00:00:00+00:00",
    ))
    assert result["registry_name"] == "approved_software"
    assert result["status"] == "active"

def test_registry_add_rejects_active_duplicate(db):
    json.loads(registry_add("approved_software", "7zip", {"approved": True}, ["06-3"]))
    result = json.loads(registry_add("approved_software", "7zip", {"approved": False}, ["06-3"]))
    assert result["error_type"] == "RegistryConflictError"

def test_registry_retire_marks_entry_retired(db):
    json.loads(registry_add("approved_software", "7zip", {"approved": True}, ["06-3"]))
    result = json.loads(registry_retire("approved_software", "7zip", "Replaced by managed package"))
    assert result["status"] == "retired"
```

- [ ] **Step 2: Run the registry tests to verify they fail**

Run: `python -m pytest mcp-server/tests/test_ssk_registry.py -q`

Expected: FAIL with `ModuleNotFoundError` for `tools.ssk_registry`.

- [ ] **Step 3: Implement registry CRUD**

Create `mcp-server/tools/ssk_registry.py`:

```python
def registry_add(registry_name, entry_key, entry_data, control_ids, pointer=None, effective_from=None) -> str:
    ...

def registry_list(registry_name: str | None = None, status: str = "active") -> str:
    ...

def registry_get(registry_name: str, entry_key: str) -> str:
    ...

def registry_retire(registry_name: str, entry_key: str, reason: str) -> str:
    ...
```

Conflict handling:

```python
existing = conn.execute(
    "SELECT registry_entry_id FROM ssk_registries WHERE registry_name=? AND entry_key=? AND status='active'",
    (registry_name, entry_key),
).fetchone()
if existing:
    raise RegistryConflictError(f"active registry entry already exists for {registry_name}:{entry_key}")
```

Retire behavior:

```python
payload = dict(current["entry_data"])
payload["retire_reason"] = reason
conn.execute(
    "UPDATE ssk_registries SET status='retired', effective_to=?, entry_data=? WHERE registry_entry_id=?",
    (utc_now(), json.dumps(payload, sort_keys=True), current["registry_entry_id"]),
)
```

- [ ] **Step 4: Re-run the registry tests**

Run: `python -m pytest mcp-server/tests/test_ssk_registry.py -q`

Expected: PASS

- [ ] **Step 5: Commit the registry layer**

```bash
git add mcp-server/tools/ssk_registry.py mcp-server/tests/test_ssk_registry.py
git commit -m "feat: add Secure SketCH registry tools"
```

---

### Task 5: Add coverage manifests and audit-binder export

**Files:**
- Create: `mcp-server/tools/ssk_binder.py`
- Modify: `mcp-server/tools/entra.py`
- Modify: `mcp-server/tools/ca.py`
- Modify: `mcp-server/tools/pp.py`
- Test: `mcp-server/tests/test_ssk_binder.py`
- Create: `mcp-server/tests/fixtures/golden/binder/index.md`
- Create: `mcp-server/tests/fixtures/golden/binder/06-asset-control.md`

- [ ] **Step 1: Write the failing binder and coverage tests**

```python
import json
from pathlib import Path
from tools.ssk_binder import ssk_export_binder, ssk_coverage

def test_ssk_coverage_reports_automated_vs_human_controls(db, tmp_path):
    _seed_catalog_and_findings(db, tmp_path)
    result = json.loads(ssk_coverage())
    assert "automated_controls" in result
    assert "human_only_controls" in result

def test_ssk_export_binder_writes_index_and_control_markdown(db, tmp_path):
    _seed_catalog_review_evidence_actions_and_findings(db, tmp_path)
    out_dir = tmp_path / "binders"
    result = json.loads(ssk_export_binder("06", output_dir=str(out_dir)))
    export_path = Path(result["output_dir"])
    assert (export_path / "index.md").exists()
    assert any(path.name == "06-3.md" for path in export_path.rglob("*.md"))
```

- [ ] **Step 2: Run the binder tests to verify they fail**

Run: `python -m pytest mcp-server/tests/test_ssk_binder.py -q`

Expected: FAIL with missing module and fixtures.

- [ ] **Step 3: Add contributor manifests to existing domain tools**

At module scope in `mcp-server/tools/entra.py`:

```python
from tools.ssk_control_map import canonical_control_id

CONTRIBUTES_TO = {
    "__tool__": [canonical_control_id("IAM-APP-01"), canonical_control_id("IAM-APP-02"), canonical_control_id("IAM-GUEST-01"), canonical_control_id("IAM-GUEST-02")],
    "missing_owner": [canonical_control_id("IAM-APP-01")],
    "expired_secret": [canonical_control_id("IAM-APP-02")],
    "expiring_secret": [canonical_control_id("IAM-APP-02")],
    "expired_cert": [canonical_control_id("IAM-APP-02")],
    "wildcard_redirect_uri": [canonical_control_id("IAM-APP-03")],
    "http_redirect_uri": [canonical_control_id("IAM-APP-03")],
    "recently_added_guest": [canonical_control_id("IAM-GUEST-01")],
    "inactive_guest": [canonical_control_id("IAM-GUEST-02")],
    "never_signed_in_guest": [canonical_control_id("IAM-GUEST-02")],
}
```

Add equivalent `CONTRIBUTES_TO` maps to `ca.py` and `pp.py`, matching each module's existing `securesketch_control` mappings.

- [ ] **Step 4: Implement coverage and binder export**

Create `mcp-server/tools/ssk_binder.py` with:

```python
def ssk_coverage() -> str:
    ...

def ssk_export_binder(scope: str, output_dir: str | None = None) -> str:
    ...
```

Coverage algorithm:

```python
modules = [tools.entra, tools.ca, tools.pp]
automated = set()
for module in modules:
    contributes = getattr(module, "CONTRIBUTES_TO", {})
    for control_ids in contributes.values():
        automated.update(control_ids)
```

Binder export:

```python
export_root = _resolve_export_dir(output_dir)
rows = _resolve_scope_rows(conn, scope)
for control in rows:
    md = _render_control_markdown(conn, control)
    control_path.parent.mkdir(parents=True, exist_ok=True)
    control_path.write_text(md, encoding="utf-8")
(export_root / "index.md").write_text(_render_index(...), encoding="utf-8")
(export_root / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
```

Per-control markdown must include, in order:

```text
1. Header
2. MCNA position
3. Control statement
4. Evidence table
5. Recommended actions table
6. Review history
7. Findings
8. Risk
```

Before rendering, call `ssk_verify_pointers(control_id=...)` so pointer status is fresh at export time.
When pulling findings for a control, normalize stored legacy `findings.securesketch_control` values with `canonical_control_id(...)` before comparing to the binder's canonical `control_id`.

- [ ] **Step 5: Create golden fixtures and compare output**

Populate `mcp-server/tests/fixtures/golden/binder/` with the exact markdown emitted by the deterministic test fixture data, then compare with:

```python
assert (export_path / "index.md").read_text(encoding="utf-8") == golden_index.read_text(encoding="utf-8")
assert control_md.read_text(encoding="utf-8") == golden_control.read_text(encoding="utf-8")
```

- [ ] **Step 6: Re-run the binder tests**

Run: `python -m pytest mcp-server/tests/test_ssk_binder.py -q`

Expected: PASS

- [ ] **Step 7: Commit the binder layer**

```bash
git add mcp-server/tools/ssk_binder.py mcp-server/tools/entra.py mcp-server/tools/ca.py mcp-server/tools/pp.py mcp-server/tests/test_ssk_binder.py mcp-server/tests/fixtures/golden/binder
git commit -m "feat: add Secure SketCH binder export and coverage"
```

---

### Task 6: Register MCP tools and add end-to-end integration coverage

**Files:**
- Modify: `mcp-server/server.py`
- Modify: `mcp-server/tests/test_ssk.py`

- [ ] **Step 1: Write the failing integration test**

Add to `mcp-server/tests/test_ssk.py`:

```python
def test_phase2b_flow_import_link_review_and_export(db, tmp_path):
    _seed_two_controls(db, tmp_path)
    evidence_one = json.loads(ssk_link_evidence(
        control_id="06-3",
        evidence_type="policy_link",
        source_kind="local_file",
        source_pointer=str(tmp_path / "asset-policy.docx"),
        title="Asset policy",
    ))
    evidence_two = json.loads(ssk_link_evidence(
        control_id="06-3",
        evidence_type="attestation",
        source_kind="local_file",
        source_pointer=str(tmp_path / "asset-review.txt"),
        title="Asset review notes",
    ))
    review = json.loads(ssk_record_review(
        control_id="06-3",
        reviewer="nof-dlafferty@nofmetalcoatings.us",
        evidence_ids=[evidence_one["evidence_id"], evidence_two["evidence_id"]],
        scope_summary="Quarterly review",
        outcome="ok",
        findings_summary="No gaps",
    ))
    binder = json.loads(ssk_export_binder("06-3", output_dir=str(tmp_path / "binder")))
    assert review["quality_flag"] in {"ok", "low_evidence_count"}
    assert Path(binder["output_dir"]).exists()
```

- [ ] **Step 2: Run the integration test to verify it fails**

Run: `python -m pytest mcp-server/tests/test_ssk.py::test_phase2b_flow_import_link_review_and_export -q`

Expected: FAIL until tool imports and registration are complete.

- [ ] **Step 3: Register the new MCP tools**

Modify `mcp-server/server.py` imports:

```python
from tools.ssk_evidence import ssk_link_evidence, ssk_list_evidence, ssk_evidence_expiring, ssk_verify_pointers
from tools.ssk_reviews import ssk_record_review, ssk_review_history, ssk_alerts, ssk_due
from tools.ssk_actions import ssk_mark_action, ssk_action_queue
from tools.ssk_registry import registry_add, registry_list, registry_get, registry_retire
from tools.ssk_binder import ssk_export_binder, ssk_coverage
```

Register them:

```python
mcp.tool()(ssk_link_evidence)
mcp.tool()(ssk_list_evidence)
mcp.tool()(ssk_evidence_expiring)
mcp.tool()(ssk_verify_pointers)
mcp.tool()(ssk_record_review)
mcp.tool()(ssk_review_history)
mcp.tool()(ssk_alerts)
mcp.tool()(ssk_due)
mcp.tool()(ssk_mark_action)
mcp.tool()(ssk_action_queue)
mcp.tool()(registry_add)
mcp.tool()(registry_list)
mcp.tool()(registry_get)
mcp.tool()(registry_retire)
mcp.tool()(ssk_export_binder)
mcp.tool()(ssk_coverage)
```

- [ ] **Step 4: Run the focused Secure SketCH test suite**

Run:

```bash
python -m pytest mcp-server/tests/test_ssk_evidence.py mcp-server/tests/test_ssk_reviews.py mcp-server/tests/test_ssk_actions.py mcp-server/tests/test_ssk_registry.py mcp-server/tests/test_ssk_binder.py mcp-server/tests/test_ssk.py -q
```

Expected: PASS

- [ ] **Step 5: Commit the server registration and integration coverage**

```bash
git add mcp-server/server.py mcp-server/tests/test_ssk.py
git commit -m "feat: register Phase 2b Secure SketCH tools"
```

---

### Task 7: Verify against the live MCP server and close Phase 2b

**Files:**
- Modify: `activity-log.md`

- [ ] **Step 1: Run the full MCP-server test suite**

Run: `python -m pytest mcp-server/tests -q`

Expected: PASS

- [ ] **Step 2: Smoke-test the live `mcna-amc` MCP server**

Run an inline Python client against `mcp-server/server.py` and verify:

```python
tools = await session.list_tools()
assert "ssk_link_evidence" in tool_names
assert "ssk_record_review" in tool_names
assert "registry_add" in tool_names
assert "ssk_export_binder" in tool_names
```

Then call:

```python
await session.call_tool("ssk_coverage", {})
await session.call_tool("ssk_list_controls", {})
```

Expected: successful JSON responses, no MCP transport errors.

- [ ] **Step 3: Append the factual completion note**

Append to `activity-log.md`:

```text
YYYY-MM-DD HH:MM — Phase 2b complete — Secure SketCH evidence, reviews, registries, actions, and audit binder tools added and verified — mcp-server/server.py, mcp-server/tools/ssk_*.py
```

- [ ] **Step 4: Commit the completion marker**

```bash
git add activity-log.md
git commit -m "chore: mark Phase 2b Secure SketCH layer complete"
```

---

## Verification checklist

Run these in order while executing the plan:

1. `python -m pytest mcp-server/tests/test_ssk_evidence.py -q`
2. `python -m pytest mcp-server/tests/test_ssk_reviews.py -q`
3. `python -m pytest mcp-server/tests/test_ssk_actions.py -q`
4. `python -m pytest mcp-server/tests/test_ssk_registry.py -q`
5. `python -m pytest mcp-server/tests/test_ssk_binder.py -q`
6. `python -m pytest mcp-server/tests/test_ssk.py -q`
7. `python -m pytest mcp-server/tests -q`
8. Live MCP smoke test against `mcp-server/server.py`

## Spec coverage self-review

- Evidence link/list/expiry/verification: covered by Task 1
- Reviews, alerts, due, status rollup: covered by Task 2
- Recommended actions: covered by Task 3
- Registry CRUD: covered by Task 4
- Coverage manifests and binder export: covered by Task 5
- MCP registration and end-to-end flow: covered by Task 6
- Final verification and factual completion logging: covered by Task 7

No open spec gaps remain for the Phase 2b scope defined after Phase 2a.
