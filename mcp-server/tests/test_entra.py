import json
import pytest
from unittest.mock import patch
from tools.entra import entra_scan_app_regs, entra_scan_guests
from db import get_connection

FAKE_TOKEN = "fake"

def _app(aid="app1", name="MyApp", owners=None, secrets=None, certs=None, web_uris=None):
    return {
        "id": aid,
        "displayName": name,
        "owners": owners or [],
        "passwordCredentials": secrets or [],
        "keyCredentials": certs or [],
        "web": {"redirectUris": web_uris or []},
        "publicClient": {"redirectUris": []},
        "requiredResourceAccess": [],
    }

def test_missing_owner_creates_high_finding(db):
    apps = [_app(owners=[])]
    with patch("tools.entra.get_token", return_value=FAKE_TOKEN), \
         patch("tools.entra.graph_get_all", return_value=apps):
        entra_scan_app_regs()
    findings = json.loads(__import__("tools.kb", fromlist=["kb_get_findings"]).kb_get_findings(domain="entra"))
    assert any(f["finding_type"] == "missing_owner" and f["severity"] == "High" for f in findings)

def test_expired_secret_creates_critical_finding(db):
    secret = {"keyId": "k1", "displayName": "sec", "endDateTime": "2020-01-01T00:00:00Z"}
    apps = [_app(secrets=[secret])]
    with patch("tools.entra.get_token", return_value=FAKE_TOKEN), \
         patch("tools.entra.graph_get_all", return_value=apps):
        entra_scan_app_regs()
    findings = json.loads(__import__("tools.kb", fromlist=["kb_get_findings"]).kb_get_findings(domain="entra", severity="Critical"))
    assert any(f["finding_type"] == "expired_secret" for f in findings)

def test_wildcard_uri_creates_critical_finding(db):
    apps = [_app(web_uris=["https://example.com/*"])]
    with patch("tools.entra.get_token", return_value=FAKE_TOKEN), \
         patch("tools.entra.graph_get_all", return_value=apps):
        entra_scan_app_regs()
    findings = json.loads(__import__("tools.kb", fromlist=["kb_get_findings"]).kb_get_findings(domain="entra"))
    assert any(f["finding_type"] == "wildcard_redirect_uri" for f in findings)

def test_scan_returns_summary_json(db):
    apps = [_app()]
    with patch("tools.entra.get_token", return_value=FAKE_TOKEN), \
         patch("tools.entra.graph_get_all", return_value=apps):
        result = json.loads(entra_scan_app_regs())
    assert "scanned" in result
    assert result["scanned"] == 1

def test_dismissed_finding_not_recreated(db):
    from tools.kb import kb_dismiss
    apps = [_app(owners=[])]
    with patch("tools.entra.get_token", return_value=FAKE_TOKEN), \
         patch("tools.entra.graph_get_all", return_value=apps):
        entra_scan_app_regs()
    findings = json.loads(__import__("tools.kb", fromlist=["kb_get_findings"]).kb_get_findings(domain="entra"))
    fid = findings[0]["finding_id"]
    kb_dismiss(fid, "accepted")
    with patch("tools.entra.get_token", return_value=FAKE_TOKEN), \
         patch("tools.entra.graph_get_all", return_value=apps):
        entra_scan_app_regs()
    open_findings = json.loads(__import__("tools.kb", fromlist=["kb_get_findings"]).kb_get_findings(domain="entra"))
    assert not any(f["finding_id"] == fid for f in open_findings)

def _guest(gid="g1", name="Guest User", created="2026-01-01T00:00:00Z", last_sign_in=None):
    return {
        "id": gid,
        "displayName": name,
        "mail": f"{gid}@external.com",
        "userPrincipalName": f"{gid}_ext#EXT#@tenant.com",
        "createdDateTime": created,
        "signInActivity": {"lastSignInDateTime": last_sign_in} if last_sign_in else None,
    }

def test_recently_added_guest_creates_low_finding(db):
    from datetime import datetime, timezone, timedelta
    recent = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat().replace("+00:00", "Z")
    guests = [_guest(created=recent)]
    with patch("tools.entra.get_token", return_value=FAKE_TOKEN), \
         patch("tools.entra.graph_get_all", return_value=guests):
        entra_scan_guests()
    findings = json.loads(__import__("tools.kb", fromlist=["kb_get_findings"]).kb_get_findings(domain="entra"))
    assert any(f["finding_type"] == "recently_added_guest" for f in findings)

def test_inactive_guest_creates_medium_finding(db):
    from datetime import datetime, timezone, timedelta
    old = (datetime.now(timezone.utc) - timedelta(days=120)).isoformat().replace("+00:00", "Z")
    guests = [_guest(last_sign_in=old)]
    with patch("tools.entra.get_token", return_value=FAKE_TOKEN), \
         patch("tools.entra.graph_get_all", return_value=guests):
        entra_scan_guests()
    findings = json.loads(__import__("tools.kb", fromlist=["kb_get_findings"]).kb_get_findings(domain="entra"))
    assert any(f["finding_type"] == "inactive_guest" for f in findings)
