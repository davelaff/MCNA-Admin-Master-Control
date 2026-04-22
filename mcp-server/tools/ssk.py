import json
from pathlib import Path
from tools.ssk_parser import parse_catalog, CatalogSourceError
from tools.ssk_loader import load_catalog
from db import get_connection


def _default_intermediate_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "kb" / "catalog-imports"


def ssk_import_catalog(
    docx_path: str,
    version: str,
    dry_run: bool = False,
    intermediate_dir: str | None = None,
) -> str:
    try:
        parsed = parse_catalog(Path(docx_path), source_version=version)
    except CatalogSourceError as e:
        return json.dumps({"error": str(e), "error_type": "CatalogSourceError"})

    out_dir = Path(intermediate_dir) if intermediate_dir else _default_intermediate_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    intermediate_path = out_dir / f"{version}.json"
    intermediate_path.write_text(json.dumps(parsed, indent=2), encoding="utf-8")

    response: dict = {
        "dry_run": dry_run,
        "parsed_controls": len(parsed["controls"]),
        "parse_failures": parsed["parse_failures"],
        "warnings": parsed["warnings"],
        "intermediate_json_path": str(intermediate_path),
        "written_controls": 0,
        "written_actions": 0,
        "history_moved": 0,
    }

    if dry_run:
        return json.dumps(response, indent=2)

    load_result = load_catalog(parsed)
    response.update({
        "written_controls": load_result["written_controls"],
        "written_actions": load_result["written_actions"],
        "history_moved": load_result["history_moved"],
    })
    return json.dumps(response, indent=2)


def ssk_list_controls(category: str | None = None) -> str:
    with get_connection() as conn:
        if category:
            rows = conn.execute(
                "SELECT control_id, category, category_name, title "
                "FROM ssk_controls WHERE category = ? ORDER BY control_id",
                (category,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT control_id, category, category_name, title "
                "FROM ssk_controls ORDER BY control_id"
            ).fetchall()
    return json.dumps([dict(r) for r in rows], indent=2)


def ssk_status(control_id: str) -> str:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT s.*, c.title, c.category, c.category_name "
            "FROM ssk_control_status s "
            "JOIN ssk_controls c ON c.control_id = s.control_id "
            "WHERE s.control_id = ?",
            (control_id,),
        ).fetchone()
    if row is None:
        return json.dumps({"error": f"control '{control_id}' not found"})
    return json.dumps(dict(row), indent=2)


def ssk_status_all(below_target: bool = False, due_before: str | None = None) -> str:
    clauses: list[str] = []
    params: list = []
    if below_target:
        clauses.append("s.current_maturity != 'regularly_reviewed'")
    if due_before:
        clauses.append("s.next_review_due IS NOT NULL AND s.next_review_due < ?")
        params.append(due_before)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    sql = (
        "SELECT s.*, c.title, c.category, c.category_name "
        "FROM ssk_control_status s "
        "JOIN ssk_controls c ON c.control_id = s.control_id "
        f"{where} ORDER BY c.control_id"
    )
    with get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()
    return json.dumps([dict(r) for r in rows], indent=2)


def ssk_gaps() -> str:
    with get_connection() as conn:
        total = conn.execute("SELECT COUNT(*) AS c FROM ssk_control_status").fetchone()["c"]
        at_target = conn.execute(
            "SELECT COUNT(*) AS c FROM ssk_control_status "
            "WHERE current_maturity = 'regularly_reviewed'"
        ).fetchone()["c"]
        gap_rows = conn.execute(
            "SELECT s.control_id, s.current_maturity, s.target_maturity, "
            " s.last_reviewed_at, s.next_review_due, s.gap_summary, "
            " c.title, c.category, c.category_name "
            "FROM ssk_control_status s "
            "JOIN ssk_controls c ON c.control_id = s.control_id "
            "WHERE s.current_maturity != 'regularly_reviewed' "
            "ORDER BY c.control_id"
        ).fetchall()

    return json.dumps({
        "total_controls": total,
        "at_target": at_target,
        "below_target": total - at_target,
        "gaps": [dict(r) for r in gap_rows],
    }, indent=2)


def ssk_get_control(control_id: str) -> str:
    with get_connection() as conn:
        control = conn.execute(
            "SELECT * FROM ssk_controls WHERE control_id = ?", (control_id,)
        ).fetchone()
        if control is None:
            return json.dumps({"error": f"control '{control_id}' not found"})
        actions = conn.execute(
            "SELECT action_id, sequence, action_text, implementation_status, "
            " implementation_notes, owner "
            "FROM ssk_recommended_actions WHERE control_id = ? ORDER BY sequence",
            (control_id,),
        ).fetchall()

    payload = dict(control)
    if payload.get("status_descriptions"):
        payload["status_descriptions"] = json.loads(payload["status_descriptions"])
    payload["recommended_actions"] = [dict(a) for a in actions]
    return json.dumps(payload, indent=2)
