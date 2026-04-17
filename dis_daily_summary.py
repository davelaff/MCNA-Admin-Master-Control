"""
dis_daily_summary.py - MCNA Tenant Intel
Reads Dave's inbox and sent items for DIS-related messages today,
produces a summary, sends it to Dave, and writes a local log.

Reads credentials from: C:/Users/dlafferty.MCNA/mcna-tenantintel.env
Auth: MSAL device code flow, tokens cached locally per account.

Two auth sessions:
  - nof-dlafferty@nofmetalcoatings.us  (admin account) - used for sendMail
  - dlafferty@nofmetalcoatings.us      (primary account) - used for mail read
"""

import sys
sys.dont_write_bytecode = True

import json
import datetime
import pathlib
import re

import msal
import requests


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

ENV_PATH = r"C:/Users/dlafferty.MCNA/mcna-tenantintel.env"

PROJECT_ROOT = pathlib.Path(__file__).parent
DIS_LOG_DIR = PROJECT_ROOT / "dis-log"
ACTIVITY_LOG = PROJECT_ROOT / "activity-log.md"

ADMIN_TOKEN_CACHE = pathlib.Path(r"C:/Users/dlafferty.MCNA/.msal_token_cache_admin.json")
PRIMARY_TOKEN_CACHE = pathlib.Path(r"C:/Users/dlafferty.MCNA/.msal_token_cache_primary.json")

GRAPH_BASE = "https://graph.microsoft.com/v1.0"

MAIL_SCOPES = [
    "Mail.Read",
    "Mail.Send",
    "User.Read",
]

ADMIN_SCOPES = [
    "Mail.Read",
    "Mail.Send",
    "User.Read",
    "Application.Read.All",
    "AuditLog.Read.All",
    "Directory.Read.All",
    "Policy.Read.All",
    "Reports.Read.All",
    "RoleManagement.Read.Directory",
]

DIS_DOMAINS = ["discomputers.com"]
DIS_KNOWN_SENDERS = ["nwhitelaw@discomputers.com", "tony@discomputers.com"]
DIS_TICKET_SENDER = "support@discomputers.com"
DIS_SUBJECT_MARKERS = ["[DIS]", "[Ticket #]", "DIS Support"]


# ---------------------------------------------------------------------------
# Load .env
# ---------------------------------------------------------------------------

def load_env(path):
    env = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def get_token(tenant_id, client_id, scopes, cache_path, login_hint=None):
    cache = msal.SerializableTokenCache()
    if cache_path.exists():
        cache.deserialize(cache_path.read_text())

    app = msal.PublicClientApplication(
        client_id=client_id,
        authority=f"https://login.microsoftonline.com/{tenant_id}",
        token_cache=cache,
    )

    accounts = app.get_accounts(username=login_hint)
    result = None
    if accounts:
        result = app.acquire_token_silent(scopes, account=accounts[0])

    if not result:
        flow = app.initiate_device_flow(scopes=scopes)
        if "user_code" not in flow:
            raise RuntimeError(f"Device flow failed: {flow}")
        print("\n" + flow["message"])
        print("Waiting for authentication...\n")
        result = app.acquire_token_by_device_flow(flow)

    if "access_token" not in result:
        raise RuntimeError(f"Auth failed: {result.get('error_description', result)}")

    if cache.has_state_changed:
        cache_path.write_text(cache.serialize())

    return result["access_token"]


# ---------------------------------------------------------------------------
# Graph helpers
# ---------------------------------------------------------------------------

def graph_get(token, url, params=None):
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(url, headers=headers, params=params)
    if resp.status_code in (401, 403):
        raise RuntimeError(f"Graph auth error {resp.status_code}: {resp.text}")
    resp.raise_for_status()
    return resp.json()


def graph_post(token, url, body):
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    resp = requests.post(url, headers=headers, json=body)
    if resp.status_code in (401, 403):
        raise RuntimeError(f"Graph auth error {resp.status_code}: {resp.text}")
    resp.raise_for_status()
    return resp


def get_all_pages(token, url, params=None):
    items = []
    data = graph_get(token, url, params)
    items.extend(data.get("value", []))
    while "@odata.nextLink" in data:
        data = graph_get(token, data["@odata.nextLink"])
        items.extend(data.get("value", []))
    return items


# ---------------------------------------------------------------------------
# Mail queries
# ---------------------------------------------------------------------------

def start_of_day_utc():
    local_now = datetime.datetime.now().astimezone()
    local_midnight = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
    utc_midnight = local_midnight.astimezone(datetime.timezone.utc)
    return utc_midnight.strftime("%Y-%m-%dT%H:%M:%SZ")


def fetch_inbox(token, start_utc):
    url = f"{GRAPH_BASE}/me/mailFolders/inbox/messages"
    params = {
        "$filter": f"receivedDateTime ge {start_utc}",
        "$select": "id,subject,from,toRecipients,ccRecipients,receivedDateTime,bodyPreview,conversationId,isRead",
        "$top": 100,
    }
    return get_all_pages(token, url, params)


def fetch_sent(token, start_utc):
    url = f"{GRAPH_BASE}/me/mailFolders/sentitems/messages"
    params = {
        "$filter": f"sentDateTime ge {start_utc}",
        "$select": "id,subject,from,toRecipients,ccRecipients,sentDateTime,bodyPreview,conversationId",
        "$top": 100,
    }
    return get_all_pages(token, url, params)


# ---------------------------------------------------------------------------
# DIS identity matching
# ---------------------------------------------------------------------------

def is_dis_address(address):
    addr = address.lower()
    if any(addr.endswith("@" + d.lower()) for d in DIS_DOMAINS):
        return True
    if addr in [s.lower() for s in DIS_KNOWN_SENDERS]:
        return True
    if addr == DIS_TICKET_SENDER.lower():
        return True
    return False


def is_dis_message(msg):
    from_addr = msg.get("from", {}).get("emailAddress", {}).get("address", "")
    if is_dis_address(from_addr):
        return True
    for r in msg.get("toRecipients", []) + msg.get("ccRecipients", []):
        if is_dis_address(r.get("emailAddress", {}).get("address", "")):
            return True
    subject = msg.get("subject", "")
    if any(marker.lower() in subject.lower() for marker in DIS_SUBJECT_MARKERS):
        return True
    return False


# ---------------------------------------------------------------------------
# Thread analysis
# ---------------------------------------------------------------------------

def classify_thread(messages):
    last = messages[-1]
    from_addr = last.get("from", {}).get("emailAddress", {}).get("address", "")
    from_name = last.get("from", {}).get("emailAddress", {}).get("name", from_addr)
    ts_str = last.get("receivedDateTime") or last.get("sentDateTime", "")
    try:
        ts = datetime.datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        time_fmt = ts.astimezone().strftime("%H:%M")
    except Exception:
        time_fmt = ts_str

    preview = last.get("bodyPreview", "").lower()
    closure_words = ["resolved", "closed", "thanks, all set", "all set", "complete", "done"]
    is_closure = any(w in preview for w in closure_words)
    last_is_dis = is_dis_address(from_addr)
    last_is_dave = not last_is_dis

    if is_closure and last_is_dave:
        return "Resolved today", from_name, time_fmt, None
    elif last_is_dis:
        return "Awaiting Dave", from_name, time_fmt, "Reply needed"
    elif last_is_dave:
        info_words = ["fyi", "for your information", "heads up", "just wanted to let"]
        if any(w in preview for w in info_words):
            return "Informational", from_name, time_fmt, None
        return "Awaiting DIS", from_name, time_fmt, None
    return "Informational", from_name, time_fmt, None


def is_ticket_message(msg):
    subject = msg.get("subject", "")
    from_addr = msg.get("from", {}).get("emailAddress", {}).get("address", "")
    return (
        from_addr.lower() == DIS_TICKET_SENDER.lower()
        or re.search(r"\[ticket\s*#?\d*\]", subject, re.IGNORECASE)
    )


def extract_ticket_info(msg):
    subject = msg.get("subject", "")
    preview = msg.get("bodyPreview", "")
    ticket_match = re.search(r"#(\d+)", subject)
    ticket_num = ticket_match.group(1) if ticket_match else "?"
    title = re.sub(r"\[ticket\s*#?\d*\]\s*", "", subject, flags=re.IGNORECASE).strip()
    status_match = re.search(
        r"(resolved|closed|open|pending|updated|assigned|escalated)",
        preview, re.IGNORECASE
    )
    status = status_match.group(1).capitalize() if status_match else "Updated"
    return ticket_num, title, status


# ---------------------------------------------------------------------------
# Summary builder
# ---------------------------------------------------------------------------

def build_summary(threads_by_conv, today_str, now_str):
    needs_response = []
    awaiting_dis = []
    resolved = []
    informational = []
    tickets = []

    total_messages = sum(len(v) for v in threads_by_conv.values())

    for conv_id, messages in threads_by_conv.items():
        messages_sorted = sorted(
            messages,
            key=lambda m: m.get("receivedDateTime") or m.get("sentDateTime", "")
        )
        subject = messages_sorted[-1].get("subject", "(no subject)")

        if any(is_ticket_message(m) for m in messages_sorted):
            ticket_num, title, status = extract_ticket_info(messages_sorted[-1])
            tickets.append(f"  #{ticket_num}: {title} - {status}")
            continue

        state, last_name, last_time, action = classify_thread(messages_sorted)
        preview = messages_sorted[-1].get("bodyPreview", "")[:120]

        if state == "Awaiting Dave":
            line = f"  [{subject}] - {preview}. Last from {last_name} at {last_time}."
            if action:
                line += f"\n    Action: {action}"
            needs_response.append(line)
        elif state == "Awaiting DIS":
            awaiting_dis.append(f"  [{subject}] - {preview}. You sent at {last_time}.")
        elif state == "Resolved today":
            resolved.append(f"  [{subject}] - Closed.")
        else:
            informational.append(f"  [{subject}] - {preview}")

    n_threads = len(threads_by_conv)

    if n_threads == 0:
        return f"No DIS activity {today_str}."

    lines = [f"{n_threads} thread{'s' if n_threads != 1 else ''}, {total_messages} total message{'s' if total_messages != 1 else ''}."]

    if needs_response:
        lines += ["", "## Needs response"] + needs_response
    if awaiting_dis:
        lines += ["", "## Awaiting DIS"] + awaiting_dis
    if resolved:
        lines += ["", "## Resolved today"] + resolved
    if informational:
        lines += ["", "## Informational"] + informational
    if tickets:
        lines += ["", "## Ticket system"] + tickets

    lines += [
        "",
        "---",
        f"Generated by mcna-tenant-intel at {now_str}.",
        f"Log: dis-log/{today_str}.md",
    ]

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Activity log
# ---------------------------------------------------------------------------

def append_activity_log(entry):
    with open(ACTIVITY_LOG, "a", encoding="utf-8") as f:
        f.write(entry + "\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    now = datetime.datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    now_str = now.strftime("%Y-%m-%d %H:%M")

    try:
        env = load_env(ENV_PATH)
    except FileNotFoundError:
        print(f"ERROR: .env not found at {ENV_PATH}")
        sys.exit(1)

    tenant_id = env["TENANT_ID"]
    client_id = env["CLIENT_ID"]
    user_email = env["USER_EMAIL"]
    primary_mailbox = env["PRIMARY_MAILBOX"]
    summary_recipient = env["SUMMARY_RECIPIENT"]

    # Auth: admin account
    print(f"Authenticating admin account ({user_email})...")
    try:
        admin_token = get_token(
            tenant_id, client_id, ADMIN_SCOPES,
            ADMIN_TOKEN_CACHE, login_hint=user_email
        )
    except Exception as e:
        msg = f"Admin auth failed: {e}"
        print(f"ERROR: {msg}")
        append_activity_log(f"{now_str} - DIS daily summary - FAILED - {msg}")
        sys.exit(1)

    # Auth: primary account
    print(f"Authenticating primary account ({primary_mailbox})...")
    try:
        primary_token = get_token(
            tenant_id, client_id, MAIL_SCOPES,
            PRIMARY_TOKEN_CACHE, login_hint=primary_mailbox
        )
    except Exception as e:
        msg = f"Primary auth failed: {e}"
        print(f"ERROR: {msg}")
        append_activity_log(f"{now_str} - DIS daily summary - FAILED - {msg}")
        sys.exit(1)

    print("Both accounts authenticated. Fetching mail...")
    start_utc = start_of_day_utc()

    try:
        admin_inbox = fetch_inbox(admin_token, start_utc)
        admin_sent = fetch_sent(admin_token, start_utc)
        print(f"  admin: {len(admin_inbox)} inbox, {len(admin_sent)} sent")
    except RuntimeError as e:
        msg = str(e)
        print(f"ERROR: {msg}")
        append_activity_log(f"{now_str} - DIS daily summary - FAILED - {msg}")
        sys.exit(1)

    try:
        primary_inbox = fetch_inbox(primary_token, start_utc)
        primary_sent = fetch_sent(primary_token, start_utc)
        print(f"  primary: {len(primary_inbox)} inbox, {len(primary_sent)} sent")
    except RuntimeError as e:
        msg = str(e)
        print(f"ERROR: {msg}")
        append_activity_log(f"{now_str} - DIS daily summary - FAILED - {msg}")
        sys.exit(1)

    all_messages = {}
    for m in admin_inbox + admin_sent + primary_inbox + primary_sent:
        all_messages[m["id"]] = m

    print(f"Total unique messages: {len(all_messages)}. Filtering for DIS...")

    dis_messages = [m for m in all_messages.values() if is_dis_message(m)]

    threads = {}
    for m in dis_messages:
        cid = m.get("conversationId", m["id"])
        threads.setdefault(cid, []).append(m)

    print(f"Found {len(threads)} DIS thread(s).")

    summary = build_summary(threads, today_str, now_str)
    print("\n--- Summary preview ---")
    print(summary)
    print("---\n")

    DIS_LOG_DIR.mkdir(exist_ok=True)
    log_path = DIS_LOG_DIR / f"{today_str}.md"
    with open(log_path, "w", encoding="utf-8") as f:
        f.write(f"# DIS activity - {today_str}\n\n")
        f.write(summary)
        f.write("\n\n---\n\n## Raw thread data\n\n")
        f.write("```json\n")
        f.write(json.dumps(threads, indent=2, default=str))
        f.write("\n```\n")

    n_threads = len(threads)
    subject = (
        f"No DIS activity {today_str}" if n_threads == 0
        else f"DIS activity - {today_str} - {n_threads} thread{'s' if n_threads != 1 else ''}"
    )

    # Send as HTML with UTF-8 charset to avoid encoding issues
    html_body = f"<html><head><meta charset='utf-8'></head><body><pre style='font-family:monospace'>{summary}</pre></body></html>"

    mail_body = {
        "message": {
            "subject": subject,
            "body": {"contentType": "HTML", "content": html_body},
            "toRecipients": [{"emailAddress": {"address": summary_recipient}}],
        },
        "saveToSentItems": True,
    }

    try:
        graph_post(admin_token, f"{GRAPH_BASE}/me/sendMail", mail_body)
        print(f"Email sent to {summary_recipient}.")
    except Exception as e:
        msg = f"sendMail failed: {e}"
        print(f"ERROR: {msg}")
        append_activity_log(f"{now_str} - DIS daily summary - FAILED - {msg}")
        sys.exit(1)

    total_messages = sum(len(v) for v in threads.values())
    append_activity_log(
        f"{now_str} - DIS daily summary - {n_threads} threads, {total_messages} messages"
        f" - dis-log/{today_str}.md"
    )

    print("Done.")


if __name__ == "__main__":
    main()
