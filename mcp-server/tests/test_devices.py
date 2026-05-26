import json
import pytest
from unittest.mock import patch
from tools.devices import devices_scan_entra
from db import get_connection

FAKE_TOKEN = "fake_auth_token"

def _entra_device(device_id="d1", name="Dave-Laptop", is_managed=True, trust_type="AzureAdJoined", os="Windows", os_version="10.0.22631", category="Corporate Laptop", last_signin="2026-05-20T10:00:00Z"):
    return {
        "id": device_id,
        "displayName": name,
        "isManaged": is_managed,
        "trustType": trust_type,
        "operatingSystem": os,
        "operatingSystemVersion": os_version,
        "deviceCategory": category,
        "approximateLastSignInDateTime": last_signin
    }

def test_unmanaged_device_creates_medium_finding(db):
    devices = [
        _entra_device(device_id="dev-unmanaged", name="JW-PersonalPC", is_managed=False, trust_type="WorkplaceJoined")
    ]
    
    with patch("tools.devices.get_token", return_value=FAKE_TOKEN), \
         patch("tools.devices.graph_get_all", return_value=devices):
        result_str = devices_scan_entra()
        result = json.loads(result_str)

    assert result["scanned"] == 1
    assert result["unmanaged"] == 1
    
    findings = json.loads(__import__("tools.kb", fromlist=["kb_get_findings"]).kb_get_findings(domain="devices"))
    
    assert len(findings) == 1
    assert findings[0]["finding_type"] == "unmanaged_entra_device"
    assert findings[0]["severity"] == "Medium"
    assert findings[0]["object_name"] == "JW-PersonalPC"
    assert "Intune" in findings[0]["recommended_action"]


def test_managed_device_does_not_trigger_finding(db):
    devices = [
        _entra_device(device_id="dev-managed", name="JW-WorkLaptop", is_managed=True, trust_type="AzureAdJoined")
    ]
    
    with patch("tools.devices.get_token", return_value=FAKE_TOKEN), \
         patch("tools.devices.graph_get_all", return_value=devices):
        result_str = devices_scan_entra()
        result = json.loads(result_str)

    assert result["scanned"] == 1
    assert result["unmanaged"] == 0
    
    findings = json.loads(__import__("tools.kb", fromlist=["kb_get_findings"]).kb_get_findings(domain="devices"))
    assert len(findings) == 0


def test_stale_device_creates_low_finding(db):
    # Device from over 60 days ago
    stale_date = "2025-12-01T00:00:00Z"
    devices = [
        _entra_device(device_id="dev-stale", name="Abandoned-tablet", is_managed=False, last_signin=stale_date)
    ]
    
    with patch("tools.devices.get_token", return_value=FAKE_TOKEN), \
         patch("tools.devices.graph_get_all", return_value=devices):
        result_str = devices_scan_entra()
        result = json.loads(result_str)

    assert result["scanned"] == 1
    assert result["unmanaged"] == 1
    
    findings = json.loads(__import__("tools.kb", fromlist=["kb_get_findings"]).kb_get_findings(domain="devices"))
    stale_unmanaged = [f for f in findings if f["object_id"] == "dev-stale"]
    assert len(stale_unmanaged) > 0
    assert "verify" in stale_unmanaged[0]["recommended_action"]
