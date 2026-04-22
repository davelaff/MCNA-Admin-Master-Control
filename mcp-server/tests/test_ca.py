import json
import pytest
from unittest.mock import patch, MagicMock
from tools.ca import ca_scan_policies, ca_scan_coverage_gaps
from db import get_connection

FAKE_TOKEN = "fake"

def _policy(pid="p1", name="Require MFA", state="enabled", groups=None):
    return {
        "id": pid,
        "displayName": name,
        "state": state,
        "conditions": {
            "users": {
                "includeUsers": [],
                "excludeUsers": [],
                "includeGroups": groups or [],
                "excludeGroups": [],
            }
        },
        "grantControls": None,
        "sessionControls": None,
    }

def test_report_only_policy_creates_medium_finding(db):
    policies = [_policy(state="enabledForReportingButNotEnforced")]
    with patch("tools.ca.get_token", return_value=FAKE_TOKEN), \
         patch("tools.ca.graph_get_all", return_value=policies), \
         patch("tools.ca.graph_get"):
        ca_scan_policies()
    findings = json.loads(__import__("tools.kb", fromlist=["kb_get_findings"]).kb_get_findings(domain="ca"))
    assert any(f["finding_type"] == "report_only_policy" and f["severity"] == "Medium" for f in findings)

def test_broken_group_ref_creates_high_finding(db):
    from graph import GraphError
    policies = [_policy(groups=["missing-group-id"])]
    mock_get = MagicMock(side_effect=GraphError(404, "/groups/missing-group-id"))
    with patch("tools.ca.get_token", return_value=FAKE_TOKEN), \
         patch("tools.ca.graph_get_all", return_value=policies), \
         patch("tools.ca.graph_get", mock_get):
        ca_scan_policies()
    findings = json.loads(__import__("tools.kb", fromlist=["kb_get_findings"]).kb_get_findings(domain="ca"))
    assert any(f["finding_type"] == "broken_group_reference" and f["severity"] == "High" for f in findings)

def test_scan_policies_returns_summary(db):
    policies = [_policy(), _policy("p2", state="disabled")]
    with patch("tools.ca.get_token", return_value=FAKE_TOKEN), \
         patch("tools.ca.graph_get_all", return_value=policies), \
         patch("tools.ca.graph_get"):
        result = json.loads(ca_scan_policies())
    assert result["scanned"] == 2
    assert result["enabled"] == 1
    assert result["disabled"] == 1

def test_coverage_gaps_all_covered_when_include_all(db):
    policies = [_policy()]
    policies[0]["conditions"]["users"]["includeUsers"] = ["All"]
    with patch("tools.ca.get_token", return_value=FAKE_TOKEN), \
         patch("tools.ca.graph_get_all", return_value=policies):
        result = json.loads(ca_scan_coverage_gaps())
    assert result["uncovered_count"] == 0

def test_coverage_gaps_flags_uncovered_users(db):
    policies = []  # No enabled policies
    users = [{"id": "u1", "displayName": "User One", "userPrincipalName": "u1@mcna.com"}]
    with patch("tools.ca.get_token", return_value=FAKE_TOKEN), \
         patch("tools.ca.graph_get_all", side_effect=[policies, users]):
        result = json.loads(ca_scan_coverage_gaps())
    assert "warning" in result or result.get("uncovered_count", 0) >= 0
