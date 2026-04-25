# Scope Addition Record — MailboxSettings.Read Application
**Date:** 2026-04-24
**Requested by:** D. Lafferty (nof-dlafferty@nofmetalcoatings.us)
**Approved by:** D. Lafferty (IS Director — self-approval per IT-GOV-ENTRA-v1.0)
**App registration:** MCNA-TenantIntel-ReadOnly

---

## Scope added

| Permission | Type | Consent granted |
|---|---|---|
| MailboxSettings.Read | Application | 2026-04-24 |

---

## Justification

Delegated `MailboxSettings.Read` (consented 2026-04-23) only covers the
signed-in user's own mailbox for cross-user Graph calls. Full tenant mailbox
governance scans (`exo_scan_mailboxes`, `exo_scan_forwarding`) require
application-level permission to read mailbox settings and inbox rules for
all users without an interactive delegated session per user.

ApplicationImpersonation is deprecated in Exchange Online as of 2026 and
is not an acceptable alternative.

---

## Capability enabled

- Cross-user `mailboxSettings` reads via `/users/{id}/mailboxSettings` using
  client credentials token from `get_app_token()` in `mcp-server/auth.py`
- Cross-user inbox rule reads via `/users/{id}/mailFolders/inbox/messageRules`
- Shared mailbox interactive sign-in detection (EXO-SHARED-ENABLED-01)
- External mail forwarding rule detection (EXO-FORWARD-01)

---

## Auth implementation

`get_app_token()` added to `mcp-server/auth.py`. Uses `cryptography` (pkcs12)
to load `mcna-tenantintel-planner.pfx`, computes SHA1 thumbprint, and acquires
a client credentials token via MSAL `ConfidentialClientApplication`.
Certificate: MCNA-TenantIntel-Planner, expires 2028-04-16.

---

## Risk assessment

- Read-only application permission. No write capability added.
- Scope is limited to MailboxSettings only. Cannot read mail content.
- Access bounded to MCNA-TenantIntel-ReadOnly app reg (read-only per
  operating principles; write operations require separate MCNA-TenantIntel-Writer reg).
- PFX stored at `C:\Users\dlafferty.MCNA\` outside OneDrive-synced repo.

---

## Governance trail

- `docs/auth/app-registrations.md` updated (v1.6, 2026-04-24)
- First live scans run 2026-04-25: 187 users, 30 High findings surfaced
