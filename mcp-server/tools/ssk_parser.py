import re
from pathlib import Path
from docx import Document


class CatalogSourceError(Exception):
    """Raised when the source .docx is missing or unreadable."""


# Matches MCNA consolidated heading: "01-1: Title textSSK Group 01: ..."
# SSK Group suffix is optional — some controls (e.g. 03-1) lack it in the heading paragraph
_CONTROL_HEADING_RE = re.compile(r'^(\d{2}-\d+):\s+(.+?)(?=SSK Group|$)')
# Extracts category name from heading suffix: "SSK Group 01: Category NameNOF MCNA..."
_CATEGORY_RE = re.compile(r'SSK Group \d+:\s+(.+?)(?=NOF MCNA|$)')
# Splits clause ID from text: "01-1.1Some clause text" -> ("01-1.1", "Some clause text")
_CLAUSE_RE = re.compile(r'^(\d{2}-\d+\.\d+)\s*(.*)')
# Extracts heading level from style name: "Heading 1" -> 1, "Heading3" -> 3
_HEADING_LEVEL_RE = re.compile(r'(?i)heading\s*(\d)')

_METADATA_KEYS = {
    "Effective Date": "effective_date",
    "Review Date": "review_date",
    "Approver": "approver",
}

# Map Heading3 text -> parser mode (keys are lowercase for case-insensitive lookup)
_SECTION_MAP = {
    "1. purpose": "overview",
    "4. standards": "clauses",
    "6. review & compliance": "review",
    "7. risks of non-compliance": "risks",
}

# Map Heading4 text (inside "review" mode) -> review sub-field (keys are lowercase, no trailing colon)
_REVIEW_SUBSECTIONS = {
    "cadence": "cadence",
    "reviewer": "reviewer",
    "audit evidence": "audit_evidence",
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

        # -- Heading 1: potential control boundary ----------------------------
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
            # else: cover page or unrecognised H1 -- skip
            continue

        if current is None:
            continue

        # -- Heading 3: section switch ----------------------------------------
        if level == 3:
            mode = _SECTION_MAP.get(text.lower(), "skip")
            review_sub = None
            clause_group = None
            continue

        # -- Heading 4: subsection (clause group name or review sub-field) ----
        if level == 4:
            if mode == "clauses":
                clause_group = text
            elif mode == "review":
                review_sub = _REVIEW_SUBSECTIONS.get(text.lower().rstrip(":").strip())
            continue

        # -- Normal / ListParagraph: content ----------------------------------
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
            elif review_sub == "audit_evidence":
                current["audit_evidence_items"].append({
                    "sequence": len(current["audit_evidence_items"]),
                    "item_text": text,
                })

        elif mode == "risks":
            current["insufficient_measures_risks"] = (
                current["insufficient_measures_risks"] + " " + text
            ).strip()

    _commit()

    # Alias cadence -> status_description for loader backward compatibility
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
