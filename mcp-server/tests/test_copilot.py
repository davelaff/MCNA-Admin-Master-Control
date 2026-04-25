import json
from unittest.mock import patch
from tools.copilot import copilot_scan_licenses, copilot_scan_settings
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


# ------------------------------------------------ copilot_scan_licenses


def test_summary_shape_no_copilot_users(db):
    skus = [_sku("O365_BUSINESS_PREMIUM", sku_id="sku-bp")]
    users = [_user("u1", "alice@mcna.com", enabled=True, sku_ids=["sku-bp"])]
    with patch("tools.copilot.get_token", return_value=FAKE_TOKEN), \
         patch("tools.copilot.graph_get_all", side_effect=[skus, users]):
        result = json.loads(copilot_scan_licenses())
    assert result["copilot_users"] == 0
    assert result["findings"] == 0


def test_copilot_user_counted(db):
    skus = [
        _sku("O365_BUSINESS_PREMIUM", sku_id="sku-bp"),
        _sku("Microsoft_365_Copilot", sku_id="sku-cop"),
    ]
    users = [_user("u1", "alice@mcna.com", enabled=True, sku_ids=["sku-bp", "sku-cop"])]
    with patch("tools.copilot.get_token", return_value=FAKE_TOKEN), \
         patch("tools.copilot.graph_get_all", side_effect=[skus, users]):
        result = json.loads(copilot_scan_licenses())
    assert result["copilot_users"] == 1
    assert result["findings"] == 0


def test_disabled_copilot_user_flags_high(db):
    skus = [
        _sku("O365_BUSINESS_PREMIUM", sku_id="sku-bp"),
        _sku("Microsoft_365_Copilot", sku_id="sku-cop"),
    ]
    users = [_user("u1", "former@mcna.com", enabled=False, sku_ids=["sku-bp", "sku-cop"])]
    with patch("tools.copilot.get_token", return_value=FAKE_TOKEN), \
         patch("tools.copilot.graph_get_all", side_effect=[skus, users]):
        copilot_scan_licenses()
    fs = json.loads(kb_get_findings(domain="copilot"))
    assert any(
        f["finding_type"] == "copilot_licensed_disabled" and f["severity"] == "High"
        for f in fs
    )


def test_enabled_copilot_user_not_flagged_as_disabled(db):
    skus = [
        _sku("O365_BUSINESS_PREMIUM", sku_id="sku-bp"),
        _sku("Microsoft_365_Copilot", sku_id="sku-cop"),
    ]
    users = [_user("u1", "active@mcna.com", enabled=True, sku_ids=["sku-bp", "sku-cop"])]
    with patch("tools.copilot.get_token", return_value=FAKE_TOKEN), \
         patch("tools.copilot.graph_get_all", side_effect=[skus, users]):
        copilot_scan_licenses()
    fs = json.loads(kb_get_findings(domain="copilot"))
    assert not any(f["finding_type"] == "copilot_licensed_disabled" for f in fs)


def test_copilot_without_base_license_flags_medium(db):
    skus = [_sku("Microsoft_365_Copilot", sku_id="sku-cop")]
    users = [_user("u1", "orphan@mcna.com", enabled=True, sku_ids=["sku-cop"])]
    with patch("tools.copilot.get_token", return_value=FAKE_TOKEN), \
         patch("tools.copilot.graph_get_all", side_effect=[skus, users]):
        copilot_scan_licenses()
    fs = json.loads(kb_get_findings(domain="copilot"))
    assert any(
        f["finding_type"] == "copilot_no_base_license" and f["severity"] == "Medium"
        for f in fs
    )


def test_copilot_with_base_license_not_flagged_no_base(db):
    skus = [
        _sku("O365_BUSINESS_PREMIUM", sku_id="sku-bp"),
        _sku("Microsoft_365_Copilot", sku_id="sku-cop"),
    ]
    users = [_user("u1", "dave@mcna.com", enabled=True, sku_ids=["sku-bp", "sku-cop"])]
    with patch("tools.copilot.get_token", return_value=FAKE_TOKEN), \
         patch("tools.copilot.graph_get_all", side_effect=[skus, users]):
        copilot_scan_licenses()
    fs = json.loads(kb_get_findings(domain="copilot"))
    assert not any(f["finding_type"] == "copilot_no_base_license" for f in fs)


def test_idempotent_second_scan_does_not_duplicate(db):
    skus = [
        _sku("O365_BUSINESS_PREMIUM", sku_id="sku-bp"),
        _sku("Microsoft_365_Copilot", sku_id="sku-cop"),
    ]
    users = [_user("u1", "former@mcna.com", enabled=False, sku_ids=["sku-bp", "sku-cop"])]
    for _ in range(2):
        with patch("tools.copilot.get_token", return_value=FAKE_TOKEN), \
             patch("tools.copilot.graph_get_all", side_effect=[list(skus), list(users)]):
            copilot_scan_licenses()
    fs = json.loads(kb_get_findings(domain="copilot"))
    disabled_findings = [f for f in fs if f["finding_type"] == "copilot_licensed_disabled"]
    assert len(disabled_findings) == 1


def test_dismissed_finding_not_reopened(db):
    from db import get_connection
    skus = [
        _sku("O365_BUSINESS_PREMIUM", sku_id="sku-bp"),
        _sku("Microsoft_365_Copilot", sku_id="sku-cop"),
    ]
    users = [_user("u1", "former@mcna.com", enabled=False, sku_ids=["sku-bp", "sku-cop"])]
    with patch("tools.copilot.get_token", return_value=FAKE_TOKEN), \
         patch("tools.copilot.graph_get_all", side_effect=[list(skus), list(users)]):
        copilot_scan_licenses()
    fs = json.loads(kb_get_findings(domain="copilot"))
    fid = next(f["finding_id"] for f in fs if f["finding_type"] == "copilot_licensed_disabled")
    with get_connection() as conn:
        conn.execute("UPDATE findings SET status='dismissed' WHERE finding_id=?", (fid,))
    with patch("tools.copilot.get_token", return_value=FAKE_TOKEN), \
         patch("tools.copilot.graph_get_all", side_effect=[list(skus), list(users)]):
        copilot_scan_licenses()
    fs2 = json.loads(kb_get_findings(domain="copilot"))
    dismissed = next(f for f in fs2 if f["finding_id"] == fid)
    assert dismissed["status"] == "dismissed"


# ------------------------------------------------ copilot_scan_settings


def test_settings_scope_gap_produces_finding(db):
    from graph import GraphError
    err = GraphError(403, "Forbidden")
    with patch("tools.copilot.get_token", return_value=FAKE_TOKEN), \
         patch("tools.copilot.graph_get", side_effect=err):
        result = json.loads(copilot_scan_settings())
    assert result["available"] is False
    fs = json.loads(kb_get_findings(domain="copilot"))
    assert any(f["finding_type"] == "copilot_scope_gap" for f in fs)


def test_settings_404_treated_as_unavailable(db):
    from graph import GraphError
    err = GraphError(404, "Not Found")
    with patch("tools.copilot.get_token", return_value=FAKE_TOKEN), \
         patch("tools.copilot.graph_get", side_effect=err):
        result = json.loads(copilot_scan_settings())
    assert result["available"] is False


def test_settings_available_returns_summary(db):
    settings_payload = {
        "isEnabledInOrg": True,
        "userAccessPolicy": "AllowAll",
    }
    with patch("tools.copilot.get_token", return_value=FAKE_TOKEN), \
         patch("tools.copilot.graph_get", return_value=settings_payload):
        result = json.loads(copilot_scan_settings())
    assert result["available"] is True
    assert "isEnabledInOrg" in result


def test_settings_copilot_disabled_tenantwide_is_informational(db):
    settings_payload = {
        "isEnabledInOrg": False,
    }
    with patch("tools.copilot.get_token", return_value=FAKE_TOKEN), \
         patch("tools.copilot.graph_get", return_value=settings_payload):
        result = json.loads(copilot_scan_settings())
    assert result["available"] is True
    assert result["findings"] == 0
