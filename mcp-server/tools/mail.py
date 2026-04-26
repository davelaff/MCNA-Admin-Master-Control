import json
import uuid
from datetime import datetime, timezone

from auth import get_token
from db import get_connection
from graph import graph_post

DOMAIN = "mail"
TOOL_NAME = "mail_send_summary"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _addresses(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        values = [value]
    else:
        values = list(value)
    return [str(item).strip() for item in values if str(item).strip()]


def _recipients(addresses: list[str]) -> list[dict]:
    return [{"emailAddress": {"address": address}} for address in addresses]


def _log_attempt(entity_id: str, outcome: str, detail: dict) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO activity_log (run_id, timestamp, tool_name, domain, entity_id, outcome, detail)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                _now(),
                TOOL_NAME,
                DOMAIN,
                entity_id,
                outcome,
                json.dumps(detail, sort_keys=True),
            ),
        )


def _message_payload(
    to_addresses: list[str],
    cc_addresses: list[str],
    subject: str,
    body: str,
    importance: str,
    save_to_sent_items: bool,
) -> dict:
    return {
        "message": {
            "subject": subject,
            "body": {
                "contentType": "Text",
                "content": body,
            },
            "toRecipients": _recipients(to_addresses),
            "ccRecipients": _recipients(cc_addresses),
            "importance": importance,
        },
        "saveToSentItems": save_to_sent_items,
    }


def mail_send_summary(
    to,
    subject: str,
    body: str,
    cc=None,
    importance: str = "normal",
    save_to_sent_items: bool = True,
    dry_run: bool = True,
) -> str:
    """Send or preview a summary email through Graph /me/sendMail.

    Dry-run is the default and never calls Graph. Real sends require a
    non-empty recipient, subject, and body.
    """
    to_addresses = _addresses(to)
    cc_addresses = _addresses(cc)
    subject = (subject or "").strip()
    body = (body or "").strip()
    entity_id = ",".join(to_addresses) if to_addresses else "no-recipient"
    detail = {
        "recipients": to_addresses,
        "cc": cc_addresses,
        "subject": subject,
        "dry_run": dry_run,
        "save_to_sent_items": save_to_sent_items,
    }

    if not dry_run and (not to_addresses or not subject or not body):
        error = "actual send requires non-empty recipient, subject, and body"
        detail["error"] = error
        _log_attempt(entity_id, "failed", detail)
        return json.dumps({
            "recipients": to_addresses,
            "cc": cc_addresses,
            "subject": subject,
            "dry_run": dry_run,
            "sent": False,
            "error": error,
        })

    if dry_run:
        _log_attempt(entity_id, "dry_run", detail)
        return json.dumps({
            "recipients": to_addresses,
            "cc": cc_addresses,
            "subject": subject,
            "dry_run": dry_run,
            "sent": False,
            "error": None,
        })

    try:
        token = get_token()
        graph_post(
            "/me/sendMail",
            token,
            _message_payload(
                to_addresses,
                cc_addresses,
                subject,
                body,
                importance,
                save_to_sent_items,
            ),
        )
    except Exception as exc:
        error = str(exc)
        detail["error"] = error
        _log_attempt(entity_id, "failed", detail)
        return json.dumps({
            "recipients": to_addresses,
            "cc": cc_addresses,
            "subject": subject,
            "dry_run": dry_run,
            "sent": False,
            "error": error,
        })

    _log_attempt(entity_id, "sent", detail)
    return json.dumps({
        "recipients": to_addresses,
        "cc": cc_addresses,
        "subject": subject,
        "dry_run": dry_run,
        "sent": True,
        "error": None,
    })
