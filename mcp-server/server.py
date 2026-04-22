from mcp.server.fastmcp import FastMCP
from db import init_db
from tools.kb import (
    kb_get_findings, kb_update_finding, kb_dismiss,
    kb_get_snapshot, kb_diff_snapshot,
)
from tools.entra import entra_scan_app_regs, entra_scan_guests
from tools.ca import ca_scan_policies, ca_scan_coverage_gaps
from tools.pp import pp_scan_environments, pp_scan_apps
from tools.pim import pim_scan_role_assignments, pim_scan_role_definitions
from tools.ssk import (
    ssk_import_catalog, ssk_list_controls, ssk_get_control,
    ssk_status, ssk_status_all, ssk_gaps,
)
from tools.ssk_evidence import (
    ssk_link_evidence, ssk_list_evidence, ssk_evidence_expiring, ssk_verify_pointers,
)
from tools.ssk_reviews import ssk_record_review, ssk_review_history, ssk_alerts, ssk_due
from tools.ssk_actions import ssk_mark_action, ssk_action_queue
from tools.ssk_registry import registry_add, registry_list, registry_get, registry_retire
from tools.ssk_binder import ssk_coverage, ssk_export_binder

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

# Entra tools
mcp.tool()(entra_scan_app_regs)
mcp.tool()(entra_scan_guests)

# CA tools
mcp.tool()(ca_scan_policies)
mcp.tool()(ca_scan_coverage_gaps)

# PP tools
mcp.tool()(pp_scan_environments)
mcp.tool()(pp_scan_apps)

# PIM tools
mcp.tool()(pim_scan_role_assignments)
mcp.tool()(pim_scan_role_definitions)

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
mcp.tool()(ssk_mark_action)
mcp.tool()(ssk_action_queue)
mcp.tool()(registry_add)
mcp.tool()(registry_list)
mcp.tool()(registry_get)
mcp.tool()(registry_retire)
mcp.tool()(ssk_coverage)
mcp.tool()(ssk_export_binder)

if __name__ == "__main__":
    init_db()
    mcp.run()
