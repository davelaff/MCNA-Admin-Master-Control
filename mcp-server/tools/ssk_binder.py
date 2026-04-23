"""Secure SketCH audit binder — coverage analysis and per-control markdown export."""

import importlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from db import get_connection
from tools import ssk_common
from tools.ssk_common import json_ok, json_error, utc_now
from tools.ssk_control_map import canonical_control_id
from tools.ssk_evidence import ssk_verify_pointers

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_BINDER_BASE = _REPO_ROOT / "reports" / "audit-binders"

_AUTOMATED_MODULES = [
    "tools.entra",
    "tools.ca",
    "tools.pp",
    "tools.pim",
    "tools.license",
    "tools.sharing",
]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _collect_automated_controls() -> dict[str, list[str]]:
    """Return {canonical_control_id: [module_name, ...]} for all automated scan coverage."""
    covered: dict[str, list[str]] = {}
    for mod_name in _AUTOMATED_MODULES:
        try:
            mod = importlib.import_module(mod_name)
        except ImportError:
            continue
        contributes = getattr(mod, "CONTRIBUTES_TO", {})
        for key, cids in contributes.items():
            if key == "__tool__":
                continue
            for cid in (cids or []):
                if cid:
                    covered.setdefault(cid, [])
                    if mod_name not in covered[cid]:
                        covered[cid].append(mod_name)
    return covered


def _resolve_export_dir(output_dir: str | None) -> Path:
    if output_dir:
        p = Path(output_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    candidate = _BINDER_BASE / today
    if not candidate.exists():
        candidate.mkdir(parents=True, exist_ok=True)
        return candidate
    # Same-day collision — add HHMMSS suffix
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d-%H%M%S")
    fallback = _BINDER_BASE / ts
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


def _render_status_descriptions(raw: str | None) -> list[str]:
    """Render status_descriptions JSON into markdown lines."""
    lines: list[str] = []
    if not raw:
        lines.append("_No position data._")
        lines.append("")
        return lines
    try:
        descs = json.loads(raw)
        if isinstance(descs, dict):
            for label, text in descs.items():
                lines.append(f"**{label}:** {text}")
                lines.append("")
        elif isinstance(descs, list):
            for d in descs:
                label = d.get("label", "")
                status = d.get("status", "")
                desc = d.get("description", "")
                header = f"{label} — {status}" if status else label
                lines.append(f"**{header}:** {desc}")
                lines.append("")
        else:
            lines.append(str(descs))
            lines.append("")
    except (json.JSONDecodeError, TypeError):
        lines.append(raw)
        lines.append("")
    return lines


def _control_markdown(conn, control_id: str) -> str:
    """Render a single control as a markdown string."""
    ctrl = conn.execute(
        "SELECT * FROM ssk_controls WHERE control_id = ?", (control_id,)
    ).fetchone()
    if ctrl is None:
        return f"# {control_id}\n\n_Control not found in database._\n"

    status = conn.execute(
        "SELECT * FROM ssk_control_status WHERE control_id = ?", (control_id,)
    ).fetchone()

    evidence_rows = conn.execute(
        """
        SELECT evidence_id, evidence_type, title, source_kind, source_pointer,
               produced_at, expires_at, verification_status
        FROM ssk_evidence WHERE control_id = ? ORDER BY produced_at DESC
        """,
        (control_id,),
    ).fetchall()

    action_rows = conn.execute(
        """
        SELECT action_id, action_text, implementation_status, owner
        FROM ssk_recommended_actions WHERE control_id = ? ORDER BY sequence
        """,
        (control_id,),
    ).fetchall()

    review_rows = conn.execute(
        """
        SELECT review_id, reviewer, reviewed_at, outcome, quality_flag,
               findings_summary, next_review_due
        FROM ssk_reviews WHERE control_id = ? ORDER BY reviewed_at DESC LIMIT 10
        """,
        (control_id,),
    ).fetchall()

    # Pull all open findings and filter to this control via canonical normalization
    all_findings = conn.execute(
        """
        SELECT finding_id, finding_type, severity, object_name, status,
               last_seen, recommended_action, securesketch_control
        FROM findings
        WHERE status != 'dismissed'
        ORDER BY severity, finding_type
        """,
    ).fetchall()
    ctrl_canonical = canonical_control_id(control_id)
    matching_findings = [
        r for r in all_findings
        if canonical_control_id(r["securesketch_control"]) == ctrl_canonical
    ]

    lines: list[str] = []

    # Header
    lines.append(f"# {control_id} — {ctrl['title']}")
    lines.append("")
    cat_label = ctrl["category"]
    if ctrl["category_name"]:
        cat_label += f" — {ctrl['category_name']}"
    lines.append(f"**Category:** {cat_label}")
    lines.append(f"**Source version:** {ctrl['source_version']}")
    if status:
        lines.append(f"**Current maturity:** {status['current_maturity']}")
        lines.append(f"**Target maturity:** {status['target_maturity']}")
        lines.append(f"**Last reviewed:** {status['last_reviewed_at'] or 'never'}")
        lines.append(f"**Next review due:** {status['next_review_due'] or 'not scheduled'}")
    lines.append("")

    # MCNA position
    lines.append("## MCNA Position")
    lines.append("")
    lines.extend(_render_status_descriptions(ctrl["status_descriptions"]))

    # Control statement
    lines.append("## Control Statement")
    lines.append("")
    lines.append(ctrl["overview"] or "_No overview._")
    lines.append("")

    # Evidence table
    lines.append("## Evidence")
    lines.append("")
    if evidence_rows:
        lines.append("| ID | Type | Title | Source | Produced | Expires | Status |")
        lines.append("|----|------|-------|--------|----------|---------|--------|")
        for e in evidence_rows:
            eid = e["evidence_id"][:8]
            pointer_short = (e["source_pointer"] or "")[:40]
            lines.append(
                f"| {eid} | {e['evidence_type']} | {e['title'] or ''} "
                f"| {e['source_kind']}:{pointer_short} "
                f"| {(e['produced_at'] or '')[:10]} "
                f"| {(e['expires_at'] or '')[:10] or '—'} "
                f"| {e['verification_status']} |"
            )
    else:
        lines.append("_No evidence linked._")
    lines.append("")

    # Recommended actions
    lines.append("## Recommended Actions")
    lines.append("")
    if action_rows:
        lines.append("| ID | Action | Status | Owner |")
        lines.append("|----|--------|--------|-------|")
        for a in action_rows:
            lines.append(
                f"| {a['action_id']} | {a['action_text']} "
                f"| {a['implementation_status']} | {a['owner'] or '—'} |"
            )
    else:
        lines.append("_No recommended actions._")
    lines.append("")

    # Review history
    lines.append("## Review History")
    lines.append("")
    if review_rows:
        lines.append("| Review ID | Reviewer | Reviewed At | Outcome | Quality | Next Due |")
        lines.append("|-----------|----------|-------------|---------|---------|----------|")
        for r in review_rows:
            lines.append(
                f"| {r['review_id'][:8]} | {r['reviewer']} "
                f"| {(r['reviewed_at'] or '')[:10]} "
                f"| {r['outcome']} | {r['quality_flag']} "
                f"| {(r['next_review_due'] or '')[:10] or '—'} |"
            )
    else:
        lines.append("_No reviews recorded._")
    lines.append("")

    # Active findings
    lines.append("## Active Findings")
    lines.append("")
    if matching_findings:
        lines.append("| Finding ID | Type | Severity | Object | Status | Last Seen |")
        lines.append("|------------|------|----------|--------|--------|-----------|")
        for f in matching_findings:
            lines.append(
                f"| {f['finding_id'][:8]} | {f['finding_type']} | {f['severity']} "
                f"| {f['object_name'] or ''} | {f['status']} "
                f"| {(f['last_seen'] or '')[:10]} |"
            )
    else:
        lines.append("_No open findings._")
    lines.append("")

    # Risk
    lines.append("## Insufficient Measures Risks")
    lines.append("")
    lines.append(ctrl["insufficient_measures_risks"] or "_No risk statement._")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Public tools
# ---------------------------------------------------------------------------

def ssk_coverage() -> str:
    """Report which Secure SketCH controls have automated scan coverage.

    Returns JSON with:
    - automated_controls: {control_id: [module_name, ...]}
    - all_control_ids: list of all imported control IDs
    - covered_count, total_count, uncovered: [control_ids with no automated coverage]
    """
    automated = _collect_automated_controls()
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT control_id FROM ssk_controls ORDER BY control_id"
        ).fetchall()
    all_ids = [r["control_id"] for r in rows]
    uncovered = [cid for cid in all_ids if cid not in automated]
    # Filter automated_controls to only controls present in DB
    automated_in_db = {cid: mods for cid, mods in automated.items() if cid in all_ids}
    return json_ok({
        "automated_controls": {k: v for k, v in sorted(automated_in_db.items())},
        "all_control_ids": all_ids,
        "covered_count": len([cid for cid in all_ids if cid in automated]),
        "total_count": len(all_ids),
        "uncovered": uncovered,
    })


def ssk_export_binder(scope: str, output_dir: str | None = None) -> str:
    """Export an audit binder for one control or all controls.

    scope: a control_id (e.g. "06-3") or "all"
    output_dir: optional directory override; defaults to reports/audit-binders/YYYY-MM-DD
    """
    if scope != "all":
        scope = canonical_control_id(scope) or scope

    # Resolve and validate control IDs before creating the output directory
    with get_connection() as conn:
        if scope == "all":
            rows = conn.execute(
                "SELECT control_id FROM ssk_controls ORDER BY control_id"
            ).fetchall()
            control_ids = [r["control_id"] for r in rows]
        else:
            row = conn.execute(
                "SELECT control_id FROM ssk_controls WHERE control_id = ?", (scope,)
            ).fetchone()
            if row is None:
                return json_error(f"Control '{scope}' not found", "UnknownControlError")
            control_ids = [scope]

    export_root = _resolve_export_dir(output_dir)
    exported: list[str] = []
    manifest_entries: list[dict] = []

    for cid in control_ids:
        # Refresh pointer verification before rendering
        ssk_verify_pointers(control_id=cid)
        with get_connection() as conn:
            md = _control_markdown(conn, cid)
        safe_name = re.sub(r"[^a-zA-Z0-9_]", "_", cid)
        out_file = export_root / f"{safe_name}.md"
        out_file.write_text(md, encoding="utf-8")
        exported.append(str(out_file))
        manifest_entries.append({"control_id": cid, "file": out_file.name})

    # Write index.md
    index_lines = [
        "# Audit Binder",
        "",
        f"Generated: {utc_now()}",
        "",
        "## Controls",
        "",
    ]
    for entry in manifest_entries:
        index_lines.append(f"- [{entry['control_id']}](./{entry['file']})")
    (export_root / "index.md").write_text("\n".join(index_lines), encoding="utf-8")

    # Write manifest.json
    manifest = {
        "generated_at": utc_now(),
        "scope": scope,
        "controls": manifest_entries,
        "output_dir": str(export_root),
    }
    (export_root / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )

    return json_ok({
        "output_dir": str(export_root),
        "controls_exported": len(exported),
        "files": exported,
    })
