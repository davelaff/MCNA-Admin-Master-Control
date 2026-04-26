"""Secure SketCH Phase 4A coverage matrix and evidence gap reports."""

import importlib
import json
import uuid
from pathlib import Path

from db import get_connection
from tools.ssk_common import append_activity, json_error, json_ok, utc_now
from tools.ssk_control_map import canonical_control_id


_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_COVERAGE_REPORT_DIR = _REPO_ROOT / "reports" / "ssk-control-coverage"
_GAP_REPORT_DIR = _REPO_ROOT / "reports" / "ssk-evidence-gaps"

_AUTOMATED_MODULES = [
    "tools.entra",
    "tools.ca",
    "tools.pp",
    "tools.pim",
    "tools.license",
    "tools.sharing",
    "tools.intune",
    "tools.purview",
    "tools.exo",
    "tools.copilot",
]

_BLOCKED_SCOPE_ACTIONS = {
    "purview_scope_gap": "Grant InformationProtectionPolicy.Read.All and rerun the Purview scan.",
    "copilot_scope_gap": "Grant Microsoft365CopilotSettings.Read.All and rerun the Copilot settings scan.",
    "sharing_scope_gap": "Grant Sites.FullControl.All and rerun SharePoint permission/sharing expansion.",
    "sharing_permission_scope_gap": "Grant Sites.FullControl.All and rerun SharePoint permission/sharing expansion.",
}

_SCAN_TOOL_CONTROLS = {
    "entra_scan_app_regs": ["IAM-APP-01", "IAM-APP-02", "IAM-APP-03"],
    "entra_scan_guests": ["IAM-GUEST-01", "IAM-GUEST-02"],
    "ca_scan_policies": ["CA-POL-01", "CA-POL-02"],
    "ca_scan_coverage_gaps": ["CA-COV-01"],
    "pp_scan_environments": ["PP-ENV-01"],
    "pp_scan_apps": ["PP-APP-01"],
    "pim_scan_role_assignments": ["PIM-PERM-01", "PIM-NON-ADMIN-01", "PIM-STALE-01", "PIM-LIC-01"],
    "pim_scan_role_definitions": ["PIM-CUSTOM-01"],
    "license_scan_skus": ["LIC-SKU-OVER-01", "LIC-SKU-UNUSED-01", "LIC-STACK-01"],
    "license_scan_users": ["LIC-DISABLED-01", "LIC-STACK-01"],
    "sharing_scan_sites": ["SHARING-STALE-01", "SHARING-VERY-STALE-01"],
    "intune_scan_devices": ["INTUNE-NONCOMPLIANT-01", "INTUNE-STALE-01", "INTUNE-ENCRYPT-01"],
    "intune_scan_compliance_policies": ["INTUNE-NOPOL-01"],
    "purview_scan_labels": ["PURVIEW-LABEL-01"],
    "purview_scan_audit": ["PURVIEW-AUDIT-01"],
    "exo_scan_mailboxes": ["EXO-SHARED-ENABLED-01"],
    "exo_scan_forwarding": ["EXO-FORWARD-01"],
    "copilot_scan_licenses": ["COP-LICENSE-01", "COP-ACCESS-01"],
    "copilot_scan_settings": ["COP-SETTINGS-01"],
}

_SOURCE_TYPE_BY_KIND = {
    "scan_run": "tenant_scan",
    "kb_row": "kb_row",
    "local_file": "local_file",
    "url": "url",
    "sharepoint": "sharepoint",
}


def _collect_automated_controls() -> dict[str, list[str]]:
    covered: dict[str, list[str]] = {}
    for mod_name in _AUTOMATED_MODULES:
        try:
            mod = importlib.import_module(mod_name)
        except ImportError:
            continue
        for key, control_ids in getattr(mod, "CONTRIBUTES_TO", {}).items():
            if key == "__tool__":
                continue
            for control_id in control_ids or []:
                canonical = canonical_control_id(control_id) if control_id else None
                if canonical:
                    covered.setdefault(canonical, [])
                    if mod_name not in covered[canonical]:
                        covered[canonical].append(mod_name)
    return {control_id: sorted(modules) for control_id, modules in covered.items()}


def _source_type(rows) -> str:
    kinds = {row["source_kind"] for row in rows if row["source_kind"]}
    if not kinds:
        return "manual_required"
    if "scan_run" in kinds:
        return "tenant_scan"
    for kind in ("sharepoint", "local_file", "url", "kb_row"):
        if kind in kinds:
            return _SOURCE_TYPE_BY_KIND[kind]
    return _SOURCE_TYPE_BY_KIND.get(sorted(kinds)[0], sorted(kinds)[0])


def _finding_payload(rows) -> list[dict]:
    return [
        {
            "finding_id": row["finding_id"],
            "finding_type": row["finding_type"],
            "severity": row["severity"],
            "object_name": row["object_name"],
            "securesketch_control": row["securesketch_control"],
        }
        for row in rows
    ]


def _evidence_payload(rows) -> list[dict]:
    return [
        {
            "evidence_id": row["evidence_id"],
            "evidence_type": row["evidence_type"],
            "source_kind": row["source_kind"],
            "source_pointer": row["source_pointer"],
            "verification_status": row["verification_status"],
        }
        for row in rows
    ]


def _blocked_scope_action(findings) -> str | None:
    for row in findings:
        action = _BLOCKED_SCOPE_ACTIONS.get(row["finding_type"])
        if action:
            return action
    return None


def _classify_control(control, evidence_rows, finding_rows, modules) -> dict:
    evidence_count = len(evidence_rows)
    open_finding_count = len(finding_rows)
    verified_count = sum(1 for row in evidence_rows if row["verification_status"] == "resolved")
    broken_count = sum(1 for row in evidence_rows if row["verification_status"] == "unresolvable")
    blocked_action = _blocked_scope_action(finding_rows)

    audit_status = "not_evidenced"
    tooling_status = "manual_required"
    evidence_source_type = _source_type(evidence_rows)
    missing_action = "Link real evidence pointer for this manual/policy control."
    rationale = "No automated tool or evidence is mapped to this control."

    if evidence_count and verified_count == evidence_count:
        audit_status = "evidenced"
        tooling_status = "tool_built_evidence_present" if modules else "manual_required"
        missing_action = ""
        rationale = "All linked evidence pointers are verified."
    elif evidence_count:
        audit_status = "partial"
        tooling_status = "tool_built_evidence_present" if modules else "manual_required"
        if broken_count:
            missing_action = "Repair or replace unverified evidence pointers."
            rationale = "Evidence exists but at least one pointer is not verified."
        else:
            missing_action = "Verify linked evidence pointers."
            rationale = "Evidence exists but has not been verified."
    elif blocked_action:
        audit_status = "not_evidenced"
        tooling_status = "blocked_by_scope"
        evidence_source_type = "manual_required"
        missing_action = blocked_action
        rationale = "A known missing Microsoft API scope blocks direct evidence collection."
    elif modules:
        audit_status = "not_evidenced"
        tooling_status = "tool_built_no_evidence"
        evidence_source_type = "manual_required"
        missing_action = "Run mapped scanner and link scan_snapshot evidence."
        rationale = "At least one automated scanner maps to this control, but no evidence is linked."
    elif open_finding_count:
        audit_status = "partial"
        tooling_status = "tool_gap"
        evidence_source_type = "manual_required"
        missing_action = "Build or identify evidence source for existing mapped findings."
        rationale = "Open findings map to this control, but no automated evidence source is registered."

    return {
        "control_id": control["control_id"],
        "title": control["title"],
        "category": control["category"],
        "category_name": control["category_name"],
        "audit_status": audit_status,
        "tooling_status": tooling_status,
        "evidence_source_type": evidence_source_type,
        "evidence_count": evidence_count,
        "automated_modules": modules,
        "open_finding_count": open_finding_count,
        "open_findings": _finding_payload(finding_rows),
        "evidence": _evidence_payload(evidence_rows),
        "missing_evidence_action": missing_action,
        "rationale": rationale,
    }


def _load_controls(conn, control_id: str | None = None):
    if control_id:
        canonical = canonical_control_id(control_id) or control_id
        return conn.execute(
            "SELECT * FROM ssk_controls WHERE control_id = ? ORDER BY control_id",
            (canonical,),
        ).fetchall()
    return conn.execute("SELECT * FROM ssk_controls ORDER BY control_id").fetchall()


def _active_evidence(conn, control_id: str):
    now = utc_now()
    return conn.execute(
        """
        SELECT * FROM ssk_evidence
        WHERE control_id = ?
          AND (expires_at IS NULL OR expires_at >= ?)
        ORDER BY produced_at DESC
        """,
        (control_id, now),
    ).fetchall()


def _open_findings(conn, control_id: str):
    rows = conn.execute(
        """
        SELECT * FROM findings
        WHERE status = 'open'
          AND securesketch_control IS NOT NULL
        ORDER BY severity, finding_type, object_name
        """,
    ).fetchall()
    return [
        row for row in rows
        if canonical_control_id(row["securesketch_control"]) == control_id
    ]


def _matrix_rows(control_id: str | None = None) -> list[dict]:
    automated = _collect_automated_controls()
    with get_connection() as conn:
        controls = _load_controls(conn, control_id)
        rows = [
            _classify_control(
                control,
                _active_evidence(conn, control["control_id"]),
                _open_findings(conn, control["control_id"]),
                automated.get(control["control_id"], []),
            )
            for control in controls
        ]
    return rows


def _matrix_markdown(rows: list[dict]) -> str:
    evidenced = sum(1 for row in rows if row["audit_status"] == "evidenced")
    partial = sum(1 for row in rows if row["audit_status"] == "partial")
    not_evidenced = sum(1 for row in rows if row["audit_status"] == "not_evidenced")
    lines = [
        "# Secure SketCH Control Coverage Matrix",
        "",
        f"Generated: {utc_now()}",
        f"Total controls: {len(rows)}",
        f"Evidenced: {evidenced}",
        f"Partial: {partial}",
        f"Not evidenced: {not_evidenced}",
        "",
        "| Control | Title | Audit Status | Tooling Status | Evidence Source | Evidence | Open Findings | Missing Evidence Action |",
        "|---|---|---|---|---|---:|---:|---|",
    ]
    for row in rows:
        modules = ", ".join(row["automated_modules"])
        action = row["missing_evidence_action"] or ""
        title = (row["title"] or "").replace("|", "\\|")
        lines.append(
            f"| {row['control_id']} | {title} | {row['audit_status']} "
            f"| {row['tooling_status']} | {row['evidence_source_type']} "
            f"| {row['evidence_count']} | {row['open_finding_count']} "
            f"| {action or modules} |"
        )
    lines.append("")
    return "\n".join(lines)


def _gaps_markdown(rows: list[dict]) -> str:
    gaps = [row for row in rows if row["audit_status"] != "evidenced"]
    lines = [
        "# Secure SketCH Evidence Gaps",
        "",
        f"Generated: {utc_now()}",
        f"Gap controls: {len(gaps)}",
        "",
        "| Control | Title | Audit Status | Tooling Status | Missing Evidence Action | Rationale |",
        "|---|---|---|---|---|---|",
    ]
    for row in gaps:
        title = (row["title"] or "").replace("|", "\\|")
        rationale = (row["rationale"] or "").replace("|", "\\|")
        action = (row["missing_evidence_action"] or "").replace("|", "\\|")
        lines.append(
            f"| {row['control_id']} | {title} | {row['audit_status']} "
            f"| {row['tooling_status']} | {action} | {rationale} |"
        )
    lines.append("")
    return "\n".join(lines)


def _default_report_path(base_dir: Path, prefix: str) -> Path:
    date = utc_now()[:10]
    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir / f"{prefix}-{date}.md"


def _write_snapshots(run_id: str, rows: list[dict]) -> None:
    created_at = utc_now()
    with get_connection() as conn:
        for row in rows:
            metadata = {
                "automated_modules": row["automated_modules"],
                "open_findings": row["open_findings"],
                "evidence": row["evidence"],
            }
            conn.execute(
                """
                INSERT INTO ssk_control_coverage_snapshots
                    (snapshot_id, run_id, control_id, audit_status, tooling_status,
                     evidence_source_type, evidence_count, open_finding_count,
                     missing_evidence_action, rationale, metadata, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()),
                    run_id,
                    row["control_id"],
                    row["audit_status"],
                    row["tooling_status"],
                    row["evidence_source_type"],
                    row["evidence_count"],
                    row["open_finding_count"],
                    row["missing_evidence_action"],
                    row["rationale"],
                    json.dumps(metadata, separators=(",", ":"), sort_keys=True),
                    created_at,
                ),
            )


def _append_activity_with_run_id(
    run_id: str,
    tool_name: str,
    outcome: str,
    detail: dict,
    entity_id: str | None = None,
) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO activity_log (run_id, timestamp, tool_name, domain, entity_id, outcome, detail)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                utc_now(),
                tool_name,
                "ssk",
                entity_id,
                outcome,
                json.dumps(detail, separators=(",", ":"), sort_keys=True),
            ),
        )


def _scan_evidence_candidates(conn) -> list[dict]:
    control_ids = {
        row["control_id"]
        for row in conn.execute("SELECT control_id FROM ssk_controls").fetchall()
    }
    activity_rows = conn.execute(
        """
        SELECT run_id, timestamp, tool_name, domain
        FROM activity_log
        WHERE outcome = 'success'
          AND tool_name IN ({})
        ORDER BY timestamp
        """.format(",".join("?" for _ in _SCAN_TOOL_CONTROLS)),
        tuple(_SCAN_TOOL_CONTROLS),
    ).fetchall()
    candidates: list[dict] = []
    for activity in activity_rows:
        source_pointer = f"activity_log:{activity['run_id']}"
        for ref in _SCAN_TOOL_CONTROLS[activity["tool_name"]]:
            control_id = canonical_control_id(ref) or ref
            if control_id not in control_ids:
                continue
            existing = conn.execute(
                """
                SELECT 1 FROM ssk_evidence
                WHERE control_id = ?
                  AND evidence_type = 'scan_snapshot'
                  AND source_kind = 'scan_run'
                  AND source_pointer = ?
                LIMIT 1
                """,
                (control_id, source_pointer),
            ).fetchone()
            if existing:
                continue
            candidates.append(
                {
                    "control_id": control_id,
                    "run_id": activity["run_id"],
                    "tool_name": activity["tool_name"],
                    "domain": activity["domain"],
                    "source_pointer": source_pointer,
                    "produced_at": activity["timestamp"],
                }
            )
    # Multiple aliases from one scan can resolve to the same canonical control.
    unique: dict[tuple[str, str], dict] = {}
    for candidate in candidates:
        unique[(candidate["control_id"], candidate["source_pointer"])] = candidate
    return list(unique.values())


def ssk_backfill_scan_evidence(dry_run: bool = True) -> str:
    with get_connection() as conn:
        candidates = _scan_evidence_candidates(conn)
        if not dry_run:
            for candidate in candidates:
                conn.execute(
                    """
                    INSERT INTO ssk_evidence
                        (evidence_id, control_id, evidence_type, title, source_kind,
                         source_pointer, source_metadata, produced_at,
                         verification_status, recorded_by, notes)
                    VALUES (?, ?, 'scan_snapshot', ?, 'scan_run', ?, ?, ?, 'unverified', ?, ?)
                    """,
                    (
                        str(uuid.uuid4()),
                        candidate["control_id"],
                        f"{candidate['tool_name']} scan snapshot",
                        candidate["source_pointer"],
                        json.dumps(
                            {
                                "run_id": candidate["run_id"],
                                "tool_name": candidate["tool_name"],
                                "domain": candidate["domain"],
                            },
                            separators=(",", ":"),
                            sort_keys=True,
                        ),
                        candidate["produced_at"],
                        "AMC",
                        "Backfilled from existing successful activity_log scan run.",
                    ),
                )

    append_activity(
        "ssk_backfill_scan_evidence",
        "dry_run" if dry_run else "success",
        {
            "dry_run": dry_run,
            "would_create": len(candidates),
            "created": 0 if dry_run else len(candidates),
        },
    )
    return json_ok(
        {
            "dry_run": dry_run,
            "would_create": len(candidates),
            "created": 0 if dry_run else len(candidates),
            "candidates": candidates,
        }
    )


def ssk_control_coverage_detail(control_id: str) -> str:
    rows = _matrix_rows(control_id)
    if not rows:
        canonical = canonical_control_id(control_id) or control_id
        return json_error(f"control '{canonical}' not found", "UnknownControlError")
    return json_ok(rows[0])


def ssk_control_matrix(
    control_id: str | None = None,
    output_path: str | None = None,
    format: str = "markdown",
) -> str:
    if format not in {"markdown", "json"}:
        return json_error("format must be 'markdown' or 'json'", "ValidationError")
    rows = _matrix_rows(control_id)
    run_id = str(uuid.uuid4())
    _write_snapshots(run_id, rows)

    path = None
    if format == "markdown":
        path = Path(output_path) if output_path else _default_report_path(
            _COVERAGE_REPORT_DIR,
            "coverage",
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_matrix_markdown(rows), encoding="utf-8")

    _append_activity_with_run_id(
        run_id,
        "ssk_control_matrix",
        "success",
        {
            "control_id": control_id,
            "control_count": len(rows),
            "output_path": str(path) if path else None,
            "format": format,
        },
        entity_id=run_id,
    )
    return json_ok(
        {
            "run_id": run_id,
            "control_count": len(rows),
            "output_path": str(path) if path else None,
            "controls": rows,
        }
    )


def ssk_evidence_gaps(
    output_path: str | None = None,
    format: str = "markdown",
) -> str:
    if format not in {"markdown", "json"}:
        return json_error("format must be 'markdown' or 'json'", "ValidationError")
    rows = _matrix_rows()
    gaps = [row for row in rows if row["audit_status"] != "evidenced"]
    path = None
    if format == "markdown":
        path = Path(output_path) if output_path else _default_report_path(
            _GAP_REPORT_DIR,
            "gaps",
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_gaps_markdown(rows), encoding="utf-8")

    append_activity(
        "ssk_evidence_gaps",
        "success",
        {
            "gap_count": len(gaps),
            "output_path": str(path) if path else None,
            "format": format,
        },
    )
    return json_ok(
        {
            "gap_count": len(gaps),
            "output_path": str(path) if path else None,
            "controls": gaps,
        }
    )
