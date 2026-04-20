"""
power_platform_hygiene.py - MCNA Tenant Intel

Inventories Power Platform environments, canvas apps, cloud flows, solutions,
and connection references. Flags governance issues for Dave's review.
Read-only throughout. No email delivery.

Run on demand (not scheduled). Run manually, weekly or after PP changes.

Reads credentials from: C:/Users/dlafferty.MCNA/mcna-tenantintel.env
Auth: Primary account, MSAL device code flow, token cached locally.
      Three token audiences: Graph (user roster), BAP API (environments),
      PowerApps Service (apps/flows), Dataverse per org (solutions/conn refs).

Prerequisites: MCNA-TenantIntel-ReadOnly app reg must have:
  - Common Data Service: user_impersonation (Dataverse access)
  - PowerApps Service: User (apps/flows/environments access)
"""

import sys
sys.dont_write_bytecode = True

import csv
import datetime
import pathlib
from urllib.parse import urlparse

import msal
import requests


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

ENV_PATH = r"C:/Users/dlafferty.MCNA/mcna-tenantintel.env"

PROJECT_ROOT = pathlib.Path(__file__).parent
REPORTS_DIR = PROJECT_ROOT / "reports" / "power-platform-hygiene"
ACTIVITY_LOG = PROJECT_ROOT / "activity-log.md"

PRIMARY_TOKEN_CACHE = pathlib.Path(r"C:/Users/dlafferty.MCNA/.msal_token_cache_primary.json")

GRAPH_V1 = "https://graph.microsoft.com/v1.0"
BAP_BASE = "https://api.bap.microsoft.com"
POWERAPPS_BASE = "https://api.powerapps.com"
FLOW_BASE = "https://api.flow.microsoft.com"

GRAPH_SCOPES = ["https://graph.microsoft.com/.default"]
BAP_SCOPES = ["https://api.bap.microsoft.com/.default"]       # environments
POWERAPPS_SCOPES = ["https://api.powerapps.com/.default"]      # apps + flows
# Dataverse scopes are per-org: [f"https://{org_host}/.default"]

HIGH = "High"
MEDIUM = "Medium"
LOW = "Low"

SEVERITY_ORDER = {HIGH: 0, MEDIUM: 1, LOW: 2, "Clean": 3}

# Environment with no apps/flows older than this is flagged unused
UNUSED_ENV_DAYS = 90

# Canvas apps shared with more than this many users → High (production workload in wrong env)
SHARED_APP_HIGH_THRESHOLD = 5


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


def get_dv_token(tenant_id, client_id, org_url, cache_path, login_hint):
    """Acquire a Dataverse token scoped to the given org URL's hostname."""
    host = urlparse(org_url).netloc
    return get_token(tenant_id, client_id, [f"https://{host}/.default"], cache_path, login_hint)


# ---------------------------------------------------------------------------
# HTTP helpers (shared across Graph, PP, and Dataverse APIs — all use OData)
# ---------------------------------------------------------------------------

def _get(token, url, params=None, headers_extra=None, fatal_on_auth_error=True):
    headers = {"Authorization": f"Bearer {token}"}
    if headers_extra:
        headers.update(headers_extra)
    resp = requests.get(url, headers=headers, params=params)
    if resp.status_code in (401, 403):
        if fatal_on_auth_error:
            raise RuntimeError(f"Auth error {resp.status_code} on {url}: {resp.text[:200]}")
        return None
    resp.raise_for_status()
    return resp


def _get_pages(token, url, params=None, headers_extra=None, fatal_on_auth_error=True):
    items = []
    resp = _get(token, url, params, headers_extra, fatal_on_auth_error)
    if resp is None:
        return items
    data = resp.json()
    items.extend(data.get("value", []))
    while "@odata.nextLink" in data:
        resp = _get(token, data["@odata.nextLink"], headers_extra=headers_extra,
                    fatal_on_auth_error=fatal_on_auth_error)
        if resp is None:
            break
        data = resp.json()
        items.extend(data.get("value", []))
    return items


# ---------------------------------------------------------------------------
# Graph queries
# ---------------------------------------------------------------------------

def fetch_all_users(token):
    return _get_pages(token, f"{GRAPH_V1}/users", params={
        "$select": "id,displayName,userPrincipalName,mail,accountEnabled,userType",
        "$top": 999,
    })


def build_active_upns(users):
    return {
        u["userPrincipalName"].lower()
        for u in users
        if u.get("accountEnabled") and u.get("userPrincipalName")
    }


# ---------------------------------------------------------------------------
# Power Platform API queries (pp_token)
# ---------------------------------------------------------------------------

def fetch_environments(bap_token):
    url = (
        f"{BAP_BASE}/providers/Microsoft.BusinessAppPlatform/environments"
        "?api-version=2016-11-01&$expand=properties/linkedEnvironmentMetadata"
    )
    resp = _get(bap_token, url)
    return resp.json().get("value", []) if resp else []


def _env_name(env):
    return env.get("name") or ""


def _env_display(env):
    return (env.get("properties") or {}).get("displayName") or env.get("name") or ""


def _env_type(env):
    return (env.get("properties") or {}).get("environmentSku") or "Unknown"


def _env_org_url(env):
    """Return the Dataverse org URL (no trailing slash) or empty string."""
    meta = ((env.get("properties") or {}).get("linkedEnvironmentMetadata") or {})
    return (meta.get("instanceUrl") or "").rstrip("/")


def _env_created(env):
    return ((env.get("properties") or {}).get("createdTime") or "")[:10]


def fetch_apps_in_env(pp_token, env_name):
    """Fetch all canvas apps in an environment via the admin scope."""
    url = (
        f"{POWERAPPS_BASE}/providers/Microsoft.PowerApps/scopes/admin"
        f"/environments/{env_name}/apps?api-version=2016-11-01"
    )
    try:
        return _get_pages(pp_token, url, fatal_on_auth_error=False)
    except Exception as e:
        print(f"    NOTE: apps fetch failed for {env_name}: {e}")
        return []


def fetch_flows_in_env(pp_token, env_name):
    """Fetch all flows in an environment via the admin scope."""
    url = (
        f"{FLOW_BASE}/providers/Microsoft.ProcessSimple/scopes/admin"
        f"/environments/{env_name}/flows?api-version=2016-11-01&$top=250"
    )
    try:
        return _get_pages(pp_token, url, fatal_on_auth_error=False)
    except Exception as e:
        print(f"    NOTE: flows fetch failed for {env_name}: {e}")
        return []


# ---------------------------------------------------------------------------
# Dataverse queries (dv_token, per org URL)
# ---------------------------------------------------------------------------

def fetch_solutions(dv_token, org_url):
    """Fetch visible solutions from a Dataverse org. Returns [] on any error."""
    url = f"{org_url}/api/data/v9.2/solutions"
    try:
        return _get_pages(dv_token, url, params={
            "$select": "uniquename,friendlyname,version,ismanaged,createdon,modifiedon",
            "$filter": "isvisible eq true",
        }, fatal_on_auth_error=False)
    except Exception as e:
        print(f"    NOTE: solutions fetch failed: {e}")
        return []


def fetch_connection_refs(dv_token, org_url):
    """Fetch connection references with creator info. Returns [] on any error."""
    url = f"{org_url}/api/data/v9.2/connectionreferences"
    try:
        return _get_pages(dv_token, url, params={
            "$select": "connectionreferencedisplayname,connectorid,connectionid,createdon",
            "$expand": "createdby($select=fullname,internalemailaddress,isdisabled)",
        }, fatal_on_auth_error=False)
    except Exception as e:
        print(f"    NOTE: connection refs fetch failed: {e}")
        return []


# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------

def parse_dt(dt_str):
    if not dt_str:
        return None
    try:
        return datetime.datetime.fromisoformat(dt_str.replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        return None


def age_days(dt_str, now):
    dt = parse_dt(dt_str)
    return (now - dt).days if dt else None


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

def analyze_canvas_app(app, default_env_name):
    """
    Returns (sev, display_name, owner_email, desc, action) if finding exists, else None.
    Only flags apps in the Default environment.
    """
    props = app.get("properties") or {}
    if ((props.get("environment") or {}).get("name") or "") != default_env_name:
        return None

    name = props.get("displayName") or app.get("name") or "(unnamed)"
    shared_users = props.get("sharedUsersCount") or 0
    tenant_shared = props.get("sharedWithTenantsCount") or 0
    owner_email = ((props.get("owner") or {}).get("email") or "")

    if tenant_shared > 0 or shared_users > SHARED_APP_HIGH_THRESHOLD:
        shared_label = "entire tenant" if tenant_shared else f"{shared_users} users"
        return (
            HIGH, name, owner_email,
            f"Canvas app '{name}' in Default environment, shared with {shared_label}",
            "Move to a dedicated Production environment",
        )
    if shared_users > 0:
        return (
            MEDIUM, name, owner_email,
            f"Canvas app '{name}' in Default environment, shared with {shared_users} user(s)",
            "Evaluate whether a dedicated environment is appropriate",
        )
    return (
        LOW, name, owner_email,
        f"Canvas app '{name}' in Default environment (personal/unshared)",
        "No immediate action needed; move if it becomes broadly shared",
    )


def analyze_connection_ref(conn_ref, active_upns):
    """Returns (sev, display_name, owner_email, desc, action) or None if clean."""
    name = conn_ref.get("connectionreferencedisplayname") or "(unnamed)"
    created_by = conn_ref.get("createdby") or {}
    owner_email = (created_by.get("internalemailaddress") or "").lower()
    owner_name = created_by.get("fullname") or owner_email
    is_disabled = created_by.get("isdisabled") or False

    # Skip system/service accounts — no email means not a real user
    if not owner_email:
        return None

    if is_disabled or owner_email not in active_upns:
        status = "disabled account" if is_disabled else "departed user"
        return (
            HIGH, name, owner_email,
            f"Connection reference '{name}' owned by {owner_name} ({status})",
            "Reassign to an active owner; verify the underlying connection is still valid",
        )
    return None


def analyze_environment(env, apps, flows, solutions, now):
    """Returns list of (sev, desc) for environment-level findings."""
    findings = []
    env_type = _env_type(env)

    if env_type == "Trial":
        findings.append((LOW, "Trial environment (auto-expires; verify renewal intent)"))
        return findings

    if env_type in ("Default", "Production"):
        return findings

    created = _env_created(env)
    a = age_days(created, now)
    if not apps and not flows and not solutions and a is not None and a > UNUSED_ENV_DAYS:
        findings.append((
            MEDIUM,
            f"{env_type} environment with no apps, flows, or Dataverse solutions (age: {a}d) — likely unused",
        ))
    return findings


def analyze_dev_env_owner(env, active_upns):
    """Returns (sev, desc) if a Developer environment is owned by a departed user, else None."""
    if _env_type(env) != "Developer":
        return None
    created_by = ((env.get("properties") or {}).get("createdBy") or {})
    upn = (created_by.get("userPrincipalName") or "").lower()
    if upn and upn not in active_upns:
        return (LOW, f"Developer environment creator '{upn}' is not an active user")
    return None


def max_severity(findings):
    if not findings:
        return "Clean"
    return min(findings, key=lambda f: SEVERITY_ORDER.get(f[0], 99))[0]


# ---------------------------------------------------------------------------
# Output: Markdown
# ---------------------------------------------------------------------------

def build_markdown(
    env_findings, app_findings, conn_ref_findings, solution_findings,
    today_str, now_str, tenant_id, envs_scanned,
):
    all_sevs = (
        [s for _, findings in env_findings for s, _ in findings]
        + [r[0] for r in app_findings]
        + [r[0] for r in conn_ref_findings]
        + [r[0] for r in solution_findings]
    )
    total = len(all_sevs)
    high = all_sevs.count(HIGH)
    medium = all_sevs.count(MEDIUM)
    low = all_sevs.count(LOW)

    lines = [
        f"# Power Platform Hygiene Report — {today_str}",
        "",
        f"Generated: {now_str}  ",
        f"Tenant: {tenant_id}  ",
        "",
        "## Summary",
        "",
        f"- Environments scanned: {envs_scanned}",
        f"- Findings: {total} — High: {high} | Medium: {medium} | Low: {low}",
        "",
    ]

    for sev in (HIGH, MEDIUM, LOW):
        sev_env = [(env, f) for env, findings in env_findings for f in findings if f[0] == sev]
        sev_apps = [r for r in app_findings if r[0] == sev]
        sev_crs = [r for r in conn_ref_findings if r[0] == sev]
        sev_sols = [r for r in solution_findings if r[0] == sev]

        if not any([sev_env, sev_apps, sev_crs, sev_sols]):
            continue

        lines += [f"## {sev} Priority", ""]

        if sev_env:
            lines += ["### Environments", ""]
            for env, (s, desc) in sorted(sev_env, key=lambda x: _env_display(x[0]).lower()):
                lines += [
                    f"**{_env_display(env)}** ({_env_type(env)})",
                    f"- Created: {_env_created(env)}",
                    f"- Finding: {desc}",
                    f"- Action: Review and delete or repurpose if no longer needed",
                    "",
                ]

        if sev_apps:
            lines += ["### Canvas Apps in Default Environment", ""]
            for s, name, owner, desc, action in sorted(sev_apps, key=lambda r: r[1].lower()):
                lines += [
                    f"**{name}**" + (f" (owner: {owner})" if owner else ""),
                    f"- Finding: {desc}",
                    f"- Action: {action}",
                    "",
                ]

        if sev_crs:
            lines += ["### Connection References", ""]
            for s, name, owner, desc, action in sorted(sev_crs, key=lambda r: r[1].lower()):
                lines += [
                    f"**{name}**" + (f" (owner: {owner})" if owner else ""),
                    f"- Finding: {desc}",
                    f"- Action: {action}",
                    "",
                ]

        if sev_sols:
            lines += ["### Unpromoted Solutions", ""]
            for s, sol_name, env_display, desc, action in sorted(sev_sols, key=lambda r: r[1].lower()):
                lines += [
                    f"**{sol_name}** (environment: {env_display})",
                    f"- Finding: {desc}",
                    f"- Action: {action}",
                    "",
                ]

    if total == 0:
        lines += ["No issues found.", ""]

    lines += [
        "---",
        f"mcna-tenant-intel power_platform_hygiene.py — {now_str}",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Output: CSV
# ---------------------------------------------------------------------------

def build_csv_rows(env_findings, app_findings, conn_ref_findings, solution_findings):
    rows = []

    for env, findings in env_findings:
        if not findings:
            continue
        rows.append({
            "Type": "Environment",
            "Display Name": _env_display(env),
            "Environment": _env_display(env),
            "Owner": "",
            "Created": _env_created(env),
            "Last Modified": "",
            "Max Severity": max_severity(findings),
            "Findings": "; ".join(f"[{s}] {d}" for s, d in findings),
            "Recommended Action": "Review and delete or repurpose if unused",
        })

    for sev, name, owner, desc, action in app_findings:
        rows.append({
            "Type": "Canvas App",
            "Display Name": name,
            "Environment": "Default",
            "Owner": owner,
            "Created": "",
            "Last Modified": "",
            "Max Severity": sev,
            "Findings": desc,
            "Recommended Action": action,
        })

    for sev, name, owner, desc, action in conn_ref_findings:
        rows.append({
            "Type": "Connection Reference",
            "Display Name": name,
            "Environment": "",
            "Owner": owner,
            "Created": "",
            "Last Modified": "",
            "Max Severity": sev,
            "Findings": desc,
            "Recommended Action": action,
        })

    for sev, sol_name, env_display, desc, action in solution_findings:
        rows.append({
            "Type": "Solution",
            "Display Name": sol_name,
            "Environment": env_display,
            "Owner": "",
            "Created": "",
            "Last Modified": "",
            "Max Severity": sev,
            "Findings": desc,
            "Recommended Action": action,
        })

    rows.sort(key=lambda r: (SEVERITY_ORDER.get(r["Max Severity"], 99), r["Display Name"].lower()))
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
        env_config = load_env(ENV_PATH)
    except FileNotFoundError:
        print(f"ERROR: .env not found at {ENV_PATH}")
        sys.exit(1)

    tenant_id = env_config["TENANT_ID"]
    client_id = env_config["CLIENT_ID"]
    user_email = env_config["PRIMARY_MAILBOX"]

    # Auth: Graph (user roster)
    print(f"Authenticating ({user_email}) for Graph...")
    try:
        graph_token = get_token(tenant_id, client_id, GRAPH_SCOPES, PRIMARY_TOKEN_CACHE, login_hint=user_email)
    except Exception as e:
        msg = f"Graph auth failed: {e}"
        print(f"ERROR: {msg}")
        append_activity_log(f"{now_str} — Power Platform hygiene scan — FAILED — {msg}")
        sys.exit(1)

    # Auth: BAP API (environment enumeration)
    print("Acquiring BAP token (environments)...")
    try:
        bap_token = get_token(tenant_id, client_id, BAP_SCOPES, PRIMARY_TOKEN_CACHE, login_hint=user_email)
    except Exception as e:
        msg = f"BAP auth failed: {e}"
        print(f"ERROR: {msg}")
        append_activity_log(f"{now_str} — Power Platform hygiene scan — FAILED — {msg}")
        sys.exit(1)

    # Auth: PowerApps Service (apps + flows)
    print("Acquiring PowerApps token (apps/flows)...")
    try:
        pa_token = get_token(tenant_id, client_id, POWERAPPS_SCOPES, PRIMARY_TOKEN_CACHE, login_hint=user_email)
    except Exception as e:
        msg = f"PowerApps auth failed: {e}"
        print(f"ERROR: {msg}")
        append_activity_log(f"{now_str} — Power Platform hygiene scan — FAILED — {msg}")
        sys.exit(1)

    # Fetch active user roster
    print("Fetching active user roster...")
    try:
        all_users = fetch_all_users(graph_token)
        active_upns = build_active_upns(all_users)
        print(f"  {len(all_users)} users ({len(active_upns)} active)")
    except RuntimeError as e:
        msg = str(e)
        print(f"ERROR: {msg}")
        append_activity_log(f"{now_str} — Power Platform hygiene scan — FAILED — {msg}")
        sys.exit(1)

    # Fetch environments
    print("Fetching Power Platform environments...")
    try:
        envs = fetch_environments(bap_token)
        print(f"  {len(envs)} environments")
    except RuntimeError as e:
        msg = str(e)
        print(f"ERROR: {msg}")
        append_activity_log(f"{now_str} — Power Platform hygiene scan — FAILED — {msg}")
        sys.exit(1)

    default_env = next((e for e in envs if _env_type(e) == "Default"), None)
    default_env_name = _env_name(default_env) if default_env else ""
    prod_envs = [e for e in envs if _env_type(e) == "Production"]

    # Per-environment apps and flows
    env_apps = {}
    env_flows = {}
    for env in envs:
        env_name = _env_name(env)
        env_display = _env_display(env)
        print(f"  Apps/flows: {env_display}...")
        env_apps[env_name] = fetch_apps_in_env(pa_token, env_name)
        env_flows[env_name] = fetch_flows_in_env(pa_token, env_name)
        print(f"    {len(env_apps[env_name])} apps, {len(env_flows[env_name])} flows")

    # Per-environment Dataverse: solutions and connection references
    env_solutions = {}
    env_conn_refs = {}
    for env in envs:
        org_url = _env_org_url(env)
        if not org_url:
            continue
        env_name = _env_name(env)
        env_display = _env_display(env)
        print(f"  Dataverse: {env_display}...")
        try:
            dv_token = get_dv_token(tenant_id, client_id, org_url, PRIMARY_TOKEN_CACHE, user_email)
            env_solutions[env_name] = fetch_solutions(dv_token, org_url)
            env_conn_refs[env_name] = fetch_connection_refs(dv_token, org_url)
            print(f"    {len(env_solutions[env_name])} solutions, {len(env_conn_refs[env_name])} connection refs")
        except Exception as e:
            print(f"    NOTE: Dataverse failed for {env_display}: {e} — skipping")
            env_solutions[env_name] = []
            env_conn_refs[env_name] = []

    # Build production solution uniquename set for promotion check
    prod_solution_names = set()
    for env in prod_envs:
        for sol in env_solutions.get(_env_name(env), []):
            name = (sol.get("uniquename") or "").lower()
            if name:
                prod_solution_names.add(name)

    # Analysis: environments
    env_findings = []
    for env in envs:
        env_name = _env_name(env)
        findings = analyze_environment(env, env_apps.get(env_name, []), env_flows.get(env_name, []), env_solutions.get(env_name, []), now)
        dev_finding = analyze_dev_env_owner(env, active_upns)
        if dev_finding:
            findings.append(dev_finding)
        env_findings.append((env, findings))

    # Analysis: canvas apps (Default environment only)
    app_findings = []
    for env in envs:
        if _env_name(env) != default_env_name:
            continue
        for app in env_apps.get(_env_name(env), []):
            result = analyze_canvas_app(app, default_env_name)
            if result:
                app_findings.append(result)

    # Analysis: connection references (all Dataverse environments)
    conn_ref_findings = []
    for env in envs:
        for cr in env_conn_refs.get(_env_name(env), []):
            result = analyze_connection_ref(cr, active_upns)
            if result:
                conn_ref_findings.append(result)

    # Analysis: unpromoted solutions (sandbox/developer environments)
    solution_findings = []
    non_prod_types = {"Sandbox", "Developer"}
    for env in envs:
        if _env_type(env) not in non_prod_types:
            continue
        env_name = _env_name(env)
        env_display = _env_display(env)
        for sol in env_solutions.get(env_name, []):
            if sol.get("ismanaged"):
                continue
            uniquename = (sol.get("uniquename") or "").lower()
            friendly = sol.get("friendlyname") or sol.get("uniquename") or "(unnamed)"
            # Skip built-in system solutions present in every Dataverse environment
            if uniquename in ("default", "active", "basic"):
                continue
            if friendly.lower() in ("common data services default solution",):
                continue
            if uniquename and uniquename not in prod_solution_names:
                solution_findings.append((
                    MEDIUM, friendly, env_display,
                    f"Solution '{friendly}' exists in {env_display} but has no counterpart in any Production environment",
                    "Promote to Production or confirm abandonment and delete",
                ))

    # Write outputs
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    md_path = REPORTS_DIR / f"{today_str}.md"
    csv_path = REPORTS_DIR / f"{today_str}.csv"

    md_content = build_markdown(
        env_findings, app_findings, conn_ref_findings, solution_findings,
        today_str, now_str, tenant_id, envs_scanned=len(envs),
    )
    md_path.write_text(md_content, encoding="utf-8")
    print(f"\nWrote: {md_path}")

    csv_rows = build_csv_rows(env_findings, app_findings, conn_ref_findings, solution_findings)
    fieldnames = [
        "Type", "Display Name", "Environment", "Owner",
        "Created", "Last Modified", "Max Severity", "Findings", "Recommended Action",
    ]
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_rows)
    print(f"Wrote: {csv_path}")

    # Tally findings for activity log
    all_sevs = (
        [s for _, findings in env_findings for s, _ in findings]
        + [r[0] for r in app_findings]
        + [r[0] for r in conn_ref_findings]
        + [r[0] for r in solution_findings]
    )
    total = len(all_sevs)
    high = all_sevs.count(HIGH)
    medium = all_sevs.count(MEDIUM)
    low = all_sevs.count(LOW)

    outcome = f"{len(envs)} environments, {total} findings (High: {high}, Medium: {medium}, Low: {low})"
    print(f"\n{outcome}")
    append_activity_log(
        f"{now_str} — Power Platform hygiene scan — {outcome}"
        f" — reports/power-platform-hygiene/{today_str}.md"
    )


if __name__ == "__main__":
    main()
