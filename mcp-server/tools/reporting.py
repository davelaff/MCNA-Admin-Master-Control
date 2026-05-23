"""Shared HTML report engine for MCNA-AMC domain scan reports."""
import html as _html_mod
import json
from datetime import datetime
from pathlib import Path
from db import get_connection

_SEV_RANK = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}

# Per-domain config: title, running-header subtitle, output subdir, entity_type for
# "clean" section (None = no clean section), first-column header, and controls string
# (empty = auto-derived from securesketch_control values in findings).
_DOMAIN_CONFIG: dict = {
    "entra": {
        "title":      "Entra Application Governance Scan",
        "header_sub": "Entra Application Governance",
        "output_dir": "app-reg-governance",
        "clean_type": "app_registration",
        "col_header": "Application",
        "controls":   "IAM-APP-01 · IAM-APP-02 · IAM-APP-03 · IAM-GUEST-01 · IAM-GUEST-02",
    },
    "exo": {
        "title":      "Exchange Online Governance Scan",
        "header_sub": "Exchange Online Governance",
        "output_dir": "exo-governance",
        "clean_type": "mailbox",
        "col_header": "Mailbox",
        "controls":   "",
    },
    "ca": {
        "title":      "Conditional Access Policy Scan",
        "header_sub": "Conditional Access Governance",
        "output_dir": "ca-governance",
        "clean_type": None,
        "col_header": "Policy",
        "controls":   "",
    },
    "pp": {
        "title":      "Power Platform Governance Scan",
        "header_sub": "Power Platform Governance",
        "output_dir": "pp-governance",
        "clean_type": None,
        "col_header": "Object",
        "controls":   "",
    },
    "pim": {
        "title":      "PIM Role Assignment Scan",
        "header_sub": "PIM Governance",
        "output_dir": "pim-governance",
        "clean_type": None,
        "col_header": "Assignment",
        "controls":   "",
    },
    "license": {
        "title":      "License Governance Scan",
        "header_sub": "License Governance",
        "output_dir": "license-governance",
        "clean_type": None,
        "col_header": "User / SKU",
        "controls":   "",
    },
    "sharing": {
        "title":      "SharePoint Sharing Governance Scan",
        "header_sub": "SharePoint Sharing Governance",
        "output_dir": "sharing-governance",
        "clean_type": "site",
        "col_header": "Site",
        "controls":   "",
    },
    "intune": {
        "title":      "Intune Device Governance Scan",
        "header_sub": "Intune Governance",
        "output_dir": "intune-governance",
        "clean_type": None,
        "col_header": "Device",
        "controls":   "",
    },
    "purview": {
        "title":      "Purview Governance Scan",
        "header_sub": "Purview Governance",
        "output_dir": "purview-governance",
        "clean_type": None,
        "col_header": "Object",
        "controls":   "",
    },
    "copilot": {
        "title":      "Copilot Governance Scan",
        "header_sub": "Copilot Governance",
        "output_dir": "copilot-governance",
        "clean_type": None,
        "col_header": "Object",
        "controls":   "",
    },
}


def _esc(s) -> str:
    return _html_mod.escape(str(s)) if s else ""


def _humanize(s: str) -> str:
    return " ".join(w.capitalize() for w in (s or "").replace("_", " ").split())


_REPORT_CSS = """
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --red:#A40A02;--pink:#F5D7D5;--grey:#F2F2F2;
  --text:#404040;--rule:#BFBFBF;--white:#FFFFFF;
  --font:'Segoe UI','Segoe UI Web (West European)',system-ui,sans-serif;
  --font-sb:'Segoe UI Semibold','Segoe UI',system-ui,sans-serif;
}
html{font-size:14px}
body{background:var(--grey);color:var(--text);font-family:var(--font);min-height:100vh;display:flex;flex-direction:column;line-height:1.5}

/* ── Running header (Word 3-line header analogue) ─────────────────── */
.doc-header{
  background:var(--white);border-bottom:2px solid var(--red);
  padding:6px 28px 4px;position:sticky;top:0;z-index:100;
  box-shadow:0 1px 6px rgba(0,0,0,.07);
}
.doc-header-line{display:flex;justify-content:space-between;align-items:baseline;font-size:.62rem;color:var(--text);line-height:1.65}
.doc-header-line .left{font-weight:700}
.doc-header-line .right{opacity:.75}
.doc-header-spacer{height:3px}

/* ── Page body wrapper ────────────────────────────────────────────── */
.page-body{display:flex;flex:1;background:var(--white);max-width:1120px;margin:18px auto 18px;width:calc(100% - 36px);box-shadow:0 2px 16px rgba(0,0,0,.1)}

/* ── Sidebar (document contents index) ───────────────────────────── */
#sidebar{
  width:188px;min-width:188px;background:var(--grey);
  border-right:1px solid var(--rule);padding:22px 13px;
  position:sticky;top:52px;height:calc(100vh - 52px);
  overflow-y:auto;display:flex;flex-direction:column;gap:16px;
  align-self:flex-start;
}
.sb-label{font-size:.58rem;font-weight:700;color:var(--red);letter-spacing:.1em;text-transform:uppercase;margin-bottom:4px}
.severity-nav{display:flex;flex-direction:column;gap:1px}
.severity-nav a{display:flex;align-items:baseline;gap:6px;padding:4px 6px;text-decoration:none;font-size:.7rem;color:var(--text)}
.severity-nav a:hover{background:var(--pink)}
.nav-sev{flex:1}
.nav-count{font-size:.68rem;font-weight:700;color:var(--red)}
.nav-count.dim{color:var(--text);font-weight:400}
.sb-meta{font-size:.6rem;color:var(--text);line-height:1.85;border-top:1px solid var(--rule);padding-top:12px}
.sb-meta strong{display:block;font-size:.57rem;font-weight:700;color:var(--red);letter-spacing:.07em;text-transform:uppercase;margin-top:8px}

/* ── Main content ─────────────────────────────────────────────────── */
#main{flex:1;padding:28px 32px 36px}

/* H1 title block */
.report-title{font-size:1.5rem;font-weight:700;color:var(--red);line-height:1.15;margin-bottom:4px}
.report-org{font-size:.75rem;color:var(--text);margin-bottom:18px;opacity:.8}

/* Metadata summary table (label-value pattern) */
table.meta-t{border-collapse:collapse;font-size:.73rem;margin-bottom:26px;width:auto}
table.meta-t td{padding:4px 10px;border:1px solid var(--rule);vertical-align:top}
table.meta-t td.lbl{background:var(--grey);font-weight:600;white-space:nowrap;min-width:110px}
table.meta-t td.val{background:var(--white);min-width:220px}
table.meta-t td.val.crit{background:var(--pink);color:var(--red);font-weight:700}

/* Section headings (H3 analogue) */
.severity-section{margin-bottom:34px}
.section-h{font-size:1rem;font-weight:700;color:var(--red);
  border-bottom:1.5px solid var(--red);padding-bottom:5px;margin-bottom:10px;
  display:flex;align-items:baseline;gap:10px;letter-spacing:.01em}
.section-h .cnt{font-size:.62rem;color:var(--text);font-weight:400;opacity:.7}

/* Findings table */
table.ft{width:100%;border-collapse:collapse;font-size:.72rem;margin-bottom:4px}
table.ft th{
  background:var(--red);color:var(--white);
  padding:5px 9px;text-align:left;font-weight:600;
  font-size:.63rem;letter-spacing:.04em;white-space:nowrap;
  border:1px solid var(--red);
}
table.ft td{padding:5px 9px;border:1px solid var(--rule);color:var(--text);vertical-align:top}
table.ft td.app{background:var(--grey);font-weight:600;min-width:130px;max-width:176px}
table.ft td.app.crit{background:var(--pink)}
table.ft td.meta{font-size:.63rem;opacity:.8;white-space:nowrap}
table.ft td.ftype{font-family:var(--font-sb);font-style:italic;white-space:nowrap;font-size:.69rem}
table.ft td.detail{max-width:300px}
table.ft td.ctrl span{
  display:inline-block;padding:1px 5px;
  border:1px solid var(--rule);font-size:.59rem;
  background:var(--grey);white-space:nowrap;
}

/* Clean objects section */
.clean-section{margin-bottom:34px}
.clean-h{font-size:1rem;font-weight:700;color:var(--text);opacity:.55;
  border-bottom:1px solid var(--rule);padding-bottom:5px;margin-bottom:10px;
  display:flex;align-items:baseline;gap:10px;letter-spacing:.01em}
.clean-h .cnt{font-size:.62rem;font-weight:400;opacity:.7}
table.ct{width:100%;border-collapse:collapse;font-size:.7rem}
table.ct td{padding:4px 9px;border:1px solid var(--rule);color:var(--text)}
table.ct td.chk{width:22px;text-align:center;background:var(--grey);color:var(--red);font-weight:700}

/* CONFIDENTIAL footer */
.doc-footer{
  background:var(--white);border-top:1px solid var(--rule);
  text-align:center;padding:8px;
  font-size:.62rem;font-weight:700;color:var(--text);
  letter-spacing:.14em;max-width:1120px;margin:0 auto 18px;
  width:calc(100% - 36px);box-shadow:0 2px 16px rgba(0,0,0,.1);
}

/* ── Export PDF button ────────────────────────────────────────────── */
.pdf-btn{
  position:fixed;bottom:24px;right:24px;z-index:200;
  background:var(--red);color:var(--white);
  border:none;padding:8px 18px;font-family:var(--font);
  font-size:.72rem;font-weight:600;letter-spacing:.04em;
  cursor:pointer;box-shadow:0 2px 8px rgba(164,10,2,.35);
}
.pdf-btn:hover{background:#8a0802}
.pdf-btn:active{background:#6e0602}

@media print{
  @page{size:letter portrait;margin:1in}
  body{background:var(--white)}
  .doc-header{position:static;box-shadow:none;border-bottom:1.5pt solid #A40A02}
  .page-body{max-width:100%;margin:0;width:100%;box-shadow:none;display:block}
  #sidebar{display:none}
  #main{padding:0}
  .doc-footer{max-width:100%;margin:0;width:100%;box-shadow:none;border-top:0.5pt solid #BFBFBF}
  .pdf-btn{display:none}
  .severity-section{page-break-inside:avoid}
  .clean-section{page-break-inside:avoid}
  .section-h,.clean-h{page-break-after:avoid}
  table.ft tr{page-break-inside:avoid}
  table.meta-t{page-break-inside:avoid}
}
"""


def _render_section_table(sev: str, apps: list, col_header: str = "Object") -> str:
    is_crit = (sev == "Critical")
    rows = []
    for app in apps:
        n          = len(app["findings"])
        type_label = _humanize(app["type"]) if app["type"] else ""
        owners_str = ", ".join(app["owners"]) if app["owners"] else "—"
        created    = app["created"] or "—"
        app_cls    = "app crit" if is_crit else "app"

        for i, f in enumerate(app["findings"]):
            ftype     = _humanize(f.get("type", ""))
            detail    = f["action"]
            ctrl      = f["control"]
            ctrl_html = f'<span>{_esc(ctrl)}</span>' if ctrl else ""
            cells = ""
            if i == 0:
                cells += (
                    f'<td class="{app_cls}" rowspan="{n}">{_esc(app["name"])}</td>'
                    f'<td class="meta" rowspan="{n}">{_esc(type_label)}</td>'
                    f'<td class="meta" rowspan="{n}">{_esc(created)}</td>'
                    f'<td class="meta" rowspan="{n}">{_esc(owners_str)}</td>'
                )
            cells += (
                f'<td class="ftype">{_esc(ftype)}</td>'
                f'<td class="detail">{_esc(detail)}</td>'
                f'<td class="ctrl">{ctrl_html}</td>'
            )
            rows.append(f'<tr>{cells}</tr>')

    rows_html = "\n".join(rows)
    return (
        f'<table class="ft">'
        f'<thead><tr>'
        f'<th>{_esc(col_header)}</th><th>Category</th><th>Created</th>'
        f'<th>Owners</th><th>Finding</th><th>Detail / Action</th><th>Control</th>'
        f'</tr></thead>'
        f'<tbody>{rows_html}</tbody>'
        f'</table>'
    )


def _render_severity_section(sev: str, apps: list, section_num: int,
                             col_header: str = "Object") -> str:
    if not apps:
        return ""
    n_find      = sum(len(a["findings"]) for a in apps)
    count_label = f"{len(apps)} · {n_find} finding{'s' if n_find != 1 else ''}"
    table_html  = _render_section_table(sev, apps, col_header)
    return (
        f'<div class="severity-section" id="sev-{sev.lower()}">'
        f'<div class="section-h">'
        f'{section_num}. {_esc(sev)} Findings'
        f'<span class="cnt">{_esc(count_label)}</span>'
        f'</div>'
        f'{table_html}'
        f'</div>'
    )


def _render_html(by_sev: dict, counts: dict, total: int, clean: list,
                 last_scan: str, generated: str,
                 title: str, header_sub: str, controls: str,
                 col_header: str = "Object") -> str:
    total_objs = sum(len(v) for v in by_sev.values())

    doc_header = (
        f'<header class="doc-header">'
        f'<div class="doc-header-line">'
        f'<span class="left">NOF Metal Coatings North America</span>'
        f'<span class="right">IT and Information Systems</span>'
        f'</div>'
        f'<div class="doc-header-line">'
        f'<span class="left">IT &amp; Management Information Systems</span>'
        f'<span class="right">{_esc(header_sub)}</span>'
        f'</div>'
        f'<div class="doc-header-spacer"></div>'
        f'</header>'
    )

    nav_items = ""
    sec_num   = 0
    for sev in ("Critical", "High", "Medium", "Low"):
        if not by_sev.get(sev):
            continue
        sec_num += 1
        cnt_cls  = "nav-count" if sev == "Critical" else "nav-count dim"
        nav_items += (
            f'<a href="#sev-{sev.lower()}">'
            f'<span class="nav-sev">{sec_num}. {sev}</span>'
            f'<span class="{cnt_cls}">{counts.get(sev, 0)}</span>'
            f'</a>'
        )
    if clean:
        sec_num += 1
        nav_items += (
            f'<a href="#sev-clean">'
            f'<span class="nav-sev">{sec_num}. Clean</span>'
            f'<span class="nav-count dim">{len(clean)}</span>'
            f'</a>'
        )

    sidebar = (
        f'<aside id="sidebar">'
        f'<div>'
        f'<div class="sb-label">Contents</div>'
        f'<nav class="severity-nav">{nav_items}</nav>'
        f'</div>'
        f'<div class="sb-meta">'
        f'<strong>Generated</strong>{_esc(generated)}'
        f'<strong>Last Scan</strong>{_esc(last_scan) or "unknown"}'
        f'<strong>Tenant</strong>NOF Metal Coatings NA'
        f'<strong>Domain</strong>IT &amp; MIS'
        f'</div>'
        f'</aside>'
    )

    def _meta_row(label: str, value: str, crit: bool = False) -> str:
        val_cls = 'val crit' if crit else 'val'
        return (
            f'<tr><td class="lbl">{_esc(label)}</td>'
            f'<td class="{val_cls}">{_esc(value)}</td></tr>'
        )

    sev_summary = " · ".join(
        f'{counts[s]} {s}'
        for s in ("Critical", "High", "Medium", "Low")
        if counts.get(s, 0) > 0
    ) or "None"

    controls_row = (
        f'<tr><td class="lbl">Controls</td>'
        f'<td class="val">{_esc(controls)}</td></tr>'
        if controls else ""
    )
    meta_rows = (
        _meta_row("Report",    title)
        + _meta_row("Generated", generated)
        + _meta_row("Last Scan", last_scan or "unknown")
        + _meta_row("Tenant",    "NOF Metal Coatings North America")
        + _meta_row("Findings",  f"{total} total — {sev_summary}",
                    crit=counts.get("Critical", 0) > 0)
        + _meta_row("Objects",   f"{total_objs} with findings · {len(clean)} clean")
        + controls_row
    )
    meta_table = f'<table class="meta-t"><tbody>{meta_rows}</tbody></table>'

    sec_num       = 0
    sections_html = ""
    for sev in ("Critical", "High", "Medium", "Low"):
        if not by_sev.get(sev):
            continue
        sec_num += 1
        sections_html += _render_severity_section(sev, by_sev[sev], sec_num, col_header)

    clean_html = ""
    if clean:
        sec_num += 1
        items = [r.get("entity_name") or r.get("entity_id", "") for r in clean]
        rows  = []
        for j in range(0, len(items), 2):
            left  = _esc(items[j])
            right = _esc(items[j + 1]) if j + 1 < len(items) else ""
            rows.append(
                f'<tr>'
                f'<td class="chk">&#10003;</td><td>{left}</td>'
                f'<td class="chk">{"&#10003;" if right else ""}</td>'
                f'<td>{right}</td>'
                f'</tr>'
            )
        clean_html = (
            f'<div class="clean-section" id="sev-clean">'
            f'<div class="clean-h">'
            f'{sec_num}. Clean Objects'
            f'<span class="cnt">{len(clean)} · no open findings</span>'
            f'</div>'
            f'<table class="ct"><tbody>{"".join(rows)}</tbody></table>'
            f'</div>'
        )

    main = (
        f'<main id="main">'
        f'<h1 class="report-title">{_esc(title)}</h1>'
        f'<p class="report-org">NOF Metal Coatings North America'
        f' &nbsp;&middot;&nbsp; IT &amp; Management Information Systems</p>'
        f'{meta_table}'
        f'{sections_html}'
        f'{clean_html}'
        f'</main>'
    )

    return (
        f'<!DOCTYPE html>\n<html lang="en">\n<head>\n'
        f'<meta charset="utf-8">\n'
        f'<meta name="viewport" content="width=device-width,initial-scale=1">\n'
        f'<title>{_esc(title)} — {_esc(generated)}</title>\n'
        f'<style>{_REPORT_CSS}</style>\n'
        f'</head>\n<body>\n'
        f'{doc_header}\n'
        f'<div class="page-body">{sidebar}{main}</div>\n'
        f'<footer class="doc-footer">CONFIDENTIAL</footer>\n'
        f'<button class="pdf-btn" onclick="window.print()">Export PDF</button>\n'
        f'</body>\n</html>'
    )


def generate_html_report(domain: str, output_path: str = None) -> str:
    """Generate a styled HTML governance report for a scan domain and write it to disk.

    Reads open findings from the local KB for the given domain, groups objects by
    worst severity, and emits a self-contained branded HTML file.

    domain: one of entra, exo, ca, pp, pim, license, sharing, intune, purview, copilot
    output_path: optional absolute path override; defaults to reports/<dir>/YYYY-MM-DD.html

    Returns JSON: {"path": "...", "total_findings": N, "objects_with_findings": N, "clean_objects": N}
    """
    cfg = _DOMAIN_CONFIG.get(domain)
    if cfg is None:
        known = ", ".join(_DOMAIN_CONFIG)
        return json.dumps({"error": f"Unknown domain '{domain}'. Valid values: {known}"})

    if output_path is None:
        date_str    = datetime.now().strftime("%Y-%m-%d")
        reports_dir = Path(__file__).resolve().parent.parent.parent / "reports" / cfg["output_dir"]
        reports_dir.mkdir(parents=True, exist_ok=True)
        out = reports_dir / f"{date_str}.html"
    else:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)

    with get_connection() as conn:
        rows = conn.execute("""
            SELECT
                f.object_id, f.object_name, f.object_type,
                f.finding_type, f.severity, f.recommended_action, f.securesketch_control,
                s.properties
            FROM findings f
            LEFT JOIN tenant_snapshot s
                ON s.entity_id = f.object_id AND s.entity_type = f.object_type
            WHERE f.domain = ? AND f.status = 'open'
            ORDER BY f.object_name,
                CASE f.severity
                    WHEN 'Critical' THEN 1 WHEN 'High'   THEN 2
                    WHEN 'Medium'   THEN 3 WHEN 'Low'    THEN 4 ELSE 5 END
        """, (domain,)).fetchall()

        clean_type = cfg.get("clean_type")
        if clean_type:
            clean_rows = conn.execute("""
                SELECT s.entity_id, s.entity_name, s.entity_type
                FROM tenant_snapshot s
                WHERE s.domain = ? AND s.entity_type = ?
                  AND NOT EXISTS (
                    SELECT 1 FROM findings f
                    WHERE f.object_id = s.entity_id AND f.domain = ? AND f.status = 'open'
                  )
                ORDER BY s.entity_name
            """, (domain, clean_type, domain)).fetchall()
        else:
            clean_rows = []

        scan_row = conn.execute(
            "SELECT MAX(last_scanned) as ts FROM tenant_snapshot WHERE domain = ?",
            (domain,)
        ).fetchone()

    objs: dict = {}
    for row in rows:
        oid = row["object_id"]
        if oid not in objs:
            props       = json.loads(row["properties"] or "{}")
            owners_list = props.get("owners", [])
            owners      = [o.get("userPrincipalName") or o.get("displayName", "")
                          for o in owners_list]
            objs[oid]   = {
                "id":       oid,
                "name":     row["object_name"] or oid,
                "type":     row["object_type"],
                "created":  (props.get("createdDateTime") or "")[:10],
                "owners":   owners,
                "findings": [],
                "worst_sev": "Low",
            }
        objs[oid]["findings"].append({
            "severity": row["severity"],
            "type":     row["finding_type"] or "",
            "action":   row["recommended_action"] or "",
            "control":  row["securesketch_control"] or "",
        })

    by_sev: dict = {"Critical": [], "High": [], "Medium": [], "Low": []}
    for obj in sorted(
        objs.values(),
        key=lambda a: (
            _SEV_RANK.get(
                min(a["findings"], key=lambda f: _SEV_RANK.get(f["severity"], 99))["severity"],
                99,
            ),
            a["name"].lower(),
        ),
    ):
        worst = min(obj["findings"], key=lambda f: _SEV_RANK.get(f["severity"], 99))["severity"]
        obj["worst_sev"] = worst
        if worst in by_sev:
            by_sev[worst].append(obj)

    counts: dict = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
    for obj in objs.values():
        for f in obj["findings"]:
            if f["severity"] in counts:
                counts[f["severity"]] += 1
    total = sum(counts.values())

    controls = cfg.get("controls", "")
    if not controls:
        controls_set = sorted(set(
            f["control"]
            for obj in objs.values()
            for f in obj["findings"]
            if f["control"]
        ))
        controls = " · ".join(controls_set)

    last_scan = (
        (scan_row["ts"] or "")[:19].replace("T", " ")
        if scan_row and scan_row["ts"] else ""
    )
    generated = datetime.now().strftime("%Y-%m-%d %H:%M")

    html_content = _render_html(
        by_sev, counts, total,
        [dict(r) for r in clean_rows],
        last_scan, generated,
        title=cfg["title"],
        header_sub=cfg["header_sub"],
        controls=controls,
        col_header=cfg.get("col_header", "Object"),
    )
    out.write_text(html_content, encoding="utf-8")
    return json.dumps({
        "path":                  str(out),
        "total_findings":        total,
        "objects_with_findings": len(objs),
        "clean_objects":         len(clean_rows),
    })
