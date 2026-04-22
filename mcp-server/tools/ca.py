import json
import uuid
from datetime import datetime, timezone
from auth import get_token
from graph import graph_get, graph_get_all, GraphError
from db import get_connection
from tools.ssk_control_map import canonical_control_id

DOMAIN = "ca"

CONTRIBUTES_TO = {
    "__tool__": [
        canonical_control_id("CA-POL-01"),
        canonical_control_id("CA-POL-02"),
        canonical_control_id("CA-COV-01"),
    ],
    "report_only_policy":    [canonical_control_id("CA-POL-01")],
    "broken_group_reference": [canonical_control_id("CA-POL-02")],
    "no_ca_coverage":        [canonical_control_id("CA-COV-01")],
}

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

def _upsert_snapshot(conn, entity_type: str, entity_id: str, entity_name: str, props: dict) -> None:
    conn.execute("""
        INSERT INTO tenant_snapshot (entity_type, entity_id, entity_name, domain, properties, last_scanned)
        VALUES (?,?,?,?,?,?)
        ON CONFLICT(entity_type, entity_id) DO UPDATE SET
            entity_name=excluded.entity_name,
            properties=excluded.properties,
            last_scanned=excluded.last_scanned
    """, (entity_type, entity_id, entity_name, DOMAIN, json.dumps(props), _now()))

def _upsert_finding(conn, object_type: str, object_id: str, object_name: str,
                    finding_type: str, severity: str, recommended_action: str,
                    securesketch_control: str = None) -> str:
    finding_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{DOMAIN}.{object_type}.{object_id}.{finding_type}"))
    existing = conn.execute("SELECT status FROM findings WHERE finding_id=?", (finding_id,)).fetchone()
    if existing and existing["status"] == "dismissed":
        return finding_id
    now = _now()
    conn.execute("""
        INSERT INTO findings
            (finding_id,domain,object_type,object_id,object_name,finding_type,
             severity,securesketch_control,recommended_action,status,first_seen,last_seen)
        VALUES (?,?,?,?,?,?,?,?,?,'open',?,?)
        ON CONFLICT(finding_id) DO UPDATE SET last_seen=excluded.last_seen, object_name=excluded.object_name
    """, (finding_id, DOMAIN, object_type, object_id, object_name, finding_type,
          severity, securesketch_control, recommended_action, now, now))
    return finding_id

def ca_scan_policies() -> str:
    """Scan CA policies: report-only state, broken group references, disabled policies."""
    token = get_token()
    policies = graph_get_all("/identity/conditionalAccess/policies", token)

    findings_count = 0
    with get_connection() as conn:
        for policy in policies:
            pid, name = policy["id"], policy.get("displayName", policy["id"])
            state = policy.get("state", "unknown")
            _upsert_snapshot(conn, "ca_policy", pid, name, policy)

            if state == "enabledForReportingButNotEnforced":
                _upsert_finding(conn, "ca_policy", pid, name, "report_only_policy", "Medium",
                               "Policy is report-only and not enforced. Enable or remove.",
                               securesketch_control="CA-POL-01")
                findings_count += 1

            conditions = policy.get("conditions", {})
            users = conditions.get("users", {})
            for gid in users.get("includeGroups", []) + users.get("excludeGroups", []):
                try:
                    graph_get(f"/groups/{gid}?$select=id", token)
                except GraphError as e:
                    if e.status == 404:
                        _upsert_finding(conn, "ca_policy", pid, name, "broken_group_reference", "High",
                                       f"Policy references deleted group {gid}.",
                                       securesketch_control="CA-POL-02")
                        findings_count += 1

    return json.dumps({
        "scanned": len(policies),
        "findings": findings_count,
        "enabled": sum(1 for p in policies if p.get("state") == "enabled"),
        "report_only": sum(1 for p in policies if p.get("state") == "enabledForReportingButNotEnforced"),
        "disabled": sum(1 for p in policies if p.get("state") == "disabled"),
    })

def ca_scan_coverage_gaps() -> str:
    """Identify member users not covered by any enabled CA policy."""
    token = get_token()
    policies = graph_get_all(
        "/identity/conditionalAccess/policies?$filter=state eq 'enabled'", token
    )

    if not policies:
        return json.dumps({
            "warning": "No enabled CA policies found. All users are uncovered.",
            "uncovered_count": "unknown",
        })

    covered_ids: set = set()
    all_included = False

    for policy in policies:
        inc_users = policy.get("conditions", {}).get("users", {}).get("includeUsers", [])
        if "All" in inc_users:
            all_included = True
            break
        covered_ids.update(inc_users)
        for gid in policy.get("conditions", {}).get("users", {}).get("includeGroups", []):
            try:
                members = graph_get_all(f"/groups/{gid}/members?$select=id", token)
                covered_ids.update(m["id"] for m in members)
            except GraphError:
                pass

    if all_included:
        return json.dumps({"message": "All users covered by at least one enabled CA policy.", "uncovered_count": 0})

    users = graph_get_all(
        "/users?$filter=userType eq 'Member'&$select=id,displayName,userPrincipalName&$top=999", token
    )
    uncovered = [u for u in users if u["id"] not in covered_ids]

    findings_count = 0
    with get_connection() as conn:
        for u in uncovered:
            _upsert_finding(conn, "user", u["id"], u.get("displayName", u["id"]),
                           "no_ca_coverage", "High",
                           "User is not included in any enabled Conditional Access policy.",
                           securesketch_control="CA-COV-01")
            findings_count += 1

    return json.dumps({
        "total_users": len(users),
        "uncovered_count": len(uncovered),
        "findings": findings_count,
        "uncovered_sample": [u.get("userPrincipalName") for u in uncovered[:10]],
    })
