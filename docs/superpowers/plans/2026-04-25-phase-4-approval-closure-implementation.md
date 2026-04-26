# Phase 4 Approval and Closure Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a KB-native remediation approval layer that records planned actions, explicit decisions, exported queues, and finding closure evidence without tenant writes.

**Architecture:** Add remediation plan/action/event tables to SQLite, then expose MCP tools in `tools/remediation.py`. Closure uses existing `ssk_evidence(evidence_type='finding_closure')` and `findings.closure_evidence_id`.

**Tech Stack:** Python, SQLite, pytest, FastMCP registration, existing `ssk_common` JSON/activity helpers.

---

### Task 1: Schema

**Files:**
- Modify: `mcp-server/db.py`
- Modify: `mcp-server/tests/test_db.py`

- [x] **Step 1: Write schema tests**

Add tests that assert `remediation_plans`, `remediation_actions`, and `remediation_events` exist after `init_db()`.

Run:

```powershell
rtk python -m pytest tests/test_db.py -q
```

Expected: failure because the remediation tables do not exist yet.

- [x] **Step 2: Add tables**

Add `CREATE TABLE IF NOT EXISTS` statements for:

- `remediation_plans`
- `remediation_actions`
- `remediation_events`

Use text timestamps and JSON text fields, consistent with the existing KB schema.

- [x] **Step 3: Verify schema tests pass**

Run:

```powershell
rtk python -m pytest tests/test_db.py -q
```

Expected: pass.

### Task 2: Core Remediation Tools

**Files:**
- Create: `mcp-server/tools/remediation.py`
- Create: `mcp-server/tests/test_remediation.py`

- [x] **Step 1: Write failing tests for plan and action creation**

Tests cover `remediation_create_plan`, `remediation_add_action`, missing finding rejection, duplicate plan/finding rejection, and activity/event logging.

Run:

```powershell
rtk python -m pytest tests/test_remediation.py -q
```

Expected: import failure because `tools.remediation` does not exist.

- [x] **Step 2: Implement plan/action creation**

Create the module with JSON helpers, validation helpers, `remediation_create_plan`, `remediation_add_action`, and event logging.

- [x] **Step 3: Verify creation tests pass**

Run:

```powershell
rtk python -m pytest tests/test_remediation.py -q
```

Expected: creation tests pass.

### Task 3: Approval, Rejection, Listing, and Export

**Files:**
- Modify: `mcp-server/tools/remediation.py`
- Modify: `mcp-server/tests/test_remediation.py`

- [x] **Step 1: Write failing lifecycle/export tests**

Tests cover pending list filters, approval metadata, rejection metadata, invalid status transitions, and Markdown export content.

- [x] **Step 2: Implement lifecycle/export functions**

Add `remediation_list_actions`, `remediation_approve_action`, `remediation_reject_action`, and `remediation_export_queue`.

- [x] **Step 3: Verify lifecycle/export tests pass**

Run:

```powershell
rtk python -m pytest tests/test_remediation.py -q
```

Expected: pass.

### Task 4: Closure Evidence

**Files:**
- Modify: `mcp-server/tools/remediation.py`
- Modify: `mcp-server/tests/test_remediation.py`

- [x] **Step 1: Write failing closure tests**

Tests cover close rejected before approval, close creates `ssk_evidence(type='finding_closure')`, close resolves the finding, and close stores `closure_evidence_id` on both the action and finding.

- [x] **Step 2: Implement closure**

Add `remediation_close_action`, using existing `ssk_controls`, `ssk_evidence`, and `findings` tables in one DB transaction.

- [x] **Step 3: Verify closure tests pass**

Run:

```powershell
rtk python -m pytest tests/test_remediation.py -q
```

Expected: pass.

### Task 5: Server Registration and Brain Files

**Files:**
- Modify: `mcp-server/server.py`
- Modify: `mcp-server/tests/test_remediation.py`
- Modify: `START_HERE.md`
- Modify: `ROADMAP.md`
- Modify: `activity-log.md`

- [x] **Step 1: Write failing registration test**

Assert `server.remediation_create_plan` and related functions resolve to the imported tool functions.

- [x] **Step 2: Register remediation tools**

Import and register the tools under a `# Remediation tools` block.

- [x] **Step 3: Update operational docs**

Record that Phase 4 approval/closure foundation exists and still performs no tenant writes.

- [x] **Step 4: Full verification**

Run:

```powershell
rtk python -m pytest --tb=short -q
```

Expected: full suite passes.

- [x] **Step 5: Commit**

Commit schema, tools, tests, and docs once the full suite passes.
