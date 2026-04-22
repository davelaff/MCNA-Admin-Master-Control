import json
import re
import sqlite3
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import requests

from auth import get_token
from db import get_connection
from graph import graph_get
from tools import ssk_common
from tools.ssk_common import (
    EVIDENCE_TYPES,
    SOURCE_KINDS,
    UnknownControlError,
    append_activity,
    json_error,
    json_ok,
    require_control,
)
from tools.ssk_control_map import canonical_control_id


_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _normalize_control_id(control_id: str) -> str:
    return canonical_control_id(control_id) or control_id


def _parse_metadata(source_metadata: dict | None) -> str | None:
    if source_metadata is None:
        return None
    return json.dumps(source_metadata, separators=(",", ":"), sort_keys=True)


def _compute_expires_at(produced_at: str, validity_window_days: int | None) -> str | None:
    if validity_window_days is None:
        return None
    return (
        datetime.fromisoformat(produced_at) + timedelta(days=validity_window_days)
    ).isoformat()


def _row_to_payload(row) -> dict:
    payload = dict(row)
    if payload.get("source_metadata"):
        payload["source_metadata"] = json.loads(payload["source_metadata"])
    return payload


def _validate_link_inputs(evidence_type: str, source_kind: str) -> None:
    if evidence_type not in EVIDENCE_TYPES:
        raise ValueError(f"unsupported evidence_type '{evidence_type}'")
    if source_kind not in SOURCE_KINDS:
        raise ValueError(f"unsupported source_kind '{source_kind}'")


def ssk_link_evidence(
    control_id: str,
    evidence_type: str,
    title: str | None,
    source_kind: str,
    source_pointer: str,
    source_metadata: dict | None = None,
    validity_window_days: int | None = None,
    recorded_by: str | None = None,
    notes: str | None = None,
) -> str:
    normalized_control_id = _normalize_control_id(control_id)
    evidence_id = str(uuid.uuid4())
    produced_at = ssk_common.utc_now()
    expires_at = _compute_expires_at(produced_at, validity_window_days)
    try:
        _validate_link_inputs(evidence_type, source_kind)
        with get_connection() as conn:
            require_control(conn, normalized_control_id)
            conn.execute(
                """
                INSERT INTO ssk_evidence
                    (evidence_id, control_id, evidence_type, title, source_kind, source_pointer,
                     source_metadata, produced_at, validity_window_days, expires_at,
                     verification_status, recorded_by, notes)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    evidence_id,
                    normalized_control_id,
                    evidence_type,
                    title,
                    source_kind,
                    source_pointer,
                    _parse_metadata(source_metadata),
                    produced_at,
                    validity_window_days,
                    expires_at,
                    "unverified",
                    recorded_by,
                    notes,
                ),
            )
            row = conn.execute(
                "SELECT * FROM ssk_evidence WHERE evidence_id = ?",
                (evidence_id,),
            ).fetchone()
        append_activity(
            "ssk_link_evidence",
            "success",
            {
                "control_id": normalized_control_id,
                "evidence_id": evidence_id,
                "source_kind": source_kind,
            },
            entity_id=evidence_id,
        )
        return json_ok(_row_to_payload(row))
    except UnknownControlError as exc:
        append_activity(
            "ssk_link_evidence",
            "error",
            {"control_id": normalized_control_id, "error_type": "UnknownControlError"},
        )
        return json_error(str(exc), "UnknownControlError")
    except ValueError as exc:
        append_activity(
            "ssk_link_evidence",
            "error",
            {"control_id": normalized_control_id, "error_type": "ValidationError"},
        )
        return json_error(str(exc), "ValidationError")


def ssk_list_evidence(
    control_id: str,
    type: str | None = None,
    active_only: bool = True,
) -> str:
    normalized_control_id = _normalize_control_id(control_id)
    clauses = ["control_id = ?"]
    params: list[object] = [normalized_control_id]
    if type is not None:
        clauses.append("evidence_type = ?")
        params.append(type)
    if active_only:
        clauses.append("(expires_at IS NULL OR expires_at >= ?)")
        params.append(ssk_common.utc_now())
    with get_connection() as conn:
        rows = conn.execute(
            f"SELECT * FROM ssk_evidence WHERE {' AND '.join(clauses)} ORDER BY produced_at DESC",
            params,
        ).fetchall()
    return json_ok([_row_to_payload(row) for row in rows])


def ssk_evidence_expiring(days_ahead: int = 30) -> str:
    now = datetime.fromisoformat(ssk_common.utc_now())
    cutoff = (now + timedelta(days=days_ahead)).isoformat()
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT * FROM ssk_evidence
            WHERE expires_at IS NOT NULL
              AND expires_at >= ?
              AND expires_at <= ?
            ORDER BY expires_at, control_id
            """,
            (now.isoformat(), cutoff),
        ).fetchall()
    return json_ok([_row_to_payload(row) for row in rows])


def _verify_local_file(source_pointer: str, source_metadata: dict | None) -> tuple[bool, dict]:
    path = Path(source_pointer)
    return path.exists(), {"path": str(path)}


def _verify_url(source_pointer: str, source_metadata: dict | None) -> tuple[bool, dict]:
    response = requests.head(source_pointer, allow_redirects=True, timeout=30)
    method = "HEAD"
    if response.status_code == 405:
        response = requests.get(source_pointer, allow_redirects=True, timeout=30)
        method = "GET"
    ok = response.ok
    return ok, {"status_code": response.status_code, "method": method}


def _verify_sharepoint(source_pointer: str, source_metadata: dict | None) -> tuple[bool, dict]:
    metadata = source_metadata or {}
    missing = [key for key in ("site_id", "drive_id", "item_id") if not metadata.get(key)]
    if missing:
        return False, {"missing_metadata": missing}
    token = get_token()
    path = (
        f"/sites/{metadata['site_id']}/drives/{metadata['drive_id']}/items/{metadata['item_id']}"
    )
    data = graph_get(path, token)
    return True, {"graph_id": data.get("id")}


def _verify_kb_row(source_pointer: str, source_metadata: dict | None) -> tuple[bool, dict]:
    parts = source_pointer.split(":", 2)
    if len(parts) != 3:
        return False, {"reason": "invalid_pointer"}
    table_name, key_column, key_value = parts
    if not _IDENTIFIER_RE.fullmatch(table_name) or not _IDENTIFIER_RE.fullmatch(key_column):
        return False, {"reason": "invalid_identifier"}
    with get_connection() as conn:
        row = conn.execute(
            f'SELECT 1 FROM "{table_name}" WHERE "{key_column}" = ? LIMIT 1',
            (key_value,),
        ).fetchone()
    return row is not None, {"table_name": table_name, "key_column": key_column}


def _verify_scan_run(source_pointer: str, source_metadata: dict | None) -> tuple[bool, dict]:
    parts = source_pointer.split(":", 1)
    if len(parts) != 2 or parts[0] != "activity_log":
        return False, {"reason": "invalid_pointer"}
    run_id = parts[1]
    with get_connection() as conn:
        row = conn.execute(
            "SELECT 1 FROM activity_log WHERE run_id = ? LIMIT 1",
            (run_id,),
        ).fetchone()
    return row is not None, {"run_id": run_id}


def _verify_pointer(source_kind: str, source_pointer: str, source_metadata: dict | None) -> tuple[bool, dict]:
    if source_kind == "local_file":
        return _verify_local_file(source_pointer, source_metadata)
    if source_kind == "url":
        return _verify_url(source_pointer, source_metadata)
    if source_kind == "sharepoint":
        return _verify_sharepoint(source_pointer, source_metadata)
    if source_kind == "kb_row":
        return _verify_kb_row(source_pointer, source_metadata)
    if source_kind == "scan_run":
        return _verify_scan_run(source_pointer, source_metadata)
    return False, {"reason": "unsupported_source_kind"}


def _upsert_pointer_broken_finding(
    conn: sqlite3.Connection,
    evidence_row,
    checked_at: str,
    verification_detail: dict,
) -> None:
    finding_id = str(
        uuid.uuid5(
            uuid.NAMESPACE_DNS,
            f"ssk.pointer_broken.{evidence_row['control_id']}.{evidence_row['evidence_id']}",
        )
    )
    existing = conn.execute(
        "SELECT status, first_seen FROM findings WHERE finding_id = ?",
        (finding_id,),
    ).fetchone()
    first_seen = existing["first_seen"] if existing else checked_at
    notes = json.dumps(verification_detail, separators=(",", ":"), sort_keys=True)
    conn.execute(
        """
        INSERT INTO findings
            (finding_id, domain, object_type, object_id, object_name, finding_type, severity,
             securesketch_control, recommended_action, evidence_pointer, status,
             first_seen, last_seen, notes)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(finding_id) DO UPDATE SET
            object_name=excluded.object_name,
            recommended_action=excluded.recommended_action,
            evidence_pointer=excluded.evidence_pointer,
            status='open',
            last_seen=excluded.last_seen,
            notes=excluded.notes
        """,
        (
            finding_id,
            "ssk",
            "ssk_evidence",
            evidence_row["evidence_id"],
            evidence_row["title"] or evidence_row["source_pointer"],
            "pointer_broken",
            "Medium",
            evidence_row["control_id"],
            "Restore or replace the evidence pointer and re-run verification.",
            evidence_row["evidence_id"],
            "open",
            first_seen,
            checked_at,
            notes,
        ),
    )


def ssk_verify_pointers(control_id: str | None = None) -> str:
    normalized_control_id = _normalize_control_id(control_id) if control_id else None
    checked_at = ssk_common.utc_now()
    clauses: list[str] = []
    params: list[object] = []
    if normalized_control_id is not None:
        clauses.append("control_id = ?")
        params.append(normalized_control_id)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""

    checked = 0
    resolved = 0
    broken = 0

    try:
        with get_connection() as conn:
            rows = conn.execute(
                f"SELECT * FROM ssk_evidence {where} ORDER BY produced_at, evidence_id",
                params,
            ).fetchall()
            if normalized_control_id is not None:
                require_control(conn, normalized_control_id)

            for row in rows:
                metadata = json.loads(row["source_metadata"]) if row["source_metadata"] else None
                try:
                    is_valid, detail = _verify_pointer(
                        row["source_kind"], row["source_pointer"], metadata
                    )
                except Exception as exc:
                    is_valid = False
                    detail = {
                        "error": str(exc),
                        "error_type": type(exc).__name__,
                    }
                checked += 1
                if is_valid:
                    conn.execute(
                        """
                        UPDATE ssk_evidence
                        SET verification_status = 'resolved',
                            verification_checked_at = ?
                        WHERE evidence_id = ?
                        """,
                        (checked_at, row["evidence_id"]),
                    )
                    resolved += 1
                    continue

                conn.execute(
                    """
                    UPDATE ssk_evidence
                    SET verification_status = 'unresolvable',
                        verification_checked_at = ?
                    WHERE evidence_id = ?
                    """,
                    (checked_at, row["evidence_id"]),
                )
                _upsert_pointer_broken_finding(conn, row, checked_at, detail)
                broken += 1
    except UnknownControlError as exc:
        append_activity(
            "ssk_verify_pointers",
            "error",
            {"control_id": normalized_control_id, "error_type": "UnknownControlError"},
            entity_id=normalized_control_id,
        )
        return json_error(str(exc), "UnknownControlError")

    append_activity(
        "ssk_verify_pointers",
        "success",
        {
            "control_id": normalized_control_id,
            "checked": checked,
            "resolved": resolved,
            "broken": broken,
        },
        entity_id=normalized_control_id,
    )
    return json_ok(
        {
            "control_id": normalized_control_id,
            "checked": checked,
            "resolved": resolved,
            "broken": broken,
            "verification_checked_at": checked_at,
        }
    )
