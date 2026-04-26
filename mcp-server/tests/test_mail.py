import json
from unittest.mock import patch

from db import get_connection
from tools.mail import mail_send_summary

FAKE_TOKEN = "fake-token"


def _activity_rows():
    with get_connection() as conn:
        return [
            dict(row)
            for row in conn.execute(
                "SELECT tool_name, domain, entity_id, outcome, detail FROM activity_log"
            ).fetchall()
        ]


def test_mail_send_summary_dry_run_does_not_call_graph_and_logs_attempt(db):
    with patch("tools.mail.get_token", return_value=FAKE_TOKEN), \
         patch("tools.mail.graph_post") as post:
        result = json.loads(mail_send_summary(
            to="ops@nofmetalcoatings.us",
            subject="Daily governance summary",
            body="No material changes.",
        ))

    post.assert_not_called()
    assert result["dry_run"] is True
    assert result["sent"] is False
    assert result["recipients"] == ["ops@nofmetalcoatings.us"]
    assert result["subject"] == "Daily governance summary"

    rows = _activity_rows()
    assert len(rows) == 1
    assert rows[0]["tool_name"] == "mail_send_summary"
    assert rows[0]["domain"] == "mail"
    assert rows[0]["outcome"] == "dry_run"
    detail = json.loads(rows[0]["detail"])
    assert detail["subject"] == "Daily governance summary"
    assert detail["recipients"] == ["ops@nofmetalcoatings.us"]


def test_mail_send_summary_sends_when_dry_run_false(db):
    with patch("tools.mail.get_token", return_value=FAKE_TOKEN), \
         patch("tools.mail.graph_post", return_value={}) as post:
        result = json.loads(mail_send_summary(
            to=["ops@nofmetalcoatings.us"],
            cc="audit@nofmetalcoatings.us",
            subject="Daily governance summary",
            body="No material changes.",
            importance="high",
            dry_run=False,
        ))

    assert result["dry_run"] is False
    assert result["sent"] is True
    assert result["error"] is None
    post.assert_called_once()
    path, token, body = post.call_args.args
    assert path == "/me/sendMail"
    assert token == FAKE_TOKEN
    assert body["saveToSentItems"] is True
    assert body["message"]["importance"] == "high"
    assert body["message"]["toRecipients"][0]["emailAddress"]["address"] == "ops@nofmetalcoatings.us"
    assert body["message"]["ccRecipients"][0]["emailAddress"]["address"] == "audit@nofmetalcoatings.us"

    rows = _activity_rows()
    assert rows[0]["outcome"] == "sent"


def test_mail_send_summary_rejects_real_send_without_required_fields(db):
    with patch("tools.mail.get_token") as get_token, \
         patch("tools.mail.graph_post") as post:
        result = json.loads(mail_send_summary(
            to="ops@nofmetalcoatings.us",
            subject="",
            body="No material changes.",
            dry_run=False,
        ))

    get_token.assert_not_called()
    post.assert_not_called()
    assert result["sent"] is False
    assert result["error"] == "actual send requires non-empty recipient, subject, and body"
    assert _activity_rows()[0]["outcome"] == "failed"


def test_mail_send_summary_logs_graph_failure_detail(db):
    with patch("tools.mail.get_token", return_value=FAKE_TOKEN), \
         patch("tools.mail.graph_post", side_effect=RuntimeError("Graph 500 at /me/sendMail: fail")):
        result = json.loads(mail_send_summary(
            to="ops@nofmetalcoatings.us",
            subject="Daily governance summary",
            body="No material changes.",
            dry_run=False,
        ))

    assert result["sent"] is False
    assert result["error"] == "Graph 500 at /me/sendMail: fail"
    rows = _activity_rows()
    assert rows[0]["outcome"] == "failed"
    assert "Graph 500" in rows[0]["detail"]


def test_mail_send_summary_registered_in_server():
    import server

    assert server.mail_send_summary is mail_send_summary
