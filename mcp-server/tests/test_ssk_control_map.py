import json
import re
from pathlib import Path

from tools.ssk import ssk_list_controls
from tools.ssk_loader import load_catalog
from tools.ssk_control_map import all_aliases, canonical_control_id


def _seed_catalog() -> None:
    catalog_path = Path(__file__).resolve().parent.parent / "kb" / "catalog-imports" / "2026-01-01.json"
    load_catalog(json.loads(catalog_path.read_text(encoding="utf-8")))


def _emitted_legacy_codes() -> set[str]:
    tools_dir = Path(__file__).resolve().parent.parent / "tools"
    pattern = re.compile(r'securesketch_control="([^"]+)"')
    emitted: set[str] = set()
    for name in ("entra.py", "ca.py", "pp.py", "pim.py", "license.py", "sharing.py", "intune.py", "purview.py", "exo.py"):
        emitted.update(pattern.findall((tools_dir / name).read_text(encoding="utf-8")))
    return emitted


def test_every_emitted_legacy_code_is_present_in_alias_file(db):
    assert _emitted_legacy_codes() <= set(all_aliases())


def test_every_alias_resolves_to_imported_control_id(db):
    _seed_catalog()
    imported_ids = {row["control_id"] for row in json.loads(ssk_list_controls())}

    for legacy_code, canonical in all_aliases().items():
        assert canonical in imported_ids, f"{legacy_code} -> {canonical} is not in imported catalog"
        assert canonical_control_id(legacy_code) == canonical


def test_all_aliases_match_emitted_legacy_codes():
    assert set(all_aliases()) == _emitted_legacy_codes()


def test_unknown_control_id_passes_through_unchanged():
    assert canonical_control_id("06-3") == "06-3"
