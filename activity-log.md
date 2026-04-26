# activity-log.md — MCNA Tenant Intel
Append-only. One line per task run.
Format: YYYY-MM-DD HH:MM — {task name} — {outcome} — {artifact path}

---
2026-04-25 — Brain file sync — MEMORY.md v25, ROADMAP.md v3.6, ARCHITECTURE.md updated (exo+purview built, 202 tests), 02-3/02-4 catalog gap noted — MEMORY.md, ROADMAP.md, ARCHITECTURE.md, activity-log.md
2026-04-25 — exo_scan_mailboxes (first live run) — 187 users, 30 High findings (shared_mailbox_interactive) — mcp-server/kb/mcna_amc.db
2026-04-25 — exo_scan_forwarding (first live run) — 441 rules, 1 High (bstraka external SMS fwd), 1 false positive (wstark X.500 DN) — mcp-server/kb/mcna_amc.db
2026-04-25 — Brain file update (EXO live scan session) — MEMORY.md v23, ROADMAP.md v3.4, activity-log.md updated, docs/governance/scope-additions/2026-04-24-exo-application-scope.md created — multiple
2026-04-23 — Brain file update (post-intune.py) — MEMORY.md v17, ARCHITECTURE.md (169 tests, intune.py built), CLAUDE.md v2.3 — MEMORY.md, ARCHITECTURE.md, CLAUDE.md
2026-04-23 11:03 — intune.py Phase 3 domain 4 — complete. 2 tools (intune_scan_devices, intune_scan_compliance_policies), 5 aliases, 20 tests. 169/169 total. — mcp-server/tools/intune.py, mcp-server/tests/test_intune.py
2026-04-23 — Binder smell-test (ssk_coverage + ssk_export_binder) — PASS. Coverage 7/73. 06-3 and 08-1 binders exported and verified. LIC-DISABLED-01 alias routing confirmed correct (resolves to 08-1 at render time). Pipeline sound. — reports/audit-binders/2026-04-23-142332/, reports/audit-binders/2026-04-23-142541/
2026-04-23 — Brain file update — MEMORY.md v16, activity-log.md updated — MEMORY.md, activity-log.md

2026-04-22 15:45 — entra_scan_app_regs — 40 apps scanned, 49 findings (8 Critical expired creds, 1 expiring, 40 missing owner) — mcp-server/kb/mcna_amc.db
2026-04-22 16:30 — Secure SketCH tracking layer design — Spec approved (Approach A, 7 tables, ~17 tools, audit binder format defined) — docs/superpowers/specs/2026-04-22-securesketch-tracking-design.md
2026-04-22 16:30 — ROADMAP.md v3.0 — Rewritten around Secure SketCH audit evidence as primary product. Phase 2 recast as SSK alignment layer. — ROADMAP.md
2026-04-22 00:00 — Task 4: Graph HTTP Client (TDD) — 7/7 tests passed, committed 9dec58e — mcp-server/graph.py, mcp-server/tests/test_graph.py
2026-04-22 00:00 — Task 2: Database Module (TDD) — 4/4 tests passed, committed 25f4c18 — mcp-server/db.py, mcp-server/tests/test_db.py
2026-04-22 00:00 — Task 8: ssk_list_controls + ssk_get_control (TDD) — 61/61 — mcp-server/tools/ssk.py
2026-04-22 00:00 — Task 1: mcp-server scaffold — DONE — mcp-server/ (tools/, kb/, tests/, requirements.txt)
2026-04-22 00:00 — Phase 2b complete — Secure SketCH evidence, reviews, actions, registries, and audit binder tools built, tested (120/120), and registered — mcp-server/tools/ssk_*.py, mcp-server/server.py
2026-04-22 — Git hygiene — Branch phase2b-task0-control-map deleted, stale worktrees pruned, .mcp.json and .claude/settings.json committed and pushed to main — (repo root)
2026-04-22 — Documentation update — MEMORY.md v13, CLAUDE.md v2.1, ROADMAP.md v3.2, ARCHITECTURE.md structure and KB schema updated to reflect Phase 1+2 complete on main — MEMORY.md, CLAUDE.md, ROADMAP.md, ARCHITECTURE.md

2026-04-16 15:31 — DIS daily summary — FAILED — Graph auth error 403: {"error":{"code":"ErrorAccessDenied","message":"Access is denied. Check credentials and try again."}}
2026-04-16 16:00 — DIS daily summary — FAILED — Graph auth error 403: {"error":{"code":"ErrorAccessDenied","message":"Access is denied. Check credentials and try again."}}
2026-04-16 16:07 — DIS daily summary — 4 threads, 4 messages — dis-log/2026-04-16.md
2026-04-16 16:14 - DIS daily summary - 4 threads, 4 messages - dis-log/2026-04-16.md
2026-04-16 16:32 - DIS daily summary - 6 threads, 6 messages - dis-log/2026-04-16.md
2026-04-17 — MEMORY.md update — CA policy & Entra role audit session captured (v4) — handoff-CA-policy-2026-04-17.md
2026-04-17 11:38 - App reg scan - 40 apps scanned, 25 with findings (Critical: 7, High: 54) - reports/app-reg-governance/2026-04-17.md
2026-04-17 11:41 - App reg scan - 40 apps scanned, 25 with findings (Critical: 7, High: 54) - reports/app-reg-governance/2026-04-17.md
2026-04-17 — Phase 1 Entra role housekeeping — Completed — Removed Authentication Administrator, Power Platform Administrator, AI Administrator from dlafferty@nofmetalcoatings.us; added to nof-dlafferty@nofmetalcoatings.us
2026-04-17 — Entra role remediation — nof-scala@ cleaned — Removed Fabric Administrator, Power Platform Administrator
2026-04-17 — Entra role remediation — MIS@ role reduction complete — Roles reduced per governance review
2026-04-17 — Entra role remediation — nof-dkochever@ — Pending meeting with Diana; Exchange Administrator on hold pending discussion
2026-04-17 — Play 3 build — Orphaned asset scanner created — orphaned_asset_scanner.py + tasks/orphaned-assets.md
2026-04-17 16:25 - Orphaned asset scan - 178 assets flagged (High: 24, Medium: 118, Low: 44) - reports/orphaned-assets/2026-04-17.md
2026-04-17 16:31 - Orphaned asset scan - 166 assets flagged (High: 26, Medium: 105, Low: 44) - reports/orphaned-assets/2026-04-17.md
2026-04-17 — QMS site remediation — luribe@nofmetalcoatings.us added as site collection admin on /sites/qualityna — clears High finding on next scan
2026-04-17 16:55 - Orphaned asset scan - 166 assets flagged (High: 26, Medium: 105, Low: 44) - reports/orphaned-assets/2026-04-17.md
2026-04-17 17:06 - Orphaned asset scan - 166 assets flagged (High: 26, Medium: 105, Low: 44) - reports/orphaned-assets/2026-04-17.md
2026-04-19 — Play 5 build — Power Platform hygiene scanner created — power_platform_hygiene.py + tasks/power-platform-hygiene.md
2026-04-20 12:41 — Power Platform hygiene scan — FAILED — Auth error 401 on https://api.powerapps.com/providers/Microsoft.PowerApps/environments?api-version=2016-11-01&$expand=properties/linkedEnvironmentMetadata: {"error":{"code":"InvalidAuthenticationAudience","message":"The received access token has been obtained from wrong audience or resource 'https://api.powerapps.com'. It should exactly match (including 
2026-04-20 12:47 — Power Platform hygiene scan — 12 environments, 26 findings (High: 17, Medium: 9, Low: 0) — reports/power-platform-hygiene/2026-04-20.md
2026-04-20 12:52 — Power Platform hygiene scan — 12 environments, 5 findings (High: 0, Medium: 5, Low: 0) — reports/power-platform-hygiene/2026-04-20.md
2026-04-20 12:54 — Power Platform hygiene scan — 12 environments, 3 findings (High: 0, Medium: 3, Low: 0) — reports/power-platform-hygiene/2026-04-20.md
2026-04-20 13:22 — Orphaned asset scan — 166 assets flagged (High: 26, Medium: 105, Low: 44) — reports/orphaned-assets/2026-04-20.md
2026-04-20 13:27 — App reg scan — 40 apps scanned, 25 with findings (Critical: 7, High: 55) — reports/app-reg-governance/2026-04-20.md
2026-04-21 08:17 — Microsoft Learn scraper skill — Created and validated — C:\Users\dlafferty.MCNA\.codex\skills\microsoft-learn-scraper
2026-04-22 00:00 — Task 7: CA Tools (TDD) — 5/5 tests passed, 40/40 total, committed 5fc2162 — mcp-server/tools/ca.py, mcp-server/tests/test_ca.py
2026-04-22 00:00 — Task 8: Power Platform Tools (TDD) — 5/5 tests passed, 45/45 total, committed dfd74a8 — mcp-server/tools/pp.py, mcp-server/tests/test_pp.py
2026-04-22 00:00 — Task 10: Claude Code MCP Configuration — DONE, committed 8d07819 — .claude/settings.json
2026-04-22 00:00 — Phase 2a Task 1: Secure SketCH Catalog Import — ssk_* tables + closure_evidence_id added to KB schema, 47/47 tests pass — mcp-server/db.py, mcp-server/requirements.txt, mcp-server/tests/test_db.py
2026-04-22 00:00 — Task 2: ssk_parser boundaries (TDD) — 48/48 passing — mcp-server/tools/ssk_parser.py
2026-04-22 00:00 — Task 3: ssk_parser section extraction (TDD) — 49/49 passing — mcp-server/tools/ssk_parser.py
2026-04-22 00:00 — Task 4: ssk_parser category headings (TDD) — 50/50 passing — mcp-server/tools/ssk_parser.py
2026-04-22 00:00 — Task 5: ssk_parser error handling (TDD) — 52/52 passing — mcp-server/tools/ssk_parser.py
2026-04-22 00:00 — Task 6: ssk_loader (TDD) — 55/55 passing — mcp-server/tools/ssk_loader.py
2026-04-22 00:00 — Task 7: ssk_import_catalog tool (TDD) — 57/57 passing — mcp-server/tools/ssk.py
2026-04-22 00:00 — Task 9: ssk_status + ssk_status_all (TDD) — 65/65 — mcp-server/tools/ssk.py

2026-04-22 18:13 — Task 10: ssk_gaps (TDD) — 66/66 passing — mcp-server/tools/ssk.py
2026-04-22 18:14 — Task 11: register ssk tools in server.py — 66/66 passing — mcp-server/server.py
2026-04-22 18:15 — Task 12: real Secure SketCH import — 73 controls and 704 actions imported from 2026-01-01 catalog; verified with ssk_list_controls, ssk_status_all, and ssk_gaps — mcp-server/kb/mcna_amc.db, mcp-server/kb/catalog-imports/2026-01-01.json
2026-04-22 — Phase 3 Task 1: tools/pim.py — pim_scan_role_assignments + pim_scan_role_definitions built (TDD), CONTRIBUTES_TO wired to 08-3/08-6. 131/131 tests passing. Registered in server.py. — mcp-server/tools/pim.py, mcp-server/tests/test_pim.py, mcp-server/server.py
2026-04-22 — Phase 3 Task 1 live scan + fix — P1-only tenant confirmed via /subscribedSkus (no P2). pim.py patched with 400 fallback to /roleAssignments. 133/133 tests. Live findings: 1 pim_not_licensed, 22 permanent_privileged_assignment, 9 privileged_role_on_non_admin_account. blynn@ open item resolved (built-in Modern Commerce User role). — mcp-server/tools/pim.py, mcp-server/kb/mcna_amc.db
2026-04-22 — Phase 3 Task 2: tools/license.py — license_scan_skus + license_scan_users built (TDD), CONTRIBUTES_TO wired to 06-3/08-1. 143/143 tests. Live findings: 1 unused SKU (ATA), 6 productivity_sku_stacking, 3 licensed_disabled_account. — mcp-server/tools/license.py, mcp-server/tests/test_license.py, mcp-server/server.py
2026-04-22 — Phase 3 Task 3: tools/sharing.py — sharing_scan_sites built (TDD), CONTRIBUTES_TO wired to 15-4. 149/149 tests. Live: 29 sites, 17 very_stale, 5 stale. Permission-based checks deferred (Sites.FullControl.All not consented). EXO pivot noted — needs MailboxSettings.Read or EXO PowerShell. — mcp-server/tools/sharing.py, mcp-server/tests/test_sharing.py, mcp-server/server.py
2026-04-23 — End-of-day handoff — MEMORY.md v15 with startup prompt at top, ARCHITECTURE/ROADMAP refreshed for Phase 3 progress (3 domains, 149 tests). Pushing to origin/main. — MEMORY.md, ARCHITECTURE.md, ROADMAP.md
2026-04-23 — Brain file review + housekeeping — MEMORY.md bumped to v16, activity-log gap patched, CLAUDE.md v2.2, scope-additions governance records created — MEMORY.md, activity-log.md, CLAUDE.md, docs/governance/scope-additions/
2026-04-23 — Intune live scan + scope fix — Consented DeviceManagementManagedDevices.Read.All + DeviceManagementConfiguration.Read.All. Fixed intune.py scope bug. 1 device scanned: JWEDGE-2018 not encrypted (High). 1 compliance policy found. Added incomplete_enrollment finding (High, 07-2). Stale scope-gap finding dismissed. — mcp-server/tools/intune.py, docs/auth/app-registrations.md, mcp-server/kb/mcna_amc.db
2026-04-23 — Phase 3 domain 5 (EXO) — exo_scan_mailboxes + exo_scan_forwarding built. MailboxSettings.Read consented. 19 tests, 201/201. MEMORY.md v19. — mcp-server/tools/exo.py, mcp-server/tests/test_exo.py
2026-04-23 17:47 — SSK evidence backfill — 15 `scan_snapshot` evidence rows linked and verified for controls 06-3, 08-1, 08-2, 08-6, 15-3, 15-4 — mcp-server/kb/mcna_amc.db
2026-04-23 17:47 — Audit binder refresh — Multi-control binder set regenerated with populated evidence sections for 06-3, 08-1, 08-2, 08-6, 15-3, 15-4 — reports/audit-binders/2026-04-23-204903/
2026-04-23 17:47 — Report usage guide — Added operator instructions for scan reports, CSVs, and audit binders — docs/how-to-use-reports.md
2026-04-23 17:47 — Binder export merge fix — `ssk_export_binder` now merges `index.md` and `manifest.json` when reusing an output directory; verified with `mcp-server/tests/test_ssk_binder.py` (15 passed using `--basetemp`) — mcp-server/tools/ssk_binder.py, mcp-server/tests/test_ssk_binder.py
2026-04-23 17:47 — Brain file update — MEMORY.md v21, activity-log.md, CLAUDE.md, CONTEXT.md, ROADMAP.md refreshed for evidence/binder state — MEMORY.md, activity-log.md, CLAUDE.md, CONTEXT.md, ROADMAP.md
2026-04-25 — EXO false-positive fix — `_is_external()` patched to skip addresses without `@`; X.500 legacy Exchange DNs now classified non-external. 19/19 tests pass. Walt Stark finding (ce25ed77) and stale exo_scope_gap finding (d4038cd6) dismissed from KB — mcp-server/tools/exo.py, mcp-server/kb/mcna_amc.db

2026-04-25 — Copilot domain agent — copilot_scan_licenses + copilot_scan_settings built (TDD), 12 tests + kb.py dismissed-finding fix (211/214 passing); live: 25 Copilot users across 187 scanned, 0 license findings; settings scope gap recorded (Microsoft365CopilotSettings.Read.All not yet consented); HTTPError fix applied for beta endpoint 400 — mcp-server/tools/copilot.py, mcp-server/tests/test_copilot.py, mcp-server/tools/kb.py
2026-04-25 16:16 — project cleanup and catalog repair — stale auth/SSK alias tests fixed; Secure SketCH catalog re-imported at 75 controls/728 actions with 02-3 and 02-4 present; 98-1/98-2 test controls removed; unpacked_sketch scratch directory removed; pytest temp paths ignored; 214/214 tests passing — mcp-server/tests/test_auth.py, mcp-server/tests/test_ssk_control_map.py, mcp-server/kb/catalog-imports/2026-01-01.json, mcp-server/kb/mcna_amc.db, .gitignore
2026-04-25 16:20 — fresh-session handoff prompt — MEMORY.md v27 updated with Phase 3 mail.py handoff, current verification facts, catalog state, and narrow v1 mail agent scope — MEMORY.md
2026-04-25 19:35 — low-token startup handoff — START_HERE.md added; AGENTS.md, CLAUDE.md, and MEMORY.md v28 updated to make full brain reads conditional — START_HERE.md, AGENTS.md, CLAUDE.md, MEMORY.md, activity-log.md
2026-04-25 19:42 — Brain Update Check guidance — Added end-of-task brain file update rules and final-answer receipt pattern — START_HERE.md, activity-log.md
2026-04-25 19:42 — startup handoff cleanup — Clarified Phase 3 work-item accounting and updated README to point at START_HERE.md — START_HERE.md, MEMORY.md, ROADMAP.md, README.md, activity-log.md
2026-04-25 19:50 — cross-document alignment audit — Reconciled startup docs, roadmap, architecture, auth scope records, pending scope gaps, KB counts, EXO cleanup status, and archived stale MEMORY.original.md — START_HERE.md, AGENTS.md, CLAUDE.md, MEMORY.md, CONTEXT.md, ARCHITECTURE.md, ROADMAP.md, archive/MEMORY.v16-original.md, docs/governance/scope-additions/
2026-04-25 20:06 — Phase 3 mail domain — mail_send_summary built and registered; dry-run default, Graph send, validation, and activity_log outcomes covered; 219/219 tests passing — mcp-server/tools/mail.py, mcp-server/tests/test_mail.py, mcp-server/server.py, START_HERE.md
2026-04-25 20:11 — EXO shared mailbox remediation worksheet — 30 open shared_mailbox_interactive findings triaged into disable, validate-then-disable, and validate-first queues — reports/exo-shared-mailbox-remediation/2026-04-25.md
2026-04-25 20:18 — Phase 4 planning transition — Documented no-action EXO remediation plan and marked Phase 3 complete / Phase 4 planning started — docs/operations/exo-shared-mailbox-remediation-plan.md, START_HERE.md, ROADMAP.md
2026-04-25 20:28 — Phase 4 approval layer design — Defined KB-native remediation plans/actions with exported approval queue and closure evidence linkage; no tenant writes — docs/superpowers/specs/2026-04-25-phase-4-approval-closure-design.md
2026-04-25 20:31 — Phase 4 approval layer implementation plan — Planned TDD build for remediation plans, actions, events, exports, and closure evidence — docs/superpowers/plans/2026-04-25-phase-4-approval-closure-implementation.md
2026-04-25 20:34 — Phase 4 approval/closure foundation — Built remediation plans/actions/events, approval/rejection, Markdown queue export, and finding closure evidence linkage; no tenant writes — mcp-server/tools/remediation.py, mcp-server/tests/test_remediation.py, mcp-server/db.py, mcp-server/server.py
2026-04-25 20:42 — EXO approval queue seed — Created KB remediation plan d5d91bf4-9ca7-49cd-98b7-d2ea0e11e8d9 with 30 pending actions split into 4 batches; exported approval queue; no tenant writes — reports/remediation-queues/exo-shared-mailbox-interactive-sign-in-2026-04-25.md
2026-04-25 23:09 — Phase 4A-4B coverage/evidence foundation — Built Secure SketCH control matrix, evidence gap reports, scan-evidence backfill, and durable coverage snapshots; 75 controls classified, 6 evidenced, 69 gaps; 247/247 tests passing — mcp-server/tools/ssk_matrix.py, mcp-server/tests/test_ssk_matrix.py, reports/ssk-control-coverage/coverage-2026-04-26.md, reports/ssk-evidence-gaps/gaps-2026-04-26.md
2026-04-25 23:16 — Secure SketCH manual evidence links — Linked and verified 6 existing local evidence pointers; coverage now 12 evidenced / 63 gaps; regenerated matrix, gap report, and full binder — mcp-server/kb/mcna_amc.db, reports/ssk-control-coverage/coverage-2026-04-26.md, reports/ssk-evidence-gaps/gaps-2026-04-26.md, reports/audit-binders/2026-04-26/
