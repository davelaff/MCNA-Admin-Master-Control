import json
import uuid
from datetime import datetime, timezone
from db import get_connection

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

def kb_get_findings(domain: str = None, severity: str = None, status: str = "open") -> str:
    clauses = ["status = ?"]
    params: list = [status]
    if domain:
        clauses.append("domain = ?")
        params.append(domain)
    if severity:
        clauses.append("severity = ?")
        params.append(severity)
    where = " AND ".join(clauses)
    with get_connection() as conn:
        rows = conn.execute(
            f"SELECT * FROM findings WHERE {where} ORDER BY severity, domain", params
        ).fetchall()
    return json.dumps([dict(r) for r in rows], indent=2)

def kb_update_finding(
    finding_id: str,
    status: str,
    notes: str = None,
    closure_evidence_id: str = None,
) -> str:
    if status not in ("acknowledged", "resolved"):
        return json.dumps({"error": "status must be 'acknowledged' or 'resolved'"})
    if closure_evidence_id and status != "resolved":
        return json.dumps({"error": "closure_evidence_id may only be set when status is 'resolved'"})
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE findings
            SET status = ?,
                notes = COALESCE(?, notes),
                closure_evidence_id = COALESCE(?, closure_evidence_id),
                last_seen = ?
            WHERE finding_id = ?
            """,
            (status, notes, closure_evidence_id, _now(), finding_id),
        )
        changed = conn.execute("SELECT changes()").fetchone()[0]
        if not changed:
            return json.dumps({"error": f"finding '{finding_id}' not found"})
        row = conn.execute(
            "SELECT * FROM findings WHERE finding_id = ?", (finding_id,)
        ).fetchone()
    return json.dumps(dict(row))

def kb_dismiss(finding_id: str, reason: str) -> str:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT finding_id FROM findings WHERE finding_id=?", (finding_id,)
        ).fetchone()
        if not row:
            return json.dumps({"error": f"finding '{finding_id}' not found"})
        conn.execute("UPDATE findings SET status='dismissed' WHERE finding_id=?", (finding_id,))
        conn.execute(
            "INSERT OR REPLACE INTO dismissed VALUES (?,?,?)",
            (finding_id, _now(), reason),
        )
    return json.dumps({"dismissed": finding_id, "reason": reason})

def kb_get_snapshot(entity_type: str = None, domain: str = None) -> str:
    clauses = []
    params: list = []
    if entity_type:
        clauses.append("entity_type = ?")
        params.append(entity_type)
    if domain:
        clauses.append("domain = ?")
        params.append(domain)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    with get_connection() as conn:
        rows = conn.execute(
            f"SELECT * FROM tenant_snapshot {where} ORDER BY domain, entity_type", params
        ).fetchall()
    return json.dumps([dict(r) for r in rows], indent=2)

def kb_diff_snapshot(entity_type: str, domain: str, current: list) -> str:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT entity_id, properties FROM tenant_snapshot WHERE entity_type=? AND domain=?",
            (entity_type, domain),
        ).fetchall()
    prior = {r["entity_id"]: json.loads(r["properties"] or "{}") for r in rows}
    current_ids = {item["id"] for item in current}
    prior_ids = set(prior.keys())
    changed = []
    for item in current:
        eid = item["id"]
        if eid in prior and json.dumps(item, sort_keys=True) != json.dumps(prior[eid], sort_keys=True):
            changed.append({"id": eid, "before": prior[eid], "after": item})
    return json.dumps({
        "new": [i for i in current if i["id"] in (current_ids - prior_ids)],
        "removed": list(prior_ids - current_ids),
        "changed": changed,
    }, indent=2)
