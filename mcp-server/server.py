from mcp.server.fastmcp import FastMCP
from db import init_db
from tools.kb import (
    kb_get_findings, kb_update_finding, kb_dismiss,
    kb_get_snapshot, kb_diff_snapshot,
)
from tools.entra import entra_scan_app_regs, entra_scan_guests
from tools.ca import ca_scan_policies, ca_scan_coverage_gaps
from tools.pp import pp_scan_environments, pp_scan_apps

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

if __name__ == "__main__":
    init_db()
    mcp.run()
