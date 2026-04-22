# AMC Phase 2a — Secure SketCH Catalog Import Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Import the Secure SketCH 2026-01-01 control catalog (73 controls) into the MCNA-AMC knowledge base and expose read-only status query tools — the foundation for the full Secure SketCH tracking layer designed in the Phase 2 spec.

**Architecture:** Extend the existing `mcna_amc.db` SQLite KB with `ssk_*` tables per the spec's data model. Build a two-stage catalog import pipeline (parse `.docx` → JSON intermediate → DB upsert). Add five read-only MCP tools for catalog and status queries. Phase 2b (evidence, reviews, registries, audit binder) follows after this plan executes.

**Tech Stack:** Python 3.14, FastMCP, SQLite (stdlib), `python-docx` (new), pytest, pytest-mock.

**Source spec:** `docs/superpowers/specs/2026-04-22-securesketch-tracking-design.md`

---

## Scope for Phase 2a

In scope:
- Schema migration for all `ssk_*` tables defined in the spec (including those Phase 2b will use — adding them all now keeps the migration clean)
- `findings.closure_evidence_id` column added
- `.docx` → parser → JSON intermediate → DB loader pipeline
- `ssk_import_catalog`, `ssk_list_controls`, `ssk_get_control`, `ssk_status`, `ssk_status_all`, `ssk_gaps` tools
- Successful import of the real `Secure_SketCH_Guidelines_2026-01-01.docx` into the KB

Out of scope (Phase 2b):
- `ssk_evidence`, `ssk_reviews`, `ssk_registries` tool surface (tables exist, but CRUD tools are Phase 2b)
- Evidence-contribution manifests on existing scan tools
- Audit binder export
- `ssk_record_review`, `ssk_link_evidence`, registry tools

---

## File Structure

**New files:**
- `mcp-server/tools/ssk.py` — Secure SketCH tool functions (catalog + status)
- `mcp-server/tools/ssk_parser.py` — `.docx` parser (kept separate from tool logic for testability)
- `mcp-server/tools/ssk_loader.py` — DB upsert logic (separate from parser so tests can supply parsed dicts without touching disk)
- `mcp-server/tests/test_ssk_parser.py` — parser tests using programmatically-built `.docx` fixtures
- `mcp-server/tests/test_ssk_loader.py` — loader tests against in-memory DB
- `mcp-server/tests/test_ssk.py` — tool tests (integration of parser + loader via `ssk_import_catalog`)

**Modified files:**
- `mcp-server/db.py` — extend `_SCHEMA` with 8 new tables + `ALTER TABLE findings` for `closure_evidence_id`
- `mcp-server/requirements.txt` — add `python-docx`
- `mcp-server/server.py` — register 6 new tools
- `mcp-server/tests/test_db.py` — assert new tables exist

**Non-code artifacts produced:**
- `mcp-server/kb/catalog-imports/2026-01-01.json` — intermediate JSON from the real `.docx`, reviewed by Dave before DB commit

**Why this split:** Parser, loader, and tool code are three concerns (file I/O, DB writes, MCP wrapping). Splitting them means each module stays under ~200 lines, tests don't need disk+DB+docx in the same fixture, and Phase 2b adds its own `tools/ssk_*.py` siblings without touching the parser.

---

## Task 1: Schema migration — add ssk_* tables and findings column

**Files:**
- Modify: `mcp-server/db.py`
- Modify: `mcp-server/requirements.txt`
- Test: `mcp-server/tests/test_db.py`

- [ ] **Step 1: Add python-docx to requirements**

Edit `mcp-server/requirements.txt` — append one line:

```
python-docx>=1.1.0
```

Then run:
```bash
pip install -r mcp-server/requirements.txt
```
Expected: `python-docx` installs successfully.

- [ ] **Step 2: Write failing test for new tables**

Add to `mcp-server/tests/test_db.py`:

```python
def test_ssk_tables_exist(db):
    from db import get_connection
    expected = {
        "ssk_controls", "ssk_controls_history", "ssk_categories",
        "ssk_recommended_actions", "ssk_control_status",
        "ssk_evidence", "ssk_reviews", "ssk_registries",
    }
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    names = {r["name"] for r in rows}
    missing = expected - names
    assert not missing, f"missing ssk tables: {missing}"

def test_findings_has_closure_evidence_id(db):
    from db import get_connection
    with get_connection() as conn:
        cols = conn.execute("PRAGMA table_info(findings)").fetchall()
    names = {c["name"] for c in cols}
    assert "closure_evidence_id" in names
```

- [ ] **Step 3: Run tests — verify they fail**

Run: `cd mcp-server && pytest tests/test_db.py -v -k "ssk_tables_exist or closure_evidence"`
Expected: 2 FAILS — tables don't exist, column doesn't exist.

- [ ] **Step 4: Extend the schema**

Edit `mcp-server/db.py` — append to the `_SCHEMA` string (before the closing `"""`):

```sql
CREATE TABLE IF NOT EXISTS ssk_controls (
    control_id                   TEXT PRIMARY KEY,
    source_version               TEXT NOT NULL,
    category                     TEXT NOT NULL,
    category_name                TEXT,
    title                        TEXT NOT NULL,
    overview                     TEXT,
    status_descriptions          TEXT,
    insufficient_measures_risks  TEXT,
    imported_at                  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS ssk_controls_history (
    history_id                   TEXT PRIMARY KEY,
    control_id                   TEXT NOT NULL,
    source_version               TEXT NOT NULL,
    category                     TEXT,
    category_name                TEXT,
    title                        TEXT,
    overview                     TEXT,
    status_descriptions          TEXT,
    insufficient_measures_risks  TEXT,
    imported_at                  TEXT,
    superseded_at                TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS ssk_categories (
    category       TEXT PRIMARY KEY,
    category_name  TEXT NOT NULL,
    display_order  INTEGER
);
CREATE TABLE IF NOT EXISTS ssk_recommended_actions (
    action_id             TEXT PRIMARY KEY,
    control_id            TEXT NOT NULL,
    source_version        TEXT NOT NULL,
    sequence              INTEGER NOT NULL,
    action_text           TEXT NOT NULL,
    implementation_status TEXT NOT NULL DEFAULT 'not_started',
    implementation_notes  TEXT,
    owner                 TEXT,
    last_updated          TEXT NOT NULL,
    FOREIGN KEY (control_id) REFERENCES ssk_controls(control_id)
);
CREATE TABLE IF NOT EXISTS ssk_control_status (
    control_id           TEXT PRIMARY KEY,
    current_maturity     TEXT NOT NULL DEFAULT 'not_regularly_reviewed',
    target_maturity      TEXT NOT NULL DEFAULT 'Regularly Reviewed',
    gap_summary          TEXT,
    owner                TEXT,
    review_cadence_days  INTEGER NOT NULL DEFAULT 90,
    last_reviewed_at     TEXT,
    next_review_due      TEXT,
    last_updated         TEXT NOT NULL,
    FOREIGN KEY (control_id) REFERENCES ssk_controls(control_id)
);
CREATE TABLE IF NOT EXISTS ssk_evidence (
    evidence_id              TEXT PRIMARY KEY,
    control_id               TEXT NOT NULL,
    evidence_type            TEXT NOT NULL,
    title                    TEXT,
    source_kind              TEXT NOT NULL,
    source_pointer           TEXT NOT NULL,
    source_metadata          TEXT,
    produced_at              TEXT NOT NULL,
    validity_window_days     INTEGER,
    expires_at               TEXT,
    verification_status      TEXT NOT NULL DEFAULT 'unverified',
    verification_checked_at  TEXT,
    recorded_by              TEXT,
    notes                    TEXT,
    FOREIGN KEY (control_id) REFERENCES ssk_controls(control_id)
);
CREATE TABLE IF NOT EXISTS ssk_reviews (
    review_id         TEXT PRIMARY KEY,
    control_id        TEXT,
    control_family    TEXT,
    reviewer          TEXT NOT NULL,
    reviewed_at       TEXT NOT NULL,
    scope_summary     TEXT,
    evidence_ids      TEXT,
    outcome           TEXT NOT NULL,
    quality_flag      TEXT NOT NULL DEFAULT 'ok',
    findings_summary  TEXT,
    next_review_due   TEXT,
    prior_review_id   TEXT,
    CHECK ((control_id IS NOT NULL) <> (control_family IS NOT NULL))
);
CREATE TABLE IF NOT EXISTS ssk_registries (
    registry_entry_id  TEXT PRIMARY KEY,
    registry_name      TEXT NOT NULL,
    control_ids        TEXT,
    entry_key          TEXT NOT NULL,
    entry_data         TEXT,
    entry_pointer      TEXT,
    status             TEXT NOT NULL DEFAULT 'active',
    effective_from     TEXT NOT NULL,
    effective_to       TEXT,
    recorded_by        TEXT,
    recorded_at        TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS ix_ssk_registries_active_key
    ON ssk_registries(registry_name, entry_key)
    WHERE status = 'active';
```

- [ ] **Step 5: Handle ALTER TABLE for the findings column**

Below the `_SCHEMA` constant and above `init_db`, add a helper:

```python
def _apply_findings_migration(conn):
    cols = conn.execute("PRAGMA table_info(findings)").fetchall()
    names = {c[1] for c in cols}
    if "closure_evidence_id" not in names:
        conn.execute("ALTER TABLE findings ADD COLUMN closure_evidence_id TEXT")
```

Modify `init_db` to call it:

```python
def init_db(path: Path = KB_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.executescript(_SCHEMA)
        _apply_findings_migration(conn)
        conn.commit()
```

- [ ] **Step 6: Run tests — verify they pass**

Run: `cd mcp-server && pytest tests/test_db.py -v`
Expected: All tests pass, including the two new ones.

- [ ] **Step 7: Commit**

```bash
git add mcp-server/db.py mcp-server/requirements.txt mcp-server/tests/test_db.py
git commit -m "feat: add ssk_* tables and closure_evidence_id to KB schema"
```

---

## Task 2: Parser — docx iteration + control boundary detection

**Files:**
- Create: `mcp-server/tools/ssk_parser.py`
- Create: `mcp-server/tests/test_ssk_parser.py`

- [ ] **Step 1: Write failing test — identifies control boundaries**

Create `mcp-server/tests/test_ssk_parser.py`:

```python
import pytest
from docx import Document
from tools.ssk_parser import parse_catalog


def _build_minimal_docx(tmp_path):
    path = tmp_path / "minimal.docx"
    doc = Document()
    doc.add_heading("Secure SketCH Guidelines", level=1)
    doc.add_heading("Introduction", level=2)
    doc.add_paragraph("General introduction text that should be ignored.")
    # Control 04-1
    doc.add_paragraph("04-1 Sample human resources control")
    doc.add_paragraph("Overview")
    doc.add_paragraph("Overview text for 04-1.")
    doc.add_paragraph("Regularly Reviewed status")
    doc.add_paragraph("Status text for 04-1.")
    doc.add_paragraph("Recommended Actions")
    doc.add_paragraph("Action one for 04-1.")
    doc.add_paragraph("Action two for 04-1.")
    doc.add_paragraph("Insufficient Measures Risks")
    doc.add_paragraph("Risk text for 04-1.")
    # Control 06-3
    doc.add_paragraph("06-3 Sample asset management control")
    doc.add_paragraph("Overview")
    doc.add_paragraph("Overview text for 06-3.")
    doc.add_paragraph("Regularly Reviewed status")
    doc.add_paragraph("Status text for 06-3.")
    doc.add_paragraph("Recommended Actions")
    doc.add_paragraph("Action one for 06-3.")
    doc.add_paragraph("Insufficient Measures Risks")
    doc.add_paragraph("Risk text for 06-3.")
    doc.save(path)
    return path


def test_parser_identifies_two_controls(tmp_path):
    path = _build_minimal_docx(tmp_path)
    result = parse_catalog(path, source_version="test-1")
    assert len(result["controls"]) == 2
    ids = [c["control_id"] for c in result["controls"]]
    assert ids == ["04-1", "06-3"]
```

- [ ] **Step 2: Run test — verify it fails**

Run: `cd mcp-server && pytest tests/test_ssk_parser.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'tools.ssk_parser'`

- [ ] **Step 3: Minimal parser implementation**

Create `mcp-server/tools/ssk_parser.py`:

```python
import re
from pathlib import Path
from docx import Document

CONTROL_ID_RE = re.compile(r"^(\d{2}-\d+)\s+(.+)$")


def parse_catalog(docx_path: Path, source_version: str) -> dict:
    doc = Document(docx_path)
    controls: list[dict] = []
    categories: dict[str, str] = {}
    parse_failures: list[dict] = []
    warnings: list[str] = []

    current: dict | None = None

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue
        m = CONTROL_ID_RE.match(text)
        if m:
            if current is not None:
                controls.append(current)
            control_id = m.group(1)
            title = m.group(2).strip()
            category = control_id.split("-")[0]
            current = {
                "control_id": control_id,
                "source_version": source_version,
                "category": category,
                "category_name": categories.get(category),
                "title": title,
                "overview": "",
                "status_description": "",
                "recommended_actions": [],
                "insufficient_measures_risks": "",
                "_current_section": None,
            }

    if current is not None:
        controls.append(current)

    for c in controls:
        c.pop("_current_section", None)

    return {
        "source_version": source_version,
        "controls": controls,
        "categories": categories,
        "parse_failures": parse_failures,
        "warnings": warnings,
    }
```

- [ ] **Step 4: Run test — verify it passes**

Run: `cd mcp-server && pytest tests/test_ssk_parser.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add mcp-server/tools/ssk_parser.py mcp-server/tests/test_ssk_parser.py
git commit -m "feat: ssk_parser skeleton — detect control boundaries"
```

---

## Task 3: Parser — section extraction (overview, status, actions, risks)

**Files:**
- Modify: `mcp-server/tools/ssk_parser.py`
- Modify: `mcp-server/tests/test_ssk_parser.py`

- [ ] **Step 1: Write failing test — extracts all sections**

Append to `mcp-server/tests/test_ssk_parser.py`:

```python
def test_parser_extracts_all_sections(tmp_path):
    path = _build_minimal_docx(tmp_path)
    result = parse_catalog(path, source_version="test-1")
    c041 = next(c for c in result["controls"] if c["control_id"] == "04-1")
    assert c041["title"] == "Sample human resources control"
    assert c041["overview"] == "Overview text for 04-1."
    assert c041["status_description"] == "Status text for 04-1."
    assert c041["recommended_actions"] == ["Action one for 04-1.", "Action two for 04-1."]
    assert c041["insufficient_measures_risks"] == "Risk text for 04-1."

    c063 = next(c for c in result["controls"] if c["control_id"] == "06-3")
    assert c063["overview"] == "Overview text for 06-3."
    assert c063["recommended_actions"] == ["Action one for 06-3."]
```

- [ ] **Step 2: Run test — verify it fails**

Run: `cd mcp-server && pytest tests/test_ssk_parser.py::test_parser_extracts_all_sections -v`
Expected: FAIL — all section fields are empty.

- [ ] **Step 3: Extend parser with state machine**

Replace the body of `parse_catalog` in `mcp-server/tools/ssk_parser.py` with the full state machine:

```python
import re
from pathlib import Path
from docx import Document

CONTROL_ID_RE = re.compile(r"^(\d{2}-\d+)\s+(.+)$")
SECTION_HEADERS = {
    "Overview": "overview",
    "Regularly Reviewed status": "status_description",
    "Recommended Actions": "recommended_actions",
    "Insufficient Measures Risks": "insufficient_measures_risks",
}


def _empty_control(control_id: str, title: str, source_version: str, category_name: str | None) -> dict:
    return {
        "control_id": control_id,
        "source_version": source_version,
        "category": control_id.split("-")[0],
        "category_name": category_name,
        "title": title,
        "overview": "",
        "status_description": "",
        "recommended_actions": [],
        "insufficient_measures_risks": "",
        "_current_section": None,
    }


def parse_catalog(docx_path: Path, source_version: str) -> dict:
    doc = Document(docx_path)
    controls: list[dict] = []
    categories: dict[str, str] = {}
    parse_failures: list[dict] = []
    warnings: list[str] = []

    current: dict | None = None

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue

        m = CONTROL_ID_RE.match(text)
        if m:
            if current is not None:
                controls.append(current)
            control_id = m.group(1)
            title = m.group(2).strip()
            category = control_id.split("-")[0]
            current = _empty_control(control_id, title, source_version, categories.get(category))
            continue

        if current is None:
            continue

        if text in SECTION_HEADERS:
            current["_current_section"] = SECTION_HEADERS[text]
            continue

        section = current["_current_section"]
        if section == "overview":
            current["overview"] = (current["overview"] + " " + text).strip()
        elif section == "status_description":
            current["status_description"] = (current["status_description"] + " " + text).strip()
        elif section == "recommended_actions":
            current["recommended_actions"].append(text)
        elif section == "insufficient_measures_risks":
            current["insufficient_measures_risks"] = (current["insufficient_measures_risks"] + " " + text).strip()

    if current is not None:
        controls.append(current)

    for c in controls:
        c.pop("_current_section", None)

    return {
        "source_version": source_version,
        "controls": controls,
        "categories": categories,
        "parse_failures": parse_failures,
        "warnings": warnings,
    }
```

- [ ] **Step 4: Run tests — verify all pass**

Run: `cd mcp-server && pytest tests/test_ssk_parser.py -v`
Expected: Both tests PASS.

- [ ] **Step 5: Commit**

```bash
git add mcp-server/tools/ssk_parser.py mcp-server/tests/test_ssk_parser.py
git commit -m "feat: ssk_parser extracts overview, status, actions, risks"
```

---

## Task 4: Parser — category heading extraction

**Files:**
- Modify: `mcp-server/tools/ssk_parser.py`
- Modify: `mcp-server/tests/test_ssk_parser.py`

- [ ] **Step 1: Write failing test — extracts categories from level-2 headings**

Append to `mcp-server/tests/test_ssk_parser.py`:

```python
def test_parser_extracts_categories_from_headings(tmp_path):
    path = tmp_path / "with_cats.docx"
    doc = Document()
    doc.add_heading("Secure SketCH Guidelines", level=1)
    cat_para = doc.add_paragraph("04 Human Resources")
    cat_para.style = doc.styles["Heading 2"]
    doc.add_paragraph("04-1 Sample HR control")
    doc.add_paragraph("Overview")
    doc.add_paragraph("Overview text.")
    doc.add_paragraph("Regularly Reviewed status")
    doc.add_paragraph("Status text.")
    doc.add_paragraph("Recommended Actions")
    doc.add_paragraph("Action one.")
    doc.add_paragraph("Insufficient Measures Risks")
    doc.add_paragraph("Risk text.")
    cat2 = doc.add_paragraph("06 Asset Management")
    cat2.style = doc.styles["Heading 2"]
    doc.add_paragraph("06-3 Sample asset control")
    doc.add_paragraph("Overview")
    doc.add_paragraph("Overview text 2.")
    doc.add_paragraph("Regularly Reviewed status")
    doc.add_paragraph("Status text 2.")
    doc.add_paragraph("Recommended Actions")
    doc.add_paragraph("Action two.")
    doc.add_paragraph("Insufficient Measures Risks")
    doc.add_paragraph("Risk text 2.")
    doc.save(path)

    result = parse_catalog(path, source_version="test-cats")
    assert result["categories"] == {"04": "Human Resources", "06": "Asset Management"}
    c041 = next(c for c in result["controls"] if c["control_id"] == "04-1")
    assert c041["category_name"] == "Human Resources"
    c063 = next(c for c in result["controls"] if c["control_id"] == "06-3")
    assert c063["category_name"] == "Asset Management"
```

- [ ] **Step 2: Run test — verify it fails**

Run: `cd mcp-server && pytest tests/test_ssk_parser.py::test_parser_extracts_categories_from_headings -v`
Expected: FAIL — `categories` is empty.

- [ ] **Step 3: Implement category detection**

At the top of `mcp-server/tools/ssk_parser.py` under the existing imports, add:

```python
CATEGORY_HEADING_RE = re.compile(r"^(\d{2})\s+(.+)$")
IGNORED_HEADINGS = {"Introduction", "Secure SketCH Guidelines"}
```

Inside `parse_catalog`, in the loop, after the `if not text: continue` line and before the `CONTROL_ID_RE.match(text)` block, insert:

```python
        style_name = (para.style.name if para.style else "") or ""
        if "Heading" in style_name and text not in IGNORED_HEADINGS:
            cat_m = CATEGORY_HEADING_RE.match(text)
            if cat_m:
                categories[cat_m.group(1)] = cat_m.group(2).strip()
                continue
```

- [ ] **Step 4: Run all parser tests — verify they pass**

Run: `cd mcp-server && pytest tests/test_ssk_parser.py -v`
Expected: All three tests PASS.

- [ ] **Step 5: Commit**

```bash
git add mcp-server/tools/ssk_parser.py mcp-server/tests/test_ssk_parser.py
git commit -m "feat: ssk_parser extracts category headings"
```

---

## Task 5: Parser — error handling for malformed controls

**Files:**
- Modify: `mcp-server/tools/ssk_parser.py`
- Modify: `mcp-server/tests/test_ssk_parser.py`

- [ ] **Step 1: Write failing test — missing section reports parse_failures**

Append to `mcp-server/tests/test_ssk_parser.py`:

```python
def test_parser_reports_missing_sections(tmp_path):
    path = tmp_path / "with_gaps.docx"
    doc = Document()
    # Control with no Overview section (missing required section)
    doc.add_paragraph("07-1 Malformed control")
    doc.add_paragraph("Recommended Actions")
    doc.add_paragraph("Only action.")
    doc.add_paragraph("Insufficient Measures Risks")
    doc.add_paragraph("Risk text.")
    doc.save(path)

    result = parse_catalog(path, source_version="test-gaps")
    assert len(result["parse_failures"]) == 1
    assert result["parse_failures"][0]["control_id"] == "07-1"
    assert "overview" in result["parse_failures"][0]["reason"].lower()
    # Malformed controls are still returned in the list so DB loader can decide
    assert len(result["controls"]) == 1


def test_parser_handles_source_file_missing(tmp_path):
    from tools.ssk_parser import CatalogSourceError
    missing = tmp_path / "does-not-exist.docx"
    with pytest.raises(CatalogSourceError):
        parse_catalog(missing, source_version="test-missing")
```

- [ ] **Step 2: Run tests — verify they fail**

Run: `cd mcp-server && pytest tests/test_ssk_parser.py::test_parser_reports_missing_sections tests/test_ssk_parser.py::test_parser_handles_source_file_missing -v`
Expected: FAIL — `parse_failures` is empty; `CatalogSourceError` doesn't exist.

- [ ] **Step 3: Add CatalogSourceError and validation**

At the top of `mcp-server/tools/ssk_parser.py`, under the imports:

```python
class CatalogSourceError(Exception):
    """Raised when the source .docx is missing or unreadable."""
```

Replace the beginning of `parse_catalog`:

```python
def parse_catalog(docx_path: Path, source_version: str) -> dict:
    docx_path = Path(docx_path)
    if not docx_path.exists():
        raise CatalogSourceError(f"Catalog source not found: {docx_path}")
    try:
        doc = Document(docx_path)
    except Exception as e:
        raise CatalogSourceError(f"Failed to read {docx_path}: {e}") from e
```

After the main loop, before the `return` statement, add validation:

```python
    required_sections = {
        "overview": "overview",
        "status_description": "regularly reviewed status",
        "recommended_actions": "recommended actions",
        "insufficient_measures_risks": "insufficient measures risks",
    }
    for c in controls:
        missing = [
            label for field, label in required_sections.items()
            if not c.get(field)
        ]
        if missing:
            parse_failures.append({
                "control_id": c["control_id"],
                "reason": f"missing required sections: {', '.join(missing)}",
            })
```

- [ ] **Step 4: Run all parser tests — verify they pass**

Run: `cd mcp-server && pytest tests/test_ssk_parser.py -v`
Expected: All five tests PASS.

- [ ] **Step 5: Commit**

```bash
git add mcp-server/tools/ssk_parser.py mcp-server/tests/test_ssk_parser.py
git commit -m "feat: ssk_parser reports missing sections and source errors"
```

---

## Task 6: Catalog loader — upsert parsed dict into DB

**Files:**
- Create: `mcp-server/tools/ssk_loader.py`
- Create: `mcp-server/tests/test_ssk_loader.py`

- [ ] **Step 1: Write failing test — loader writes rows and initializes status**

Create `mcp-server/tests/test_ssk_loader.py`:

```python
import json
from tools.ssk_loader import load_catalog


def _parsed_payload():
    return {
        "source_version": "2026-01-01",
        "categories": {"06": "Asset Management"},
        "controls": [
            {
                "control_id": "06-3",
                "source_version": "2026-01-01",
                "category": "06",
                "category_name": "Asset Management",
                "title": "Management of software assets",
                "overview": "Define rules for managing software assets.",
                "status_description": "Inventory of software assets is taken periodically.",
                "recommended_actions": ["Action one.", "Action two."],
                "insufficient_measures_risks": "Vulns may go undetected.",
            }
        ],
        "parse_failures": [],
        "warnings": [],
    }


def test_loader_inserts_control_and_actions(db):
    from db import get_connection
    result = load_catalog(_parsed_payload())
    assert result["written_controls"] == 1
    assert result["written_actions"] == 2

    with get_connection() as conn:
        controls = conn.execute("SELECT * FROM ssk_controls").fetchall()
        actions = conn.execute("SELECT * FROM ssk_recommended_actions ORDER BY sequence").fetchall()
        status = conn.execute("SELECT * FROM ssk_control_status").fetchall()
        cats = conn.execute("SELECT * FROM ssk_categories").fetchall()

    assert len(controls) == 1
    assert controls[0]["control_id"] == "06-3"
    assert controls[0]["source_version"] == "2026-01-01"
    assert controls[0]["category_name"] == "Asset Management"
    descriptions = json.loads(controls[0]["status_descriptions"])
    assert descriptions == {"Regularly Reviewed": "Inventory of software assets is taken periodically."}

    assert len(actions) == 2
    assert [a["action_id"] for a in actions] == ["06-3-a", "06-3-b"]
    assert actions[0]["action_text"] == "Action one."
    assert actions[0]["implementation_status"] == "not_started"

    assert len(status) == 1
    assert status[0]["control_id"] == "06-3"
    assert status[0]["current_maturity"] == "not_regularly_reviewed"
    assert status[0]["target_maturity"] == "Regularly Reviewed"

    assert len(cats) == 1
    assert cats[0]["category"] == "06"
    assert cats[0]["category_name"] == "Asset Management"


def test_loader_upsert_is_idempotent(db):
    from db import get_connection
    payload = _parsed_payload()
    load_catalog(payload)
    load_catalog(payload)
    with get_connection() as conn:
        count = conn.execute("SELECT COUNT(*) AS c FROM ssk_controls").fetchone()["c"]
    assert count == 1


def test_loader_moves_old_row_to_history_on_version_bump(db):
    from db import get_connection
    p1 = _parsed_payload()
    load_catalog(p1)
    p2 = _parsed_payload()
    p2["source_version"] = "2026-07-01"
    p2["controls"][0]["source_version"] = "2026-07-01"
    p2["controls"][0]["overview"] = "Updated overview."
    load_catalog(p2)

    with get_connection() as conn:
        current = conn.execute("SELECT * FROM ssk_controls").fetchone()
        history = conn.execute("SELECT * FROM ssk_controls_history").fetchall()
    assert current["source_version"] == "2026-07-01"
    assert current["overview"] == "Updated overview."
    assert len(history) == 1
    assert history[0]["source_version"] == "2026-01-01"
```

- [ ] **Step 2: Run tests — verify they fail**

Run: `cd mcp-server && pytest tests/test_ssk_loader.py -v`
Expected: FAIL — `tools.ssk_loader` doesn't exist.

- [ ] **Step 3: Implement loader**

Create `mcp-server/tools/ssk_loader.py`:

```python
import json
import uuid
from datetime import datetime, timezone
from db import get_connection


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_catalog(parsed: dict) -> dict:
    source_version = parsed["source_version"]
    controls = parsed["controls"]
    categories = parsed.get("categories", {})
    now = _now()

    written_controls = 0
    written_actions = 0
    history_moved = 0

    with get_connection() as conn:
        for cat_id, cat_name in categories.items():
            conn.execute(
                "INSERT INTO ssk_categories (category, category_name) VALUES (?, ?) "
                "ON CONFLICT(category) DO UPDATE SET category_name = excluded.category_name",
                (cat_id, cat_name),
            )

        for c in controls:
            existing = conn.execute(
                "SELECT * FROM ssk_controls WHERE control_id = ?",
                (c["control_id"],),
            ).fetchone()

            if existing is not None and existing["source_version"] != source_version:
                conn.execute(
                    "INSERT INTO ssk_controls_history "
                    "(history_id, control_id, source_version, category, category_name, "
                    " title, overview, status_descriptions, insufficient_measures_risks, "
                    " imported_at, superseded_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        str(uuid.uuid4()),
                        existing["control_id"],
                        existing["source_version"],
                        existing["category"],
                        existing["category_name"],
                        existing["title"],
                        existing["overview"],
                        existing["status_descriptions"],
                        existing["insufficient_measures_risks"],
                        existing["imported_at"],
                        now,
                    ),
                )
                history_moved += 1

            status_descriptions = json.dumps(
                {"Regularly Reviewed": c.get("status_description", "")}
            )
            conn.execute(
                "INSERT INTO ssk_controls "
                "(control_id, source_version, category, category_name, title, overview, "
                " status_descriptions, insufficient_measures_risks, imported_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(control_id) DO UPDATE SET "
                " source_version=excluded.source_version, category=excluded.category, "
                " category_name=excluded.category_name, title=excluded.title, "
                " overview=excluded.overview, status_descriptions=excluded.status_descriptions, "
                " insufficient_measures_risks=excluded.insufficient_measures_risks, "
                " imported_at=excluded.imported_at",
                (
                    c["control_id"], source_version, c["category"], c.get("category_name"),
                    c["title"], c.get("overview", ""), status_descriptions,
                    c.get("insufficient_measures_risks", ""), now,
                ),
            )
            written_controls += 1

            conn.execute(
                "DELETE FROM ssk_recommended_actions WHERE control_id = ?",
                (c["control_id"],),
            )
            for idx, action_text in enumerate(c.get("recommended_actions", [])):
                action_letter = chr(ord("a") + idx)
                action_id = f"{c['control_id']}-{action_letter}"
                conn.execute(
                    "INSERT INTO ssk_recommended_actions "
                    "(action_id, control_id, source_version, sequence, action_text, last_updated) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (action_id, c["control_id"], source_version, idx, action_text, now),
                )
                written_actions += 1

            conn.execute(
                "INSERT INTO ssk_control_status (control_id, last_updated) VALUES (?, ?) "
                "ON CONFLICT(control_id) DO NOTHING",
                (c["control_id"], now),
            )

    return {
        "written_controls": written_controls,
        "written_actions": written_actions,
        "history_moved": history_moved,
    }
```

- [ ] **Step 4: Run loader tests — verify they pass**

Run: `cd mcp-server && pytest tests/test_ssk_loader.py -v`
Expected: All three tests PASS.

- [ ] **Step 5: Commit**

```bash
git add mcp-server/tools/ssk_loader.py mcp-server/tests/test_ssk_loader.py
git commit -m "feat: ssk_loader upserts controls, actions, categories, status; versions move to history"
```

---

## Task 7: `ssk_import_catalog` tool — dry-run + commit modes

**Files:**
- Create: `mcp-server/tools/ssk.py`
- Create: `mcp-server/tests/test_ssk.py`

- [ ] **Step 1: Write failing test — dry_run writes JSON only**

Create `mcp-server/tests/test_ssk.py`:

```python
import json
from pathlib import Path
from docx import Document
from tools.ssk import ssk_import_catalog


def _build_minimal_docx(tmp_path):
    path = tmp_path / "minimal.docx"
    doc = Document()
    doc.add_paragraph("04-1 Sample control")
    doc.add_paragraph("Overview")
    doc.add_paragraph("Overview text.")
    doc.add_paragraph("Regularly Reviewed status")
    doc.add_paragraph("Status text.")
    doc.add_paragraph("Recommended Actions")
    doc.add_paragraph("Action one.")
    doc.add_paragraph("Insufficient Measures Risks")
    doc.add_paragraph("Risk text.")
    doc.save(path)
    return path


def test_ssk_import_catalog_dry_run_writes_json_only(db, tmp_path):
    from db import get_connection
    docx_path = _build_minimal_docx(tmp_path)
    intermediate_dir = tmp_path / "intermediate"
    result_json = ssk_import_catalog(
        docx_path=str(docx_path),
        version="test-1",
        dry_run=True,
        intermediate_dir=str(intermediate_dir),
    )
    result = json.loads(result_json)
    assert result["dry_run"] is True
    assert result["parsed_controls"] == 1
    assert result["written_controls"] == 0

    with get_connection() as conn:
        rows = conn.execute("SELECT COUNT(*) AS c FROM ssk_controls").fetchone()
    assert rows["c"] == 0

    intermediate = Path(result["intermediate_json_path"])
    assert intermediate.exists()
    payload = json.loads(intermediate.read_text(encoding="utf-8"))
    assert payload["controls"][0]["control_id"] == "04-1"


def test_ssk_import_catalog_commit_writes_db(db, tmp_path):
    from db import get_connection
    docx_path = _build_minimal_docx(tmp_path)
    intermediate_dir = tmp_path / "intermediate"
    result_json = ssk_import_catalog(
        docx_path=str(docx_path),
        version="test-1",
        dry_run=False,
        intermediate_dir=str(intermediate_dir),
    )
    result = json.loads(result_json)
    assert result["dry_run"] is False
    assert result["written_controls"] == 1
    assert result["written_actions"] == 1

    with get_connection() as conn:
        rows = conn.execute("SELECT COUNT(*) AS c FROM ssk_controls").fetchone()
    assert rows["c"] == 1
```

- [ ] **Step 2: Run tests — verify they fail**

Run: `cd mcp-server && pytest tests/test_ssk.py -v`
Expected: FAIL — `tools.ssk` doesn't exist.

- [ ] **Step 3: Implement `ssk_import_catalog`**

Create `mcp-server/tools/ssk.py`:

```python
import json
from datetime import datetime, timezone
from pathlib import Path
from tools.ssk_parser import parse_catalog, CatalogSourceError
from tools.ssk_loader import load_catalog


def _default_intermediate_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "kb" / "catalog-imports"


def ssk_import_catalog(
    docx_path: str,
    version: str,
    dry_run: bool = False,
    intermediate_dir: str | None = None,
) -> str:
    try:
        parsed = parse_catalog(Path(docx_path), source_version=version)
    except CatalogSourceError as e:
        return json.dumps({"error": str(e), "error_type": "CatalogSourceError"})

    out_dir = Path(intermediate_dir) if intermediate_dir else _default_intermediate_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    intermediate_path = out_dir / f"{version}.json"
    intermediate_path.write_text(json.dumps(parsed, indent=2), encoding="utf-8")

    response: dict = {
        "dry_run": dry_run,
        "parsed_controls": len(parsed["controls"]),
        "parse_failures": parsed["parse_failures"],
        "warnings": parsed["warnings"],
        "intermediate_json_path": str(intermediate_path),
        "written_controls": 0,
        "written_actions": 0,
        "history_moved": 0,
    }

    if dry_run:
        return json.dumps(response, indent=2)

    load_result = load_catalog(parsed)
    response.update({
        "written_controls": load_result["written_controls"],
        "written_actions": load_result["written_actions"],
        "history_moved": load_result["history_moved"],
    })
    return json.dumps(response, indent=2)
```

- [ ] **Step 4: Run tests — verify they pass**

Run: `cd mcp-server && pytest tests/test_ssk.py -v`
Expected: Both tests PASS.

- [ ] **Step 5: Commit**

```bash
git add mcp-server/tools/ssk.py mcp-server/tests/test_ssk.py
git commit -m "feat: ssk_import_catalog tool with dry_run + commit modes"
```

---

## Task 8: `ssk_list_controls` and `ssk_get_control` read tools

**Files:**
- Modify: `mcp-server/tools/ssk.py`
- Modify: `mcp-server/tests/test_ssk.py`

- [ ] **Step 1: Write failing tests**

Append to `mcp-server/tests/test_ssk.py`:

```python
from tools.ssk import ssk_list_controls, ssk_get_control


def _seed_two_controls(db, tmp_path):
    docx_path = tmp_path / "two.docx"
    doc = Document()
    doc.add_paragraph("04-1 HR control")
    doc.add_paragraph("Overview")
    doc.add_paragraph("HR overview.")
    doc.add_paragraph("Regularly Reviewed status")
    doc.add_paragraph("HR status.")
    doc.add_paragraph("Recommended Actions")
    doc.add_paragraph("HR action.")
    doc.add_paragraph("Insufficient Measures Risks")
    doc.add_paragraph("HR risk.")
    doc.add_paragraph("06-3 Asset control")
    doc.add_paragraph("Overview")
    doc.add_paragraph("Asset overview.")
    doc.add_paragraph("Regularly Reviewed status")
    doc.add_paragraph("Asset status.")
    doc.add_paragraph("Recommended Actions")
    doc.add_paragraph("Asset action one.")
    doc.add_paragraph("Asset action two.")
    doc.add_paragraph("Insufficient Measures Risks")
    doc.add_paragraph("Asset risk.")
    doc.save(docx_path)
    ssk_import_catalog(str(docx_path), version="seed", dry_run=False,
                       intermediate_dir=str(tmp_path / "i"))


def test_ssk_list_controls_returns_all(db, tmp_path):
    _seed_two_controls(db, tmp_path)
    result = json.loads(ssk_list_controls())
    ids = [c["control_id"] for c in result]
    assert ids == ["04-1", "06-3"]


def test_ssk_list_controls_filters_by_category(db, tmp_path):
    _seed_two_controls(db, tmp_path)
    result = json.loads(ssk_list_controls(category="06"))
    assert len(result) == 1
    assert result[0]["control_id"] == "06-3"


def test_ssk_get_control_includes_recommended_actions(db, tmp_path):
    _seed_two_controls(db, tmp_path)
    result = json.loads(ssk_get_control("06-3"))
    assert result["control_id"] == "06-3"
    assert result["title"] == "Asset control"
    assert len(result["recommended_actions"]) == 2
    assert result["recommended_actions"][0]["action_text"] == "Asset action one."
    assert result["recommended_actions"][0]["action_id"] == "06-3-a"


def test_ssk_get_control_unknown_returns_error(db):
    result = json.loads(ssk_get_control("99-9"))
    assert "error" in result
```

- [ ] **Step 2: Run tests — verify they fail**

Run: `cd mcp-server && pytest tests/test_ssk.py -v -k "list_controls or get_control"`
Expected: FAIL — functions don't exist.

- [ ] **Step 3: Implement tools**

Append to `mcp-server/tools/ssk.py`:

```python
from db import get_connection


def ssk_list_controls(category: str | None = None) -> str:
    with get_connection() as conn:
        if category:
            rows = conn.execute(
                "SELECT control_id, category, category_name, title "
                "FROM ssk_controls WHERE category = ? ORDER BY control_id",
                (category,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT control_id, category, category_name, title "
                "FROM ssk_controls ORDER BY control_id"
            ).fetchall()
    return json.dumps([dict(r) for r in rows], indent=2)


def ssk_get_control(control_id: str) -> str:
    with get_connection() as conn:
        control = conn.execute(
            "SELECT * FROM ssk_controls WHERE control_id = ?", (control_id,)
        ).fetchone()
        if control is None:
            return json.dumps({"error": f"control '{control_id}' not found"})
        actions = conn.execute(
            "SELECT action_id, sequence, action_text, implementation_status, "
            " implementation_notes, owner "
            "FROM ssk_recommended_actions WHERE control_id = ? ORDER BY sequence",
            (control_id,),
        ).fetchall()

    payload = dict(control)
    if payload.get("status_descriptions"):
        payload["status_descriptions"] = json.loads(payload["status_descriptions"])
    payload["recommended_actions"] = [dict(a) for a in actions]
    return json.dumps(payload, indent=2)
```

- [ ] **Step 4: Run tests — verify they pass**

Run: `cd mcp-server && pytest tests/test_ssk.py -v`
Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add mcp-server/tools/ssk.py mcp-server/tests/test_ssk.py
git commit -m "feat: ssk_list_controls + ssk_get_control read tools"
```

---

## Task 9: `ssk_status` and `ssk_status_all` tools

**Files:**
- Modify: `mcp-server/tools/ssk.py`
- Modify: `mcp-server/tests/test_ssk.py`

- [ ] **Step 1: Write failing tests**

Append to `mcp-server/tests/test_ssk.py`:

```python
from tools.ssk import ssk_status, ssk_status_all


def test_ssk_status_default_after_import(db, tmp_path):
    _seed_two_controls(db, tmp_path)
    result = json.loads(ssk_status("06-3"))
    assert result["control_id"] == "06-3"
    assert result["current_maturity"] == "not_regularly_reviewed"
    assert result["target_maturity"] == "Regularly Reviewed"
    assert result["title"] == "Asset control"
    assert result["last_reviewed_at"] is None


def test_ssk_status_unknown_returns_error(db):
    result = json.loads(ssk_status("99-9"))
    assert "error" in result


def test_ssk_status_all_returns_every_imported_control(db, tmp_path):
    _seed_two_controls(db, tmp_path)
    result = json.loads(ssk_status_all())
    assert len(result) == 2
    ids = [r["control_id"] for r in result]
    assert ids == ["04-1", "06-3"]


def test_ssk_status_all_below_target_filter(db, tmp_path):
    _seed_two_controls(db, tmp_path)
    # All controls start below target after import — filter should return both
    result = json.loads(ssk_status_all(below_target=True))
    assert len(result) == 2
```

- [ ] **Step 2: Run tests — verify they fail**

Run: `cd mcp-server && pytest tests/test_ssk.py -v -k "status"`
Expected: FAIL — functions don't exist.

- [ ] **Step 3: Implement tools**

Append to `mcp-server/tools/ssk.py`:

```python
def ssk_status(control_id: str) -> str:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT s.*, c.title, c.category, c.category_name "
            "FROM ssk_control_status s "
            "JOIN ssk_controls c ON c.control_id = s.control_id "
            "WHERE s.control_id = ?",
            (control_id,),
        ).fetchone()
    if row is None:
        return json.dumps({"error": f"control '{control_id}' not found"})
    return json.dumps(dict(row), indent=2)


def ssk_status_all(below_target: bool = False, due_before: str | None = None) -> str:
    clauses: list[str] = []
    params: list = []
    if below_target:
        clauses.append("s.current_maturity != 'regularly_reviewed'")
    if due_before:
        clauses.append("s.next_review_due IS NOT NULL AND s.next_review_due < ?")
        params.append(due_before)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    sql = (
        "SELECT s.*, c.title, c.category, c.category_name "
        "FROM ssk_control_status s "
        "JOIN ssk_controls c ON c.control_id = s.control_id "
        f"{where} ORDER BY c.control_id"
    )
    with get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()
    return json.dumps([dict(r) for r in rows], indent=2)
```

- [ ] **Step 4: Run tests — verify they pass**

Run: `cd mcp-server && pytest tests/test_ssk.py -v`
Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add mcp-server/tools/ssk.py mcp-server/tests/test_ssk.py
git commit -m "feat: ssk_status + ssk_status_all read tools"
```

---

## Task 10: `ssk_gaps` tool

**Files:**
- Modify: `mcp-server/tools/ssk.py`
- Modify: `mcp-server/tests/test_ssk.py`

- [ ] **Step 1: Write failing test**

Append to `mcp-server/tests/test_ssk.py`:

```python
from tools.ssk import ssk_gaps


def test_ssk_gaps_lists_controls_below_target(db, tmp_path):
    _seed_two_controls(db, tmp_path)
    result = json.loads(ssk_gaps())
    assert result["total_controls"] == 2
    assert result["at_target"] == 0
    assert result["below_target"] == 2
    assert len(result["gaps"]) == 2
    gap_ids = {g["control_id"] for g in result["gaps"]}
    assert gap_ids == {"04-1", "06-3"}
    for g in result["gaps"]:
        assert g["current_maturity"] == "not_regularly_reviewed"
        assert "title" in g
```

- [ ] **Step 2: Run test — verify it fails**

Run: `cd mcp-server && pytest tests/test_ssk.py::test_ssk_gaps_lists_controls_below_target -v`
Expected: FAIL — `ssk_gaps` doesn't exist.

- [ ] **Step 3: Implement tool**

Append to `mcp-server/tools/ssk.py`:

```python
def ssk_gaps() -> str:
    with get_connection() as conn:
        total = conn.execute("SELECT COUNT(*) AS c FROM ssk_control_status").fetchone()["c"]
        at_target = conn.execute(
            "SELECT COUNT(*) AS c FROM ssk_control_status "
            "WHERE current_maturity = 'regularly_reviewed'"
        ).fetchone()["c"]
        gap_rows = conn.execute(
            "SELECT s.control_id, s.current_maturity, s.target_maturity, "
            " s.last_reviewed_at, s.next_review_due, s.gap_summary, "
            " c.title, c.category, c.category_name "
            "FROM ssk_control_status s "
            "JOIN ssk_controls c ON c.control_id = s.control_id "
            "WHERE s.current_maturity != 'regularly_reviewed' "
            "ORDER BY c.control_id"
        ).fetchall()

    return json.dumps({
        "total_controls": total,
        "at_target": at_target,
        "below_target": total - at_target,
        "gaps": [dict(r) for r in gap_rows],
    }, indent=2)
```

- [ ] **Step 4: Run all SSK tests — verify they pass**

Run: `cd mcp-server && pytest tests/test_ssk.py tests/test_ssk_parser.py tests/test_ssk_loader.py -v`
Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add mcp-server/tools/ssk.py mcp-server/tests/test_ssk.py
git commit -m "feat: ssk_gaps roll-up tool"
```

---

## Task 11: Register Phase 2a tools in `server.py`

**Files:**
- Modify: `mcp-server/server.py`

- [ ] **Step 1: Wire up the new tools**

Edit `mcp-server/server.py`. Add this import block alongside the others (after the `pp` import):

```python
from tools.ssk import (
    ssk_import_catalog, ssk_list_controls, ssk_get_control,
    ssk_status, ssk_status_all, ssk_gaps,
)
```

Add the registration block after the existing `# PP tools` block, before the `if __name__ == "__main__":` line:

```python
# Secure SketCH tools (Phase 2a)
mcp.tool()(ssk_import_catalog)
mcp.tool()(ssk_list_controls)
mcp.tool()(ssk_get_control)
mcp.tool()(ssk_status)
mcp.tool()(ssk_status_all)
mcp.tool()(ssk_gaps)
```

- [ ] **Step 2: Syntax check**

Run: `cd mcp-server && python -c "import server"`
Expected: No output (successful import).

- [ ] **Step 3: Full test suite**

Run: `cd mcp-server && pytest -v`
Expected: All tests PASS (parser, loader, ssk tools, plus all pre-existing tests).

- [ ] **Step 4: Commit**

```bash
git add mcp-server/server.py
git commit -m "feat: register Phase 2a Secure SketCH tools with MCP server"
```

---

## Task 12: Real `.docx` dry-run import checkpoint

**Files:**
- Non-code: `mcp-server/kb/catalog-imports/2026-01-01.json` (generated)

This task is a manual checkpoint with Dave. It is not a code task, but it is how Phase 2a proves it works on real data before marking the phase complete.

- [ ] **Step 1: Restart Claude Code so the new MCP tools load**

Dave closes and reopens Claude Code. The new `ssk_*` tools become available.

- [ ] **Step 2: Run a dry-run import against the real `.docx`**

Invoke:
```
ssk_import_catalog(
    docx_path="Secure_SketCH_Guidelines_2026-01-01.docx",
    version="2026-01-01",
    dry_run=True,
)
```
Expected: Returns JSON with `parsed_controls: 73` and any `parse_failures` listed. Intermediate JSON written to `mcp-server/kb/catalog-imports/2026-01-01.json`.

- [ ] **Step 3: Review the intermediate JSON with Dave**

Open `mcp-server/kb/catalog-imports/2026-01-01.json`. Look for:
- Control count matches Dave's expectation (73).
- All categories have names populated (or identify the ones that don't for a manual `ssk_categories` INSERT).
- Spot-check 3–5 random controls: does the `overview`, `status_description`, `recommended_actions`, and `insufficient_measures_risks` text look right?
- `parse_failures` list is empty, or reasons make sense.

- [ ] **Step 4: If parse issues found, tune parser and re-run dry-run**

Possible fixes:
- Heading style detection failing for the real doc's styles → adjust `"Heading" in style_name` check.
- Section header casing variation → normalize `SECTION_HEADERS` keys.
- Multi-paragraph overview being split → already handled by accumulation, but double-check.

Any parser changes get their own test in `test_ssk_parser.py` first, then commit.

- [ ] **Step 5: Commit the intermediate JSON as audit-trail**

```bash
git add mcp-server/kb/catalog-imports/2026-01-01.json
git commit -m "chore: Secure SketCH catalog 2026-01-01 intermediate JSON (dry-run)"
```

- [ ] **Step 6: Run the real import (commit mode)**

Invoke:
```
ssk_import_catalog(
    docx_path="Secure_SketCH_Guidelines_2026-01-01.docx",
    version="2026-01-01",
    dry_run=False,
)
```
Expected: `written_controls` matches `parsed_controls`. DB now has 73 rows in `ssk_controls`, 73 rows in `ssk_control_status`, actions in `ssk_recommended_actions`, categories in `ssk_categories`.

- [ ] **Step 7: Verify with read tools**

```
ssk_list_controls()                   # expect 73 entries
ssk_get_control("06-3")               # expect full detail
ssk_status_all()                      # expect 73 rows, all below target
ssk_gaps()                            # expect at_target=0, below_target=73
```

- [ ] **Step 8: Log to activity-log.md**

Append to `activity-log.md`:
```
YYYY-MM-DD HH:MM — ssk_import_catalog (real) — 73 controls imported from 2026-01-01 catalog — mcp-server/kb/mcna_amc.db
```

- [ ] **Step 9: Final commit marking Phase 2a complete**

(No code change needed — just activity-log.)
```bash
git add activity-log.md
git commit -m "chore: Phase 2a complete — Secure SketCH catalog imported (73 controls)"
```

---

## Phase 2a complete

At the end of Task 12:

- `mcna_amc.db` contains the full 2026-01-01 Secure SketCH catalog.
- Dave can query catalog content and MCNA's (initial, all-failing) control status via MCP tools.
- All infrastructure needed for Phase 2b exists: `ssk_evidence`, `ssk_reviews`, `ssk_registries` tables are created and waiting for their tool surface.

**Next phase:** Invoke `superpowers:writing-plans` again for Phase 2b (evidence linking, review attestation, registries, audit binder export, evidence-contribution manifests on existing scan tools).
