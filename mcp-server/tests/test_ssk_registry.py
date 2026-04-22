import json

from tools.ssk_registry import registry_add, registry_list, registry_get, registry_retire


# ---------------------------------------------------------------------------
# registry_add
# ---------------------------------------------------------------------------

def test_registry_add_persists_active_entry(db):
    result = json.loads(
        registry_add(
            registry_name="approved_software",
            entry_key="7zip",
            entry_data={"publisher": "7-Zip", "approved": True},
            control_ids=["06-3"],
            pointer="https://sharepoint.example/item",
            effective_from="2026-04-22T00:00:00+00:00",
        )
    )
    assert result["registry_name"] == "approved_software"
    assert result["entry_key"] == "7zip"
    assert result["status"] == "active"


def test_registry_add_rejects_active_duplicate(db):
    registry_add("approved_software", "7zip", {"approved": True}, ["06-3"])
    result = json.loads(
        registry_add("approved_software", "7zip", {"approved": False}, ["06-3"])
    )
    assert "error" in result
    assert result["error_type"] == "RegistryConflictError"


def test_registry_add_allows_same_key_in_different_registry(db):
    registry_add("approved_software", "7zip", {"approved": True}, ["06-3"])
    result = json.loads(
        registry_add("blocked_software", "7zip", {"blocked": True}, ["06-3"])
    )
    assert result["status"] == "active"


def test_registry_add_allows_reuse_of_retired_key(db):
    registry_add("approved_software", "7zip", {"approved": True}, ["06-3"])
    registry_retire("approved_software", "7zip", "Replaced")
    result = json.loads(
        registry_add("approved_software", "7zip", {"approved": True, "version": 2}, ["06-3"])
    )
    assert result["status"] == "active"


# ---------------------------------------------------------------------------
# registry_list
# ---------------------------------------------------------------------------

def test_registry_list_returns_active_entries(db):
    registry_add("approved_software", "7zip", {"approved": True}, ["06-3"])
    registry_add("approved_software", "notepad++", {"approved": True}, ["06-3"])
    result = json.loads(registry_list("approved_software"))
    keys = [r["entry_key"] for r in result]
    assert "7zip" in keys
    assert "notepad++" in keys


def test_registry_list_excludes_retired(db):
    registry_add("approved_software", "7zip", {"approved": True}, ["06-3"])
    registry_retire("approved_software", "7zip", "Dropped")
    result = json.loads(registry_list("approved_software"))
    assert not any(r["entry_key"] == "7zip" for r in result)


def test_registry_list_filters_by_status(db):
    registry_add("approved_software", "7zip", {"approved": True}, ["06-3"])
    registry_retire("approved_software", "7zip", "Old")
    result = json.loads(registry_list("approved_software", status="retired"))
    assert any(r["entry_key"] == "7zip" for r in result)


def test_registry_list_no_registry_name_returns_all_active(db):
    registry_add("approved_software", "7zip", {"approved": True}, ["06-3"])
    registry_add("allowed_ports", "443", {"protocol": "HTTPS"}, ["06-3"])
    result = json.loads(registry_list())
    names = {r["registry_name"] for r in result}
    assert "approved_software" in names
    assert "allowed_ports" in names


# ---------------------------------------------------------------------------
# registry_get
# ---------------------------------------------------------------------------

def test_registry_get_returns_active_entry(db):
    registry_add("approved_software", "7zip", {"approved": True}, ["06-3"])
    result = json.loads(registry_get("approved_software", "7zip"))
    assert result["entry_key"] == "7zip"
    assert result["status"] == "active"


def test_registry_get_returns_error_for_unknown_key(db):
    result = json.loads(registry_get("approved_software", "missing"))
    assert "error" in result


# ---------------------------------------------------------------------------
# registry_retire
# ---------------------------------------------------------------------------

def test_registry_retire_marks_entry_retired(db):
    registry_add("approved_software", "7zip", {"approved": True}, ["06-3"])
    result = json.loads(registry_retire("approved_software", "7zip", "Replaced by managed package"))
    assert result["status"] == "retired"


def test_registry_retire_embeds_reason_in_entry_data(db):
    registry_add("approved_software", "7zip", {"approved": True}, ["06-3"])
    registry_retire("approved_software", "7zip", "End of life")
    result = json.loads(registry_get("approved_software", "7zip", include_retired=True))
    data = json.loads(result["entry_data"])
    assert data.get("retire_reason") == "End of life"


def test_registry_retire_sets_effective_to(db):
    registry_add("approved_software", "7zip", {"approved": True}, ["06-3"])
    result = json.loads(registry_retire("approved_software", "7zip", "Old"))
    assert result["effective_to"] is not None


def test_registry_retire_returns_error_for_unknown_key(db):
    result = json.loads(registry_retire("approved_software", "missing", "No reason"))
    assert "error" in result
