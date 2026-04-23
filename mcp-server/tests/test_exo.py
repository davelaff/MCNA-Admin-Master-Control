import json
from unittest.mock import patch, MagicMock

import pytest
import requests

from graph import GraphError
from tools.exo import exo_scan_mailboxes, exo_scan_forwarding
from tools.kb import kb_get_findings

FAKE_TOKEN = "fake-token"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _user(uid: str, purpose: str = "user", enabled: bool = True) -> dict:
    return {
        "id": uid,
        "displayName": f"User-{uid}",
        "userPrincipalName": f"user{uid}@nofmetalcoatings.us",
        "mail": f"user{uid}@nofmetalcoatings.us",
        "accountEnabled": enabled,
        "assignedLicenses": [{"skuId": "abc"}],
    }


def _mailbox_settings(purpose: str = "user") -> dict:
    return {"userPurpose": purpose, "timeZone": "Eastern Standard Time"}


def _rule(rule_id: str, forward_to: list[str] = None, redirect_to: list[str] = None,
          enabled: bool = True) -> dict:
    def _recipients(addresses):
        return [{"emailAddress": {"address": a, "name": a}} for a in (addresses or [])]
    return {
        "id": rule_id,
        "displayName": f"Rule-{rule_id}",
        "isEnabled": enabled,
        "actions": {
            "forwardTo": _recipients(forward_to),
            "forwardAsAttachmentTo": [],
            "redirectTo": _recipients(redirect_to),
        },
    }


def _403(path, token, params=None):
    raise GraphError(403, path, "Forbidden")


def _404_http_error():
    resp = MagicMock()
    resp.status_code = 404
    err = requests.exceptions.HTTPError(response=resp)
    return err


# ---------------------------------------------------------------------------
# exo_scan_mailboxes — scope gap
# ---------------------------------------------------------------------------

def test_scan_mailboxes_scope_gap_emits_finding(db):
    with patch("tools.exo.get_token", return_value=FAKE_TOKEN), \
         patch("tools.exo.graph_get_all", return_value=[_user("u1")]), \
         patch("tools.exo._get_mailbox_settings", return_value=(None, False)):
        result = json.loads(exo_scan_mailboxes())
    assert result["findings"] == 1
    findings = json.loads(kb_get_findings(domain="exo"))
    assert any(f["finding_type"] == "exo_scope_gap" and f["severity"] == "Medium"
               for f in findings)


def test_scan_mailboxes_scope_gap_emitted_once_for_multiple_users(db):
    users = [_user("u1"), _user("u2"), _user("u3")]
    with patch("tools.exo.get_token", return_value=FAKE_TOKEN), \
         patch("tools.exo.graph_get_all", return_value=users), \
         patch("tools.exo._get_mailbox_settings", return_value=(None, False)):
        result = json.loads(exo_scan_mailboxes())
    assert result["findings"] == 1


# ---------------------------------------------------------------------------
# exo_scan_mailboxes — 404 (no mailbox) skipped silently
# ---------------------------------------------------------------------------

def test_scan_mailboxes_no_mailbox_user_skipped(db):
    with patch("tools.exo.get_token", return_value=FAKE_TOKEN), \
         patch("tools.exo.graph_get_all", return_value=[_user("u1")]), \
         patch("tools.exo._get_mailbox_settings", return_value=(None, True)):
        result = json.loads(exo_scan_mailboxes())
    assert result["findings"] == 0
    assert result["user_mailboxes"] == 0


# ---------------------------------------------------------------------------
# exo_scan_mailboxes — userPurpose classification
# ---------------------------------------------------------------------------

def test_user_mailbox_counted(db):
    settings_resp = _mailbox_settings("user")
    with patch("tools.exo.get_token", return_value=FAKE_TOKEN), \
         patch("tools.exo.graph_get_all", return_value=[_user("u1")]), \
         patch("tools.exo.graph_get", return_value=settings_resp):
        result = json.loads(exo_scan_mailboxes())
    assert result["user_mailboxes"] == 1
    assert result["shared_mailboxes"] == 0
    assert result["resource_mailboxes"] == 0
    assert result["findings"] == 0


def test_room_mailbox_counted_as_resource(db):
    settings_resp = _mailbox_settings("room")
    with patch("tools.exo.get_token", return_value=FAKE_TOKEN), \
         patch("tools.exo.graph_get_all", return_value=[_user("u1")]), \
         patch("tools.exo.graph_get", return_value=settings_resp):
        result = json.loads(exo_scan_mailboxes())
    assert result["resource_mailboxes"] == 1
    assert result["findings"] == 0


def test_equipment_mailbox_counted_as_resource(db):
    settings_resp = _mailbox_settings("equipment")
    with patch("tools.exo.get_token", return_value=FAKE_TOKEN), \
         patch("tools.exo.graph_get_all", return_value=[_user("u1")]), \
         patch("tools.exo.graph_get", return_value=settings_resp):
        result = json.loads(exo_scan_mailboxes())
    assert result["resource_mailboxes"] == 1
    assert result["findings"] == 0


# ---------------------------------------------------------------------------
# exo_scan_mailboxes — shared mailbox interactive login
# ---------------------------------------------------------------------------

def test_shared_mailbox_enabled_account_flagged_high(db):
    settings_resp = _mailbox_settings("shared")
    with patch("tools.exo.get_token", return_value=FAKE_TOKEN), \
         patch("tools.exo.graph_get_all", return_value=[_user("u1", enabled=True)]), \
         patch("tools.exo.graph_get", return_value=settings_resp):
        result = json.loads(exo_scan_mailboxes())
    assert result["shared_interactive"] == 1
    assert result["findings"] == 1
    findings = json.loads(kb_get_findings(domain="exo"))
    assert any(f["finding_type"] == "shared_mailbox_interactive" and f["severity"] == "High"
               for f in findings)


def test_shared_mailbox_disabled_account_no_finding(db):
    settings_resp = _mailbox_settings("shared")
    with patch("tools.exo.get_token", return_value=FAKE_TOKEN), \
         patch("tools.exo.graph_get_all", return_value=[_user("u1", enabled=False)]), \
         patch("tools.exo.graph_get", return_value=settings_resp):
        result = json.loads(exo_scan_mailboxes())
    assert result["shared_interactive"] == 0
    assert result["findings"] == 0


def test_shared_mailboxes_counted_regardless_of_enabled(db):
    settings_resp = _mailbox_settings("shared")
    users = [_user("u1", enabled=True), _user("u2", enabled=False)]
    with patch("tools.exo.get_token", return_value=FAKE_TOKEN), \
         patch("tools.exo.graph_get_all", return_value=users), \
         patch("tools.exo.graph_get", return_value=settings_resp):
        result = json.loads(exo_scan_mailboxes())
    assert result["shared_mailboxes"] == 2
    assert result["shared_interactive"] == 1


def test_scan_mailboxes_summary_shape(db):
    def _dispatch_settings(path, token, params=None):
        if "u1" in path:
            return _mailbox_settings("user")
        if "u2" in path:
            return _mailbox_settings("shared")
        if "u3" in path:
            return _mailbox_settings("room")
        return _mailbox_settings("user")

    users = [_user("u1"), _user("u2", enabled=True), _user("u3")]
    with patch("tools.exo.get_token", return_value=FAKE_TOKEN), \
         patch("tools.exo.graph_get_all", return_value=users), \
         patch("tools.exo.graph_get", side_effect=_dispatch_settings):
        result = json.loads(exo_scan_mailboxes())
    assert result["user_mailboxes"] == 1
    assert result["shared_mailboxes"] == 1
    assert result["resource_mailboxes"] == 1


# ---------------------------------------------------------------------------
# exo_scan_forwarding — scope gap
# ---------------------------------------------------------------------------

def test_scan_forwarding_scope_gap_emits_finding(db):
    def _rules_403(path, token, params=None):
        if "messageRules" in path:
            raise GraphError(403, path, "Forbidden")
        return [_user("u1")]

    with patch("tools.exo.get_token", return_value=FAKE_TOKEN), \
         patch("tools.exo.graph_get_all", side_effect=_rules_403):
        result = json.loads(exo_scan_forwarding())
    assert result["findings"] == 1
    findings = json.loads(kb_get_findings(domain="exo"))
    assert any(f["finding_type"] == "exo_scope_gap" for f in findings)


def test_scan_forwarding_scope_gap_emitted_once(db):
    call_count = [0]

    def _dispatch(path, token, params=None):
        if "messageRules" in path:
            raise GraphError(403, path, "Forbidden")
        return [_user("u1"), _user("u2"), _user("u3")]

    with patch("tools.exo.get_token", return_value=FAKE_TOKEN), \
         patch("tools.exo.graph_get_all", side_effect=_dispatch):
        result = json.loads(exo_scan_forwarding())
    assert result["findings"] == 1


# ---------------------------------------------------------------------------
# exo_scan_forwarding — no external rules
# ---------------------------------------------------------------------------

def test_no_forwarding_rules_no_finding(db):
    def _dispatch(path, token, params=None):
        if "messageRules" in path:
            return []
        return [_user("u1")]

    with patch("tools.exo.get_token", return_value=FAKE_TOKEN), \
         patch("tools.exo.graph_get_all", side_effect=_dispatch):
        result = json.loads(exo_scan_forwarding())
    assert result["findings"] == 0
    assert result["external_forwarding_rules"] == 0


def test_internal_forwarding_rule_not_flagged(db):
    internal_rule = _rule("r1", forward_to=["colleague@nofmetalcoatings.us"])

    def _dispatch(path, token, params=None):
        if "messageRules" in path:
            return [internal_rule]
        return [_user("u1")]

    with patch("tools.exo.get_token", return_value=FAKE_TOKEN), \
         patch("tools.exo.graph_get_all", side_effect=_dispatch):
        result = json.loads(exo_scan_forwarding())
    assert result["findings"] == 0
    assert result["external_forwarding_rules"] == 0


# ---------------------------------------------------------------------------
# exo_scan_forwarding — external rules detected
# ---------------------------------------------------------------------------

def test_external_forward_flagged_high(db):
    ext_rule = _rule("r1", forward_to=["personal@gmail.com"])

    def _dispatch(path, token, params=None):
        if "messageRules" in path:
            return [ext_rule]
        return [_user("u1")]

    with patch("tools.exo.get_token", return_value=FAKE_TOKEN), \
         patch("tools.exo.graph_get_all", side_effect=_dispatch):
        result = json.loads(exo_scan_forwarding())
    assert result["external_forwarding_rules"] == 1
    assert result["findings"] == 1
    findings = json.loads(kb_get_findings(domain="exo"))
    assert any(f["finding_type"] == "external_forwarding_rule" and f["severity"] == "High"
               for f in findings)


def test_external_redirect_flagged(db):
    redirect_rule = _rule("r2", redirect_to=["attacker@external.io"])

    def _dispatch(path, token, params=None):
        if "messageRules" in path:
            return [redirect_rule]
        return [_user("u1")]

    with patch("tools.exo.get_token", return_value=FAKE_TOKEN), \
         patch("tools.exo.graph_get_all", side_effect=_dispatch):
        result = json.loads(exo_scan_forwarding())
    assert result["external_forwarding_rules"] == 1


def test_disabled_external_rule_not_flagged(db):
    disabled_rule = _rule("r3", forward_to=["personal@gmail.com"], enabled=False)

    def _dispatch(path, token, params=None):
        if "messageRules" in path:
            return [disabled_rule]
        return [_user("u1")]

    with patch("tools.exo.get_token", return_value=FAKE_TOKEN), \
         patch("tools.exo.graph_get_all", side_effect=_dispatch):
        result = json.loads(exo_scan_forwarding())
    assert result["findings"] == 0


def test_multiple_users_external_rules_counted_per_rule(db):
    ext_rule1 = _rule("r1", forward_to=["ext@gmail.com"])
    ext_rule2 = _rule("r2", redirect_to=["other@yahoo.com"])
    int_rule = _rule("r3", forward_to=["ok@nofmetalcoatings.us"])

    call_state = {"users_returned": False}

    def _dispatch(path, token, params=None):
        if "messageRules" in path:
            if "u1" in path:
                return [ext_rule1, int_rule]
            if "u2" in path:
                return [ext_rule2]
            return []
        return [_user("u1"), _user("u2")]

    with patch("tools.exo.get_token", return_value=FAKE_TOKEN), \
         patch("tools.exo.graph_get_all", side_effect=_dispatch):
        result = json.loads(exo_scan_forwarding())
    assert result["external_forwarding_rules"] == 2
    assert result["rules_scanned"] == 3
    assert result["findings"] == 2


def test_onmicrosoft_domain_not_flagged(db):
    internal_ms_rule = _rule("r1", forward_to=["user@nofmetalcoatings.onmicrosoft.com"])

    def _dispatch(path, token, params=None):
        if "messageRules" in path:
            return [internal_ms_rule]
        return [_user("u1")]

    with patch("tools.exo.get_token", return_value=FAKE_TOKEN), \
         patch("tools.exo.graph_get_all", side_effect=_dispatch):
        result = json.loads(exo_scan_forwarding())
    assert result["findings"] == 0
