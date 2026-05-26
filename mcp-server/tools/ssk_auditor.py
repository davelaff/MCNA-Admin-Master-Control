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


def _clauses_for_control(conn, control_id: str) -> list[dict]:
    rows = conn.execute(
        """
        SELECT clause_id, group_name, clause_text
        FROM ssk_clauses
        WHERE control_id = ?
        ORDER BY sequence
        """,
        (control_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def _audit_evidence_items_for_control(conn, control_id: str) -> list[dict]:
    rows = conn.execute(
        """
        SELECT item_id, item_text
        FROM ssk_audit_evidence_items
        WHERE control_id = ?
        ORDER BY sequence
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


_SEV_ORDER = ["Critical", "High", "Medium", "Low"]
_SEV_LABEL = {"warn": "⚠ Warn", "pass": "✓ Pass", "manual_required": "Manual Required"}

_CHECK_HTML_CSS = """
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{--red:#A40A02;--pink:#F5D7D5;--grey:#F2F2F2;--text:#404040;--rule:#BFBFBF;--white:#FFFFFF;--font:'Segoe UI','Segoe UI Web (West European)',system-ui,sans-serif;--font-sb:'Segoe UI Semibold','Segoe UI',system-ui,sans-serif}
html{font-size:14px}
body{background:var(--grey);color:var(--text);font-family:var(--font);min-height:100vh;display:flex;flex-direction:column;line-height:1.5}
.doc-header{background:var(--white);border-bottom:2px solid var(--red);padding:6px 28px 4px;position:sticky;top:0;z-index:100;box-shadow:0 1px 6px rgba(0,0,0,.07)}
.doc-header-line{display:flex;justify-content:space-between;align-items:baseline;font-size:.62rem;color:var(--text);line-height:1.65}
.doc-header-line .left{font-weight:700}
.doc-header-line .right{opacity:.75}
.doc-header-spacer{height:3px}
.page-body{display:flex;flex:1;background:var(--white);max-width:1120px;margin:18px auto 18px;width:calc(100% - 36px);box-shadow:0 2px 16px rgba(0,0,0,.1)}
#sidebar{width:188px;min-width:188px;background:var(--grey);border-right:1px solid var(--rule);padding:22px 13px;position:sticky;top:52px;height:calc(100vh - 52px);overflow-y:auto;display:flex;flex-direction:column;gap:16px;align-self:flex-start}
.sb-label{font-size:.58rem;font-weight:700;color:var(--red);letter-spacing:.1em;text-transform:uppercase;margin-bottom:4px}
.severity-nav{display:flex;flex-direction:column;gap:1px}
.severity-nav a{display:flex;align-items:baseline;gap:6px;padding:4px 6px;text-decoration:none;font-size:.7rem;color:var(--text)}
.severity-nav a:hover{background:var(--pink)}
.nav-sev{flex:1}
.nav-count{font-size:.68rem;font-weight:700;color:var(--red)}
.nav-count.dim{color:var(--text);font-weight:400}
.sb-meta{font-size:.6rem;color:var(--text);line-height:1.85;border-top:1px solid var(--rule);padding-top:12px}
.sb-meta strong{display:block;font-size:.57rem;font-weight:700;color:var(--red);letter-spacing:.07em;text-transform:uppercase;margin-top:8px}
#main{flex:1;padding:28px 32px 36px}
.report-title{font-size:1.5rem;font-weight:700;color:var(--red);line-height:1.15;margin-bottom:4px}
.report-org{font-size:.75rem;color:var(--text);margin-bottom:18px;opacity:.8}
table.meta-t{border-collapse:collapse;font-size:.73rem;margin-bottom:26px;width:auto}
table.meta-t td{padding:4px 10px;border:1px solid var(--rule);vertical-align:top}
table.meta-t td.lbl{background:var(--grey);font-weight:600;white-space:nowrap;min-width:110px}
table.meta-t td.val{background:var(--white);min-width:220px}
.severity-section{margin-bottom:34px}
.section-h{font-size:1rem;font-weight:700;color:var(--red);border-bottom:1.5px solid var(--red);padding-bottom:5px;margin-bottom:10px;display:flex;align-items:baseline;gap:10px;letter-spacing:.01em}
.section-h .cnt{font-size:.62rem;color:var(--text);font-weight:400;opacity:.7}
table.ft{width:100%;border-collapse:collapse;font-size:.72rem;margin-bottom:4px}
table.ft th{background:var(--red);color:var(--white);padding:5px 9px;text-align:left;font-weight:600;font-size:.63rem;letter-spacing:.04em;white-space:nowrap;border:1px solid var(--red)}
table.ft td{padding:5px 9px;border:1px solid var(--rule);color:var(--text);vertical-align:top}
table.ft td.obj{background:var(--grey);font-weight:600;min-width:130px;max-width:176px}
table.ft td.obj-hi{background:var(--pink)}
table.ft td.meta{font-size:.63rem;opacity:.8;white-space:nowrap}
table.ft td.ftype{font-style:italic;white-space:nowrap;font-size:.69rem}
table.ft td.detail{max-width:340px}
details{margin-bottom:6px;border:1px solid var(--rule)}
summary{padding:6px 10px;font-size:.72rem;font-weight:600;cursor:pointer;background:var(--grey);user-select:none}
summary:hover{background:var(--pink)}
pre{padding:12px;font-size:.63rem;overflow-x:auto;background:#fafafa;line-height:1.45}
.doc-footer{background:var(--white);border-top:1px solid var(--rule);text-align:center;padding:8px;font-size:.62rem;font-weight:700;color:var(--text);letter-spacing:.14em;max-width:1120px;margin:0 auto 18px;width:calc(100% - 36px);box-shadow:0 2px 16px rgba(0,0,0,.1)}
.pdf-btn{position:fixed;bottom:24px;right:24px;z-index:200;background:var(--red);color:var(--white);border:none;padding:8px 18px;font-family:var(--font);font-size:.72rem;font-weight:600;letter-spacing:.04em;cursor:pointer;box-shadow:0 2px 8px rgba(164,10,2,.35)}
.pdf-btn:hover{background:#8a0802}
@media print{
  @page{size:letter landscape;margin:0.5in}
  body{background:var(--white)}
  .doc-header{position:static;box-shadow:none;border-bottom:1.5pt solid #A40A02}
  .page-body{max-width:100%;margin:0;width:100%;box-shadow:none;display:block}
  #sidebar{display:none}
  #main{padding:0}
  .doc-footer{max-width:100%;margin:0;width:100%;box-shadow:none;border-top:0.5pt solid #BFBFBF}
  .pdf-btn{display:none}
  .severity-section{page-break-inside:avoid}
  .section-h{page-break-after:avoid}
  table.ft tr{page-break-inside:avoid}
  table.meta-t{page-break-inside:avoid}
}
"""


def _render_check_html(payload: dict) -> str:
    control_id = payload["control_id"]
    title = payload["title"]
    date_str = payload["generated_at"][:10]
    generated_by = payload.get("generated_by", "")
    status = payload["status"]
    findings = payload.get("findings", [])
    tool_results = payload.get("tool_results", [])
    evidence_id = payload.get("evidence_id") or ""
    notes = payload.get("notes") or ""

    status_label = _SEV_LABEL.get(status, status)
    status_color = "var(--red)" if status == "warn" else ("green" if status == "pass" else "var(--text)")

    # Group findings by severity
    by_sev: dict[str, list] = {}
    for f in findings:
        sev = (f.get("severity") or "Unknown").capitalize()
        by_sev.setdefault(sev, []).append(f)

    # Sidebar nav
    nav_items = []
    sec_idx = 1
    for sev in _SEV_ORDER:
        group = by_sev.get(sev, [])
        if group:
            nav_items.append(
                f'<a href="#sev-{sev.lower()}"><span class="nav-sev">{sec_idx}. {sev}</span>'
                f'<span class="nav-count">{len(group)}</span></a>'
            )
            sec_idx += 1
    if tool_results:
        nav_items.append(
            f'<a href="#tools-run"><span class="nav-sev">{sec_idx}. Tools Run</span>'
            f'<span class="nav-count dim">{len(tool_results)}</span></a>'
        )
        sec_idx += 1
        nav_items.append(
            f'<a href="#raw-results"><span class="nav-sev">{sec_idx}. Raw Results</span>'
            f'<span class="nav-count dim">{len(tool_results)}</span></a>'
        )
    nav_html = "\n".join(nav_items) or '<span style="font-size:.68rem;opacity:.6">No findings</span>'

    # Meta table
    meta_rows_html = "".join([
        f'<tr><td class="lbl">Control</td><td class="val">{html.escape(control_id)}</td></tr>',
        f'<tr><td class="lbl">Title</td><td class="val">{html.escape(title)}</td></tr>',
        f'<tr><td class="lbl">Status</td><td class="val"><span style="font-weight:700;color:{status_color}">{html.escape(status_label)}</span></td></tr>',
        f'<tr><td class="lbl">Generated</td><td class="val">{html.escape(date_str)}</td></tr>',
        f'<tr><td class="lbl">Generated By</td><td class="val">{html.escape(generated_by)}</td></tr>',
        f'<tr><td class="lbl">Findings</td><td class="val">{len(findings)}</td></tr>',
        f'<tr><td class="lbl">Tools Run</td><td class="val">{len(tool_results)}</td></tr>',
        f'<tr><td class="lbl">Evidence ID</td><td class="val">{html.escape(evidence_id[:8]) if evidence_id else "—"}</td></tr>',
    ])

    # Findings sections
    sev_sections = []
    sec_idx = 1
    for sev in _SEV_ORDER:
        group = by_sev.get(sev, [])
        if not group:
            continue
        hi_class = " obj-hi" if sev in ("Critical", "High") else ""
        rows = "".join(
            f'<tr>'
            f'<td class="obj{hi_class}">{html.escape(f.get("object_name") or "—")}</td>'
            f'<td class="ftype">{html.escape(f.get("finding_type") or "")}</td>'
            f'<td class="detail">{html.escape(f.get("recommended_action") or "")}</td>'
            f'<td class="meta">{html.escape((f.get("last_seen") or "")[:10])}</td>'
            f'</tr>'
            for f in group
        )
        sev_sections.append(
            f'<div class="severity-section" id="sev-{sev.lower()}">'
            f'<div class="section-h">{sec_idx}. {html.escape(sev)} Findings'
            f'<span class="cnt">{len(group)} finding{"s" if len(group) != 1 else ""}</span></div>'
            f'<table class="ft"><thead><tr>'
            f'<th>Object</th><th>Finding Type</th><th>Recommended Action</th><th>Last Seen</th>'
            f'</tr></thead><tbody>{rows}</tbody></table></div>'
        )
        sec_idx += 1

    findings_html = "\n".join(sev_sections) if sev_sections else (
        '<p style="font-size:.8rem;color:green;padding:8px 0">&#10003; No open findings after this check.</p>'
    )

    # Tools run + raw results
    if tool_results:
        tools_list = "".join(f"<li style='padding:3px 0'><code>{html.escape(t['tool_name'])}</code></li>" for t in tool_results)
        tools_section = (
            f'<div class="severity-section" id="tools-run">'
            f'<div class="section-h">{sec_idx}. Tools Run<span class="cnt">{len(tool_results)}</span></div>'
            f'<ul style="font-size:.8rem;padding-left:1.4rem;line-height:1.8">{tools_list}</ul>'
            f'</div>'
        )
        sec_idx += 1
        raw_items = "".join(
            f'<details><summary><code>{html.escape(t["tool_name"])}</code></summary>'
            f'<pre>{html.escape(json.dumps(t["result"], indent=2, default=str))}</pre></details>'
            for t in tool_results
        )
        raw_section = (
            f'<div class="severity-section" id="raw-results">'
            f'<div class="section-h">{sec_idx}. Raw Tool Results</div>'
            f'{raw_items}</div>'
        )
    else:
        _manual_notes = (
            f'<p style="font-size:.8rem;margin-top:8px"><strong>Notes:</strong> {html.escape(notes)}</p>'
            if notes else ""
        )
        tools_section = (
            f'<div class="severity-section" id="tools-run">'
            f'<div class="section-h">1. Assessment</div>'
            f'<p style="font-size:.8rem">No automated checks mapped to this control. Manual review required.</p>'
            f'{_manual_notes}'
            f'</div>'
        )
        raw_section = ""

    notes_html = (
        f'<p style="font-size:.8rem;margin-bottom:16px;padding:6px 8px;background:var(--grey);border-left:3px solid var(--red)">'
        f'<strong>Notes:</strong> {html.escape(notes)}</p>'
    ) if notes and tool_results else ""

    eid_short = html.escape(evidence_id[:8]) if evidence_id else "—"

    return (
        f'<!doctype html>\n<html lang="en">\n<head>\n'
        f'<meta charset="utf-8">\n'
        f'<meta name="viewport" content="width=device-width,initial-scale=1">\n'
        f'<title>Control Check {html.escape(control_id)} — {html.escape(date_str)}</title>\n'
        f'<style>{_CHECK_HTML_CSS}</style>\n'
        f'</head>\n<body>\n'
        f'<header class="doc-header">'
        f'<div class="doc-header-line"><span class="left">NOF Metal Coatings North America</span><span class="right">IT and Information Systems</span></div>'
        f'<div class="doc-header-line"><span class="left">IT &amp; Management Information Systems</span><span class="right">Control Check</span></div>'
        f'<div class="doc-header-spacer"></div></header>\n'
        f'<div class="page-body">'
        f'<aside id="sidebar">'
        f'<div><div class="sb-label">Contents</div><nav class="severity-nav">{nav_html}</nav></div>'
        f'<div class="sb-meta">'
        f'<strong>Control</strong>{html.escape(control_id)}'
        f'<strong>Status</strong>{html.escape(status_label)}'
        f'<strong>Generated</strong>{html.escape(date_str)}'
        f'<strong>Findings</strong>{len(findings)}'
        f'<strong>Evidence ID</strong>{eid_short}'
        f'</div></aside>'
        f'<main id="main">'
        f'<h1 class="report-title">Control Check — {html.escape(control_id)}</h1>'
        f'<p class="report-org">NOF Metal Coatings North America &nbsp;&middot;&nbsp; IT &amp; Management Information Systems</p>'
        f'<table class="meta-t"><tbody>{meta_rows_html}</tbody></table>'
        f'{notes_html}'
        f'{findings_html}'
        f'{tools_section}'
        f'{raw_section}'
        f'</main></div>\n'
        f'<footer class="doc-footer">CONFIDENTIAL</footer>\n'
        f'<button class="pdf-btn" onclick="window.print()">Export PDF</button>\n'
        f'</body>\n</html>\n'
    )


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

    lines += ["", "## Standards Clauses", ""]
    if payload["clauses"]:
        lines.append("| Clause | Group | Requirement |")
        lines.append("|--------|-------|-------------|")
        for item in payload["clauses"]:
            lines.append(f"| {item['clause_id']} | {item['group_name'] or '—'} | {item['clause_text']} |")
    else:
        lines.append("_No clauses._")

    lines += ["", "## Audit Evidence Requirements", ""]
    if payload["audit_evidence_items"]:
        for item in payload["audit_evidence_items"]:
            lines.append(f"- {item['item_text']}")
    else:
        lines.append("_No audit evidence requirements defined._")

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
    clause_rows_html = "".join(
        f"<tr><td>{html.escape(item['clause_id'])}</td><td>{html.escape(item['group_name'] or '—')}</td><td>{html.escape(item['clause_text'])}</td></tr>"
        for item in payload["clauses"]
    ) or "<tr><td colspan='3'>No clauses.</td></tr>"
    audit_evidence_items_html = "".join(
        f"<li>{html.escape(item['item_text'])}</li>"
        for item in payload["audit_evidence_items"]
    ) or "<li>No audit evidence requirements defined.</li>"

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
  <h2>Standards Clauses</h2>
  <table><thead><tr><th>Clause</th><th>Group</th><th>Requirement</th></tr></thead><tbody>{clause_rows_html}</tbody></table>
  <h2>Audit Evidence Requirements</h2>
  <ul>{audit_evidence_items_html}</ul>
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
                    "clauses": _clauses_for_control(conn, control_id),
                    "audit_evidence_items": _audit_evidence_items_for_control(conn, control_id),
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
    html_path = out_dir / "check.html"

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
        html_path.write_text(_render_check_html(payload), encoding="utf-8")
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
    payload["html_path"] = str(html_path)
    result_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    html_path.write_text(_render_check_html(payload), encoding="utf-8")
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
