import json
import pytest
from unittest.mock import patch, MagicMock
from tools.pp import pp_scan_environments, pp_scan_apps
from db import get_connection

FAKE_TOKEN = "fake"

def _env(eid="env1", name="Default", sku="Default", is_default=True):
    return {
        "name": eid,
        "properties": {
            "displayName": name,
            "environmentSku": sku,
            "isDefault": is_default,
        },
    }

def _app(aid="app1", name="MyApp", env_id="env1", owner_id=None, owner_upn=None):
    return {
        "name": aid,
        "properties": {
            "displayName": name,
            "owner": {"id": owner_id, "userPrincipalName": owner_upn} if owner_id else {},
        },
    }

def test_production_in_default_env_creates_high_finding(db):
    envs = [_env(sku="Production", is_default=True)]
    with patch("tools.pp.get_token", return_value=FAKE_TOKEN), \
         patch("tools.pp._bap_get_all", return_value=envs):
        pp_scan_environments()
    findings = json.loads(__import__("tools.kb", fromlist=["kb_get_findings"]).kb_get_findings(domain="pp"))
    assert any(f["finding_type"] == "production_in_default" and f["severity"] == "High" for f in findings)

def test_non_default_env_no_finding(db):
    envs = [_env(sku="Sandbox", is_default=False)]
    with patch("tools.pp.get_token", return_value=FAKE_TOKEN), \
         patch("tools.pp._bap_get_all", return_value=envs):
        pp_scan_environments()
    findings = json.loads(__import__("tools.kb", fromlist=["kb_get_findings"]).kb_get_findings(domain="pp"))
    assert not any(f["finding_type"] == "production_in_default" for f in findings)

def test_scan_environments_returns_summary(db):
    envs = [_env(), _env("env2", "Prod", "Production", False)]
    with patch("tools.pp.get_token", return_value=FAKE_TOKEN), \
         patch("tools.pp._bap_get_all", return_value=envs):
        result = json.loads(pp_scan_environments())
    assert result["scanned"] == 2

def test_app_with_disabled_owner_creates_high_finding(db):
    envs = [_env()]
    apps = [_app(owner_id="disabled-user", owner_upn="ex@mcna.com")]
    disabled_users = [{"id": "disabled-user", "userPrincipalName": "ex@mcna.com"}]

    with patch("tools.pp.get_token", return_value=FAKE_TOKEN), \
         patch("tools.pp._bap_get_all", side_effect=[envs, apps]), \
         patch("tools.pp.graph_get_all", return_value=disabled_users):
        pp_scan_apps()
    findings = json.loads(__import__("tools.kb", fromlist=["kb_get_findings"]).kb_get_findings(domain="pp"))
    assert any(f["finding_type"] == "inactive_owner" and f["severity"] == "High" for f in findings)

def test_app_with_active_owner_no_finding(db):
    envs = [_env()]
    apps = [_app(owner_id="active-user", owner_upn="active@mcna.com")]
    disabled_users = []  # No disabled users

    with patch("tools.pp.get_token", return_value=FAKE_TOKEN), \
         patch("tools.pp._bap_get_all", side_effect=[envs, apps]), \
         patch("tools.pp.graph_get_all", return_value=disabled_users):
        pp_scan_apps()
    findings = json.loads(__import__("tools.kb", fromlist=["kb_get_findings"]).kb_get_findings(domain="pp"))
    assert not any(f["finding_type"] == "inactive_owner" for f in findings)
