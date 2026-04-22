import re
from pathlib import Path
from docx import Document

CONTROL_ID_RE = re.compile(r"^(\d{2}-\d+)\s+(.+)$")
CATEGORY_HEADING_RE = re.compile(r"^(\d{2})\s+(.+)$")
IGNORED_HEADINGS = {"Introduction", "Secure SketCH Guidelines"}
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

        style_name = (para.style.name if para.style else "") or ""
        if "Heading" in style_name and text not in IGNORED_HEADINGS:
            cat_m = CATEGORY_HEADING_RE.match(text)
            if cat_m:
                categories[cat_m.group(1)] = cat_m.group(2).strip()
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
