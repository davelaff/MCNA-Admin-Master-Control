# Consolidated MCNA SSK Parser Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Secure SketCH Guidelines parser with one that handles the consolidated MCNA `IT-STD-SSK-CONSOLIDATED` format, adding `ssk_clauses` and `ssk_audit_evidence_items` tables plus five new columns on `ssk_controls`.

**Architecture:** Four files change in dependency order: `db.py` (schema) → `ssk_parser.py` (extract) → `ssk_loader.py` (write) → `ssk.py` (serve). The new parser is a complete state-machine rewrite; it reads Heading1/Heading3/Heading4 structure instead of keyword sections. `ssk_recommended_actions` is not deleted but will be empty after re-import since the new format has no "Recommended Actions" section — `ssk_clauses` replaces it. Existing operational data (`ssk_control_status`, `ssk_evidence`, `ssk_reviews`) is untouched since all FKs are on `control_id` (stable NN-N format).

**Tech Stack:** Python 3.14, python-docx, SQLite (stdlib), pytest

**Source file:** `C:\Users\dlafferty.MCNA\OneDrive - NOF\DL OneDrive\OneDrive - NOF\Documents - Gov Sec\02_Policy_and_Standards\IT-STD-SSK-CONSOLIDATED_MCNA_Consolidated_Cybersecurity_Standatrds.docx`

---

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `mcp-server/db.py` | Modify | Add `ssk_clauses`, `ssk_audit_evidence_items` to `_SCHEMA`; add `_apply_ssk_controls_migration` for 5 new columns |
| `mcp-server/tools/ssk_parser.py` | Rewrite | State-machine parser for MCNA consolidated format |
| `mcp-server/tools/ssk_loader.py` | Modify | Write `ssk_clauses` + `ssk_audit_evidence_items`; include new `ssk_controls` columns in upsert + history archive |
| `mcp-server/tools/ssk.py` | Modify | `ssk_get_control` returns clauses + audit evidence items; `ssk_import_catalog` reports new counters |
| `mcp-server/tests/test_db.py` | Modify | Assert new tables and columns exist |
| `mcp-server/tests/test_ssk_parser.py` | Replace | Tests for MCNA consolidated format; old Secure SketCH format tests removed |
| `mcp-server/tests/test_ssk_loader.py` | Modify | Updated fixture with clauses + evidence items; assert new tables written |
| `mcp-server/tests/test_ssk.py` | Modify | `_build_minimal_docx` → new MCNA format; `test_ssk_get_control` asserts clauses |

---

## Task 1: DB schema — new tables + column migrations

**Files:**
- Modify: `mcp-server/db.py`
- Test: `mcp-server/tests/test_db.py`

- [ ] **Step 1: Write failing tests**

Add to `mcp-server/tests/test_db.py` (append after the last test):

```python
def test_ssk_new_tables_exist(tmp_db):
    with sqlite3.connect(tmp_db) as conn:
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    assert "ssk_clauses" in tables
    assert "ssk_audit_evidence_items" in tables


def test_ssk_controls_has_new_columns(tmp_db):
    with sqlite3.connect(tmp_db) as conn:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(ssk_controls)").fetchall()}
    assert {"effective_date", "review_date", "approver", "cadence", "reviewer"} <= cols


def test_init_creates_all_tables_updated(tmp_db):
    with sqlite3.connect(tmp_db) as conn:
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    assert "ssk_clauses" in tables
    assert "ssk_audit_evidence_items" in tables
```

- [ ] **Step 2: Run tests to verify they fail**

```
cd mcp-server
python -m pytest tests/test_db.py::test_ssk_new_tables_exist tests/test_db.py::test_ssk_controls_has_new_columns -v
```

Expected: FAIL — `AssertionError: assert 'ssk_clauses' in ...`

- [ ] **Step 3: Update `_SCHEMA` in `db.py`**

Add after the `ssk_control_coverage_snapshots` block (before `remediation_plans`):

```python
CREATE TABLE IF NOT EXISTS ssk_clauses (
    clause_id      TEXT PRIMARY KEY,
    control_id     TEXT NOT NULL,
    source_version TEXT NOT NULL,
    group_name     TEXT,
    sequence       INTEGER NOT NULL,
    clause_text    TEXT NOT NULL,
    FOREIGN KEY (control_id) REFERENCES ssk_controls(control_id)
);
CREATE TABLE IF NOT EXISTS ssk_audit_evidence_items (
    item_id        TEXT PRIMARY KEY,
    control_id     TEXT NOT NULL,
    source_version TEXT NOT NULL,
    sequence       INTEGER NOT NULL,
    item_text      TEXT NOT NULL,
    FOREIGN KEY (control_id) REFERENCES ssk_controls(control_id)
);
```

- [ ] **Step 4: Add column migration function in `db.py`**

Add after `_apply_findings_migration` (before `init_db`):

```python
def _apply_ssk_controls_migration(conn: sqlite3.Connection) -> None:
    _NEW_COLS = {"effective_date": "TEXT", "review_date": "TEXT",
                 "approver": "TEXT", "cadence": "TEXT", "reviewer": "TEXT"}
    for table in ("ssk_controls", "ssk_controls_history"):
        existing = {c[1] for c in conn.execute(f"PRAGMA table_info({table})").fetchall()}
        for col, typ in _NEW_COLS.items():
            if col not in existing:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {typ}")
```

- [ ] **Step 5: Call the new migration in `init_db`**

Change `init_db` to:

```python
def init_db(path: Path = KB_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.executescript(_SCHEMA)
        _apply_findings_migration(conn)
        _apply_ssk_controls_migration(conn)
        conn.commit()
```

- [ ] **Step 6: Update `test_init_creates_all_tables` and `test_init_is_idempotent` in `test_db.py`**

Replace the existing `test_init_creates_all_tables` and `test_init_is_idempotent` tests:

```python
def test_init_creates_all_tables(tmp_db):
    with sqlite3.connect(tmp_db) as conn:
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    assert tables == {
        "tenant_snapshot", "findings", "baselines", "dismissed", "activity_log",
        "ssk_controls", "ssk_controls_history", "ssk_categories",
        "ssk_recommended_actions", "ssk_control_status",
        "ssk_evidence", "ssk_reviews", "ssk_registries",
        "ssk_control_coverage_snapshots",
        "ssk_clauses", "ssk_audit_evidence_items",
        "remediation_plans", "remediation_actions", "remediation_events",
    }


def test_init_is_idempotent(tmp_db):
    init_db(tmp_db)  # second call must not raise
    with sqlite3.connect(tmp_db) as conn:
        tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    assert len(tables) == 19
```

- [ ] **Step 7: Run tests to verify they pass**

```
python -m pytest tests/test_db.py -v
```

Expected: all PASS

- [ ] **Step 8: Commit**

```
git add mcp-server/db.py mcp-server/tests/test_db.py
git commit -m "feat(ssk): add ssk_clauses, ssk_audit_evidence_items tables and ssk_controls column migration"
```

---

## Task 2: Parser rewrite

**Files:**
- Rewrite: `mcp-server/tools/ssk_parser.py`
- Replace: `mcp-server/tests/test_ssk_parser.py`

- [ ] **Step 1: Replace `test_ssk_parser.py` with new-format tests**

Write `mcp-server/tests/test_ssk_parser.py` in full:

```python
import pytest
from docx import Document
from tools.ssk_parser import parse_catalog, CatalogSourceError


def _build_minimal_mcna_docx(tmp_path, controls=None):
    """Build a minimal MCNA consolidated-format .docx for parser tests."""
    if controls is None:
        controls = [
            {
                "control_id": "04-1",
                "title": "Sample HR control",
                "category_suffix": "Human Resources Standards",
                "effective_date": "2026-05-15",
                "review_date": "2027-05-15",
                "approver": "CFO / Executive Sponsor",
                "purpose": "Purpose text for 04-1.",
                "clause_groups": [
                    ("Governance", [("04-1.1", "Clause one."), ("04-1.2", "Clause two.")]),
                ],
                "cadence": "Annually.",
                "reviewer": "IT-MIS Director.",
                "audit_evidence": ["Evidence item one.", "Evidence item two."],
                "risks": "Risk text for 04-1.",
            }
        ]
    path = tmp_path / "minimal_mcna.docx"
    doc = Document()
    doc.add_heading("MCNA Cyber Security Standards", level=1)
    for c in controls:
        cid = c["control_id"]
        gnum = cid.split("-")[0]
        doc.add_heading(
            f"{cid}: {c['title']}SSK Group {gnum}: {c['category_suffix']}"
            "NOF MCNA IT and Information Systems Security Policy and Standards",
            level=1,
        )
        for key, val in [
            ("Document ID", f"IT-STD-SSK-{cid}"),
            ("Effective Date", c["effective_date"]),
            ("Review Date", c["review_date"]),
            ("Approver", c["approver"]),
        ]:
            doc.add_paragraph(key)
            doc.add_paragraph(val)
        doc.add_heading("1. Purpose", level=3)
        doc.add_paragraph(c["purpose"])
        doc.add_heading("4. Standards", level=3)
        doc.add_paragraph("The obligations below apply to MCNA.")
        current_group = None
        for group_name, clauses in c["clause_groups"]:
            if group_name != current_group:
                doc.add_heading(group_name, level=4)
                current_group = group_name
            for clause_id, clause_text in clauses:
                doc.add_paragraph(f"{clause_id}{clause_text}")
        doc.add_heading("6. Review & Compliance", level=3)
        doc.add_heading("Cadence", level=4)
        doc.add_paragraph(c["cadence"])
        doc.add_heading("Reviewer", level=4)
        doc.add_paragraph(c["reviewer"])
        doc.add_heading("Audit evidence", level=4)
        for item in c["audit_evidence"]:
            p = doc.add_paragraph(item)
            p.style = doc.styles["List Paragraph"]
        doc.add_heading("7. Risks of Non-compliance", level=3)
        doc.add_paragraph(c["risks"])
    doc.save(path)
    return path


def test_parser_identifies_control(tmp_path):
    path = _build_minimal_mcna_docx(tmp_path)
    result = parse_catalog(path, source_version="test-1")
    assert len(result["controls"]) == 1
    assert result["controls"][0]["control_id"] == "04-1"
    assert result["parse_failures"] == []


def test_parser_extracts_metadata(tmp_path):
    path = _build_minimal_mcna_docx(tmp_path)
    result = parse_catalog(path, source_version="test-1")
    c = result["controls"][0]
    assert c["title"] == "Sample HR control"
    assert c["effective_date"] == "2026-05-15"
    assert c["review_date"] == "2027-05-15"
    assert c["approver"] == "CFO / Executive Sponsor"
    assert c["category"] == "04"
    assert c["category_name"] is not None and "Human Resources" in c["category_name"]


def test_parser_extracts_overview(tmp_path):
    path = _build_minimal_mcna_docx(tmp_path)
    result = parse_catalog(path, source_version="test-1")
    assert result["controls"][0]["overview"] == "Purpose text for 04-1."


def test_parser_extracts_clauses(tmp_path):
    path = _build_minimal_mcna_docx(tmp_path)
    result = parse_catalog(path, source_version="test-1")
    clauses = result["controls"][0]["clauses"]
    assert len(clauses) == 2
    assert clauses[0]["clause_id"] == "04-1.1"
    assert clauses[0]["clause_text"] == "Clause one."
    assert clauses[0]["group_name"] == "Governance"
    assert clauses[0]["sequence"] == 0
    assert clauses[1]["clause_id"] == "04-1.2"
    assert clauses[1]["sequence"] == 1


def test_parser_extracts_review_section(tmp_path):
    path = _build_minimal_mcna_docx(tmp_path)
    result = parse_catalog(path, source_version="test-1")
    c = result["controls"][0]
    assert c["cadence"] == "Annually."
    assert c["reviewer"] == "IT-MIS Director."
    assert c["status_description"] == "Annually."  # cadence is aliased to status_description


def test_parser_extracts_audit_evidence(tmp_path):
    path = _build_minimal_mcna_docx(tmp_path)
    result = parse_catalog(path, source_version="test-1")
    items = result["controls"][0]["audit_evidence_items"]
    assert len(items) == 2
    assert items[0]["item_text"] == "Evidence item one."
    assert items[0]["sequence"] == 0
    assert items[1]["item_text"] == "Evidence item two."
    assert items[1]["sequence"] == 1


def test_parser_extracts_risks(tmp_path):
    path = _build_minimal_mcna_docx(tmp_path)
    result = parse_catalog(path, source_version="test-1")
    assert "Risk text for 04-1." in result["controls"][0]["insufficient_measures_risks"]


def test_parser_reports_failures_for_missing_sections(tmp_path):
    path = tmp_path / "bad.docx"
    doc = Document()
    doc.add_heading(
        "04-1: Missing Sections ControlSSK Group 04: HR StandardsNOF MCNA...", level=1
    )
    doc.add_heading("7. Risks of Non-compliance", level=3)
    doc.add_paragraph("Some risk.")
    doc.save(path)
    result = parse_catalog(path, source_version="test-fail")
    assert len(result["parse_failures"]) == 1
    failure = result["parse_failures"][0]
    assert failure["control_id"] == "04-1"
    assert "overview" in failure["reason"]
    assert "standards clauses" in failure["reason"]


def test_parser_handles_two_controls(tmp_path):
    path = _build_minimal_mcna_docx(
        tmp_path,
        controls=[
            {
                "control_id": "04-1",
                "title": "HR control",
                "category_suffix": "Human Resources Standards",
                "effective_date": "2026-05-15",
                "review_date": "2027-05-15",
                "approver": "CFO / Executive Sponsor",
                "purpose": "HR purpose.",
                "clause_groups": [("G", [("04-1.1", "HR clause.")])],
                "cadence": "Annually.",
                "reviewer": "IT-MIS Director.",
                "audit_evidence": ["HR evidence."],
                "risks": "HR risk.",
            },
            {
                "control_id": "06-3",
                "title": "Asset control",
                "category_suffix": "Asset Management Standards",
                "effective_date": "2026-05-15",
                "review_date": "2027-05-15",
                "approver": "CFO / Executive Sponsor",
                "purpose": "Asset purpose.",
                "clause_groups": [
                    ("G", [("06-3.1", "Asset clause one."), ("06-3.2", "Asset clause two.")])
                ],
                "cadence": "Annually.",
                "reviewer": "IT-MIS Director.",
                "audit_evidence": ["Asset evidence one.", "Asset evidence two."],
                "risks": "Asset risk.",
            },
        ],
    )
    result = parse_catalog(path, source_version="test-two")
    assert len(result["controls"]) == 2
    assert [c["control_id"] for c in result["controls"]] == ["04-1", "06-3"]
    assert result["controls"][1]["clauses"][0]["clause_id"] == "06-3.1"


def test_parser_skips_cover_heading(tmp_path):
    """The first Heading1 ('MCNA Cyber Security Standards') must not be parsed as a control."""
    path = _build_minimal_mcna_docx(tmp_path)
    result = parse_catalog(path, source_version="test-cover")
    ids = [c["control_id"] for c in result["controls"]]
    assert "MCNA" not in ids
    assert len(result["controls"]) == 1


def test_parser_missing_file_raises(tmp_path):
    with pytest.raises(CatalogSourceError):
        parse_catalog(tmp_path / "does-not-exist.docx", source_version="x")
```

- [ ] **Step 2: Run new tests to verify they fail**

```
python -m pytest tests/test_ssk_parser.py -v
```

Expected: all FAIL — `ImportError` or `AssertionError` since parser still has old logic.

- [ ] **Step 3: Rewrite `ssk_parser.py`**

Replace `mcp-server/tools/ssk_parser.py` entirely:

```python
import re
from pathlib import Path
from docx import Document


class CatalogSourceError(Exception):
    """Raised when the source .docx is missing or unreadable."""


# Matches MCNA consolidated heading: "01-1: Title textSSK Group 01: ..."
_CONTROL_HEADING_RE = re.compile(r'^(\d{2}-\d+):\s+(.+?)(?=SSK Group)')
# Extracts category name from heading suffix: "SSK Group 01: Category NameNOF MCNA..."
_CATEGORY_RE = re.compile(r'SSK Group \d+:\s+(.+?)(?=NOF MCNA|$)')
# Splits clause ID from text: "01-1.1Some clause text" → ("01-1.1", "Some clause text")
_CLAUSE_RE = re.compile(r'^(\d{2}-\d+\.\d+)\s*(.*)')
# Extracts heading level from style name: "Heading 1" → 1, "Heading3" → 3
_HEADING_LEVEL_RE = re.compile(r'(?i)heading\s*(\d)')

_METADATA_KEYS = {
    "Effective Date": "effective_date",
    "Review Date": "review_date",
    "Approver": "approver",
}

# Map Heading3 text → parser mode
_SECTION_MAP = {
    "1. Purpose": "overview",
    "4. Standards": "clauses",
    "6. Review & Compliance": "review",
    "7. Risks of Non-compliance": "risks",
}

# Map Heading4 text (inside "review" mode) → review sub-field
_REVIEW_SUBSECTIONS = {
    "Cadence": "cadence",
    "Reviewer": "reviewer",
    "Audit evidence": "audit_evidence",
}


def _heading_level(style_name: str) -> int | None:
    m = _HEADING_LEVEL_RE.search(style_name)
    return int(m.group(1)) if m else None


def _is_list_para(style_name: str) -> bool:
    return "list" in style_name.lower()


def _empty_control(control_id: str, title: str, source_version: str,
                   category_name: str | None) -> dict:
    return {
        "control_id": control_id,
        "source_version": source_version,
        "category": control_id.split("-")[0],
        "category_name": category_name,
        "title": title,
        "effective_date": None,
        "review_date": None,
        "approver": None,
        "overview": "",
        "cadence": "",
        "reviewer": "",
        "status_description": "",   # set to cadence after parsing; preserved for loader compat
        "insufficient_measures_risks": "",
        "clauses": [],
        "audit_evidence_items": [],
    }


def parse_catalog(docx_path: Path, source_version: str) -> dict:
    docx_path = Path(docx_path)
    if not docx_path.exists():
        raise CatalogSourceError(f"Catalog source not found: {docx_path}")
    try:
        doc = Document(docx_path)
    except Exception as e:
        raise CatalogSourceError(f"Failed to read {docx_path}: {e}") from e

    controls: list[dict] = []
    parse_failures: list[dict] = []

    current: dict | None = None
    mode: str | None = None      # None | "meta" | "overview" | "clauses" | "review" | "risks" | "skip"
    review_sub: str | None = None  # "cadence" | "reviewer" | "audit_evidence" | None
    clause_group: str | None = None
    meta_last_key: str | None = None

    def _commit():
        nonlocal current
        if current is not None:
            controls.append(current)
        current = None

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue

        style_name = (para.style.name or "") if para.style else ""
        level = _heading_level(style_name)
        is_list = _is_list_para(style_name)

        # ── Heading 1: potential control boundary ──────────────────────────
        if level == 1:
            norm = text.replace("\n", " ")
            m = _CONTROL_HEADING_RE.match(norm)
            if m:
                _commit()
                control_id = m.group(1)
                title = m.group(2).strip()
                cat_m = _CATEGORY_RE.search(norm)
                category_name = cat_m.group(1).strip() if cat_m else None
                current = _empty_control(control_id, title, source_version, category_name)
                mode = "meta"
                meta_last_key = None
                clause_group = None
                review_sub = None
            # else: cover page or unrecognised H1 — skip
            continue

        if current is None:
            continue

        # ── Heading 3: section switch ──────────────────────────────────────
        if level == 3:
            mode = _SECTION_MAP.get(text, "skip")
            review_sub = None
            clause_group = None
            continue

        # ── Heading 4: subsection (clauses group name or review sub-field) ─
        if level == 4:
            if mode == "clauses":
                clause_group = text
            elif mode == "review":
                review_sub = _REVIEW_SUBSECTIONS.get(text)
            continue

        # ── Normal / ListParagraph: content ───────────────────────────────
        if mode == "meta":
            if text in _METADATA_KEYS:
                meta_last_key = text
            elif meta_last_key in _METADATA_KEYS:
                current[_METADATA_KEYS[meta_last_key]] = text  # type: ignore[index]
                meta_last_key = None
            else:
                meta_last_key = None

        elif mode == "overview":
            current["overview"] = (current["overview"] + " " + text).strip()

        elif mode == "clauses":
            cm = _CLAUSE_RE.match(text)
            if cm:
                current["clauses"].append({
                    "clause_id": cm.group(1),
                    "group_name": clause_group,
                    "sequence": len(current["clauses"]),
                    "clause_text": cm.group(2).strip(),
                })

        elif mode == "review":
            if review_sub == "cadence" and not is_list:
                current["cadence"] = (current["cadence"] + " " + text).strip()
            elif review_sub == "reviewer" and not is_list:
                current["reviewer"] = (current["reviewer"] + " " + text).strip()
            elif review_sub == "audit_evidence" and is_list:
                current["audit_evidence_items"].append({
                    "sequence": len(current["audit_evidence_items"]),
                    "item_text": text,
                })

        elif mode == "risks":
            current["insufficient_measures_risks"] = (
                current["insufficient_measures_risks"] + " " + text
            ).strip()

    _commit()

    # Alias cadence → status_description for loader backward compatibility
    for c in controls:
        c["status_description"] = c["cadence"]

    # Validate required sections
    _REQUIRED = {
        "overview": "overview",
        "clauses": "standards clauses",
        "insufficient_measures_risks": "risks of non-compliance",
    }
    for c in controls:
        missing = [label for field, label in _REQUIRED.items() if not c.get(field)]
        if missing:
            parse_failures.append({
                "control_id": c["control_id"],
                "reason": f"missing required sections: {', '.join(missing)}",
            })

    return {
        "source_version": source_version,
        "controls": controls,
        "parse_failures": parse_failures,
        "warnings": [],
    }
```

- [ ] **Step 4: Run parser tests**

```
python -m pytest tests/test_ssk_parser.py -v
```

Expected: all PASS

- [ ] **Step 5: Commit**

```
git add mcp-server/tools/ssk_parser.py mcp-server/tests/test_ssk_parser.py
git commit -m "feat(ssk): rewrite parser for MCNA consolidated format; extracts clauses, audit evidence, metadata"
```

---

## Task 3: Loader update

**Files:**
- Modify: `mcp-server/tools/ssk_loader.py`
- Modify: `mcp-server/tests/test_ssk_loader.py`

- [ ] **Step 1: Update `test_ssk_loader.py` fixture and add new assertions**

Replace `mcp-server/tests/test_ssk_loader.py` entirely:

```python
import json
from tools.ssk_loader import load_catalog


def _parsed_payload():
    return {
        "source_version": "2026-01-01",
        "categories": {},
        "controls": [
            {
                "control_id": "06-3",
                "source_version": "2026-01-01",
                "category": "06",
                "category_name": "Asset Management Standards",
                "title": "Management of software assets",
                "effective_date": "2026-05-15",
                "review_date": "2027-05-15",
                "approver": "CFO / Executive Sponsor",
                "overview": "Define rules for managing software assets.",
                "cadence": "At least annually.",
                "reviewer": "IT-MIS Director.",
                "status_description": "At least annually.",
                "insufficient_measures_risks": "Vulns may go undetected.",
                "clauses": [
                    {
                        "clause_id": "06-3.1",
                        "group_name": "Software Management",
                        "sequence": 0,
                        "clause_text": "Download software only from authorized vendors.",
                    },
                    {
                        "clause_id": "06-3.2",
                        "group_name": "Software Management",
                        "sequence": 1,
                        "clause_text": "Use IT asset management tools.",
                    },
                ],
                "audit_evidence_items": [
                    {"sequence": 0, "item_text": "Software asset inventory extract."},
                    {"sequence": 1, "item_text": "License management ledger."},
                ],
            }
        ],
        "parse_failures": [],
        "warnings": [],
    }


def test_loader_inserts_control_and_clauses(db):
    from db import get_connection
    result = load_catalog(_parsed_payload())
    assert result["written_controls"] == 1
    assert result["written_clauses"] == 2
    assert result["written_evidence_items"] == 2

    with get_connection() as conn:
        controls = conn.execute("SELECT * FROM ssk_controls").fetchall()
        clauses = conn.execute(
            "SELECT * FROM ssk_clauses ORDER BY sequence"
        ).fetchall()
        evidence = conn.execute(
            "SELECT * FROM ssk_audit_evidence_items ORDER BY sequence"
        ).fetchall()
        status = conn.execute("SELECT * FROM ssk_control_status").fetchall()

    assert len(controls) == 1
    c = controls[0]
    assert c["control_id"] == "06-3"
    assert c["effective_date"] == "2026-05-15"
    assert c["review_date"] == "2027-05-15"
    assert c["approver"] == "CFO / Executive Sponsor"
    assert c["cadence"] == "At least annually."
    assert c["reviewer"] == "IT-MIS Director."
    descriptions = json.loads(c["status_descriptions"])
    assert descriptions == {"Regularly Reviewed": "At least annually."}

    assert len(clauses) == 2
    assert clauses[0]["clause_id"] == "06-3.1"
    assert clauses[0]["clause_text"] == "Download software only from authorized vendors."
    assert clauses[0]["group_name"] == "Software Management"
    assert clauses[0]["sequence"] == 0
    assert clauses[1]["clause_id"] == "06-3.2"

    assert len(evidence) == 2
    assert evidence[0]["item_id"] == "06-3-ae-0"
    assert evidence[0]["item_text"] == "Software asset inventory extract."
    assert evidence[1]["item_id"] == "06-3-ae-1"

    assert len(status) == 1
    assert status[0]["control_id"] == "06-3"
    assert status[0]["current_maturity"] == "not_regularly_reviewed"


def test_loader_upsert_is_idempotent(db):
    from db import get_connection
    payload = _parsed_payload()
    load_catalog(payload)
    load_catalog(payload)
    with get_connection() as conn:
        count = conn.execute("SELECT COUNT(*) AS c FROM ssk_controls").fetchone()["c"]
        clause_count = conn.execute("SELECT COUNT(*) AS c FROM ssk_clauses").fetchone()["c"]
    assert count == 1
    assert clause_count == 2  # DELETE+INSERT, idempotent


def test_loader_moves_old_row_to_history_on_version_bump(db):
    from db import get_connection
    p1 = _parsed_payload()
    load_catalog(p1)
    p2 = _parsed_payload()
    p2["source_version"] = "2026-07-01"
    p2["controls"][0]["source_version"] = "2026-07-01"
    p2["controls"][0]["overview"] = "Updated overview."
    p2["controls"][0]["effective_date"] = "2026-07-01"
    load_catalog(p2)

    with get_connection() as conn:
        current = conn.execute("SELECT * FROM ssk_controls").fetchone()
        history = conn.execute("SELECT * FROM ssk_controls_history").fetchall()
    assert current["source_version"] == "2026-07-01"
    assert current["overview"] == "Updated overview."
    assert current["effective_date"] == "2026-07-01"
    assert len(history) == 1
    assert history[0]["source_version"] == "2026-01-01"
    assert history[0]["effective_date"] == "2026-05-15"
```

- [ ] **Step 2: Run tests to verify they fail**

```
python -m pytest tests/test_ssk_loader.py -v
```

Expected: FAIL — `KeyError: 'written_clauses'` and `AssertionError` on new column assertions.

- [ ] **Step 3: Rewrite `ssk_loader.py`**

Replace `mcp-server/tools/ssk_loader.py` entirely:

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
    written_clauses = 0
    written_evidence_items = 0
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
                    " effective_date, review_date, approver, cadence, reviewer, "
                    " imported_at, superseded_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
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
                        existing["effective_date"],
                        existing["review_date"],
                        existing["approver"],
                        existing["cadence"],
                        existing["reviewer"],
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
                " status_descriptions, insufficient_measures_risks, "
                " effective_date, review_date, approver, cadence, reviewer, imported_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(control_id) DO UPDATE SET "
                " source_version=excluded.source_version, category=excluded.category, "
                " category_name=excluded.category_name, title=excluded.title, "
                " overview=excluded.overview, status_descriptions=excluded.status_descriptions, "
                " insufficient_measures_risks=excluded.insufficient_measures_risks, "
                " effective_date=excluded.effective_date, review_date=excluded.review_date, "
                " approver=excluded.approver, cadence=excluded.cadence, "
                " reviewer=excluded.reviewer, imported_at=excluded.imported_at",
                (
                    c["control_id"], source_version, c["category"], c.get("category_name"),
                    c["title"], c.get("overview", ""), status_descriptions,
                    c.get("insufficient_measures_risks", ""),
                    c.get("effective_date"), c.get("review_date"), c.get("approver"),
                    c.get("cadence", ""), c.get("reviewer", ""), now,
                ),
            )
            written_controls += 1

            # Clauses (replace-on-import)
            conn.execute(
                "DELETE FROM ssk_clauses WHERE control_id = ?", (c["control_id"],)
            )
            for clause in c.get("clauses", []):
                conn.execute(
                    "INSERT INTO ssk_clauses "
                    "(clause_id, control_id, source_version, group_name, sequence, clause_text) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        clause["clause_id"], c["control_id"], source_version,
                        clause.get("group_name"), clause["sequence"], clause["clause_text"],
                    ),
                )
                written_clauses += 1

            # Audit evidence items (replace-on-import)
            conn.execute(
                "DELETE FROM ssk_audit_evidence_items WHERE control_id = ?", (c["control_id"],)
            )
            for item in c.get("audit_evidence_items", []):
                item_id = f"{c['control_id']}-ae-{item['sequence']}"
                conn.execute(
                    "INSERT INTO ssk_audit_evidence_items "
                    "(item_id, control_id, source_version, sequence, item_text) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (item_id, c["control_id"], source_version, item["sequence"], item["item_text"]),
                )
                written_evidence_items += 1

            # Recommended actions: clear old data on reimport (new format has none)
            conn.execute(
                "DELETE FROM ssk_recommended_actions WHERE control_id = ?",
                (c["control_id"],),
            )

            conn.execute(
                "INSERT INTO ssk_control_status (control_id, last_updated) VALUES (?, ?) "
                "ON CONFLICT(control_id) DO NOTHING",
                (c["control_id"], now),
            )

    return {
        "written_controls": written_controls,
        "written_actions": written_clauses,  # backward-compat key
        "written_clauses": written_clauses,
        "written_evidence_items": written_evidence_items,
        "history_moved": history_moved,
    }
```

- [ ] **Step 4: Run loader tests**

```
python -m pytest tests/test_ssk_loader.py -v
```

Expected: all PASS

- [ ] **Step 5: Commit**

```
git add mcp-server/tools/ssk_loader.py mcp-server/tests/test_ssk_loader.py
git commit -m "feat(ssk): loader writes ssk_clauses and ssk_audit_evidence_items; adds new ssk_controls columns"
```

---

## Task 4: Update `ssk_get_control` to return clauses and audit evidence

**Files:**
- Modify: `mcp-server/tools/ssk.py` (two functions)

- [ ] **Step 1: Replace `ssk_get_control` in `ssk.py`**

Replace the `ssk_get_control` function (lines 126–144 in original):

```python
def ssk_get_control(control_id: str) -> str:
    with get_connection() as conn:
        control = conn.execute(
            "SELECT * FROM ssk_controls WHERE control_id = ?", (control_id,)
        ).fetchone()
        if control is None:
            return json.dumps({"error": f"control '{control_id}' not found"})
        clauses = conn.execute(
            "SELECT clause_id, group_name, sequence, clause_text "
            "FROM ssk_clauses WHERE control_id = ? ORDER BY sequence",
            (control_id,),
        ).fetchall()
        audit_evidence_items = conn.execute(
            "SELECT sequence, item_text "
            "FROM ssk_audit_evidence_items WHERE control_id = ? ORDER BY sequence",
            (control_id,),
        ).fetchall()

    payload = dict(control)
    if payload.get("status_descriptions"):
        payload["status_descriptions"] = json.loads(payload["status_descriptions"])
    payload["clauses"] = [dict(c) for c in clauses]
    payload["audit_evidence_items"] = [dict(e) for e in audit_evidence_items]
    return json.dumps(payload, indent=2)
```

- [ ] **Step 2: Update `ssk_import_catalog` response fields in `ssk.py`**

Replace the `response.update(...)` block inside `ssk_import_catalog` (after `load_result = load_catalog(parsed)`):

```python
    load_result = load_catalog(parsed)
    response.update({
        "written_controls": load_result["written_controls"],
        "written_actions": load_result.get("written_clauses", 0),
        "written_clauses": load_result.get("written_clauses", 0),
        "written_evidence_items": load_result.get("written_evidence_items", 0),
        "history_moved": load_result["history_moved"],
    })
```

Also add `"written_clauses": 0` and `"written_evidence_items": 0` to the initial `response` dict (so dry_run responses include these keys):

```python
    response: dict = {
        "dry_run": dry_run,
        "parsed_controls": len(parsed["controls"]),
        "parse_failures": parsed["parse_failures"],
        "warnings": parsed["warnings"],
        "intermediate_json_path": str(intermediate_path),
        "written_controls": 0,
        "written_actions": 0,
        "written_clauses": 0,
        "written_evidence_items": 0,
        "history_moved": 0,
    }
```

- [ ] **Step 3: Run existing ssk tests to check nothing obviously broken**

```
python -m pytest tests/test_ssk_loader.py tests/test_db.py tests/test_ssk_parser.py -v
```

Expected: all PASS (test_ssk.py not yet updated — skip for now)

- [ ] **Step 4: Commit**

```
git add mcp-server/tools/ssk.py
git commit -m "feat(ssk): ssk_get_control returns clauses and audit_evidence_items; import reports written_clauses"
```

---

## Task 5: Update integration tests

**Files:**
- Modify: `mcp-server/tests/test_ssk.py`

The MCNA fixture helper replaces `_build_minimal_docx`. The docx must have exactly 1 clause for the `test_ssk_import_catalog_commit_writes_db` assertion (`written_actions == 1`).

- [ ] **Step 1: Replace `_build_minimal_docx` and `_seed_two_controls` in `test_ssk.py`**

Replace the `_build_minimal_docx` function and `_seed_two_controls` function:

```python
def _build_minimal_docx(tmp_path):
    """Single control, 1 clause — used for basic import tests."""
    path = tmp_path / "minimal.docx"
    doc = Document()
    doc.add_heading("MCNA Cyber Security Standards", level=1)
    doc.add_heading(
        "04-1: Sample controlSSK Group 04: Human Resources StandardsNOF MCNA...", level=1
    )
    for key, val in [
        ("Effective Date", "2026-05-15"),
        ("Review Date", "2027-05-15"),
        ("Approver", "CFO / Executive Sponsor"),
    ]:
        doc.add_paragraph(key)
        doc.add_paragraph(val)
    doc.add_heading("1. Purpose", level=3)
    doc.add_paragraph("Overview text.")
    doc.add_heading("4. Standards", level=3)
    doc.add_paragraph("The obligations below apply to MCNA.")
    doc.add_heading("Governance", level=4)
    doc.add_paragraph("04-1.1Action one.")
    doc.add_heading("6. Review & Compliance", level=3)
    doc.add_heading("Cadence", level=4)
    doc.add_paragraph("Status text.")
    doc.add_heading("Reviewer", level=4)
    doc.add_paragraph("IT-MIS Director.")
    doc.add_heading("Audit evidence", level=4)
    p = doc.add_paragraph("Audit evidence item.")
    p.style = doc.styles["List Paragraph"]
    doc.add_heading("7. Risks of Non-compliance", level=3)
    doc.add_paragraph("Risk text.")
    doc.save(path)
    return path


def _seed_two_controls(db, tmp_path):
    path = tmp_path / "two.docx"
    doc = Document()
    doc.add_heading("MCNA Cyber Security Standards", level=1)
    # Control 04-1
    doc.add_heading(
        "04-1: HR controlSSK Group 04: Human Resources StandardsNOF MCNA...", level=1
    )
    for key, val in [("Effective Date", "2026-05-15"), ("Review Date", "2027-05-15"),
                     ("Approver", "CFO / Executive Sponsor")]:
        doc.add_paragraph(key)
        doc.add_paragraph(val)
    doc.add_heading("1. Purpose", level=3)
    doc.add_paragraph("HR overview.")
    doc.add_heading("4. Standards", level=3)
    doc.add_paragraph("The obligations below apply to MCNA.")
    doc.add_heading("G", level=4)
    doc.add_paragraph("04-1.1HR action.")
    doc.add_heading("6. Review & Compliance", level=3)
    doc.add_heading("Cadence", level=4)
    doc.add_paragraph("HR status.")
    doc.add_heading("Reviewer", level=4)
    doc.add_paragraph("IT-MIS Director.")
    doc.add_heading("Audit evidence", level=4)
    p = doc.add_paragraph("HR evidence.")
    p.style = doc.styles["List Paragraph"]
    doc.add_heading("7. Risks of Non-compliance", level=3)
    doc.add_paragraph("HR risk.")
    # Control 06-3
    doc.add_heading(
        "06-3: Asset controlSSK Group 06: Asset Management StandardsNOF MCNA...", level=1
    )
    for key, val in [("Effective Date", "2026-05-15"), ("Review Date", "2027-05-15"),
                     ("Approver", "CFO / Executive Sponsor")]:
        doc.add_paragraph(key)
        doc.add_paragraph(val)
    doc.add_heading("1. Purpose", level=3)
    doc.add_paragraph("Asset overview.")
    doc.add_heading("4. Standards", level=3)
    doc.add_paragraph("The obligations below apply to MCNA.")
    doc.add_heading("G", level=4)
    doc.add_paragraph("06-3.1Asset clause one.")
    doc.add_paragraph("06-3.2Asset clause two.")
    doc.add_heading("6. Review & Compliance", level=3)
    doc.add_heading("Cadence", level=4)
    doc.add_paragraph("Asset status.")
    doc.add_heading("Reviewer", level=4)
    doc.add_paragraph("IT-MIS Director.")
    doc.add_heading("Audit evidence", level=4)
    p = doc.add_paragraph("Asset evidence.")
    p.style = doc.styles["List Paragraph"]
    doc.add_heading("7. Risks of Non-compliance", level=3)
    doc.add_paragraph("Asset risk.")
    doc.save(path)
    ssk_import_catalog(str(path), version="seed", dry_run=False,
                       intermediate_dir=str(tmp_path / "i"))
```

- [ ] **Step 2: Update `test_ssk_get_control_includes_recommended_actions`**

Rename and rewrite the test (it no longer tests recommended_actions):

```python
def test_ssk_get_control_includes_clauses(db, tmp_path):
    _seed_two_controls(db, tmp_path)
    result = json.loads(ssk_get_control("06-3"))
    assert result["control_id"] == "06-3"
    assert result["title"] == "Asset control"
    assert len(result["clauses"]) == 2
    assert result["clauses"][0]["clause_text"] == "Asset clause one."
    assert result["clauses"][0]["clause_id"] == "06-3.1"
    assert len(result["audit_evidence_items"]) == 1
    assert result["audit_evidence_items"][0]["item_text"] == "Asset evidence."
```

- [ ] **Step 3: Update `test_ssk_import_catalog_commit_writes_db`**

The single-control minimal fixture has 1 clause. Update the written_actions assertion:

```python
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
    assert result["written_clauses"] == 1
    assert result["written_evidence_items"] == 1

    with get_connection() as conn:
        rows = conn.execute("SELECT COUNT(*) AS c FROM ssk_controls").fetchone()
    assert rows["c"] == 1
```

- [ ] **Step 4: Run the full test suite**

```
python -m pytest tests/ -v
```

Expected: all PASS

- [ ] **Step 5: Commit**

```
git add mcp-server/tests/test_ssk.py
git commit -m "test(ssk): update integration fixtures and assertions for MCNA consolidated parser"
```

---

## Task 6: Validate against the real consolidated file

This task is manual verification — no code changes, no commit.

- [ ] **Step 1: Run dry-run import against the real file**

From `mcp-server/`:

```python
import json
from tools.ssk import ssk_import_catalog

result = json.loads(ssk_import_catalog(
    docx_path=r"C:\Users\dlafferty.MCNA\OneDrive - NOF\DL OneDrive\OneDrive - NOF\Documents - Gov Sec\02_Policy_and_Standards\IT-STD-SSK-CONSOLIDATED_MCNA_Consolidated_Cybersecurity_Standatrds.docx",
    version="2026-01-01",
    dry_run=True,
))
print(f"Parsed controls: {result['parsed_controls']}")
print(f"Parse failures: {len(result['parse_failures'])}")
for f in result['parse_failures']:
    print(f"  FAIL {f['control_id']}: {f['reason']}")
```

Run as:
```
python -c "exec(open('_validate.py').read())"
```
(Write the above snippet to a temp `_validate.py`, run, then delete it.)

Expected:
- `parsed_controls == 75`
- `parse_failures == []` (or investigate any failures before proceeding)

- [ ] **Step 2: If failures exist, investigate and patch**

Check the intermediate JSON (`mcp-server/kb/catalog-imports/2026-01-01.json`) for the failing control. Compare its structure in the real docx against the parser logic. Common causes:
- Section heading has unexpected text (e.g., "1. Purpose " with trailing space) → add `.strip()` where needed
- A control is missing a required section → confirm in Word and add a `warnings` entry instead of failing

- [ ] **Step 3: Run the real import (commit to DB)**

Once dry-run shows 75 controls, 0 failures:

```python
result = json.loads(ssk_import_catalog(
    docx_path=r"C:\Users\dlafferty.MCNA\OneDrive - NOF\DL OneDrive\OneDrive - NOF\Documents - Gov Sec\02_Policy_and_Standards\IT-STD-SSK-CONSOLIDATED_MCNA_Consolidated_Cybersecurity_Standatrds.docx",
    version="2026-01-01",
    dry_run=False,
))
print(json.dumps(result, indent=2))
```

Expected output (approximately):
```json
{
  "dry_run": false,
  "parsed_controls": 75,
  "parse_failures": [],
  "written_controls": 75,
  "written_clauses": 693,
  "written_evidence_items": ~300,
  "history_moved": 75
}
```

- [ ] **Step 4: Spot-check the DB**

```python
import sqlite3
db = r"mcp-server\kb\mcna_amc.db"
conn = sqlite3.connect(db)
print("ssk_controls:", conn.execute("SELECT COUNT(*) FROM ssk_controls").fetchone()[0])
print("ssk_clauses:", conn.execute("SELECT COUNT(*) FROM ssk_clauses").fetchone()[0])
print("ssk_audit_evidence_items:", conn.execute("SELECT COUNT(*) FROM ssk_audit_evidence_items").fetchone()[0])
# Check a specific control
import json
row = conn.execute("SELECT * FROM ssk_controls WHERE control_id='01-1'").fetchone()
cols = [d[0] for d in conn.execute("PRAGMA table_info(ssk_controls)").fetchall()]
print(dict(zip(cols, row)))
conn.close()
```

Expected: `ssk_controls = 75`, `ssk_clauses ≈ 693`, evidence items populated.

- [ ] **Step 5: Update SOURCE.md**

Update `mcp-server` is not the skill location — update `C:\Users\dlafferty.MCNA\.claude\skills\mcna-ssk-reference\scripts\SOURCE.md`:

Change "Last skill rebuild" line to today's date and update the KB import note.

---

## Self-Review

**Spec coverage:**
- ✅ New heading regex handles `NN-N: Title...SSK Group...` format
- ✅ Metadata table parsing: effective_date, review_date, approver
- ✅ Section 1 → overview
- ✅ Section 4 → clauses with clause_id, group_name, sequence, text
- ✅ Section 6 → cadence, reviewer, audit_evidence_items
- ✅ Section 7 → insufficient_measures_risks
- ✅ ssk_clauses table (new)
- ✅ ssk_audit_evidence_items table (new)
- ✅ ssk_controls: 5 new columns (effective_date, review_date, approver, cadence, reviewer)
- ✅ ssk_controls_history: same 5 new columns (via migration)
- ✅ Loader archives old data to history on version bump (including new columns)
- ✅ ssk_get_control returns clauses + audit_evidence_items
- ✅ ssk_import_catalog response includes written_clauses + written_evidence_items
- ✅ Backward compat: written_actions key still returned (= written_clauses)
- ✅ Existing operational data (ssk_control_status, ssk_evidence, ssk_reviews) untouched
- ✅ All tests updated; old Secure SketCH format tests removed
- ✅ Real-file dry-run validation step

**Type consistency:**
- `parse_catalog` returns `controls[].clauses[].{clause_id, group_name, sequence, clause_text}` — matches loader INSERT columns exactly
- `parse_catalog` returns `controls[].audit_evidence_items[].{sequence, item_text}` — matches loader INSERT columns exactly
- `load_catalog` returns `written_clauses` — matches `ssk.py` key access

**No placeholders:** All code steps contain complete, runnable code.
