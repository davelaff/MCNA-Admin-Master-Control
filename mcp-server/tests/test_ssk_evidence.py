import json
from datetime import datetime, timedelta

from db import get_connection
from tools import ssk_common
from tools.ssk_evidence import ssk_link_evidence, ssk_verify_pointers


def _seed_control(control_id: str = "06-3") -> None:
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
                "test-1",
                "06",
                "Assets",
                "Asset control",
                "Overview",
                "{}",
                "Risks",
                "2026-01-01T00:00:00+00:00",
            ),
        )


def test_ssk_link_evidence_persists_row_and_computes_expiry(db, monkeypatch):
    _seed_control()
    produced_at = "2026-04-22T12:00:00+00:00"
    monkeypatch.setattr(ssk_common, "utc_now", lambda: produced_at)

    result = json.loads(
        ssk_link_evidence(
            control_id="06-3",
            evidence_type="policy_link",
            source_kind="local_file",
            source_pointer="C:/evidence/review-cadence.docx",
            validity_window_days=30,
            title="Documented review cadence",
            notes="Seeded from test",
        )
    )

    assert result["control_id"] == "06-3"
    assert result["verification_status"] == "unverified"
    assert result["expires_at"] == (
        datetime.fromisoformat(produced_at) + timedelta(days=30)
    ).isoformat()

    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM ssk_evidence WHERE evidence_id = ?",
            (result["evidence_id"],),
        ).fetchone()
        activity = conn.execute(
            "SELECT tool_name, outcome, entity_id, detail FROM activity_log WHERE entity_id = ?",
            (result["evidence_id"],),
        ).fetchone()

    assert row is not None
    assert row["control_id"] == "06-3"
    assert row["verification_status"] == "unverified"
    assert row["produced_at"] == produced_at
    assert row["expires_at"] == result["expires_at"]
    assert activity is not None
    assert activity["tool_name"] == "ssk_link_evidence"
    assert activity["outcome"] == "success"


def test_ssk_link_evidence_rejects_unknown_control(db):
    result = json.loads(
        ssk_link_evidence(
            control_id="99-9",
            evidence_type="policy_link",
            source_kind="local_file",
            source_pointer="C:/evidence/missing.docx",
            title="Missing control evidence",
        )
    )

    assert result["error_type"] == "UnknownControlError"


def test_ssk_link_evidence_rejects_blank_source_pointer(db):
    _seed_control()

    result = json.loads(
        ssk_link_evidence(
            control_id="06-3",
            evidence_type="policy_link",
            source_kind="local_file",
            source_pointer="   ",
            title="Blank pointer",
        )
    )

    assert result["error_type"] == "ValidationError"


def test_ssk_verify_pointers_closes_pointer_broken_finding_after_recovery(db, tmp_path):
    _seed_control()
    source_path = tmp_path / "evidence.docx"

    link_result = json.loads(
        ssk_link_evidence(
            control_id="06-3",
            evidence_type="policy_link",
            source_kind="local_file",
            source_pointer=str(source_path),
            title="Broken local file",
            notes="Should fail verification",
        )
    )

    assert link_result["verification_status"] == "unverified"

    verify_result = json.loads(ssk_verify_pointers(control_id="06-3"))
    assert verify_result["checked"] == 1
    assert verify_result["broken"] == 1

    with get_connection() as conn:
        evidence = conn.execute(
            "SELECT verification_status, verification_checked_at FROM ssk_evidence WHERE evidence_id = ?",
            (link_result["evidence_id"],),
        ).fetchone()
        finding = conn.execute(
            "SELECT finding_id, finding_type, status, evidence_pointer, securesketch_control "
            "FROM findings WHERE object_id = ?",
            (link_result["evidence_id"],),
        ).fetchone()

    assert evidence["verification_status"] == "unresolvable"
    assert evidence["verification_checked_at"] is not None
    assert finding is not None
    assert finding["finding_type"] == "pointer_broken"
    assert finding["status"] == "open"
    assert finding["evidence_pointer"] == link_result["evidence_id"]
    assert finding["securesketch_control"] == "06-3"

    source_path.write_text("recovered", encoding="utf-8")

    verify_again_result = json.loads(ssk_verify_pointers(control_id="06-3"))
    assert verify_again_result["checked"] == 1
    assert verify_again_result["resolved"] == 1
    assert verify_again_result["broken"] == 0

    with get_connection() as conn:
        recovered_evidence = conn.execute(
            "SELECT verification_status, verification_checked_at FROM ssk_evidence WHERE evidence_id = ?",
            (link_result["evidence_id"],),
        ).fetchone()
        recovered_finding = conn.execute(
            "SELECT status FROM findings WHERE finding_id = ?",
            (finding["finding_id"],),
        ).fetchone()

    assert recovered_evidence["verification_status"] == "resolved"
    assert recovered_evidence["verification_checked_at"] is not None
    assert recovered_finding is not None
    assert recovered_finding["status"] != "open"
