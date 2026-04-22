import time
import requests

BASE_URL = "https://graph.microsoft.com/v1.0"

class GraphError(Exception):
    def __init__(self, status: int, url: str, detail: str = ""):
        self.status = status
        self.url = url
        super().__init__(f"Graph {status} at {url}: {detail}")

def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Accept": "application/json"}

def graph_get(path: str, token: str, params: dict = None) -> dict:
    url = path if path.startswith("https://") else f"{BASE_URL}{path}"
    resp = requests.get(url, headers=_headers(token), params=params, timeout=30)
    if resp.status_code in (401, 403):
        raise GraphError(resp.status_code, url, resp.text[:200])
    if resp.status_code == 429:
        retry_after = int(resp.headers.get("Retry-After", "10"))
        time.sleep(retry_after)
        resp = requests.get(url, headers=_headers(token), params=params, timeout=30)
        if resp.status_code == 429:
            raise GraphError(429, url, "throttled after retry")
    resp.raise_for_status()
    return resp.json()

def graph_get_all(path: str, token: str, params: dict = None) -> list:
    results = []
    url = path if path.startswith("https://") else f"{BASE_URL}{path}"
    while url:
        data = graph_get(url, token, params)
        results.extend(data.get("value", []))
        url = data.get("@odata.nextLink")
        params = None
    return results

def graph_post(path: str, token: str, body: dict) -> dict:
    url = f"{BASE_URL}{path}"
    resp = requests.post(
        url,
        headers={**_headers(token), "Content-Type": "application/json"},
        json=body,
        timeout=30,
    )
    if resp.status_code in (401, 403):
        raise GraphError(resp.status_code, url, resp.text[:200])
    resp.raise_for_status()
    return resp.json() if resp.content else {}
