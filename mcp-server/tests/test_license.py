import json
from unittest.mock import patch
from tools.license import license_scan_skus, license_scan_users
from tools.kb import kb_get_findings

FAKE_TOKEN = "fake"


def _sku(part: str, sku_id: str = None, prepaid: int = 10, consumed: int = 5) -> dict:
    return {
        "id": f"tenant_{part}",
        "skuId": sku_id or f"sku-{part}",
        "skuPartNumber": part,
        "prepaidUnits": {"enabled": prepaid, "suspended": 0, "warning": 0},
        "consumedUnits": consumed,
        "servicePlans": [],
    }


def _user(uid: str, upn: str, enabled: bool = True, sku_ids: list = None) -> dict:
    return {
        "id": uid,
        "userPrincipalName": upn,
        "displayName": upn.split("@")[0],
        "accountEnabled": enabled,
        "assignedLicenses": [{"skuId": s, "disabledPlans": []} for s in (sku_ids or [])],
    }


# -------------------------------------------------------- license_scan_skus


def test_overconsumed_sku_flags_high(db):
    skus = [_sku("O365_BUSINESS_PREMIUM", prepaid=10, consumed=12)]
    with patch("tools.license.get_token", return_value=FAKE_TOKEN), \
         patch("tools.license.graph_get_all", return_value=skus):
        license_scan_skus()
    fs = json.loads(kb_get_findings(domain="license"))
    assert any(f["finding_type"] == "sku_overconsumed" and f["severity"] == "High" for f in fs)


def test_balanced_sku_not_flagged(db):
    skus = [_sku("O365_BUSINESS_PREMIUM", prepaid=10, consumed=8)]
    with patch("tools.license.get_token", return_value=FAKE_TOKEN), \
         patch("tools.license.graph_get_all", return_value=skus):
        license_scan_skus()
    fs = json.loads(kb_get_findings(domain="license"))
    assert not any(f["finding_type"] == "sku_overconsumed" for f in fs)
    assert not any(f["finding_type"] == "sku_unused" for f in fs)


def test_unused_prepaid_sku_flags_low(db):
    skus = [_sku("VISIOCLIENT", prepaid=5, consumed=0)]
    with patch("tools.license.get_token", return_value=FAKE_TOKEN), \
         patch("tools.license.graph_get_all", return_value=skus):
        license_scan_skus()
    fs = json.loads(kb_get_findings(domain="license"))
    assert any(f["finding_type"] == "sku_unused" and f["severity"] == "Low" for f in fs)


def test_free_sku_with_zero_consumption_not_flagged(db):
    # FLOW_FREE-style SKUs: prepaid=10000 (self-serve pool), consumed=0 is normal
    skus = [_sku("FLOW_FREE", prepaid=10000, consumed=0)]
    with patch("tools.license.get_token", return_value=FAKE_TOKEN), \
         patch("tools.license.graph_get_all", return_value=skus):
        license_scan_skus()
    fs = json.loads(kb_get_findings(domain="license"))
    assert not any(f["finding_type"] == "sku_unused" for f in fs)


def test_scan_skus_summary_shape(db):
    skus = [_sku("A", prepaid=5, consumed=3), _sku("B", prepaid=2, consumed=3)]
    with patch("tools.license.get_token", return_value=FAKE_TOKEN), \
         patch("tools.license.graph_get_all", return_value=skus):
        result = json.loads(license_scan_skus())
    assert result["scanned"] == 2
    assert result["overconsumed"] == 1
    assert "findings" in result


# -------------------------------------------------------- license_scan_users


def test_licensed_disabled_user_flags_medium(db):
    skus = [_sku("O365_BUSINESS_PREMIUM", sku_id="sku-bp", prepaid=10, consumed=1)]
    users = [_user("u1", "former@mcna.com", enabled=False, sku_ids=["sku-bp"])]
    with patch("tools.license.get_token", return_value=FAKE_TOKEN), \
         patch("tools.license.graph_get_all", side_effect=[skus, users]):
        license_scan_users()
    fs = json.loads(kb_get_findings(domain="license"))
    assert any(f["finding_type"] == "licensed_disabled_account" and f["severity"] == "Medium" for f in fs)


def test_unlicensed_disabled_user_not_flagged(db):
    skus = []
    users = [_user("u1", "former@mcna.com", enabled=False, sku_ids=[])]
    with patch("tools.license.get_token", return_value=FAKE_TOKEN), \
         patch("tools.license.graph_get_all", side_effect=[skus, users]):
        license_scan_users()
    fs = json.loads(kb_get_findings(domain="license"))
    assert not any(f["finding_type"] == "licensed_disabled_account" for f in fs)


def test_productivity_sku_stacking_flags_medium(db):
    skus = [
        _sku("O365_BUSINESS_PREMIUM", sku_id="sku-bp"),
        _sku("SPE_E3", sku_id="sku-e3"),
    ]
    users = [_user("u1", "dave@mcna.com", enabled=True, sku_ids=["sku-bp", "sku-e3"])]
    with patch("tools.license.get_token", return_value=FAKE_TOKEN), \
         patch("tools.license.graph_get_all", side_effect=[skus, users]):
        license_scan_users()
    fs = json.loads(kb_get_findings(domain="license"))
    assert any(f["finding_type"] == "productivity_sku_stacking" and f["severity"] == "Medium" for f in fs)


def test_single_productivity_sku_not_flagged(db):
    skus = [_sku("O365_BUSINESS_PREMIUM", sku_id="sku-bp")]
    users = [_user("u1", "dave@mcna.com", enabled=True, sku_ids=["sku-bp"])]
    with patch("tools.license.get_token", return_value=FAKE_TOKEN), \
         patch("tools.license.graph_get_all", side_effect=[skus, users]):
        license_scan_users()
    fs = json.loads(kb_get_findings(domain="license"))
    assert not any(f["finding_type"] == "productivity_sku_stacking" for f in fs)


def test_copilot_plus_bp_is_not_stacking(db):
    # Copilot is an add-on, not a standalone productivity suite; pairing it with
    # BP should not trip the stacking flag.
    skus = [
        _sku("O365_BUSINESS_PREMIUM", sku_id="sku-bp"),
        _sku("Microsoft_365_Copilot", sku_id="sku-copilot"),
    ]
    users = [_user("u1", "dave@mcna.com", enabled=True, sku_ids=["sku-bp", "sku-copilot"])]
    with patch("tools.license.get_token", return_value=FAKE_TOKEN), \
         patch("tools.license.graph_get_all", side_effect=[skus, users]):
        license_scan_users()
    fs = json.loads(kb_get_findings(domain="license"))
    assert not any(f["finding_type"] == "productivity_sku_stacking" for f in fs)
