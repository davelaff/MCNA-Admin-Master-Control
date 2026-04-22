import json
from pathlib import Path
from docx import Document
from tools.ssk import ssk_import_catalog, ssk_list_controls, ssk_get_control, ssk_status, ssk_status_all, ssk_gaps


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
