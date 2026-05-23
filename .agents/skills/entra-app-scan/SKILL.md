---
name: entra-app-scan
description: >
  Runs the Entra application governance scan — app registrations and guest accounts —
  via the MCNA-AMC MCP server. Surfaces findings by severity, writes results to
  reports/app-reg-governance/, and appends to activity-log.md.
  Trigger when user says "run the app scan", "scan app regs", "check Entra apps",
  "scan guests", or invokes /entra-app-scan.
---

## What this skill does

Calls two MCP tools against the live tenant:

| Tool | Scope |
|------|-------|
| `entra_scan_app_regs` | All app registrations — missing owners, expired/expiring secrets and certs, risky redirect URIs |
| `entra_scan_guests` | All guest accounts — recently added, inactive 90+ days, never signed in |

Results are upserted into the local knowledge base (`mcp-server/kb/mcna_amc.db`) and
returned as a JSON summary `{"scanned": N, "findings": M}`.

## Trigger conditions

Run both tools unless the user specifies one. Typical invocations:
- "Run the Entra scan" → both tools
- "Scan app regs" / "check app registrations" → `entra_scan_app_regs` only
- "Scan guests" / "check guest accounts" → `entra_scan_guests` only

## Auth requirements

- Token: admin account (`nof-dlafferty@nofmetalcoatings.us`)
- Cache: `C:/Users/dlafferty.MCNA/.msal_token_cache_admin.json`
- Required scopes (already granted): `Application.Read.All`, `Directory.Read.All`,
  `AuditLog.Read.All`, `Reports.Read.All`, `User.Read`
- If MCP returns a 401/403 or auth error: stop immediately, report to Dave, do not retry

## Execution steps

1. Call `entra_scan_app_regs` via MCP. Record `{"scanned": N, "findings": M}`.
2. Call `entra_scan_guests` via MCP (if in scope). Record results.
3. Query the KB for open findings from this run — group by severity (Critical, High, Medium, Low).
4. Write the report (see Output format below).
5. Append one line to `activity-log.md`.

## Output format

Write to `reports/app-reg-governance/YYYY-MM-DD.md`:

```
# Entra Application Scan — YYYY-MM-DD

## Summary
- App registrations scanned: N
- Guest accounts scanned: N
- Total open findings: N (Critical: X | High: Y | Medium: Z | Low: W)

## Critical findings
| App / Guest | Finding | Detail |
|-------------|---------|--------|
| ...         | ...     | ...    |

## High findings
...

## Medium findings
...

## Low findings
...

## Controls covered
IAM-APP-01 · IAM-APP-02 · IAM-APP-03 · IAM-GUEST-01 · IAM-GUEST-02
```

Omit severity sections with zero findings. If no findings at any severity, write
"No open findings." and stop.

## Activity log entry

Success:
```
YYYY-MM-DD HH:MM — Entra app scan — {N} app regs, {M} guests scanned; {X} findings (Critical: A, High: B) — reports/app-reg-governance/YYYY-MM-DD.md
```

Failure:
```
YYYY-MM-DD HH:MM — Entra app scan — FAILED — {reason}
```

## Guardrails

- Read-only throughout. No writes to Entra, no modification of any app reg or user.
- If any Graph call returns 401/403: surface the error to Dave immediately. Do not
  paper over it with empty output.
- Dismissed findings in the KB (status = "dismissed") are skipped by the scanner —
  do not re-surface them.
- Power Platform system apps with > 20 key credentials are excluded from expired-cert
  findings automatically (platform-managed cert rotation).

## Suppressed apps (missing owner check)

The scanner suppresses missing-owner findings for:
- `Report Message`
- `MessageCenterFeedBot`
- Any app whose display name starts with `ConnectSyncProvisioning_`

---

## Copilot Studio agent path

It is possible to expose this scan as a Copilot Studio agent action, but it requires
re-hosting. The current tool is local-only (Python MCP server + MSAL device code flow
+ local SQLite). Copilot Studio calls HTTP endpoints, not local processes.

**What would need to change:**

| Current | Required for Copilot Studio |
|---------|-----------------------------|
| Local Python MCP server | Azure Function (Python) hosting the same scan logic |
| MSAL device code flow | Client credentials flow (app-only) using `MCNA-TenantIntel-ReadOnly` cert or secret |
| Local SQLite KB | SharePoint list or Dataverse table for findings output |
| Claude Code invocation | Custom connector in Copilot Studio → Azure Function HTTP trigger |

**What's already in place:**
- `MCNA-TenantIntel-ReadOnly` already has `Application.Read.All` (application scope,
  admin consented) — no auth work needed for the Graph side.
- The scan logic in `mcp-server/tools/entra.py` is clean and self-contained — it can
  be lifted into an Azure Function with minimal changes.

**Effort estimate:** Medium. Azure Function + custom connector + output target (SharePoint
or Dataverse) + Copilot Studio action wiring. One sprint of focused work.

**Recommendation:** Build the Azure Function first and test it standalone before wiring
Copilot Studio. The custom connector layer is straightforward once the Function is stable.
