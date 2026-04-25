# Copilot Domain Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `tools/copilot.py` with two MCP tools — `copilot_scan_licenses` and `copilot_scan_settings` — that inventory Copilot for Microsoft 365 license assignments, surface oversharing-risk accounts, and probe the tenant's Copilot governance posture.

**Architecture:** Follows the established domain tool pattern: `get_token()` → Graph API calls → `_upsert_snapshot()` + `_upsert_finding()` → KB → JSON summary return. Both tools handle scope gaps gracefully (403/404 → scope_gap finding, not exception). New `COP-*` aliases added to `ssk_control_aliases.json` pointing to existing SSK controls that Copilot evidence supports.

**Tech Stack:** Python 3, `msal`/`auth.get_token`, `graph.graph_get_all`/`graph_get`/`GraphError`, `db.get_connection`, `tools.ssk_control_map.canonical_control_id`, `uuid5` for deterministic finding IDs, `pytest` with `db` fixture and `unittest.mock.patch`.

---

## File Structure

| File | Action | Purpose |
|------|--------|---------|
| `mcp-server/tools/copilot.py` | Create | Domain tool: two scan functions |
| `mcp-server/tests/test_copilot.py` | Create | Full test suite (TDD) |
| `mcp-server/kb/ssk_control_aliases.json` | Modify | Add 4 COP-* aliases |
| `mcp-server/server.py` | Modify | Register two new MCP tools |

---

## Task 1: Add COP-* control aliases

**Files:**
- Modify: `mcp-server/kb/ssk_control_aliases.json`

Copilot evidence contributes to four existing SSK controls. Aliases let `CONTRIBUTES_TO` dicts use readable keys without coupling to raw control IDs.

- [ ] **Step 1: Read current aliases file**

```bash
cat mcp-server/kb/ssk_control_aliases.json
```

- [ ] **Step 2: Add four COP-* entries**

Open `mcp-server/kb/ssk_control_aliases.json`. Insert before the closing `}`:

```json
  "COP-LICENSE-01": "06-3",
  "COP-ACCESS-01":  "08-3",
  "COP-SETTINGS-01": "15-3",
  "COP-USAGE-01":   "15-4"
```

Make sure the preceding line has a trailing comma. The full set of new lines:

```json
  "COP-LICENSE-01":  "06-3",
  "COP-ACCESS-01":   "08-3",
  "COP-SETTINGS-01": "15-3",
  "COP-USAGE-01":    "15-4"
```

- [ ] **Step 3: Verify JSON is valid**

```bash
cd mcp-server && python3 -c "import json; json.load(open('kb/ssk_control_aliases.json')); print('OK')"
```

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
rtk git add mcp-server/kb/ssk_control_aliases.json
rtk git commit -m "feat(copilot): add COP-* SSK control aliases (06-3, 08-3, 15-3, 15-4)"
```

---

## Task 2: Write failing tests for `copilot_scan_licenses`

**Files:**
- Create: `mcp-server/tests/test_copilot.py`
- Test: all tests in this file

These tests are written before the implementation. They will all fail with `ModuleNotFoundError` or `AttributeError` until Task 3 is complete.

- [ ] **Step 1: Create the test file**

Create `mcp-server/tests/test_copilot.py`:

```python
import json
from unittest.mock import patch
from tools.copilot import copilot_scan_licenses, copilot_scan_settings
from tools.kb import kb_get_findings

FAKE_TOKEN = "fake"


def _sku(part: str, sku_id: str = None, prepaid: int = 10, consumed: int = 5) -> dict:
    return {
        "id": f"tenant_{part}",
        "skuId": sku_id or f"sku-{part}",
        "skuPartNumber": part,
        "prepaidUnits": {"enabled": prepaid, "suspended": 0, "warning": 0},
        "consumedUnits": consumed,
        "servicePlans": [],
    }


def _user(uid: str, upn: str, enabled: bool = True, sku_ids: list = None) -> dict:
    return {
        "id": uid,
        "userPrincipalName": upn,
        "displayName": upn.split("@")[0],
        "accountEnabled": enabled,
        "assignedLicenses": [{"skuId": s, "disabledPlans": []} for s in (sku_ids or [])],
    }


# ------------------------------------------------ copilot_scan_licenses


def test_summary_shape_no_copilot_users(db):
    skus = [_sku("O365_BUSINESS_PREMIUM", sku_id="sku-bp")]
    users = [_user("u1", "alice@mcna.com", enabled=True, sku_ids=["sku-bp"])]
    with patch("tools.copilot.get_token", return_value=FAKE_TOKEN), \
         patch("tools.copilot.graph_get_all", side_effect=[skus, users]):
        result = json.loads(copilot_scan_licenses())
    assert result["copilot_users"] == 0
    assert result["findings"] == 0


def test_copilot_user_counted(db):
    skus = [
        _sku("O365_BUSINESS_PREMIUM", sku_id="sku-bp"),
        _sku("Microsoft_365_Copilot", sku_id="sku-cop"),
    ]
    users = [_user("u1", "alice@mcna.com", enabled=True, sku_ids=["sku-bp", "sku-cop"])]
    with patch("tools.copilot.get_token", return_value=FAKE_TOKEN), \
         patch("tools.copilot.graph_get_all", side_effect=[skus, users]):
        result = json.loads(copilot_scan_licenses())
    assert result["copilot_users"] == 1
    assert result["findings"] == 0


def test_disabled_copilot_user_flags_high(db):
    skus = [
        _sku("O365_BUSINESS_PREMIUM", sku_id="sku-bp"),
        _sku("Microsoft_365_Copilot", sku_id="sku-cop"),
    ]
    users = [_user("u1", "former@mcna.com", enabled=False, sku_ids=["sku-bp", "sku-cop"])]
    with patch("tools.copilot.get_token", return_value=FAKE_TOKEN), \
         patch("tools.copilot.graph_get_all", side_effect=[skus, users]):
        copilot_scan_licenses()
    fs = json.loads(kb_get_findings(domain="copilot"))
    assert any(
        f["finding_type"] == "copilot_licensed_disabled" and f["severity"] == "High"
        for f in fs
    )


def test_enabled_copilot_user_not_flagged_as_disabled(db):
    skus = [
        _sku("O365_BUSINESS_PREMIUM", sku_id="sku-bp"),
        _sku("Microsoft_365_Copilot", sku_id="sku-cop"),
    ]
    users = [_user("u1", "active@mcna.com", enabled=True, sku_ids=["sku-bp", "sku-cop"])]
    with patch("tools.copilot.get_token", return_value=FAKE_TOKEN), \
         patch("tools.copilot.graph_get_all", side_effect=[skus, users]):
        copilot_scan_licenses()
    fs = json.loads(kb_get_findings(domain="copilot"))
    assert not any(f["finding_type"] == "copilot_licensed_disabled" for f in fs)


def test_copilot_without_base_license_flags_medium(db):
    # Copilot is an add-on requiring a qualifying M365 base license.
    # A user assigned only the Copilot SKU has a misconfigured license.
    skus = [_sku("Microsoft_365_Copilot", sku_id="sku-cop")]
    users = [_user("u1", "orphan@mcna.com", enabled=True, sku_ids=["sku-cop"])]
    with patch("tools.copilot.get_token", return_value=FAKE_TOKEN), \
         patch("tools.copilot.graph_get_all", side_effect=[skus, users]):
        copilot_scan_licenses()
    fs = json.loads(kb_get_findings(domain="copilot"))
    assert any(
        f["finding_type"] == "copilot_no_base_license" and f["severity"] == "Medium"
        for f in fs
    )


def test_copilot_with_base_license_not_flagged_no_base(db):
    skus = [
        _sku("O365_BUSINESS_PREMIUM", sku_id="sku-bp"),
        _sku("Microsoft_365_Copilot", sku_id="sku-cop"),
    ]
    users = [_user("u1", "dave@mcna.com", enabled=True, sku_ids=["sku-bp", "sku-cop"])]
    with patch("tools.copilot.get_token", return_value=FAKE_TOKEN), \
         patch("tools.copilot.graph_get_all", side_effect=[skus, users]):
        copilot_scan_licenses()
    fs = json.loads(kb_get_findings(domain="copilot"))
    assert not any(f["finding_type"] == "copilot_no_base_license" for f in fs)


def test_idempotent_second_scan_does_not_duplicate(db):
    skus = [
        _sku("O365_BUSINESS_PREMIUM", sku_id="sku-bp"),
        _sku("Microsoft_365_Copilot", sku_id="sku-cop"),
    ]
    users = [_user("u1", "former@mcna.com", enabled=False, sku_ids=["sku-bp", "sku-cop"])]
    for _ in range(2):
        with patch("tools.copilot.get_token", return_value=FAKE_TOKEN), \
             patch("tools.copilot.graph_get_all", side_effect=[skus[:], users[:]]):
            copilot_scan_licenses()
    fs = json.loads(kb_get_findings(domain="copilot"))
    disabled_findings = [f for f in fs if f["finding_type"] == "copilot_licensed_disabled"]
    assert len(disabled_findings) == 1


def test_dismissed_finding_not_reopened(db):
    from db import get_connection
    skus = [
        _sku("O365_BUSINESS_PREMIUM", sku_id="sku-bp"),
        _sku("Microsoft_365_Copilot", sku_id="sku-cop"),
    ]
    users = [_user("u1", "former@mcna.com", enabled=False, sku_ids=["sku-bp", "sku-cop"])]
    with patch("tools.copilot.get_token", return_value=FAKE_TOKEN), \
         patch("tools.copilot.graph_get_all", side_effect=[skus, users]):
        copilot_scan_licenses()
    fs = json.loads(kb_get_findings(domain="copilot"))
    fid = next(f["finding_id"] for f in fs if f["finding_type"] == "copilot_licensed_disabled")
    with get_connection() as conn:
        conn.execute("UPDATE findings SET status='dismissed' WHERE finding_id=?", (fid,))
    with patch("tools.copilot.get_token", return_value=FAKE_TOKEN), \
         patch("tools.copilot.graph_get_all", side_effect=[skus, users]):
        copilot_scan_licenses()
    fs2 = json.loads(kb_get_findings(domain="copilot"))
    dismissed = next(f for f in fs2 if f["finding_id"] == fid)
    assert dismissed["status"] == "dismissed"


# ------------------------------------------------ copilot_scan_settings


def test_settings_scope_gap_produces_finding(db):
    from graph import GraphError
    err = GraphError(403, "Forbidden")
    with patch("tools.copilot.get_token", return_value=FAKE_TOKEN), \
         patch("tools.copilot.graph_get", side_effect=err):
        result = json.loads(copilot_scan_settings())
    assert result["available"] is False
    fs = json.loads(kb_get_findings(domain="copilot"))
    assert any(f["finding_type"] == "copilot_scope_gap" for f in fs)


def test_settings_404_treated_as_unavailable(db):
    from graph import GraphError
    err = GraphError(404, "Not Found")
    with patch("tools.copilot.get_token", return_value=FAKE_TOKEN), \
         patch("tools.copilot.graph_get", side_effect=err):
        result = json.loads(copilot_scan_settings())
    assert result["available"] is False


def test_settings_available_returns_summary(db):
    settings_payload = {
        "isEnabledInOrg": True,
        "userAccessPolicy": "AllowAll",
    }
    with patch("tools.copilot.get_token", return_value=FAKE_TOKEN), \
         patch("tools.copilot.graph_get", return_value=settings_payload):
        result = json.loads(copilot_scan_settings())
    assert result["available"] is True
    assert "isEnabledInOrg" in result


def test_settings_copilot_disabled_tenantwide_is_informational(db):
    # Copilot disabled at tenant level = no findings (it is off, not misconfigured)
    settings_payload = {
        "isEnabledInOrg": False,
    }
    with patch("tools.copilot.get_token", return_value=FAKE_TOKEN), \
         patch("tools.copilot.graph_get", return_value=settings_payload):
        result = json.loads(copilot_scan_settings())
    assert result["available"] is True
    assert result["findings"] == 0
```

- [ ] **Step 2: Run tests to confirm they all fail with import error**

```bash
cd mcp-server && python3 -m pytest tests/test_copilot.py -v 2>&1 | head -20
```

Expected: `ImportError: cannot import name 'copilot_scan_licenses' from 'tools.copilot'` (or `ModuleNotFoundError`). All tests fail — that's correct.

- [ ] **Step 3: Commit failing tests**

```bash
rtk git add mcp-server/tests/test_copilot.py
rtk git commit -m "test(copilot): failing tests for copilot_scan_licenses + copilot_scan_settings"
```

---

## Task 3: Implement `tools/copilot.py`

**Files:**
- Create: `mcp-server/tools/copilot.py`

- [ ] **Step 1: Check GraphError import signature**

```bash
cd mcp-server && grep -n "class GraphError" graph.py
```

Expected: line showing `class GraphError(Exception):` with `status` and `message` in `__init__`. Confirm attribute name is `.status` (not `.status_code`).

- [ ] **Step 2: Create `mcp-server/tools/copilot.py`**

```python
import json
import uuid
from datetime import datetime, timezone
from auth import get_token
from graph import graph_get, graph_get_all, GraphError
from db import get_connection
from tools.ssk_control_map import canonical_control_id

DOMAIN = "copilot"

CONTRIBUTES_TO = {
    "__tool__": [
        canonical_control_id("COP-LICENSE-01"),
        canonical_control_id("COP-ACCESS-01"),
        canonical_control_id("COP-SETTINGS-01"),
        canonical_control_id("COP-USAGE-01"),
    ],
    "copilot_licensed_disabled": [
        canonical_control_id("COP-ACCESS-01"),
        canonical_control_id("COP-LICENSE-01"),
    ],
    "copilot_no_base_license": [canonical_control_id("COP-LICENSE-01")],
    "copilot_scope_gap":       [canonical_control_id("COP-SETTINGS-01")],
}

# SKU partNumbers that constitute qualifying M365 base licenses for Copilot.
# Copilot for Microsoft 365 requires one of these as a prerequisite.
BASE_LICENSE_SKUS: set[str] = {
    "O365_BUSINESS_PREMIUM",
    "O365_BUSINESS_ESSENTIALS",
    "O365_BUSINESS",
    "SPB",
    "SPE_E3",
    "SPE_E5",
    "ENTERPRISEPACK",
    "ENTERPRISEPREMIUM",
    "STANDARDPACK",
    "TEAMS_ESSENTIALS",
    "Microsoft_Teams_Essentials",
}

# SKU partNumbers that are Copilot for Microsoft 365.
COPILOT_SKUS: set[str] = {
    "Microsoft_365_Copilot",
    "COPILOT_FOR_M365",
}

COPILOT_SETTINGS_PATH = "/beta/admin/microsoft365/copilotSettings"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _upsert_snapshot(conn, entity_type: str, entity_id: str, entity_name: str, props: dict) -> None:
    conn.execute("""
        INSERT INTO tenant_snapshot (entity_type, entity_id, entity_name, domain, properties, last_scanned)
        VALUES (?,?,?,?,?,?)
        ON CONFLICT(entity_type, entity_id) DO UPDATE SET
            entity_name=excluded.entity_name,
            properties=excluded.properties,
            last_scanned=excluded.last_scanned
    """, (entity_type, entity_id, entity_name, DOMAIN, json.dumps(props), _now()))


def _upsert_finding(conn, object_type: str, object_id: str, object_name: str,
                    finding_type: str, severity: str, recommended_action: str,
                    owner: str = None, securesketch_control: str = None) -> str:
    finding_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{DOMAIN}.{object_type}.{object_id}.{finding_type}"))
    existing = conn.execute("SELECT status FROM findings WHERE finding_id=?", (finding_id,)).fetchone()
    if existing and existing["status"] == "dismissed":
        return finding_id
    now = _now()
    conn.execute("""
        INSERT INTO findings
            (finding_id,domain,object_type,object_id,object_name,owner,finding_type,
             severity,securesketch_control,recommended_action,status,first_seen,last_seen)
        VALUES (?,?,?,?,?,?,?,?,?,?,'open',?,?)
        ON CONFLICT(finding_id) DO UPDATE SET
            last_seen=excluded.last_seen,
            object_name=excluded.object_name,
            owner=excluded.owner
    """, (finding_id, DOMAIN, object_type, object_id, object_name, owner,
          finding_type, severity, securesketch_control, recommended_action, now, now))
    return finding_id


def copilot_scan_licenses() -> str:
    """Inventory Copilot for Microsoft 365 license assignments.
    Flags disabled accounts holding Copilot (oversharing risk if reactivated)
    and Copilot assignments without a qualifying base license (misconfiguration).
    Requires no scopes beyond Directory.Read.All already consented."""
    token = get_token()
    skus = graph_get_all("/subscribedSkus", token)
    sku_part = {s["skuId"]: s.get("skuPartNumber", s["skuId"]) for s in skus}

    users = graph_get_all(
        "/users?$select=id,userPrincipalName,displayName,accountEnabled,assignedLicenses&$top=999",
        token,
    )

    copilot_user_count = 0
    findings_count = 0

    with get_connection() as conn:
        for u in users:
            uid = u["id"]
            upn = u.get("userPrincipalName") or uid
            name = u.get("displayName") or upn
            enabled = u.get("accountEnabled", True)
            licenses = u.get("assignedLicenses") or []
            license_parts = [sku_part.get(lic["skuId"], lic["skuId"]) for lic in licenses]

            has_copilot = any(p in COPILOT_SKUS for p in license_parts)
            if not has_copilot:
                continue

            copilot_user_count += 1
            _upsert_snapshot(conn, "copilot_user", uid, name, {
                "upn": upn,
                "enabled": enabled,
                "license_parts": license_parts,
            })

            if not enabled:
                _upsert_finding(
                    conn, "copilot_user", uid, name,
                    "copilot_licensed_disabled", "High",
                    f"Disabled account {upn} holds a Copilot for M365 license. "
                    "Remove the Copilot license to eliminate the oversharing risk surface "
                    "if this account is ever reactivated.",
                    owner=upn,
                    securesketch_control="COP-ACCESS-01",
                )
                findings_count += 1

            has_base = any(p in BASE_LICENSE_SKUS for p in license_parts)
            if not has_base:
                _upsert_finding(
                    conn, "copilot_user", uid, name,
                    "copilot_no_base_license", "Medium",
                    f"{upn} has Copilot for M365 but no qualifying base license "
                    f"({', '.join(BASE_LICENSE_SKUS) if len(license_parts) < 3 else ', '.join(license_parts)}). "
                    "Assign a qualifying M365 base license (E3, Business Premium, etc.) "
                    "or remove the Copilot license.",
                    owner=upn,
                    securesketch_control="COP-LICENSE-01",
                )
                findings_count += 1

    return json.dumps({
        "domain": DOMAIN,
        "scanned_users": len(users),
        "copilot_users": copilot_user_count,
        "findings": findings_count,
    })


def copilot_scan_settings() -> str:
    """Probe the Copilot for M365 admin settings via the Graph beta endpoint.
    Returns tenant-level enablement and access policy. 403/404 = scope gap finding.
    Requires no additional scopes for the probe; full settings read needs
    Microsoft365CopilotSettings.Read.All (not yet consented)."""
    token = get_token()
    findings_count = 0

    try:
        settings = graph_get(COPILOT_SETTINGS_PATH, token)
        available = True
    except GraphError as e:
        settings = {}
        available = e.status not in (400, 403, 404)
        if not available:
            with get_connection() as conn:
                _upsert_finding(
                    conn, "tenant", "copilot-settings", "Copilot Settings",
                    "copilot_scope_gap", "Medium",
                    "Grant Microsoft365CopilotSettings.Read.All delegated consent to the "
                    "MCNA-TenantIntel-ReadOnly app registration to enable Copilot settings "
                    "governance visibility.",
                    securesketch_control="COP-SETTINGS-01",
                )
                findings_count += 1
            return json.dumps({
                "domain": DOMAIN,
                "available": False,
                "findings": findings_count,
            })
        raise

    with get_connection() as conn:
        _upsert_snapshot(conn, "copilot_settings", "tenant", "Copilot Settings", settings)

    result = {
        "domain": DOMAIN,
        "available": True,
        "findings": findings_count,
    }
    if "isEnabledInOrg" in settings:
        result["isEnabledInOrg"] = settings["isEnabledInOrg"]
    if "userAccessPolicy" in settings:
        result["userAccessPolicy"] = settings["userAccessPolicy"]
    return json.dumps(result)
```

- [ ] **Step 3: Run tests**

```bash
cd mcp-server && python3 -m pytest tests/test_copilot.py -v
```

Expected: all 14 tests pass. If any fail, fix before proceeding.

- [ ] **Step 4: Run full suite to catch regressions**

```bash
cd mcp-server && python3 -m pytest --tb=short -q
```

Expected: previous test count + 14 new, all green.

- [ ] **Step 5: Commit**

```bash
rtk git add mcp-server/tools/copilot.py
rtk git commit -m "feat(copilot): implement copilot_scan_licenses + copilot_scan_settings"
```

---

## Task 4: Register tools in `server.py`

**Files:**
- Modify: `mcp-server/server.py`

- [ ] **Step 1: Add import**

In `mcp-server/server.py`, find the block of domain imports (around line 13–15 where `exo` is imported). Add after the `exo` import line:

```python
from tools.copilot import copilot_scan_licenses, copilot_scan_settings
```

- [ ] **Step 2: Register tools**

Find the block where `exo_scan_mailboxes` and `exo_scan_forwarding` are registered (around line 76–77). Add after them:

```python
mcp.tool()(copilot_scan_licenses)
mcp.tool()(copilot_scan_settings)
```

- [ ] **Step 3: Verify server imports cleanly**

```bash
cd mcp-server && python3 -c "import server; print('OK')"
```

Expected: `OK` with no errors.

- [ ] **Step 4: Run full suite once more**

```bash
cd mcp-server && python3 -m pytest --tb=short -q
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
rtk git add mcp-server/server.py
rtk git commit -m "feat(copilot): register copilot_scan_licenses + copilot_scan_settings in server.py"
```

---

## Task 5: Live scan and activity log

**Files:**
- Modify: `activity-log.md`

- [ ] **Step 1: Run live `copilot_scan_licenses`**

In Claude Code, call the MCP tool:

```
copilot_scan_licenses
```

Record the output — note `copilot_users`, `findings`, and any finding types produced.

- [ ] **Step 2: Run live `copilot_scan_settings`**

```
copilot_scan_settings
```

Note whether `available` is `true` or `false`. If `false`, record the scope gap finding in the KB — that's the correct behavior, no action needed until `Microsoft365CopilotSettings.Read.All` is consented.

- [ ] **Step 3: Query KB findings**

```
kb_get_findings domain=copilot
```

Verify findings are present and correctly typed.

- [ ] **Step 4: Append to activity-log.md**

Add one line at the end of `activity-log.md`:

```
YYYY-MM-DD HH:MM — copilot domain agent — copilot_scan_licenses + copilot_scan_settings built (TDD), N tests passing; live scan: X copilot users, Y findings — mcp-server/tools/copilot.py, mcp-server/tests/test_copilot.py
```

Fill in actual date, test count, user count, and finding count.

- [ ] **Step 5: Final commit**

```bash
rtk git add activity-log.md
rtk git commit -m "docs: activity-log entry for copilot domain agent"
```

---

## Self-Review

**Spec coverage:**
- `copilot_scan_licenses` — Copilot license utilization ✓, disabled accounts ✓, no-base-license misconfiguration ✓
- `copilot_scan_settings` — Governance posture probe ✓, scope gap handling ✓, oversharing risk (label coverage) deferred — covered by `purview_scan_labels` already in KB
- CONTRIBUTES_TO wired ✓ (4 aliases × 2 finding types)
- server.py registration ✓
- idempotency tested ✓
- dismissed finding not reopened tested ✓

**Deferred (not in scope here):**
- `Reports.Read.All` usage telemetry (`getMicrosoft365CopilotUserDetailReport`) — needs CSV parsing, lower priority
- `Microsoft365CopilotSettings.Read.All` consent — can be added in a scope-add session after this lands; `copilot_scan_settings` will produce a scope_gap finding in the meantime

**Placeholder check:** None found.

**Type consistency:** `GraphError.status` used consistently (matches `graph.py` implementation in this codebase — verify at Task 3 Step 1 if unsure).
