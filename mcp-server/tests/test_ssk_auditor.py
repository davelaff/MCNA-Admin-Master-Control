import json
from pathlib import Path

from db import get_connection
from tools.ssk_auditor import ssk_auditor_package, ssk_run_control_check


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


def _seed_evidence(
    control_id: str,
    evidence_id: str = "ev1",
    evidence_type: str = "scan_snapshot",
    source_kind: str = "scan_run",
    source_pointer: str = "activity_log:run-1",
    status: str = "resolved",
) -> None:
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
                evidence_type,
                "Evidence",
                source_kind,
                source_pointer,
                "2026-04-25T00:00:00+00:00",
                status,
            ),
        )


def _seed_review(control_id: str) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO ssk_reviews
                (review_id, control_id, reviewer, reviewed_at, outcome, quality_flag)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "review-1",
                control_id,
                "Dave Lafferty",
                "2026-04-25T00:00:00+00:00",
                "ok",
                "ok",
            ),
        )
        conn.execute(
            """
            UPDATE ssk_control_status
            SET current_maturity = ?, last_reviewed_at = ?, next_review_due = ?
            WHERE control_id = ?
            """,
            (
                "regularly_reviewed",
                "2026-04-25T00:00:00+00:00",
                "2026-07-24T00:00:00+00:00",
                control_id,
            ),
        )


def _seed_open_finding(control_id: str, finding_type: str = "test_finding") -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO findings
                (finding_id, domain, object_type, object_id, object_name, finding_type,
                 severity, securesketch_control, recommended_action, status, first_seen, last_seen)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"finding-{control_id}-{finding_type}",
                "test",
                "tenant",
                "tenant",
                "Tenant",
                finding_type,
                "High",
                control_id,
                "Investigate",
                "open",
                "2026-04-25T00:00:00+00:00",
                "2026-04-25T00:00:00+00:00",
            ),
        )


def test_run_control_check_rejects_unknown_control(db, tmp_path):
    result = json.loads(ssk_run_control_check("99-9", output_dir=str(tmp_path)))

    assert result["error_type"] == "UnknownControlError"


def test_run_control_check_creates_reports_and_evidence(db, tmp_path, monkeypatch):
    _seed_control("06-3", "License control")

    def fake_resolver(control_id):
        assert control_id == "06-3"
        return [
            (
                "license_scan_skus",
                lambda: json.dumps({"scanned": 2, "findings": 0}),
            )
        ]

    import tools.ssk_auditor as ssk_auditor_mod

    monkeypatch.setattr(ssk_auditor_mod, "_resolve_check_functions", fake_resolver)

    result = json.loads(ssk_run_control_check("06-3", output_dir=str(tmp_path)))

    assert result["status"] == "pass"
    assert result["control_id"] == "06-3"
    assert result["evidence_id"] is not None
    assert Path(result["output_dir"]).exists()
    assert (Path(result["output_dir"]) / "check.md").exists()
    assert (Path(result["output_dir"]) / "result.json").exists()

    with get_connection() as conn:
        evidence = conn.execute(
            "SELECT * FROM ssk_evidence WHERE evidence_id = ?",
            (result["evidence_id"],),
        ).fetchone()

    assert evidence["control_id"] == "06-3"
    assert evidence["evidence_type"] == "control_check"
    assert evidence["source_kind"] == "control_check"
    assert evidence["verification_status"] == "resolved"


def test_run_control_check_manual_control_returns_manual_required(db, tmp_path):
    _seed_control("01-1", "Manual control")

    result = json.loads(ssk_run_control_check("01-1", output_dir=str(tmp_path)))

    assert result["status"] == "manual_required"
    assert result["evidence_id"] is None
    assert (Path(result["output_dir"]) / "result.json").exists()
    with get_connection() as conn:
        evidence_count = conn.execute(
            "SELECT COUNT(*) AS c FROM ssk_evidence WHERE control_id = '01-1'"
        ).fetchone()["c"]
    assert evidence_count == 0


def test_auditor_package_writes_expected_files(db, tmp_path):
    _seed_control("06-3", "License control")
    _seed_evidence("06-3")
    _seed_review("06-3")
    _seed_open_finding("06-3")

    result = json.loads(
        ssk_auditor_package(
            quarter="2026-Q2",
            output_dir=str(tmp_path / "pkg"),
        )
    )

    out_dir = Path(result["output_dir"])
    assert result["quarter"] == "2026-Q2"
    assert (out_dir / "auditor-binder.pdf").exists()
    assert (out_dir / "index.md").exists()
    assert (out_dir / "index.html").exists()
    assert (out_dir / "manifest.json").exists()
    assert (out_dir / "controls" / "06_3.md").exists()
    assert (out_dir / "controls" / "06_3.html").exists()
    assert (out_dir / "evidence" / "index.json").exists()

    manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["controls"][0]["control_id"] == "06-3"
    assert manifest["controls"][0]["evidence_count"] == 1
    assert manifest["controls"][0]["open_finding_count"] == 1


def test_auditor_package_includes_control_check_evidence(db, tmp_path, monkeypatch):
    _seed_control("06-3", "License control")

    def fake_resolver(control_id):
        return [("license_scan_skus", lambda: json.dumps({"scanned": 1, "findings": 0}))]

    import tools.ssk_auditor as ssk_auditor_mod

    monkeypatch.setattr(ssk_auditor_mod, "_resolve_check_functions", fake_resolver)
    check_result = json.loads(ssk_run_control_check("06-3", output_dir=str(tmp_path / "checks")))

    package_result = json.loads(
        ssk_auditor_package(
            quarter="2026-Q2",
            output_dir=str(tmp_path / "pkg"),
        )
    )

    manifest = json.loads((Path(package_result["output_dir"]) / "manifest.json").read_text(encoding="utf-8"))
    control = manifest["controls"][0]
    assert control["control_id"] == "06-3"
    assert check_result["evidence_id"] in control["evidence_ids"]
    assert any(
        item["source_kind"] == "control_check"
        for item in control["evidence"]
    )


def test_ssk_auditor_tools_registered_in_server():
    import server
    import tools.ssk_auditor as ssk_auditor

    assert server.ssk_auditor_package is ssk_auditor.ssk_auditor_package
    assert server.ssk_run_control_check is ssk_auditor.ssk_run_control_check
