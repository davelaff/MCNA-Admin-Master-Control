import functools
import json as _json
from mcp.server.fastmcp import FastMCP
from db import init_db
from tools.kb import (
    kb_get_findings, kb_update_finding, kb_dismiss,
    kb_get_snapshot, kb_diff_snapshot,
)
from tools.entra import entra_scan_app_regs, entra_scan_guests, entra_generate_html_report
from tools.reporting import generate_html_report
from tools.ca import ca_scan_policies, ca_scan_coverage_gaps
from tools.pp import pp_scan_environments, pp_scan_apps
from tools.pim import pim_scan_role_assignments, pim_scan_role_definitions
from tools.license import license_scan_skus, license_scan_users
from tools.sharing import sharing_scan_sites
from tools.intune import intune_scan_devices, intune_scan_compliance_policies
from tools.purview import purview_scan_labels, purview_scan_audit
from tools.exo import exo_scan_mailboxes, exo_scan_forwarding
from tools.copilot import copilot_scan_licenses, copilot_scan_settings
from tools.mail import mail_send_summary
from tools.remediation import (
    remediation_create_plan,
    remediation_add_action,
    remediation_list_actions,
    remediation_approve_action,
    remediation_reject_action,
    remediation_export_queue,
    remediation_close_action,
)
from tools.ssk import (
    ssk_import_catalog, ssk_list_controls, ssk_get_control,
    ssk_status, ssk_status_all, ssk_gaps,
)
from tools.ssk_evidence import (
    ssk_link_evidence, ssk_list_evidence, ssk_evidence_expiring, ssk_verify_pointers,
)
from tools.ssk_reviews import (
    ssk_record_review,
    ssk_review_history,
    ssk_alerts,
    ssk_due,
    ssk_review_notifications,
)
from tools.ssk_actions import ssk_mark_action, ssk_action_queue
from tools.ssk_registry import registry_add, registry_list, registry_get, registry_retire
from tools.ssk_binder import ssk_coverage, ssk_export_binder
from tools.ssk_matrix import (
    ssk_backfill_scan_evidence,
    ssk_control_matrix,
    ssk_evidence_gaps,
    ssk_control_coverage_detail,
    ssk_maturity_dashboard,
    ssk_quarterly_packet,
    ssk_portal_submission_packet,
)
from tools.ssk_auditor import ssk_auditor_package, ssk_run_control_check

def _scan(fn, domain: str):
    """Wrap a scan tool to auto-generate the domain HTML report after each run."""
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        result = fn(*args, **kwargs)
        try:
            html = _json.loads(generate_html_report(domain=domain))
            r = _json.loads(result)
            r["report"] = html.get("path", "")
            return _json.dumps(r)
        except Exception:
            return result
    return wrapper


mcp = FastMCP(
    "mcna-amc",
    instructions=(
        "MCNA Admin Master Control — Microsoft estate governance tools. "
        "All scan tools write findings to the local SQLite knowledge base before returning. "
        "Use kb_get_findings to query accumulated findings across sessions."
    ),
)

# KB tools
mcp.tool()(kb_get_findings)
mcp.tool()(kb_update_finding)
mcp.tool()(kb_dismiss)
mcp.tool()(kb_get_snapshot)
mcp.tool()(kb_diff_snapshot)

# Entra tools — HTML report auto-generated after each scan
mcp.tool()(_scan(entra_scan_app_regs, "entra"))
mcp.tool()(_scan(entra_scan_guests, "entra"))
mcp.tool()(entra_generate_html_report)

# Generic HTML report (on-demand, any domain)
mcp.tool()(generate_html_report)

# CA tools
mcp.tool()(_scan(ca_scan_policies, "ca"))
mcp.tool()(_scan(ca_scan_coverage_gaps, "ca"))

# PP tools
mcp.tool()(_scan(pp_scan_environments, "pp"))
mcp.tool()(_scan(pp_scan_apps, "pp"))

# PIM tools
mcp.tool()(_scan(pim_scan_role_assignments, "pim"))
mcp.tool()(_scan(pim_scan_role_definitions, "pim"))

# License tools
mcp.tool()(_scan(license_scan_skus, "license"))
mcp.tool()(_scan(license_scan_users, "license"))

# Sharing tools
mcp.tool()(_scan(sharing_scan_sites, "sharing"))

# Intune tools
mcp.tool()(_scan(intune_scan_devices, "intune"))
mcp.tool()(_scan(intune_scan_compliance_policies, "intune"))

# Purview tools
mcp.tool()(_scan(purview_scan_labels, "purview"))
mcp.tool()(_scan(purview_scan_audit, "purview"))

# Exchange Online tools
mcp.tool()(_scan(exo_scan_mailboxes, "exo"))
mcp.tool()(_scan(exo_scan_forwarding, "exo"))

# Copilot tools
mcp.tool()(_scan(copilot_scan_licenses, "copilot"))
mcp.tool()(_scan(copilot_scan_settings, "copilot"))

# Mail tools
mcp.tool()(mail_send_summary)

# Remediation tools
mcp.tool()(remediation_create_plan)
mcp.tool()(remediation_add_action)
mcp.tool()(remediation_list_actions)
mcp.tool()(remediation_approve_action)
mcp.tool()(remediation_reject_action)
mcp.tool()(remediation_export_queue)
mcp.tool()(remediation_close_action)

# Secure SketCH tools (Phase 2a)
mcp.tool()(ssk_import_catalog)
mcp.tool()(ssk_list_controls)
mcp.tool()(ssk_get_control)
mcp.tool()(ssk_status)
mcp.tool()(ssk_status_all)
mcp.tool()(ssk_gaps)

# Secure SketCH tools (Phase 2b — evidence, reviews, actions, registry, binder)
mcp.tool()(ssk_link_evidence)
mcp.tool()(ssk_list_evidence)
mcp.tool()(ssk_evidence_expiring)
mcp.tool()(ssk_verify_pointers)
mcp.tool()(ssk_record_review)
mcp.tool()(ssk_review_history)
mcp.tool()(ssk_alerts)
mcp.tool()(ssk_due)
mcp.tool()(ssk_review_notifications)
mcp.tool()(ssk_mark_action)
mcp.tool()(ssk_action_queue)
mcp.tool()(registry_add)
mcp.tool()(registry_list)
mcp.tool()(registry_get)
mcp.tool()(registry_retire)
mcp.tool()(ssk_coverage)
mcp.tool()(ssk_export_binder)
mcp.tool()(ssk_backfill_scan_evidence)
mcp.tool()(ssk_control_matrix)
mcp.tool()(ssk_evidence_gaps)
mcp.tool()(ssk_control_coverage_detail)
mcp.tool()(ssk_maturity_dashboard)
mcp.tool()(ssk_quarterly_packet)
mcp.tool()(ssk_portal_submission_packet)
mcp.tool()(ssk_auditor_package)
mcp.tool()(ssk_run_control_check)

if __name__ == "__main__":
    init_db()
    mcp.run()
