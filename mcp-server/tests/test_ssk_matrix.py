import json
from pathlib import Path

from db import get_connection
from tools.ssk_binder import ssk_coverage
from tools.ssk_control_map import canonical_control_id
from tools.ssk_loader import load_catalog
from tools.ssk_matrix import (
    ssk_backfill_scan_evidence,
    ssk_control_coverage_detail,
    ssk_control_matrix,
    ssk_evidence_gaps,
    ssk_maturity_dashboard,
    ssk_quarterly_packet,
)


def _seed_catalog() -> None:
    catalog_path = (
        Path(__file__).resolve().parent.parent
        / "kb"
        / "catalog-imports"
        / "2026-01-01.json"
    )
    load_catalog(json.loads(catalog_path.read_text(encoding="utf-8")))


def _seed_control(control_id: str, title: str = "Control") -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO ssk_controls
                (control_id, source_version, category, category_name, title, overview,
                 status_descriptions, insufficient_measures_risks, imported_at)
            VALUES (?,?,?,?,?,?,?,?,?)
            """,
            (
                control_id,
                "test",
                control_id.split("-", 1)[0],
                "Test category",
                title,
                "Overview",
                "{}",
                "Risks",
                "2026-01-01T00:00:00+00:00",
            ),
        )
        conn.execute(
            """
            INSERT INTO ssk_control_status (control_id, last_updated)
            VALUES (?, ?)
            """,
            (control_id, "2026-01-01T00:00:00+00:00"),
        )


def _seed_activity(run_id: str, tool_name: str = "license_scan_skus") -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO activity_log (run_id, timestamp, tool_name, domain, outcome, detail)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                "2026-04-25T00:00:00+00:00",
                tool_name,
                "license",
                "success",
                "{}",
            ),
        )


def _seed_evidence(control_id: str, evidence_id: str = "ev1", status: str = "resolved") -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO ssk_evidence
                (evidence_id, control_id, evidence_type, title, source_kind,
                 source_pointer, produced_at, verification_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                evidence_id,
                control_id,
                "scan_snapshot",
                "License scan",
                "scan_run",
                "activity_log:run-1",
                "2026-04-25T00:00:00+00:00",
                status,
            ),
        )


def _seed_open_finding(control_ref: str, finding_type: str = "purview_scope_gap") -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO findings
                (finding_id, domain, object_type, object_id, object_name, finding_type,
                 severity, securesketch_control, recommended_action, status, first_seen, last_seen)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"finding-{finding_type}",
                "purview",
                "tenant",
                "tenant",
                "Tenant",
                finding_type,
                "High",
                control_ref,
                "Grant missing scope.",
                "open",
                "2026-04-25T00:00:00+00:00",
                "2026-04-25T00:00:00+00:00",
            ),
        )


def test_ssk_coverage_counts_all_current_automated_modules(db):
    _seed_catalog()
    result = json.loads(ssk_coverage())
    assert "07-2" in result["automated_controls"]
    assert "06-1" in result["automated_controls"]
    assert "15-3" in result["automated_controls"]
    assert "tools.intune" in result["automated_controls"]["07-2"]
    assert "tools.purview" in result["automated_controls"]["06-1"]
    assert "tools.exo" in result["automated_controls"]["06-1"]
    assert "tools.copilot" in result["automated_controls"]["15-3"]


def test_ssk_coverage_canonicalizes_alias_controls(db):
    _seed_catalog()
    result = json.loads(ssk_coverage())
    canonical = canonical_control_id("EXO-SHARED-ENABLED-01")
    assert canonical == "08-1"
    assert "tools.exo" in result["automated_controls"][canonical]


def test_control_matrix_returns_all_real_catalog_controls(db):
    _seed_catalog()
    result = json.loads(ssk_control_matrix(format="json"))
    assert result["control_count"] == 75
    assert len(result["controls"]) == 75


def test_control_matrix_classifies_resolved_evidence_as_evidenced(db):
    _seed_control("06-3", "License control")
    _seed_activity("run-1")
    _seed_evidence("06-3", status="resolved")

    result = json.loads(ssk_control_coverage_detail("06-3"))

    assert result["audit_status"] == "evidenced"
    assert result["tooling_status"] == "tool_built_evidence_present"
    assert result["evidence_source_type"] == "tenant_scan"
    assert result["evidence_count"] == 1


def test_control_matrix_classifies_tool_built_without_evidence(db):
    _seed_control("07-2", "Endpoint compliance")

    result = json.loads(ssk_control_coverage_detail("07-2"))

    assert result["audit_status"] == "not_evidenced"
    assert result["tooling_status"] == "tool_built_no_evidence"
    assert result["missing_evidence_action"] == "Run mapped scanner and link scan_snapshot evidence."


def test_control_matrix_classifies_manual_required(db):
    _seed_control("01-1", "Manual governance control")

    result = json.loads(ssk_control_coverage_detail("01-1"))

    assert result["audit_status"] == "not_evidenced"
    assert result["tooling_status"] == "manual_required"
    assert result["evidence_source_type"] == "manual_required"


def test_control_matrix_classifies_broken_evidence_as_partial(db):
    _seed_control("06-3", "License control")
    _seed_activity("run-1")
    _seed_evidence("06-3", status="unresolvable")

    result = json.loads(ssk_control_coverage_detail("06-3"))

    assert result["audit_status"] == "partial"
    assert result["tooling_status"] == "tool_built_evidence_present"
    assert "Evidence exists but at least one pointer is not verified." in result["rationale"]


def test_control_matrix_classifies_blocked_scope_finding(db):
    _seed_control("06-1", "Information protection")
    _seed_open_finding("PURVIEW-SCOPE-01", "purview_scope_gap")

    result = json.loads(ssk_control_coverage_detail("06-1"))

    assert result["audit_status"] == "not_evidenced"
    assert result["tooling_status"] == "blocked_by_scope"
    assert "InformationProtectionPolicy.Read.All" in result["missing_evidence_action"]


def test_control_matrix_writes_snapshot_rows_and_activity(db):
    _seed_control("06-3", "License control")

    result = json.loads(ssk_control_matrix(format="json"))

    with get_connection() as conn:
        snapshots = conn.execute(
            "SELECT * FROM ssk_control_coverage_snapshots WHERE run_id = ?",
            (result["run_id"],),
        ).fetchall()
        activity = conn.execute(
            "SELECT * FROM activity_log WHERE run_id = ?",
            (result["run_id"],),
        ).fetchone()

    assert len(snapshots) == 1
    assert snapshots[0]["control_id"] == "06-3"
    assert activity["tool_name"] == "ssk_control_matrix"


def test_control_matrix_exports_markdown_with_totals(tmp_path, db):
    _seed_control("06-3", "License control")
    out = tmp_path / "matrix.md"

    result = json.loads(ssk_control_matrix(output_path=str(out)))

    assert result["output_path"] == str(out)
    text = out.read_text(encoding="utf-8")
    assert "# Secure SketCH Control Coverage Matrix" in text
    assert "Total controls: 1" in text
    assert "| 06-3 | License control |" in text


def test_evidence_gaps_exports_only_non_evidenced_rows(tmp_path, db):
    _seed_control("06-3", "License control")
    _seed_control("01-1", "Manual governance control")
    _seed_activity("run-1")
    _seed_evidence("06-3", status="resolved")
    out = tmp_path / "gaps.md"

    result = json.loads(ssk_evidence_gaps(output_path=str(out)))

    assert result["gap_count"] == 1
    text = out.read_text(encoding="utf-8")
    assert "01-1" in text
    assert "06-3" not in text


def test_backfill_scan_evidence_links_real_activity_runs(db):
    _seed_control("06-3", "License control")
    _seed_activity("run-1", "license_scan_skus")

    result = json.loads(ssk_backfill_scan_evidence(dry_run=False))

    assert result["dry_run"] is False
    assert result["created"] == 1
    with get_connection() as conn:
        evidence = conn.execute(
            "SELECT * FROM ssk_evidence WHERE control_id = '06-3'"
        ).fetchone()
    assert evidence["evidence_type"] == "scan_snapshot"
    assert evidence["source_kind"] == "scan_run"
    assert evidence["source_pointer"] == "activity_log:run-1"
    assert evidence["verification_status"] == "unverified"


def test_backfill_scan_evidence_dry_run_does_not_write(db):
    _seed_control("06-3", "License control")
    _seed_activity("run-1", "license_scan_skus")

    result = json.loads(ssk_backfill_scan_evidence(dry_run=True))

    assert result["dry_run"] is True
    assert result["would_create"] == 1
    with get_connection() as conn:
        count = conn.execute("SELECT COUNT(*) AS c FROM ssk_evidence").fetchone()["c"]
    assert count == 0


def test_backfill_scan_evidence_is_idempotent(db):
    _seed_control("06-3", "License control")
    _seed_activity("run-1", "license_scan_skus")

    first = json.loads(ssk_backfill_scan_evidence(dry_run=False))
    second = json.loads(ssk_backfill_scan_evidence(dry_run=False))

    assert first["created"] == 1
    assert second["created"] == 0
    with get_connection() as conn:
        count = conn.execute("SELECT COUNT(*) AS c FROM ssk_evidence").fetchone()["c"]
    assert count == 1


def test_ssk_matrix_tools_registered_in_server():
    import server
    import tools.ssk_matrix as ssk_matrix

    assert server.ssk_backfill_scan_evidence is ssk_matrix.ssk_backfill_scan_evidence
    assert server.ssk_control_matrix is ssk_matrix.ssk_control_matrix
    assert server.ssk_evidence_gaps is ssk_matrix.ssk_evidence_gaps
    assert server.ssk_control_coverage_detail is ssk_matrix.ssk_control_coverage_detail


# --- ssk_maturity_dashboard tests ---


def test_maturity_dashboard_empty_db(db):
    result = json.loads(ssk_maturity_dashboard())

    assert result["summary"]["total_controls"] == 0
    assert result["summary"]["total_evidenced"] == 0
    assert result["summary"]["total_evidence_gaps"] == 0
    assert result["summary"]["never_reviewed_count"] == 0
    assert result["summary"]["overdue_count"] == 0
    assert result["categories"] == []


def test_maturity_dashboard_groups_controls_by_category(db):
    _seed_control("06-3", "License control")
    _seed_control("08-1", "Access control")

    result = json.loads(ssk_maturity_dashboard())

    category_ids = [c["category"] for c in result["categories"]]
    assert "06" in category_ids
    assert "08" in category_ids
    assert len(result["categories"]) == 2


def test_maturity_dashboard_summary_total_controls(db):
    _seed_control("06-3")
    _seed_control("06-4")
    _seed_control("08-1")

    result = json.loads(ssk_maturity_dashboard())

    assert result["summary"]["total_controls"] == 3
    cat_06 = next(c for c in result["categories"] if c["category"] == "06")
    assert cat_06["control_count"] == 2


def test_maturity_dashboard_evidenced_count(db):
    _seed_control("06-3", "License control")
    _seed_control("08-1", "Access control")
    _seed_activity("run-1")
    _seed_evidence("06-3", status="resolved")

    result = json.loads(ssk_maturity_dashboard())

    assert result["summary"]["total_evidenced"] == 1
    assert result["summary"]["total_evidence_gaps"] == 1
    cat_06 = next(c for c in result["categories"] if c["category"] == "06")
    cat_08 = next(c for c in result["categories"] if c["category"] == "08")
    assert cat_06["evidenced"] == 1
    assert cat_06["evidence_gaps"] == 0
    assert cat_08["evidenced"] == 0
    assert cat_08["evidence_gaps"] == 1


def test_maturity_dashboard_never_reviewed_count(db):
    _seed_control("06-3")
    _seed_control("08-1")

    result = json.loads(ssk_maturity_dashboard())

    assert result["summary"]["never_reviewed_count"] == 2
    assert result["summary"]["overdue_count"] == 0


def test_maturity_dashboard_overdue_count(db):
    _seed_control("06-3")
    with get_connection() as conn:
        conn.execute(
            "UPDATE ssk_control_status SET next_review_due = ?, last_reviewed_at = ? WHERE control_id = ?",
            ("2026-01-01T00:00:00+00:00", "2025-10-01T00:00:00+00:00", "06-3"),
        )

    result = json.loads(ssk_maturity_dashboard())

    assert result["summary"]["overdue_count"] == 1
    assert result["summary"]["never_reviewed_count"] == 0
    cat_06 = next(c for c in result["categories"] if c["category"] == "06")
    assert cat_06["overdue_count"] == 1
    assert cat_06["never_reviewed_count"] == 0


def test_maturity_dashboard_maturity_breakdown(db):
    _seed_control("06-3")
    _seed_control("06-4")
    with get_connection() as conn:
        conn.execute(
            "UPDATE ssk_control_status SET current_maturity = 'regularly_reviewed' WHERE control_id = ?",
            ("06-3",),
        )

    result = json.loads(ssk_maturity_dashboard())

    cat_06 = next(c for c in result["categories"] if c["category"] == "06")
    assert cat_06["maturity_breakdown"].get("regularly_reviewed") == 1
    assert cat_06["maturity_breakdown"].get("not_regularly_reviewed") == 1
    assert result["summary"]["maturity_breakdown"].get("regularly_reviewed") == 1
    assert result["summary"]["maturity_breakdown"].get("not_regularly_reviewed") == 1


def test_maturity_dashboard_registered_in_server():
    import server
    import tools.ssk_matrix as ssk_matrix

    assert server.ssk_maturity_dashboard is ssk_matrix.ssk_maturity_dashboard


# --- ssk_quarterly_packet tests ---


def test_quarterly_packet_writes_markdown_file(tmp_path, db):
    _seed_control("06-3", "License control")
    out = tmp_path / "packet.md"

    result = json.loads(ssk_quarterly_packet(output_path=str(out)))

    assert result["output_path"] == str(out)
    assert out.exists()
    text = out.read_text(encoding="utf-8")
    assert "# MCNA Secure SketCH Quarterly Governance Review" in text


def test_quarterly_packet_includes_summary_table(tmp_path, db):
    _seed_control("06-3", "License control")
    out = tmp_path / "packet.md"

    json.loads(ssk_quarterly_packet(output_path=str(out)))
    text = out.read_text(encoding="utf-8")

    assert "Total controls" in text
    assert "Program Summary" in text


def test_quarterly_packet_review_queue_shows_overdue(tmp_path, db):
    _seed_control("06-3", "License control")
    with get_connection() as conn:
        conn.execute(
            "UPDATE ssk_control_status SET next_review_due = ?, last_reviewed_at = ? WHERE control_id = ?",
            ("2026-01-01T00:00:00+00:00", "2025-10-01T00:00:00+00:00", "06-3"),
        )
    out = tmp_path / "packet.md"

    json.loads(ssk_quarterly_packet(output_path=str(out)))
    text = out.read_text(encoding="utf-8")

    assert "06-3" in text
    assert "overdue" in text


def test_quarterly_packet_review_queue_empty_message(tmp_path, db):
    _seed_control("06-3", "License control")
    with get_connection() as conn:
        conn.execute(
            "UPDATE ssk_control_status SET next_review_due = ? WHERE control_id = ?",
            ("2030-01-01T00:00:00+00:00", "06-3"),
        )
    out = tmp_path / "packet.md"

    json.loads(ssk_quarterly_packet(output_path=str(out)))
    text = out.read_text(encoding="utf-8")

    assert "No controls overdue or never reviewed." in text


def test_quarterly_packet_evidence_gaps_section(tmp_path, db):
    _seed_control("06-3", "License control")
    out = tmp_path / "packet.md"

    json.loads(ssk_quarterly_packet(output_path=str(out)))
    text = out.read_text(encoding="utf-8")

    assert "## Evidence Gaps" in text
    assert "06-3" in text


def test_quarterly_packet_no_gaps_message(tmp_path, db):
    _seed_control("06-3", "License control")
    _seed_activity("run-1")
    _seed_evidence("06-3", status="resolved")
    out = tmp_path / "packet.md"

    json.loads(ssk_quarterly_packet(output_path=str(out)))
    text = out.read_text(encoding="utf-8")

    assert "No evidence gaps." in text


def test_quarterly_packet_recommended_actions_all_good(tmp_path, db):
    _seed_control("06-3", "License control")
    _seed_activity("run-1")
    _seed_evidence("06-3", status="resolved")
    with get_connection() as conn:
        conn.execute(
            "UPDATE ssk_control_status SET next_review_due = ? WHERE control_id = ?",
            ("2030-01-01T00:00:00+00:00", "06-3"),
        )
    out = tmp_path / "packet.md"

    json.loads(ssk_quarterly_packet(output_path=str(out)))
    text = out.read_text(encoding="utf-8")

    assert "Maintain current cadence" in text


def test_quarterly_packet_registered_in_server():
    import server
    import tools.ssk_matrix as ssk_matrix

    assert server.ssk_quarterly_packet is ssk_matrix.ssk_quarterly_packet
