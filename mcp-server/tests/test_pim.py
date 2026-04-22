import json
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock
import requests
from tools.pim import pim_scan_role_assignments, pim_scan_role_definitions
from tools.kb import kb_get_findings

FAKE_TOKEN = "fake"


def _http400():
    resp = MagicMock()
    resp.status_code = 400
    return requests.exceptions.HTTPError(response=resp)


def _role_def(rid: str, name: str, built_in: bool = True) -> dict:
    return {"id": rid, "displayName": name, "isBuiltIn": built_in, "templateId": rid}


def _schedule(principal_id: str, role_id: str, upn: str = None, display: str = None,
              assignment_type: str = "Assigned", created_days_ago: int = 10) -> dict:
    created = datetime.now(timezone.utc) - timedelta(days=created_days_ago)
    return {
        "id": f"sched-{principal_id}-{role_id}",
        "principalId": principal_id,
        "roleDefinitionId": role_id,
        "assignmentType": assignment_type,
        "directoryScopeId": "/",
        "createdDateTime": created.isoformat().replace("+00:00", "Z"),
        "principal": {
            "id": principal_id,
            "displayName": display or principal_id,
            "userPrincipalName": upn,
            "@odata.type": "#microsoft.graph.user" if upn else "#microsoft.graph.servicePrincipal",
        },
    }


def _graph_dispatch(defs=None, active=None, eligible=None):
    defs = defs or []
    active = active or []
    eligible = eligible or []

    def side_effect(path, token, params=None):
        if "roleDefinitions" in path:
            return defs
        if "roleAssignmentSchedules" in path:
            return active
        if "roleEligibilitySchedules" in path:
            return eligible
        return []

    return side_effect


# ---------------------------------------------------------------- role assignments


def test_permanent_privileged_assignment_flags_high(db):
    defs = [_role_def("ga", "Global Administrator")]
    active = [_schedule("u1", "ga", upn="nof-dlafferty@mcna.com",
                        display="Dave (admin)", assignment_type="Assigned")]
    with patch("tools.pim.get_token", return_value=FAKE_TOKEN), \
         patch("tools.pim.graph_get_all", side_effect=_graph_dispatch(defs, active, [])):
        pim_scan_role_assignments()
    findings = json.loads(kb_get_findings(domain="pim"))
    assert any(
        f["finding_type"] == "permanent_privileged_assignment" and f["severity"] == "High"
        for f in findings
    )


def test_pim_activated_assignment_is_not_flagged_as_permanent(db):
    defs = [_role_def("ga", "Global Administrator")]
    active = [_schedule("u1", "ga", upn="nof-dlafferty@mcna.com",
                        assignment_type="Activated")]
    with patch("tools.pim.get_token", return_value=FAKE_TOKEN), \
         patch("tools.pim.graph_get_all", side_effect=_graph_dispatch(defs, active, [])):
        pim_scan_role_assignments()
    findings = json.loads(kb_get_findings(domain="pim"))
    assert not any(f["finding_type"] == "permanent_privileged_assignment" for f in findings)


def test_non_privileged_role_is_not_flagged(db):
    defs = [_role_def("reader", "Directory Readers")]
    active = [_schedule("u1", "reader", upn="someone@mcna.com")]
    with patch("tools.pim.get_token", return_value=FAKE_TOKEN), \
         patch("tools.pim.graph_get_all", side_effect=_graph_dispatch(defs, active, [])):
        pim_scan_role_assignments()
    findings = json.loads(kb_get_findings(domain="pim"))
    assert not any(f["finding_type"] == "permanent_privileged_assignment" for f in findings)
    assert not any(f["finding_type"] == "privileged_role_on_non_admin_account" for f in findings)


def test_privileged_role_on_non_admin_account_flags_high(db):
    defs = [_role_def("ga", "Global Administrator")]
    active = [_schedule("u1", "ga", upn="dlafferty@mcna.com",
                        display="Dave (daily driver)")]
    with patch("tools.pim.get_token", return_value=FAKE_TOKEN), \
         patch("tools.pim.graph_get_all", side_effect=_graph_dispatch(defs, active, [])):
        pim_scan_role_assignments()
    findings = json.loads(kb_get_findings(domain="pim"))
    assert any(
        f["finding_type"] == "privileged_role_on_non_admin_account" and f["severity"] == "High"
        for f in findings
    )


def test_service_principal_not_flagged_as_non_admin_account(db):
    defs = [_role_def("ga", "Global Administrator")]
    active = [_schedule("sp1", "ga", upn=None, display="Some SP")]  # service principal
    with patch("tools.pim.get_token", return_value=FAKE_TOKEN), \
         patch("tools.pim.graph_get_all", side_effect=_graph_dispatch(defs, active, [])):
        pim_scan_role_assignments()
    findings = json.loads(kb_get_findings(domain="pim"))
    assert not any(f["finding_type"] == "privileged_role_on_non_admin_account" for f in findings)


def test_long_standing_eligible_assignment_flags_low(db):
    defs = [_role_def("ga", "Global Administrator")]
    eligible = [_schedule("u1", "ga", upn="nof-dlafferty@mcna.com",
                          assignment_type="Assigned", created_days_ago=120)]
    with patch("tools.pim.get_token", return_value=FAKE_TOKEN), \
         patch("tools.pim.graph_get_all", side_effect=_graph_dispatch(defs, [], eligible)):
        pim_scan_role_assignments()
    findings = json.loads(kb_get_findings(domain="pim"))
    assert any(
        f["finding_type"] == "long_standing_eligible_assignment" and f["severity"] == "Low"
        for f in findings
    )


def test_fresh_eligible_assignment_not_flagged(db):
    defs = [_role_def("ga", "Global Administrator")]
    eligible = [_schedule("u1", "ga", upn="nof-dlafferty@mcna.com",
                          assignment_type="Assigned", created_days_ago=10)]
    with patch("tools.pim.get_token", return_value=FAKE_TOKEN), \
         patch("tools.pim.graph_get_all", side_effect=_graph_dispatch(defs, [], eligible)):
        pim_scan_role_assignments()
    findings = json.loads(kb_get_findings(domain="pim"))
    assert not any(f["finding_type"] == "long_standing_eligible_assignment" for f in findings)


def test_scan_role_assignments_summary_shape(db):
    defs = [_role_def("ga", "Global Administrator"), _role_def("reader", "Directory Readers")]
    active = [_schedule("u1", "ga", upn="nof-dlafferty@mcna.com"),
              _schedule("u2", "reader", upn="someone@mcna.com")]
    with patch("tools.pim.get_token", return_value=FAKE_TOKEN), \
         patch("tools.pim.graph_get_all", side_effect=_graph_dispatch(defs, active, [])):
        result = json.loads(pim_scan_role_assignments())
    assert result["active_assignments"] == 2
    assert result["privileged_active"] == 1
    assert "findings" in result


# ---------------------------------------------------------------- role definitions


def test_unused_custom_role_flags_low(db):
    defs = [_role_def("cust1", "Custom Billing Reader", built_in=False)]
    with patch("tools.pim.get_token", return_value=FAKE_TOKEN), \
         patch("tools.pim.graph_get_all", side_effect=_graph_dispatch(defs, [], [])):
        pim_scan_role_definitions()
    findings = json.loads(kb_get_findings(domain="pim"))
    assert any(
        f["finding_type"] == "unused_custom_role" and f["severity"] == "Low"
        for f in findings
    )


def test_used_custom_role_not_flagged(db):
    defs = [_role_def("cust1", "Custom Billing Reader", built_in=False)]
    active = [_schedule("u1", "cust1", upn="someone@mcna.com")]
    with patch("tools.pim.get_token", return_value=FAKE_TOKEN), \
         patch("tools.pim.graph_get_all", side_effect=_graph_dispatch(defs, active, [])):
        pim_scan_role_definitions()
    findings = json.loads(kb_get_findings(domain="pim"))
    assert not any(f["finding_type"] == "unused_custom_role" for f in findings)


def test_builtin_role_not_flagged_as_unused(db):
    defs = [_role_def("reader", "Directory Readers", built_in=True)]
    with patch("tools.pim.get_token", return_value=FAKE_TOKEN), \
         patch("tools.pim.graph_get_all", side_effect=_graph_dispatch(defs, [], [])):
        pim_scan_role_definitions()
    findings = json.loads(kb_get_findings(domain="pim"))
    assert not any(f["finding_type"] == "unused_custom_role" for f in findings)


# ---------------------------------------------------------------- P2 fallback


def _graph_dispatch_no_p2(defs=None, basic_assignments=None):
    """Simulate a P1-only tenant: schedule endpoints 400, /roleAssignments works."""
    defs = defs or []
    basic_assignments = basic_assignments or []

    def side_effect(path, token, params=None):
        if "roleDefinitions" in path:
            return defs
        if "roleAssignmentSchedules" in path or "roleEligibilitySchedules" in path:
            raise _http400()
        if "/roleAssignments" in path:
            return basic_assignments
        return []

    return side_effect


def test_no_p2_emits_pim_not_licensed_finding(db):
    defs = [_role_def("ga", "Global Administrator")]
    with patch("tools.pim.get_token", return_value=FAKE_TOKEN), \
         patch("tools.pim.graph_get_all", side_effect=_graph_dispatch_no_p2(defs, [])):
        result = json.loads(pim_scan_role_assignments())
    assert result["pim_available"] is False
    findings = json.loads(kb_get_findings(domain="pim"))
    assert any(
        f["finding_type"] == "pim_not_licensed" and f["severity"] == "High"
        for f in findings
    )


def test_no_p2_flags_every_privileged_assignment_as_permanent(db):
    defs = [_role_def("ga", "Global Administrator")]
    basic = [_schedule("u1", "ga", upn="nof-dlafferty@mcna.com")]
    # strip assignmentType to simulate /roleAssignments response
    basic[0].pop("assignmentType", None)
    with patch("tools.pim.get_token", return_value=FAKE_TOKEN), \
         patch("tools.pim.graph_get_all", side_effect=_graph_dispatch_no_p2(defs, basic)):
        pim_scan_role_assignments()
    findings = json.loads(kb_get_findings(domain="pim"))
    assert any(f["finding_type"] == "permanent_privileged_assignment" for f in findings)
