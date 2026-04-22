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
