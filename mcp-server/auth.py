import sys
from pathlib import Path
import msal

ENV_PATH = Path(r"C:\Users\dlafferty.MCNA\mcna-tenantintel.env")
CACHE_PATH = Path(r"C:\Users\dlafferty.MCNA\.msal_token_cache_admin.json")
ACCOUNT = "nof-dlafferty@nofmetalcoatings.us"

def _load_env() -> dict:
    env = {}
    with open(ENV_PATH) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip()
    return env

def get_token(resource: str = "https://graph.microsoft.com") -> str:
    env = _load_env()
    cache = msal.SerializableTokenCache()
    if CACHE_PATH.exists():
        cache.deserialize(CACHE_PATH.read_text())

    app = msal.PublicClientApplication(
        client_id=env["CLIENT_ID"],
        authority=f"https://login.microsoftonline.com/{env['TENANT_ID']}",
        token_cache=cache,
    )

    scopes = [f"{resource}/.default"]
    accounts = app.get_accounts(username=ACCOUNT)
    result = None

    if accounts:
        result = app.acquire_token_silent(scopes, account=accounts[0])

    if not result:
        flow = app.initiate_device_flow(scopes=scopes)
        print(flow["message"], file=sys.stderr, flush=True)
        result = app.acquire_token_by_device_flow(flow)

    if "access_token" not in result:
        raise RuntimeError(f"Auth failed: {result.get('error_description', result)}")

    if cache.has_state_changed:
        CACHE_PATH.write_text(cache.serialize())

    return result["access_token"]
