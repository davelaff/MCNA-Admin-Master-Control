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
