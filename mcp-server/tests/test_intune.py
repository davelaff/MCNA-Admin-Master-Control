import json
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from graph import GraphError
from db import get_connection
from tools.intune import intune_scan_devices, intune_scan_compliance_policies
from tools.kb import kb_get_findings

FAKE_TOKEN = "fake-token"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _device(
    device_id: str,
    compliance_state: str = "compliant",
    last_sync_days_ago: int = 1,
    is_encrypted: bool = True,
    os_type: str = "Windows",
) -> dict:
    sync_dt = (
        datetime.now(timezone.utc) - timedelta(days=last_sync_days_ago)
    ).isoformat()
    return {
        "id": device_id,
        "deviceName": f"Device-{device_id}",
        "operatingSystem": os_type,
        "complianceState": compliance_state,
        "isEncrypted": is_encrypted,
        "lastSyncDateTime": sync_dt,
        "managedDeviceOwnerType": "company",
    }


def _policy(policy_id: str, name: str = "Default Policy") -> dict:
    return {
        "id": policy_id,
        "displayName": name,
        "scheduledActionsForRule": [],
        "lastModifiedDateTime": "2026-01-01T00:00:00Z",
    }


def _dispatch(devices=None, policies=None):
    """Return a side_effect callable that routes Graph calls by URL path."""
    def side_effect(path, token, params=None):
        if "managedDevices" in path:
            return devices if devices is not None else []
        if "deviceCompliancePolicies" in path:
            return policies if policies is not None else []
        return []
    return side_effect


def _raises_403(path, token, params=None):
    raise GraphError(403, path, "Forbidden")


# ---------------------------------------------------------------------------
# intune_scan_devices — scope not consented
# ---------------------------------------------------------------------------

def test_scan_devices_not_available_emits_finding(db):
    with patch("tools.intune.get_token", return_value=FAKE_TOKEN), \
         patch("tools.intune.graph_get_all", side_effect=_raises_403):
        result = json.loads(intune_scan_devices())
    assert result["intune_available"] is False
    assert result["findings"] == 1
    findings = json.loads(kb_get_findings(domain="intune"))
    assert any(f["finding_type"] == "intune_not_available" and f["severity"] == "Medium"
               for f in findings)


def test_scan_devices_not_available_returns_zero_counts(db):
    with patch("tools.intune.get_token", return_value=FAKE_TOKEN), \
         patch("tools.intune.graph_get_all", side_effect=_raises_403):
        result = json.loads(intune_scan_devices())
    assert result["scanned"] == 0
    assert result["not_compliant"] == 0
    assert result["stale"] == 0
    assert result["not_encrypted"] == 0


# ---------------------------------------------------------------------------
# intune_scan_devices — compliance state
# ---------------------------------------------------------------------------

def test_compliant_device_no_finding(db):
    with patch("tools.intune.get_token", return_value=FAKE_TOKEN), \
         patch("tools.intune.graph_get_all", side_effect=_dispatch(
             devices=[_device("d1", compliance_state="compliant")])):
        intune_scan_devices()
    findings = json.loads(kb_get_findings(domain="intune"))
    assert not any(f["finding_type"] == "device_not_compliant" for f in findings)


def test_noncompliant_device_flagged_high(db):
    with patch("tools.intune.get_token", return_value=FAKE_TOKEN), \
         patch("tools.intune.graph_get_all", side_effect=_dispatch(
             devices=[_device("d2", compliance_state="noncompliant")])):
        intune_scan_devices()
    findings = json.loads(kb_get_findings(domain="intune"))
    assert any(f["finding_type"] == "device_not_compliant" and f["severity"] == "High"
               for f in findings)


def test_unknown_compliance_not_flagged(db):
    """'unknown' is a valid transient state, not a policy violation."""
    with patch("tools.intune.get_token", return_value=FAKE_TOKEN), \
         patch("tools.intune.graph_get_all", side_effect=_dispatch(
             devices=[_device("d3", compliance_state="unknown")])):
        intune_scan_devices()
    findings = json.loads(kb_get_findings(domain="intune"))
    assert not any(f["finding_type"] == "device_not_compliant" for f in findings)


def test_inGracePeriod_device_flagged(db):
    with patch("tools.intune.get_token", return_value=FAKE_TOKEN), \
         patch("tools.intune.graph_get_all", side_effect=_dispatch(
             devices=[_device("d4", compliance_state="inGracePeriod")])):
        intune_scan_devices()
    findings = json.loads(kb_get_findings(domain="intune"))
    assert any(f["finding_type"] == "device_not_compliant" for f in findings)


# ---------------------------------------------------------------------------
# intune_scan_devices — staleness
# ---------------------------------------------------------------------------

def test_stale_device_flagged_low(db):
    with patch("tools.intune.get_token", return_value=FAKE_TOKEN), \
         patch("tools.intune.graph_get_all", side_effect=_dispatch(
             devices=[_device("d5", last_sync_days_ago=35)])):
        intune_scan_devices()
    findings = json.loads(kb_get_findings(domain="intune"))
    assert any(f["finding_type"] == "stale_device" and f["severity"] == "Low"
               for f in findings)


def test_fresh_device_not_stale(db):
    with patch("tools.intune.get_token", return_value=FAKE_TOKEN), \
         patch("tools.intune.graph_get_all", side_effect=_dispatch(
             devices=[_device("d6", last_sync_days_ago=5)])):
        intune_scan_devices()
    findings = json.loads(kb_get_findings(domain="intune"))
    assert not any(f["finding_type"] == "stale_device" for f in findings)


def test_device_within_stale_window_not_flagged(db):
    """29 days old — clearly within the 30-day window, should not be flagged."""
    with patch("tools.intune.get_token", return_value=FAKE_TOKEN), \
         patch("tools.intune.graph_get_all", side_effect=_dispatch(
             devices=[_device("d7", last_sync_days_ago=29)])):
        intune_scan_devices()
    findings = json.loads(kb_get_findings(domain="intune"))
    assert not any(f["finding_type"] == "stale_device" for f in findings)


# ---------------------------------------------------------------------------
# intune_scan_devices — encryption
# ---------------------------------------------------------------------------

def test_windows_unencrypted_flagged_high(db):
    with patch("tools.intune.get_token", return_value=FAKE_TOKEN), \
         patch("tools.intune.graph_get_all", side_effect=_dispatch(
             devices=[_device("d8", is_encrypted=False, os_type="Windows")])):
        intune_scan_devices()
    findings = json.loads(kb_get_findings(domain="intune"))
    assert any(f["finding_type"] == "encryption_not_enabled" and f["severity"] == "High"
               for f in findings)


def test_macos_unencrypted_flagged_high(db):
    with patch("tools.intune.get_token", return_value=FAKE_TOKEN), \
         patch("tools.intune.graph_get_all", side_effect=_dispatch(
             devices=[_device("d9", is_encrypted=False, os_type="macOS")])):
        intune_scan_devices()
    findings = json.loads(kb_get_findings(domain="intune"))
    assert any(f["finding_type"] == "encryption_not_enabled" and f["severity"] == "High"
               for f in findings)


def test_encrypted_windows_no_finding(db):
    with patch("tools.intune.get_token", return_value=FAKE_TOKEN), \
         patch("tools.intune.graph_get_all", side_effect=_dispatch(
             devices=[_device("d10", is_encrypted=True, os_type="Windows")])):
        intune_scan_devices()
    findings = json.loads(kb_get_findings(domain="intune"))
    assert not any(f["finding_type"] == "encryption_not_enabled" for f in findings)


def test_ios_unencrypted_not_flagged(db):
    """iOS encrypts at OS level; isEncrypted field is unreliable — skip check."""
    with patch("tools.intune.get_token", return_value=FAKE_TOKEN), \
         patch("tools.intune.graph_get_all", side_effect=_dispatch(
             devices=[_device("d11", is_encrypted=False, os_type="iOS")])):
        intune_scan_devices()
    findings = json.loads(kb_get_findings(domain="intune"))
    assert not any(f["finding_type"] == "encryption_not_enabled" for f in findings)


def test_android_unencrypted_not_flagged(db):
    with patch("tools.intune.get_token", return_value=FAKE_TOKEN), \
         patch("tools.intune.graph_get_all", side_effect=_dispatch(
             devices=[_device("d12", is_encrypted=False, os_type="Android")])):
        intune_scan_devices()
    findings = json.loads(kb_get_findings(domain="intune"))
    assert not any(f["finding_type"] == "encryption_not_enabled" for f in findings)


# ---------------------------------------------------------------------------
# intune_scan_devices — empty / multi-device summary
# ---------------------------------------------------------------------------

def test_empty_device_list_no_findings(db):
    with patch("tools.intune.get_token", return_value=FAKE_TOKEN), \
         patch("tools.intune.graph_get_all", side_effect=_dispatch(devices=[])):
        result = json.loads(intune_scan_devices())
    assert result["scanned"] == 0
    assert result["findings"] == 0


def test_scan_devices_summary_shape(db):
    devices = [
        _device("e1", compliance_state="noncompliant"),
        _device("e2", last_sync_days_ago=45),
        _device("e3", is_encrypted=False, os_type="Windows"),
        _device("e4", compliance_state="compliant"),
    ]
    with patch("tools.intune.get_token", return_value=FAKE_TOKEN), \
         patch("tools.intune.graph_get_all", side_effect=_dispatch(devices=devices)):
        result = json.loads(intune_scan_devices())
    assert result["scanned"] == 4
    assert result["not_compliant"] == 1
    assert result["stale"] == 1
    assert result["not_encrypted"] == 1
    assert result["intune_available"] is True


def test_scan_devices_records_success_activity(db):
    with patch("tools.intune.get_token", return_value=FAKE_TOKEN), \
         patch("tools.intune.graph_get_all", side_effect=_dispatch(
             devices=[_device("activity1")])):
        intune_scan_devices()

    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT * FROM activity_log
            WHERE tool_name = 'intune_scan_devices'
              AND domain = 'intune'
              AND outcome = 'success'
            """
        ).fetchone()

    assert row is not None
    assert json.loads(row["detail"])["scanned"] == 1


# ---------------------------------------------------------------------------
# intune_scan_compliance_policies — scope not consented
# ---------------------------------------------------------------------------

def test_scan_policies_not_available_emits_finding(db):
    with patch("tools.intune.get_token", return_value=FAKE_TOKEN), \
         patch("tools.intune.graph_get_all", side_effect=_raises_403):
        result = json.loads(intune_scan_compliance_policies())
    assert result["intune_available"] is False
    findings = json.loads(kb_get_findings(domain="intune"))
    assert any(f["finding_type"] == "intune_not_available" for f in findings)


# ---------------------------------------------------------------------------
# intune_scan_compliance_policies — no policies defined
# ---------------------------------------------------------------------------

def test_no_compliance_policies_flagged_high(db):
    with patch("tools.intune.get_token", return_value=FAKE_TOKEN), \
         patch("tools.intune.graph_get_all", side_effect=_dispatch(policies=[])):
        result = json.loads(intune_scan_compliance_policies())
    assert result["policies_found"] == 0
    assert result["findings"] == 1
    findings = json.loads(kb_get_findings(domain="intune"))
    assert any(f["finding_type"] == "no_compliance_policies" and f["severity"] == "High"
               for f in findings)


# ---------------------------------------------------------------------------
# intune_scan_compliance_policies — policies exist
# ---------------------------------------------------------------------------

def test_policies_exist_no_finding(db):
    with patch("tools.intune.get_token", return_value=FAKE_TOKEN), \
         patch("tools.intune.graph_get_all", side_effect=_dispatch(
             policies=[_policy("p1"), _policy("p2", "macOS Baseline")])):
        result = json.loads(intune_scan_compliance_policies())
    assert result["policies_found"] == 2
    assert result["findings"] == 0
    findings = json.loads(kb_get_findings(domain="intune"))
    assert not any(f["finding_type"] == "no_compliance_policies" for f in findings)


def test_single_policy_no_finding(db):
    with patch("tools.intune.get_token", return_value=FAKE_TOKEN), \
         patch("tools.intune.graph_get_all", side_effect=_dispatch(
             policies=[_policy("p3")])):
        result = json.loads(intune_scan_compliance_policies())
    assert result["policies_found"] == 1
    assert result["findings"] == 0
