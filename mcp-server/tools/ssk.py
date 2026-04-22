import json
from pathlib import Path
from tools.ssk_parser import parse_catalog, CatalogSourceError
from tools.ssk_loader import load_catalog


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
