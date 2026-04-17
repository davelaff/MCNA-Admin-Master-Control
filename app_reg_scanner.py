"""
app_reg_scanner.py - MCNA Tenant Intel

Inventories every app registration and enterprise app in the tenant.
Scores each finding by severity. Writes a risk register to reports/app-reg-governance/.

Run on demand (not scheduled). No email delivery.

Reads credentials from: C:/Users/dlafferty.MCNA/mcna-tenantintel.env
Auth: Admin account only (nof-dlafferty@nofmetalcoatings.us)
      MSAL device code flow, token cached locally.
"""

import sys
sys.dont_write_bytecode = True

import csv
import datetime
import pathlib

import msal
import requests


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

ENV_PATH = r"C:/Users/dlafferty.MCNA/mcna-tenantintel.env"

PROJECT_ROOT = pathlib.Path(__file__).parent
REPORTS_DIR = PROJECT_ROOT / "reports" / "app-reg-governance"
ACTIVITY_LOG = PROJECT_ROOT / "activity-log.md"

ADMIN_TOKEN_CACHE = pathlib.Path(r"C:/Users/dlafferty.MCNA/.msal_token_cache_admin.json")

GRAPH_V1 = "https://graph.microsoft.com/v1.0"
GRAPH_BETA = "https://graph.microsoft.com/beta"

ADMIN_SCOPES = [
    "Application.Read.All",
    "AuditLog.Read.All",
    "Directory.Read.All",
    "Reports.Read.All",
    "User.Read",
]

# Microsoft Services tenant ID -- used to filter out Microsoft-owned SPs
MICROSOFT_ORG_ID = "f8cdef31-a31e-4b4a-93e4-5f571e91255a"

CRITICAL = "Critical"
HIGH = "High"
MEDIUM = "Medium"
LOW = "Low"

SEVERITY_ORDER = {CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3, "Clean": 4}


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
# Auth (same pattern as dis_daily_summary.py)
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
# Graph helpers (same pattern as dis_daily_summary.py)
# ---------------------------------------------------------------------------

def graph_get(token, url, params=None):
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(url, headers=headers, params=params)
    if resp.status_code in (401, 403):
        raise RuntimeError(f"Graph auth error {resp.status_code}: {resp.text}")
    resp.raise_for_status()
    return resp.json()


def get_all_pages(token, url, params=None):
    items = []
    data = graph_get(token, url, params)
    items.extend(data.get("value", []))
    while "@odata.nextLink" in data:
        data = graph_get(token, data["@odata.nextLink"])
        items.extend(data.get("value", []))
    return items


# ---------------------------------------------------------------------------
# Graph queries
# ---------------------------------------------------------------------------

def fetch_app_registrations(token):
    """Fetch all app registrations (MCNA-owned) with credential and owner data."""
    url = f"{GRAPH_V1}/applications"
    params = {
        "$select": (
            "id,appId,displayName,createdDateTime,signInAudience,"
            "requiredResourceAccess,passwordCredentials,keyCredentials,"
            "web,publicClient,spa"
        ),
        "$expand": "owners($select=id,displayName,userPrincipalName)",
        "$top": 999,
    }
    return get_all_pages(token, url, params)


def fetch_service_principals(token):
    """Fetch all service principals (enterprise apps + first-party SP entries)."""
    url = f"{GRAPH_V1}/servicePrincipals"
    params = {
        "$select": (
            "id,appId,displayName,appOwnerOrganizationId,verifiedPublisher,"
            "tags,servicePrincipalType,accountEnabled"
        ),
        "$top": 999,
    }
    return get_all_pages(token, url, params)


def fetch_sp_sign_in_activities(token):
    """
    Fetch last sign-in datetime per service principal (appId -> datetime string).
    Returns None if the endpoint is unavailable -- callers skip that check.
    """
    headers = {"Authorization": f"Bearer {token}"}

    for base in (GRAPH_V1, GRAPH_BETA):
        url = f"{base}/reports/servicePrincipalSignInActivities"
        resp = requests.get(url, headers=headers)
        if resp.status_code in (401, 403):
            raise RuntimeError(f"Graph auth error {resp.status_code}: {resp.text}")
        if resp.status_code in (400, 404):
            # 404: endpoint not in this API version
            # 400: tenant lacks required license/feature (e.g. no AAD P2 / Entra ID P2)
            continue
        resp.raise_for_status()

        activities = {}
        data = resp.json()
        for item in data.get("value", []):
            app_id = item.get("appId")
            activity = item.get("lastSignInActivity") or {}
            last_dt = activity.get("lastSignInDateTime")
            if app_id:
                activities[app_id] = last_dt
        while "@odata.nextLink" in data:
            resp = requests.get(data["@odata.nextLink"], headers=headers)
            resp.raise_for_status()
            data = resp.json()
            for item in data.get("value", []):
                app_id = item.get("appId")
                activity = item.get("lastSignInActivity") or {}
                last_dt = activity.get("lastSignInDateTime")
                if app_id:
                    activities[app_id] = last_dt

        print(f"  {len(activities)} sign-in activity records (from {base})")
        return activities

    print("  NOTE: servicePrincipalSignInActivities not available -- skipping last sign-in checks.")
    return None


# ---------------------------------------------------------------------------
# Checks per app registration
# ---------------------------------------------------------------------------

def check_credentials(app, now):
    """Returns findings for expired or expiring secrets and certs."""
    findings = []
    now_naive = now.replace(tzinfo=None)

    def check_cred_list(cred_list, kind):
        for cred in cred_list:
            end_str = cred.get("endDateTime")
            if not end_str:
                continue
            try:
                end_dt = datetime.datetime.fromisoformat(
                    end_str.replace("Z", "+00:00")
                ).replace(tzinfo=None)
                days_left = (end_dt - now_naive).days
            except Exception:
                continue
            hint = cred.get("displayName") or (cred.get("keyId") or "")[:8]
            if days_left < 0:
                findings.append((CRITICAL, f"{kind} expired {abs(days_left)} days ago ({hint})"))
            elif days_left <= 30:
                findings.append((HIGH, f"{kind} expires in {days_left} days ({hint})"))
            elif days_left <= 90:
                findings.append((MEDIUM, f"{kind} expires in {days_left} days ({hint})"))

    check_cred_list(app.get("passwordCredentials") or [], "Secret")
    check_cred_list(app.get("keyCredentials") or [], "Certificate")
    return findings


def check_owners(app):
    owners = app.get("owners") or []
    if not owners:
        return [(HIGH, "No owners assigned")]
    return []


def check_redirect_uris(app):
    findings = []
    all_uris = []
    for key in ("web", "spa", "publicClient"):
        section = app.get(key) or {}
        all_uris.extend(section.get("redirectUris") or [])

    for uri in all_uris:
        uri_lower = uri.lower()
        if (
            uri_lower.startswith("http://")
            and "localhost" not in uri_lower
            and "127.0.0.1" not in uri_lower
        ):
            findings.append((HIGH, f"Insecure redirect URI (non-localhost http): {uri}"))
        if "*" in uri:
            findings.append((HIGH, f"Wildcard redirect URI: {uri}"))
    return findings


def check_audience(app):
    audience = app.get("signInAudience") or ""
    if audience in (
        "AzureADMultipleOrgs",
        "AzureADandPersonalMicrosoftAccount",
        "PersonalMicrosoftAccount",
    ):
        return [(MEDIUM, f"Multi-tenant sign-in audience: {audience}")]
    return []


def check_sign_in_activity(app, sp_map, sign_in_activities, now):
    """Flag apps with active credentials but no or stale sign-in activity."""
    if sign_in_activities is None:
        return []

    app_id = app.get("appId")
    if not sp_map.get(app_id):
        return []

    # Only flag if app has at least one active credential
    now_naive = now.replace(tzinfo=None)
    has_active_creds = False
    for cred in (app.get("passwordCredentials") or []) + (app.get("keyCredentials") or []):
        end_str = cred.get("endDateTime")
        if not end_str:
            continue
        try:
            end_dt = datetime.datetime.fromisoformat(
                end_str.replace("Z", "+00:00")
            ).replace(tzinfo=None)
            if end_dt > now_naive:
                has_active_creds = True
                break
        except Exception:
            pass

    if not has_active_creds:
        return []

    last_dt_str = sign_in_activities.get(app_id)
    if not last_dt_str:
        return [(MEDIUM, "Active credentials but no recorded sign-in activity")]

    try:
        last_dt = datetime.datetime.fromisoformat(
            last_dt_str.replace("Z", "+00:00")
        ).replace(tzinfo=None)
        days_since = (now_naive - last_dt).days
        if days_since > 90:
            return [(MEDIUM, f"Active credentials, last sign-in {days_since} days ago")]
    except Exception:
        pass

    return []


def analyze_app_reg(app, sp_map, sign_in_activities, now):
    findings = []
    findings.extend(check_credentials(app, now))
    findings.extend(check_owners(app))
    findings.extend(check_redirect_uris(app))
    findings.extend(check_audience(app))
    findings.extend(check_sign_in_activity(app, sp_map, sign_in_activities, now))
    return findings


def max_severity(findings):
    if not findings:
        return "Clean"
    return min(findings, key=lambda f: SEVERITY_ORDER.get(f[0], 99))[0]


# ---------------------------------------------------------------------------
# Enterprise app checks (3rd-party service principals)
# ---------------------------------------------------------------------------

def analyze_enterprise_apps(service_principals, owned_app_ids):
    """
    Returns list of (sp, findings) for 3rd-party enterprise apps with findings.
    Skips: MCNA-owned app regs, Microsoft-owned apps, managed identities.
    """
    results = []
    for sp in service_principals:
        app_id = sp.get("appId")
        if app_id in owned_app_ids:
            continue
        if sp.get("appOwnerOrganizationId") == MICROSOFT_ORG_ID:
            continue
        if sp.get("servicePrincipalType") == "ManagedIdentity":
            continue

        findings = []
        vp = sp.get("verifiedPublisher") or {}
        if not vp.get("displayName"):
            findings.append((LOW, "Publisher unverified"))

        if findings:
            results.append((sp, findings))

    return results


# ---------------------------------------------------------------------------
# Output: Markdown
# ---------------------------------------------------------------------------

def build_markdown(app_reg_results, enterprise_app_results, today_str, now_str, tenant_id):
    total_apps = len(app_reg_results)
    apps_with_findings = sum(1 for _, f in app_reg_results if f)
    counts = {sev: 0 for sev in (CRITICAL, HIGH, MEDIUM, LOW)}
    for _, findings in app_reg_results:
        for sev, _ in findings:
            if sev in counts:
                counts[sev] += 1

    lines = [
        f"# App Registration Governance Scan - {today_str}",
        f"",
        f"Generated: {now_str}  ",
        f"Tenant: {tenant_id}  ",
        f"",
        f"## Summary",
        f"",
        f"- App registrations scanned: {total_apps}",
        f"- Apps with findings: {apps_with_findings}",
        (
            f"- Critical: {counts[CRITICAL]} | "
            f"High: {counts[HIGH]} | "
            f"Medium: {counts[MEDIUM]} | "
            f"Low: {counts[LOW]}"
        ),
        f"",
    ]

    for sev_label in (CRITICAL, HIGH, MEDIUM, LOW):
        section_apps = [
            (app, findings)
            for app, findings in app_reg_results
            if any(s == sev_label for s, _ in findings)
        ]
        if not section_apps:
            continue
        lines += [f"## {sev_label}", ""]
        for app, findings in sorted(
            section_apps, key=lambda x: x[0].get("displayName", "").lower()
        ):
            name = app.get("displayName", "(unnamed)")
            app_id = app.get("appId", "")
            created = (app.get("createdDateTime") or "")[:10]
            owners = app.get("owners") or []
            owner_str = ", ".join(
                o.get("userPrincipalName") or o.get("displayName", "?")
                for o in owners
            ) or "NONE"
            lines += [
                f"### {name}",
                f"- App ID: `{app_id}`",
                f"- Created: {created}",
                f"- Owners: {owner_str}",
                f"- Findings:",
            ]
            for s, desc in sorted(findings, key=lambda x: SEVERITY_ORDER.get(x[0], 99)):
                lines += [f"  - **[{s}]** {desc}"]
            lines += [""]

    clean_apps = [(app, f) for app, f in app_reg_results if not f]
    if clean_apps:
        lines += ["## Clean (no findings)", ""]
        for app, _ in sorted(clean_apps, key=lambda x: x[0].get("displayName", "").lower()):
            name = app.get("displayName", "(unnamed)")
            app_id = app.get("appId", "")
            lines += [f"- {name} (`{app_id}`)"]
        lines += [""]

    if enterprise_app_results:
        display_count = min(len(enterprise_app_results), 20)
        lines += [f"## Enterprise apps (3rd party) - unverified publisher", ""]
        for sp, findings in enterprise_app_results[:display_count]:
            name = sp.get("displayName", "(unnamed)")
            app_id = sp.get("appId", "")
            lines += [f"- {name} (`{app_id}`)"]
            for s, desc in findings:
                lines += [f"  - [{s}] {desc}"]
        if len(enterprise_app_results) > 20:
            lines += [f"  ... and {len(enterprise_app_results) - 20} more (see CSV)"]
        lines += [""]

    lines += [
        "---",
        f"mcna-tenant-intel app_reg_scanner.py - {now_str}",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Output: CSV
# ---------------------------------------------------------------------------

def build_csv_rows(app_reg_results, enterprise_app_results):
    rows = []
    for app, findings in app_reg_results:
        owners = app.get("owners") or []
        owner_str = ", ".join(
            o.get("userPrincipalName") or o.get("displayName", "?")
            for o in owners
        ) or "NONE"
        rows.append({
            "Type": "App Registration",
            "Display Name": app.get("displayName", ""),
            "App ID": app.get("appId", ""),
            "Created": (app.get("createdDateTime") or "")[:10],
            "Owners": owner_str,
            "Max Severity": max_severity(findings),
            "Findings": "; ".join(f"[{s}] {d}" for s, d in findings) if findings else "",
        })
    for sp, findings in enterprise_app_results:
        rows.append({
            "Type": "Enterprise App",
            "Display Name": sp.get("displayName", ""),
            "App ID": sp.get("appId", ""),
            "Created": "",
            "Owners": "",
            "Max Severity": max_severity(findings),
            "Findings": "; ".join(f"[{s}] {d}" for s, d in findings) if findings else "",
        })
    rows.sort(
        key=lambda r: (SEVERITY_ORDER.get(r["Max Severity"], 99), r["Display Name"].lower())
    )
    return rows


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

    print(f"Authenticating admin account ({user_email})...")
    try:
        token = get_token(
            tenant_id, client_id, ADMIN_SCOPES,
            ADMIN_TOKEN_CACHE, login_hint=user_email,
        )
    except Exception as e:
        msg = f"Admin auth failed: {e}"
        print(f"ERROR: {msg}")
        append_activity_log(f"{now_str} - App reg scan - FAILED - {msg}")
        sys.exit(1)

    print("Authenticated. Fetching app registrations...")
    try:
        app_regs = fetch_app_registrations(token)
        print(f"  {len(app_regs)} app registrations")
    except RuntimeError as e:
        msg = str(e)
        print(f"ERROR: {msg}")
        append_activity_log(f"{now_str} - App reg scan - FAILED - {msg}")
        sys.exit(1)

    print("Fetching service principals...")
    try:
        service_principals = fetch_service_principals(token)
        print(f"  {len(service_principals)} service principals")
    except RuntimeError as e:
        msg = str(e)
        print(f"ERROR: {msg}")
        append_activity_log(f"{now_str} - App reg scan - FAILED - {msg}")
        sys.exit(1)

    print("Fetching sign-in activity data...")
    try:
        sign_in_activities = fetch_sp_sign_in_activities(token)
    except RuntimeError as e:
        msg = str(e)
        print(f"ERROR: {msg}")
        append_activity_log(f"{now_str} - App reg scan - FAILED - {msg}")
        sys.exit(1)

    # Build SP lookup: appId -> SP record
    sp_map = {sp["appId"]: sp for sp in service_principals if sp.get("appId")}
    owned_app_ids = {app["appId"] for app in app_regs if app.get("appId")}

    print(f"\nAnalyzing {len(app_regs)} app registrations...")
    app_reg_results = []
    for app in sorted(app_regs, key=lambda a: a.get("displayName", "").lower()):
        findings = analyze_app_reg(app, sp_map, sign_in_activities, now)
        app_reg_results.append((app, findings))

    print("Analyzing enterprise apps...")
    enterprise_app_results = analyze_enterprise_apps(service_principals, owned_app_ids)
    print(f"  {len(enterprise_app_results)} enterprise apps with findings")

    # Write outputs
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    md_path = REPORTS_DIR / f"{today_str}.md"
    csv_path = REPORTS_DIR / f"{today_str}.csv"

    md_content = build_markdown(
        app_reg_results, enterprise_app_results, today_str, now_str, tenant_id
    )
    md_path.write_text(md_content, encoding="utf-8")
    print(f"\nWrote: {md_path}")

    csv_rows = build_csv_rows(app_reg_results, enterprise_app_results)
    fieldnames = ["Type", "Display Name", "App ID", "Created", "Owners", "Max Severity", "Findings"]
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:  # utf-8-sig for Excel
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_rows)
    print(f"Wrote: {csv_path}")

    total_findings = sum(1 for _, f in app_reg_results if f)
    counts = {sev: 0 for sev in (CRITICAL, HIGH, MEDIUM, LOW)}
    for _, findings in app_reg_results:
        for sev, _ in findings:
            if sev in counts:
                counts[sev] += 1

    outcome = (
        f"{len(app_regs)} apps scanned, {total_findings} with findings "
        f"(Critical: {counts[CRITICAL]}, High: {counts[HIGH]})"
    )
    print(f"\n{outcome}")
    append_activity_log(
        f"{now_str} - App reg scan - {outcome}"
        f" - reports/app-reg-governance/{today_str}.md"
    )


if __name__ == "__main__":
    main()
