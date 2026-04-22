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
