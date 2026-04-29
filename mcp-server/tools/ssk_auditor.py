import html
import importlib
import json
import re
import uuid
from datetime import datetime
from pathlib import Path

from db import get_connection
from tools.ssk_common import append_activity, json_error, json_ok, require_control, utc_now
from tools.ssk_control_map import canonical_control_id
from tools.ssk_matrix import _CATEGORY_NAMES, _SCAN_TOOL_CONTROLS, _matrix_rows


_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_AUDITOR_PACKAGE_DIR = _REPO_ROOT / "reports" / "auditor-packages"
_CONTROL_CHECK_DIR = _REPO_ROOT / "reports" / "control-checks"


def _safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]+", "_", value)


def _quarter_slug(now: str) -> str:
    dt = datetime.fromisoformat(now)
    quarter = (dt.month - 1) // 3 + 1
    return f"{dt.year}-Q{quarter}"


def _control_check_dir(control_id: str, output_dir: str | None = None) -> Path:
    timestamp = datetime.fromisoformat(utc_now()).strftime("%Y%m%dT%H%M%SZ")
    if output_dir:
        root = Path(output_dir)
    else:
        root = _CONTROL_CHECK_DIR / _safe_name(control_id)
    out_dir = root / timestamp
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def _auditor_package_dir(quarter: str | None, output_dir: str | None = None) -> tuple[str, Path]:
    now = utc_now()
    slug = quarter or _quarter_slug(now)
    out_dir = Path(output_dir) if output_dir else (_AUDITOR_PACKAGE_DIR / slug)
    out_dir.mkdir(parents=True, exist_ok=True)
    return slug, out_dir


def _load_control_row(control_id: str):
    with get_connection() as conn:
        require_control(conn, control_id)
        row = conn.execute("SELECT * FROM ssk_controls WHERE control_id = ?", (control_id,)).fetchone()
    return row


def _open_findings_for_control(conn, control_id: str) -> list[dict]:
    rows = conn.execute(
        """
        SELECT finding_id, finding_type, severity, object_name, status,
               recommended_action, last_seen, securesketch_control
        FROM findings
        WHERE status = 'open' AND securesketch_control IS NOT NULL
        ORDER BY severity, finding_type, object_name
        """
    ).fetchall()
    return [
        dict(row)
        for row in rows
        if canonical_control_id(row["securesketch_control"]) == control_id
    ]


def _evidence_for_control(conn, control_id: str) -> list[dict]:
    rows = conn.execute(
        """
        SELECT evidence_id, evidence_type, title, source_kind, source_pointer, source_metadata,
               produced_at, expires_at, verification_status, verification_checked_at
        FROM ssk_evidence
        WHERE control_id = ?
        ORDER BY produced_at DESC, evidence_id DESC
        """,
        (control_id,),
    ).fetchall()
    payload = []
    for row in rows:
        item = dict(row)
        if item["source_metadata"]:
            item["source_metadata"] = json.loads(item["source_metadata"])
        payload.append(item)
    return payload


def _reviews_for_control(conn, control_id: str) -> list[dict]:
    rows = conn.execute(
        """
        SELECT review_id, reviewer, reviewed_at, outcome, quality_flag, findings_summary, next_review_due
        FROM ssk_reviews
        WHERE control_id = ?
        ORDER BY reviewed_at DESC, review_id DESC
        LIMIT 10
        """,
        (control_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def _actions_for_control(conn, control_id: str) -> list[dict]:
    rows = conn.execute(
        """
        SELECT action_id, action_text, implementation_status, owner
        FROM ssk_recommended_actions
        WHERE control_id = ?
        ORDER BY sequence, action_id
        """,
        (control_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def _status_for_control(conn, control_id: str) -> dict | None:
    row = conn.execute(
        """
        SELECT current_maturity, target_maturity, gap_summary, owner,
               review_cadence_days, last_reviewed_at, next_review_due, last_updated
        FROM ssk_control_status
        WHERE control_id = ?
        """,
        (control_id,),
    ).fetchone()
    return dict(row) if row else None


def _resolve_check_functions(control_id: str) -> list[tuple[str, object]]:
    resolved: list[tuple[str, object]] = []
    for tool_name, control_refs in sorted(_SCAN_TOOL_CONTROLS.items()):
        canonical_refs = {canonical_control_id(ref) or ref for ref in control_refs}
        if control_id not in canonical_refs:
            continue
        module_prefix = tool_name.split("_", 1)[0]
        module = importlib.import_module(f"tools.{module_prefix}")
        resolved.append((tool_name, getattr(module, tool_name)))
    return resolved


def _parse_tool_result(raw):
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"raw": raw}
    if isinstance(raw, dict):
        return raw
    return {"raw": raw}


def _check_markdown(payload: dict) -> str:
    lines = [
        f"# Control Check {payload['control_id']}",
        "",
        f"Generated: {payload['generated_at']}",
        f"Generated by: {payload['generated_by']}",
        f"Title: {payload['title']}",
        f"Status: {payload['status']}",
        "",
        "## Tools Run",
        "",
    ]
    if payload["tool_results"]:
        for item in payload["tool_results"]:
            lines.append(f"- `{item['tool_name']}`")
    else:
        lines.append("- No automated check is mapped to this control.")

    lines += ["", "## Findings", ""]
    if payload["linked_finding_ids"]:
        for item in payload["findings"]:
            lines.append(
                f"- `{item['finding_id']}` `{item['severity']}` `{item['finding_type']}` {item['recommended_action']}"
            )
    else:
        lines.append("- No open findings linked to this control after this check.")

    if payload.get("notes"):
        lines += ["", "## Notes", "", payload["notes"]]

    lines += ["", "## Raw Tool Results", ""]
    for item in payload["tool_results"]:
        lines.append(f"### {item['tool_name']}")
        lines.append("")
        lines.append("```json")
        lines.append(json.dumps(item["result"], indent=2, default=str))
        lines.append("```")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def _render_control_markdown(payload: dict) -> str:
    status = payload["status"] or {}
    lines = [
        f"# {payload['control_id']} — {payload['title']}",
        "",
        f"Generated: {payload['generated_at']}",
        f"Category: {payload['category']} — {payload['category_name']}",
        f"Audit status: {payload['audit_status']}",
        f"Current maturity: {status.get('current_maturity') or 'not_regularly_reviewed'}",
        f"Last reviewed: {(status.get('last_reviewed_at') or 'never')[:10] if status.get('last_reviewed_at') else 'never'}",
        f"Next review due: {(status.get('next_review_due') or 'not scheduled')[:10] if status.get('next_review_due') else 'not scheduled'}",
        "",
        "## Overview",
        "",
        payload["overview"] or "_No overview._",
        "",
        "## Evidence",
        "",
    ]
    if payload["evidence"]:
        lines.append("| Evidence ID | Type | Source | Produced | Status |")
        lines.append("|---|---|---|---|---|")
        for item in payload["evidence"]:
            lines.append(
                f"| {item['evidence_id']} | {item['evidence_type']} | {item['source_kind']}:{item['source_pointer']} | {(item['produced_at'] or '')[:10]} | {item['verification_status']} |"
            )
    else:
        lines.append("_No evidence linked._")

    lines += ["", "## Open Findings", ""]
    if payload["findings"]:
        lines.append("| Finding ID | Type | Severity | Object | Last Seen |")
        lines.append("|---|---|---|---|---|")
        for item in payload["findings"]:
            lines.append(
                f"| {item['finding_id']} | {item['finding_type']} | {item['severity']} | {item['object_name'] or ''} | {(item['last_seen'] or '')[:10]} |"
            )
    else:
        lines.append("_No open findings._")

    lines += ["", "## Review History", ""]
    if payload["reviews"]:
        lines.append("| Review ID | Reviewer | Reviewed At | Outcome | Next Due |")
        lines.append("|---|---|---|---|---|")
        for item in payload["reviews"]:
            lines.append(
                f"| {item['review_id']} | {item['reviewer']} | {(item['reviewed_at'] or '')[:10]} | {item['outcome']} | {(item['next_review_due'] or '—')[:10] if item['next_review_due'] else '—'} |"
            )
    else:
        lines.append("_No reviews recorded._")

    lines += ["", "## Recommended Actions", ""]
    if payload["actions"]:
        for item in payload["actions"]:
            lines.append(
                f"- {item['action_text']} [{item['implementation_status']}]"
            )
    else:
        lines.append("_No recommended actions._")

    return "\n".join(lines).rstrip() + "\n"


def _render_control_html(payload: dict) -> str:
    evidence_rows = "".join(
        f"<tr><td>{html.escape(item['evidence_id'])}</td><td>{html.escape(item['evidence_type'])}</td><td>{html.escape(item['source_kind'])}:{html.escape(item['source_pointer'])}</td><td>{html.escape((item['produced_at'] or '')[:10])}</td><td>{html.escape(item['verification_status'])}</td></tr>"
        for item in payload["evidence"]
    ) or "<tr><td colspan='5'>No evidence linked.</td></tr>"
    finding_rows = "".join(
        f"<tr><td>{html.escape(item['finding_id'])}</td><td>{html.escape(item['finding_type'])}</td><td>{html.escape(item['severity'])}</td><td>{html.escape(item['object_name'] or '')}</td><td>{html.escape((item['last_seen'] or '')[:10])}</td></tr>"
        for item in payload["findings"]
    ) or "<tr><td colspan='5'>No open findings.</td></tr>"
    review_rows = "".join(
        f"<tr><td>{html.escape(item['review_id'])}</td><td>{html.escape(item['reviewer'])}</td><td>{html.escape((item['reviewed_at'] or '')[:10])}</td><td>{html.escape(item['outcome'])}</td><td>{html.escape((item['next_review_due'] or '—')[:10] if item['next_review_due'] else '—')}</td></tr>"
        for item in payload["reviews"]
    ) or "<tr><td colspan='5'>No reviews recorded.</td></tr>"
    action_items = "".join(
        f"<li>{html.escape(item['action_text'])} [{html.escape(item['implementation_status'])}]</li>"
        for item in payload["actions"]
    ) or "<li>No recommended actions.</li>"

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{html.escape(payload['control_id'])} - Auditor Package</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 32px; color: #1f2933; }}
    h1, h2 {{ margin-bottom: 0.4rem; }}
    .meta {{ margin: 0 0 1rem 0; color: #52606d; }}
    table {{ width: 100%; border-collapse: collapse; margin: 1rem 0 2rem; }}
    th, td {{ border: 1px solid #d9e2ec; padding: 8px; text-align: left; vertical-align: top; }}
    th {{ background: #f5f7fa; }}
  </style>
</head>
<body>
  <h1>{html.escape(payload['control_id'])} - {html.escape(payload['title'])}</h1>
  <p class="meta">Generated {html.escape(payload['generated_at'])} | Category {html.escape(payload['category'])} - {html.escape(payload['category_name'])} | Audit status {html.escape(payload['audit_status'])}</p>
  <h2>Overview</h2>
  <p>{html.escape(payload['overview'] or 'No overview.')}</p>
  <h2>Evidence</h2>
  <table><thead><tr><th>Evidence ID</th><th>Type</th><th>Source</th><th>Produced</th><th>Status</th></tr></thead><tbody>{evidence_rows}</tbody></table>
  <h2>Open Findings</h2>
  <table><thead><tr><th>Finding ID</th><th>Type</th><th>Severity</th><th>Object</th><th>Last Seen</th></tr></thead><tbody>{finding_rows}</tbody></table>
  <h2>Review History</h2>
  <table><thead><tr><th>Review ID</th><th>Reviewer</th><th>Reviewed At</th><th>Outcome</th><th>Next Due</th></tr></thead><tbody>{review_rows}</tbody></table>
  <h2>Recommended Actions</h2>
  <ul>{action_items}</ul>
</body>
</html>
"""


def _render_index_markdown(quarter: str, generated_at: str, controls: list[dict]) -> str:
    lines = [
        f"# MCNA Auditor Package {quarter}",
        "",
        f"Generated: {generated_at}",
        "",
        "| Control | Title | Audit Status | Evidence | Open Findings | Page |",
        "|---|---|---|---:|---:|---|",
    ]
    for item in controls:
        lines.append(
            f"| {item['control_id']} | {item['title']} | {item['audit_status']} | {item['evidence_count']} | {item['open_finding_count']} | [details](./controls/{item['slug']}.html) |"
        )
    return "\n".join(lines) + "\n"


def _render_index_html(quarter: str, generated_at: str, controls: list[dict]) -> str:
    rows = "".join(
        f"<tr><td>{html.escape(item['control_id'])}</td><td>{html.escape(item['title'])}</td><td>{html.escape(item['audit_status'])}</td><td>{item['evidence_count']}</td><td>{item['open_finding_count']}</td><td><a href='controls/{item['slug']}.html'>details</a></td></tr>"
        for item in controls
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>MCNA Auditor Package {html.escape(quarter)}</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 32px; color: #1f2933; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ border: 1px solid #d9e2ec; padding: 8px; text-align: left; }}
    th {{ background: #f5f7fa; }}
  </style>
</head>
<body>
  <h1>MCNA Auditor Package {html.escape(quarter)}</h1>
  <p>Generated {html.escape(generated_at)}</p>
  <table>
    <thead><tr><th>Control</th><th>Title</th><th>Audit Status</th><th>Evidence</th><th>Open Findings</th><th>Page</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
</body>
</html>
"""


def _escape_pdf_text(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _write_pdf(path: Path, lines: list[str]) -> None:
    lines_per_page = 52
    pages = [lines[i:i + lines_per_page] for i in range(0, len(lines), lines_per_page)] or [["MCNA Auditor Package"]]

    objects: list[bytes] = []
    page_object_numbers: list[int] = []
    content_object_numbers: list[int] = []

    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objects.append(b"<< /Type /Pages /Count 0 /Kids [] >>")
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    for page_lines in pages:
        content_lines = ["BT", "/F1 10 Tf", "14 TL", "50 792 Td"]
        first = True
        for line in page_lines:
            if first:
                content_lines.append(f"({_escape_pdf_text(line)}) Tj")
                first = False
            else:
                content_lines.append("T*")
                if line:
                    content_lines.append(f"({_escape_pdf_text(line)}) Tj")
        content_lines.append("ET")
        content = "\n".join(content_lines).encode("latin-1", errors="replace")
        objects.append(f"<< /Length {len(content)} >>\nstream\n".encode("ascii") + content + b"\nendstream")
        content_object_numbers.append(len(objects))
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 3 0 R >> >> /Contents {content_object_numbers[-1]} 0 R >>".encode("ascii")
        )
        page_object_numbers.append(len(objects))

    kids = " ".join(f"{number} 0 R" for number in page_object_numbers)
    objects[1] = f"<< /Type /Pages /Count {len(page_object_numbers)} /Kids [{kids}] >>".encode("ascii")

    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for idx, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{idx} 0 obj\n".encode("ascii"))
        pdf.extend(obj)
        pdf.extend(b"\nendobj\n")
    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode("ascii")
    )
    path.write_bytes(pdf)


def _package_pdf_lines(quarter: str, generated_at: str, controls: list[dict]) -> list[str]:
    lines = [
        f"MCNA Auditor Package {quarter}",
        f"Generated {generated_at}",
        "",
        f"Total controls: {len(controls)}",
        f"Evidenced: {sum(1 for item in controls if item['audit_status'] == 'evidenced')}",
        f"Open findings: {sum(item['open_finding_count'] for item in controls)}",
        "",
    ]
    for item in controls:
        lines.extend(
            [
                f"{item['control_id']} {item['title']}",
                f"Category {item['category']} {item['category_name']}",
                f"Audit status: {item['audit_status']}",
                f"Evidence: {item['evidence_count']}  Open findings: {item['open_finding_count']}",
                f"Last reviewed: {(item['status'].get('last_reviewed_at') or 'never')[:10] if item['status'].get('last_reviewed_at') else 'never'}",
                "",
            ]
        )
    return lines


def _control_payloads(generated_at: str) -> list[dict]:
    matrix_rows = {row["control_id"]: row for row in _matrix_rows()}
    payloads: list[dict] = []
    with get_connection() as conn:
        controls = conn.execute("SELECT * FROM ssk_controls ORDER BY control_id").fetchall()
        for control in controls:
            control_id = control["control_id"]
            matrix = matrix_rows[control_id]
            evidence = _evidence_for_control(conn, control_id)
            findings = _open_findings_for_control(conn, control_id)
            status = _status_for_control(conn, control_id)
            payloads.append(
                {
                    "control_id": control_id,
                    "slug": _safe_name(control_id),
                    "title": control["title"],
                    "category": control["category"],
                    "category_name": control["category_name"] or _CATEGORY_NAMES.get(control["category"], control["category"]),
                    "overview": control["overview"],
                    "audit_status": matrix["audit_status"],
                    "tooling_status": matrix["tooling_status"],
                    "missing_evidence_action": matrix["missing_evidence_action"],
                    "status": status,
                    "evidence": evidence,
                    "evidence_ids": [item["evidence_id"] for item in evidence],
                    "evidence_count": len(evidence),
                    "findings": findings,
                    "open_finding_count": len(findings),
                    "reviews": _reviews_for_control(conn, control_id),
                    "actions": _actions_for_control(conn, control_id),
                    "generated_at": generated_at,
                }
            )
    return payloads


def ssk_run_control_check(
    control_id: str,
    generated_by: str = "Dave Lafferty",
    notes: str | None = None,
    output_dir: str | None = None,
) -> str:
    normalized = canonical_control_id(control_id) or control_id
    generated_at = utc_now()
    try:
        control = _load_control_row(normalized)
    except ValueError as exc:
        append_activity(
            "ssk_run_control_check",
            "error",
            {"control_id": normalized, "error_type": "UnknownControlError"},
            entity_id=normalized,
        )
        return json_error(str(exc), "UnknownControlError")

    tool_functions = _resolve_check_functions(normalized)
    out_dir = _control_check_dir(normalized, output_dir=output_dir)
    result_path = out_dir / "result.json"
    check_path = out_dir / "check.md"

    if not tool_functions:
        payload = {
            "control_id": normalized,
            "title": control["title"],
            "generated_at": generated_at,
            "generated_by": generated_by,
            "status": "manual_required",
            "notes": notes,
            "tool_results": [],
            "findings": [],
            "linked_finding_ids": [],
            "evidence_id": None,
            "output_dir": str(out_dir),
        }
        check_path.write_text(_check_markdown(payload), encoding="utf-8")
        result_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        append_activity(
            "ssk_run_control_check",
            "manual_required",
            {"control_id": normalized, "output_dir": str(out_dir)},
            entity_id=normalized,
        )
        return json_ok(payload)

    tool_results = []
    for tool_name, tool_fn in tool_functions:
        raw = tool_fn()
        parsed = _parse_tool_result(raw)
        if isinstance(parsed, dict) and parsed.get("error_type"):
            append_activity(
                "ssk_run_control_check",
                "error",
                {"control_id": normalized, "tool_name": tool_name, "error_type": parsed["error_type"]},
                entity_id=normalized,
            )
            return json.dumps(parsed)
        tool_results.append({"tool_name": tool_name, "result": parsed})

    with get_connection() as conn:
        findings = _open_findings_for_control(conn, normalized)

    status = "pass" if not findings else "warn"
    payload = {
        "control_id": normalized,
        "title": control["title"],
        "generated_at": generated_at,
        "generated_by": generated_by,
        "status": status,
        "notes": notes,
        "tool_results": tool_results,
        "findings": findings,
        "linked_finding_ids": [item["finding_id"] for item in findings],
    }
    check_path.write_text(_check_markdown(payload), encoding="utf-8")
    result_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    evidence_id = str(uuid.uuid4())
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO ssk_evidence
                (evidence_id, control_id, evidence_type, title, source_kind, source_pointer,
                 source_metadata, produced_at, verification_status, verification_checked_at, recorded_by, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                evidence_id,
                normalized,
                "control_check",
                f"{normalized} control check",
                "control_check",
                str(result_path),
                json.dumps(
                    {
                        "markdown_path": str(check_path),
                        "tool_names": [item["tool_name"] for item in tool_results],
                        "status": status,
                        "linked_finding_ids": payload["linked_finding_ids"],
                    },
                    separators=(",", ":"),
                    sort_keys=True,
                ),
                generated_at,
                "resolved",
                generated_at,
                generated_by,
                notes,
            ),
        )

    payload["evidence_id"] = evidence_id
    payload["output_dir"] = str(out_dir)
    result_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    append_activity(
        "ssk_run_control_check",
        "success",
        {
            "control_id": normalized,
            "status": status,
            "tool_names": [item["tool_name"] for item in tool_results],
            "evidence_id": evidence_id,
            "output_dir": str(out_dir),
        },
        entity_id=evidence_id,
    )
    return json_ok(payload)


def ssk_auditor_package(
    quarter: str | None = None,
    generated_by: str = "Dave Lafferty",
    output_dir: str | None = None,
) -> str:
    generated_at = utc_now()
    quarter_slug, out_dir = _auditor_package_dir(quarter, output_dir=output_dir)
    controls_dir = out_dir / "controls"
    evidence_dir = out_dir / "evidence"
    controls_dir.mkdir(parents=True, exist_ok=True)
    evidence_dir.mkdir(parents=True, exist_ok=True)

    controls = _control_payloads(generated_at)
    for item in controls:
        (controls_dir / f"{item['slug']}.md").write_text(_render_control_markdown(item), encoding="utf-8")
        (controls_dir / f"{item['slug']}.html").write_text(_render_control_html(item), encoding="utf-8")

    manifest = {
        "generated_at": generated_at,
        "generated_by": generated_by,
        "quarter": quarter_slug,
        "output_dir": str(out_dir),
        "pdf_path": str(out_dir / "auditor-binder.pdf"),
        "controls": [
            {
                "control_id": item["control_id"],
                "title": item["title"],
                "category": item["category"],
                "category_name": item["category_name"],
                "audit_status": item["audit_status"],
                "evidence_count": item["evidence_count"],
                "evidence_ids": item["evidence_ids"],
                "evidence": [
                    {
                        "evidence_id": evidence["evidence_id"],
                        "evidence_type": evidence["evidence_type"],
                        "source_kind": evidence["source_kind"],
                        "source_pointer": evidence["source_pointer"],
                        "verification_status": evidence["verification_status"],
                    }
                    for evidence in item["evidence"]
                ],
                "open_finding_count": item["open_finding_count"],
                "review_status": (item["status"] or {}).get("current_maturity"),
                "last_reviewed_at": (item["status"] or {}).get("last_reviewed_at"),
                "next_review_due": (item["status"] or {}).get("next_review_due"),
                "html_page": f"controls/{item['slug']}.html",
                "markdown_page": f"controls/{item['slug']}.md",
            }
            for item in controls
        ],
    }

    (out_dir / "index.md").write_text(_render_index_markdown(quarter_slug, generated_at, controls), encoding="utf-8")
    (out_dir / "index.html").write_text(_render_index_html(quarter_slug, generated_at, controls), encoding="utf-8")
    (evidence_dir / "index.json").write_text(
        json.dumps(
            {
                "generated_at": generated_at,
                "controls": [
                    {
                        "control_id": item["control_id"],
                        "evidence": item["evidence"],
                    }
                    for item in controls
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    _write_pdf(out_dir / "auditor-binder.pdf", _package_pdf_lines(quarter_slug, generated_at, controls))

    append_activity(
        "ssk_auditor_package",
        "success",
        {
            "quarter": quarter_slug,
            "control_count": len(controls),
            "output_dir": str(out_dir),
            "pdf_path": str(out_dir / "auditor-binder.pdf"),
        },
    )
    return json_ok(
        {
            "quarter": quarter_slug,
            "output_dir": str(out_dir),
            "control_count": len(controls),
            "pdf_path": str(out_dir / "auditor-binder.pdf"),
        }
    )
