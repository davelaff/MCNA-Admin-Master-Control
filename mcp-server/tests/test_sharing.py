import json
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from tools.sharing import sharing_scan_sites
from tools.kb import kb_get_findings

FAKE_TOKEN = "fake"


def _site(sid: str, name: str, days_ago: int) -> dict:
    ts = (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat().replace("+00:00", "Z")
    return {
        "id": sid,
        "displayName": name,
        "webUrl": f"https://mcna.sharepoint.com/sites/{sid}",
        "createdDateTime": ts,
        "lastModifiedDateTime": ts,
    }


def test_very_stale_site_flags_high(db):
    sites = [_site("old1", "Old Site", days_ago=800)]
    with patch("tools.sharing.get_token", return_value=FAKE_TOKEN), \
         patch("tools.sharing.graph_get_all", return_value=sites):
        sharing_scan_sites()
    fs = json.loads(kb_get_findings(domain="sharing"))
    assert any(f["finding_type"] == "very_stale_site" and f["severity"] == "High" for f in fs)


def test_stale_site_flags_medium(db):
    sites = [_site("mid1", "Stale Site", days_ago=500)]
    with patch("tools.sharing.get_token", return_value=FAKE_TOKEN), \
         patch("tools.sharing.graph_get_all", return_value=sites):
        sharing_scan_sites()
    fs = json.loads(kb_get_findings(domain="sharing"))
    assert any(f["finding_type"] == "stale_site" and f["severity"] == "Medium" for f in fs)


def test_very_stale_not_double_flagged_as_stale(db):
    # A 730+ day site should only emit the High finding, not also Medium.
    sites = [_site("old1", "Old Site", days_ago=800)]
    with patch("tools.sharing.get_token", return_value=FAKE_TOKEN), \
         patch("tools.sharing.graph_get_all", return_value=sites):
        sharing_scan_sites()
    fs = json.loads(kb_get_findings(domain="sharing"))
    assert not any(f["finding_type"] == "stale_site" for f in fs)


def test_active_site_not_flagged(db):
    sites = [_site("fresh1", "Active Site", days_ago=30)]
    with patch("tools.sharing.get_token", return_value=FAKE_TOKEN), \
         patch("tools.sharing.graph_get_all", return_value=sites):
        sharing_scan_sites()
    fs = json.loads(kb_get_findings(domain="sharing"))
    assert not any(f["finding_type"] in {"stale_site", "very_stale_site"} for f in fs)


def test_scan_sites_summary_shape(db):
    sites = [
        _site("a", "A", days_ago=30),
        _site("b", "B", days_ago=500),
        _site("c", "C", days_ago=900),
    ]
    with patch("tools.sharing.get_token", return_value=FAKE_TOKEN), \
         patch("tools.sharing.graph_get_all", return_value=sites):
        result = json.loads(sharing_scan_sites())
    assert result["scanned"] == 3
    assert result["stale"] == 1
    assert result["very_stale"] == 1


def test_site_missing_lastmodified_is_skipped_not_flagged(db):
    s = _site("weird", "No Timestamp", days_ago=30)
    s.pop("lastModifiedDateTime")
    with patch("tools.sharing.get_token", return_value=FAKE_TOKEN), \
         patch("tools.sharing.graph_get_all", return_value=[s]):
        sharing_scan_sites()
    fs = json.loads(kb_get_findings(domain="sharing"))
    assert not any(f["finding_type"] in {"stale_site", "very_stale_site"} for f in fs)
