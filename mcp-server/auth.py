from pathlib import Path
import hashlib
import msal
from cryptography.hazmat.primitives.serialization import pkcs12, Encoding, PrivateFormat, NoEncryption

ENV_PATH = Path(r"C:\Users\dlafferty.MCNA\mcna-tenantintel.env")
CACHE_PATH = Path(r"C:\Users\dlafferty.MCNA\.msal_token_cache_admin.json")
PFX_PATH = Path(r"C:\Users\dlafferty.MCNA\mcna-tenantintel-planner.pfx")
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
        msg = flow.get("message", "Device flow required but no message returned.")
        raise RuntimeError(
            f"MSAL token cache expired or missing for {ACCOUNT}.\n"
            f"Run  python mcp-server/refresh_auth.py  to re-authenticate, then retry.\n\n"
            f"Device code prompt:\n{msg}"
        )

    if "access_token" not in result:
        raise RuntimeError(f"Auth failed: {result.get('error_description', result)}")

    if cache.has_state_changed:
        CACHE_PATH.write_text(cache.serialize())

    return result["access_token"]


def get_app_token(resource: str = "https://graph.microsoft.com") -> str:
    env = _load_env()
    pfx_bytes = PFX_PATH.read_bytes()
    private_key, certificate, _ = pkcs12.load_key_and_certificates(pfx_bytes, password=None)
    private_key_pem = private_key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption()).decode()
    thumbprint = hashlib.sha1(certificate.public_bytes(Encoding.DER)).hexdigest().upper()

    app = msal.ConfidentialClientApplication(
        client_id=env["CLIENT_ID"],
        authority=f"https://login.microsoftonline.com/{env['TENANT_ID']}",
        client_credential={"thumbprint": thumbprint, "private_key": private_key_pem},
    )
    result = app.acquire_token_for_client(scopes=[f"{resource}/.default"])
    if not result or "access_token" not in result:
        raise RuntimeError(f"App token acquisition failed: {result.get('error_description', result)}")
    return result["access_token"]
