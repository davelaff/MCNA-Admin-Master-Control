"""
Re-authenticate MSAL token cache for the MCNA-TenantIntel-ReadOnly app.
Run this from the repo root when MCP tool calls fail with "token cache expired".

    python mcp-server/refresh_auth.py
"""
from pathlib import Path
import msal

ENV_PATH = Path(r"C:\Users\dlafferty.MCNA\mcna-tenantintel.env")
CACHE_PATH = Path(r"C:\Users\dlafferty.MCNA\.msal_token_cache_admin.json")
ACCOUNT = "nof-dlafferty@nofmetalcoatings.us"
SCOPES = ["https://graph.microsoft.com/.default"]


def _load_env() -> dict:
    env = {}
    with open(ENV_PATH) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip()
    return env


def main():
    env = _load_env()
    cache = msal.SerializableTokenCache()
    if CACHE_PATH.exists():
        cache.deserialize(CACHE_PATH.read_text())

    app = msal.PublicClientApplication(
        client_id=env["CLIENT_ID"],
        authority=f"https://login.microsoftonline.com/{env['TENANT_ID']}",
        token_cache=cache,
    )

    accounts = app.get_accounts(username=ACCOUNT)
    if accounts:
        result = app.acquire_token_silent(SCOPES, account=accounts[0])
        if result and "access_token" in result:
            print(f"Token still valid. No re-auth needed.")
            return

    print("Silent auth failed — starting device code flow...\n", flush=True)
    flow = app.initiate_device_flow(scopes=SCOPES)
    print(flow["message"], flush=True)
    print(flush=True)

    result = app.acquire_token_by_device_flow(flow)

    if "access_token" not in result:
        print(f"Auth failed: {result.get('error_description', result)}")
        raise SystemExit(1)

    if cache.has_state_changed:
        CACHE_PATH.write_text(cache.serialize())

    print(f"\nAuthenticated as {ACCOUNT}. Token cached.")
    print(f"Cache written to: {CACHE_PATH}")


if __name__ == "__main__":
    main()
