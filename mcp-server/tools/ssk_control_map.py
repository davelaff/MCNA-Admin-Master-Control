import json
from pathlib import Path


ALIAS_PATH = Path(__file__).resolve().parent.parent / "kb" / "ssk_control_aliases.json"


def all_aliases() -> dict[str, str]:
    return json.loads(ALIAS_PATH.read_text(encoding="utf-8"))


def canonical_control_id(control_ref: str | None) -> str | None:
    if control_ref is None:
        return None
    return all_aliases().get(control_ref, control_ref)
