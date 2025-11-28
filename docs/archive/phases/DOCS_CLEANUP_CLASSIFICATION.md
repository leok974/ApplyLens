# Markdown Documentation Cleanup Classification

**Total markdown files (excluding node_modules):** ~400 files
**Recommendation:** KEEP 89 core docs | DELETE 311+ transient/narrative docs

---

## ✅ KEEP (Core Documentation - 89 files)

### Repository Root
- `README.md`

### Security & Auth
- `docs/SECURITY.md`
- `docs/SECRETS_POLICY.md`
- `docs/SECURITY_KEYS_AND_CSRF.md`
- `docs/TOKEN_ENCRYPTION_CSRF_2025-10-20.md`

### Production Operations
- `DEPLOYMENT_STATUS.md`
- `docs/DEPLOYMENT.md`
- `docs/PRODUCTION_HANDBOOK.md`
- `docs/PRODUCTION_SETUP.md`
- `docs/PRODUCTION_QUICKREF.md`
- `docs/ONCALL_HANDBOOK.md`
- `docs/OPS.md`
- `docs/OPERATIONAL_STATUS.md`

### Runbooks
- `docs/RUNBOOK_ACTIVE.md`
- `docs/RUNBOOK_POLICY.md`
- `docs/RUNBOOK_WAREHOUSE_HEALTH.md`
- `docs/runbooks/APPROVAL_WORKFLOWS.md`
- `docs/runbooks/GUARDRAILS_CONFIG.md`
- `docs/runbooks/PHASE4_TROUBLESHOOTING.md`
- `docs/runbooks/POLICY_MANAGEMENT.md`
- `docs/runbooks/RUNBOOK_ROLLBACK.md`
- `runbooks/503_upstream_stale.md`
- `runbooks/profile-warehouse.md`

### Architecture & System Design
- `analytics/ARCHITECTURE.md`
- `docs/ARCHITECTURE.md`
- `docs/OVERVIEW.md`
- `docs/GETTING_STARTED.md`
- `docs/DEVELOPMENT.md`
- `docs/BACKEND.md`
- `docs/FRONTEND.md`

### API Documentation
- `services/api/docs/API_REFERENCE.md`
- `docs/API_ROUTE_POLICY.md`

### Infrastructure
- `infra/cloudflared/README.md`
- `infra/nginx/README.md`
- `infra/secrets/README.md`
- `infra/docs/CLOUDFLARE_TUNNEL_RUNBOOK.md`
- `infra/docs/CLOUDFLARE_HARDENING_CHECKLIST.md`
- `infra/docs/OAUTH_SETUP.md`
- `infra/CLOUDFLARE_TUNNEL_QUICKSTART.md`
- `infra/kibana/saved-queries.md`

### Testing
- `apps/web/tests/README.md`
- `apps/web/tests/e2e/README.md`
- `tests/e2e/README.md`
- `services/api/tests/README_TEST_INFRASTRUCTURE.md`
- `docs/TESTING.md`
- `docs/RUNNING_TESTS.md`
- `docs/PLAYWRIGHT_E2E_SETUP.md`

### Data Pipeline & Analytics
- `analytics/README.md`
- `analytics/RUNBOOK.md`
- `analytics/dbt/README.md`
- `analytics/fivetran/README.md`
- `analytics/ingest/README.md`
- `analytics/ops/README.md`
- `analytics/ops/COST-MONITORING.md`
- `analytics/ops/UPTIME-MONITORING.md`
- `analytics/ops/VERIFICATION-QUERIES.md`

### Features & Capabilities
- `services/api/docs/BUDGETS_AND_GATES.md`
- `services/api/docs/GATE_BRIDGES.md`
- `services/api/docs/INTERVENTIONS_GUIDE.md`
- `services/api/docs/PLAYBOOKS.md`
- `services/api/docs/EVAL_GUIDE.md`
- `services/api/docs/INTELLIGENCE_REPORT.md`
- `services/api/docs/REDTEAM.md`
- `docs/AGENTS_QUICKSTART.md`
- `docs/AGENTS_OBSERVABILITY.md`
- `services/api/docs/APPROVALS_GROUPING_UI.md`

### Search & Elasticsearch
- `docs/SEARCH_ES.md`
- `services/api/docs/ES_ILM_RETENTION.md`
- `services/api/docs/ES_RBAC_API_KEYS.md`

### Monitoring & Observability
- `docs/PROMETHEUS_METRICS.md`
- `docs/PROMETHEUS_QUICKSTART.md`
- `docs/PROMQL_QUICKREF.md`
- `docs/PROMQL_RECIPES.md`
- `docs/GRAFANA_SETUP.md`
- `docs/GRAFANA_QUICKSTART.md`
- `services/api/grafana/README.md`
- `grafana/README.md`
- `kibana/README_monitoring.md`

### Quick References & Setup Guides
- `services/api/README.md`
- `services/api/QUICK_START.md`
- `scripts/README.md`
- `scripts/fivetran/README.md`
- `scripts/README-ES-API-KEY.md`
- `deploy/README.md`
- `secrets/README.md`
- `docs/README.md`
- `docs/QUICK_REFERENCE.md`
- `docs/SETUP_GUIDE.md`

### Policy & Compliance
- `docs/POLICY_STUDIO.md`
- `docs/POLICY_RECIPES.md`

### Service-Specific
- `services/api/app/ingest/README_due_dates.md`
- `services/api/scripts/README_backfill.md`

---

## ❌ DELETE (Transient/Narrative/Snapshot Notes - 311+ files)

### Version-Specific Deployment Snapshots (DELETE ALL)
All files matching patterns like `v0.4.XX`, `PHASE_XX`, etc.:

**Root Level:**
- `ACTIONS_IMPLEMENTATION.md` - Implementation narrative
- `API_RESTART_SUMMARY.md` - One-off troubleshooting note
- `AUTH_CHECK_LOOP_FIX.md` - Bugfix narrative
- `AUTO_DRAFT_DEPLOYMENT_SUMMARY.md` - Deployment snapshot
- `BROWSER_CACHE_FIX.md` - Bugfix narrative
- `BUGFIX_HEALTHBADGE_2025_10_22.md` - Daily bugfix note
- `CHANGELOG_v0.4.44.md` - Version-specific changelog
- `CHANGELOG_v0.4.45.md`
- `CHANGELOG_v0.4.46.md`
- `CHANGELOG_v0.4.47e.md`
- `CHANGELOG_v0.4.48.md`
- `CI_INTEGRATION_mailboxAssistant.md` - Phase implementation note
- `CLOUDFLARE_TUNNEL_530_FIX.md` - Incident narrative
- `CLOUDFLARE_TUNNEL_ACTIVE.md` - Snapshot
- `CSRF_403_FIX.md` - Bugfix narrative
- `CSRF_FIX_SUMMARY.md`
- `CSRF_FIX_v0.4.27.md`
- `CUTOVER_RUNBOOK_V31.md` - Phase-specific runbook (outdated)
- `CUTOVER_SUMMARY_V31.md`
- `DATABASE_PASSWORD_FIX.md` - Bugfix narrative
- `DEMO_TRANSCRIPT_v0.4.47e.md` - Demo script
- `DEPENDENCIES_DOWN_ALERT_FIX.md` - Alert fix narrative
- `DEPLOY_SUCCESS.md` - Deployment celebration note
- `DEPLOY_TO_PRODUCTION.md` - Redundant with docs/DEPLOYMENT.md
- `DEPLOY-QUICK-REF.md` - Redundant with docs/PRODUCTION_QUICKREF.md
- `DEPLOYMENT_2025_10_22.md` - Daily deployment note
- `DEPLOYMENT_CHECKLIST_v0.4.26.md` - Version-specific checklist
- `DEPLOYMENT_COMPLETE_v0.4.3.md` - Version snapshot
- `DEPLOYMENT_COMPLETE_v0.4.49.md`
- `DEPLOYMENT_COMPLETE_V31_FINAL.md`
- `DEPLOYMENT_GUIDE_RELOAD_FIX.md` - One-off fix guide
- `DEPLOYMENT_SUCCESS_v0.4.27.md` - Deployment celebration
- `DEPLOYMENT_SUCCESS.md`
- `DEPLOYMENT_V1.0.0.md`
- `DEPLOYMENT_v0.4.27.md`
- `DEPLOYMENT_v0.4.47e.md`
- `DEPLOYMENT_v0.4.48.md`
- `DEPLOYMENT_v0.4.49.md`
- `DIAGNOSTIC_RESULTS_OAUTH_403_400.md` - Debugging session notes
- `DOCUMENTATION_INDEX_V31.md` - Phase-specific index
- `ELASTICSEARCH_DIAGNOSTICS.md` - Debugging session
- `EMAIL_RISK_V31_COMPLETE.md` - Phase completion note
- `ES_API_KEY_LEAST_PRIVILEGE.md` - One-off security note (covered in docs/ES_RBAC)
- `ES_API_KEY_PERMISSIONS_COMPARISON.md`
- `FAIL_SOFT_SUGGESTIONS_V0.4.19-hotfix3.md` - Hotfix narrative
- `FINAL_DIAGNOSIS_AND_FIX.md` - Debugging narrative
- `FIVETRAN_OAUTH_FINAL_STATUS.md` - Status snapshot
- `FIVETRAN_OAUTH_QUICK_CHECK.md` - Troubleshooting checklist
- `FIVETRAN_OAUTH_VERIFICATION_COMPLETE.md` - Verification snapshot
- `FIVETRAN_RATE_LIMIT_ANALYSIS.md` - Analysis narrative
- `FRONTEND_DRAFT_REPLY_COMPLETE.md` - Feature completion note
- `GOOGLE_OAUTH_CONFIG_FIX.md` - One-off fix
- `GRAFANA_DASHBOARDS_COMPLETE.md` - Completion snapshot
- `GRAFANA_PROMETHEUS_SETUP.md` - Redundant with docs/GRAFANA_SETUP.md
- `GRAFANA_QUERIES.md` - Covered in PROMQL docs
- `HACKATHON_REPORT_PART1.md` - **DELETE** Hackathon narrative
- `HACKATHON_REPORT_PART2A.md`
- `HACKATHON_REPORT_PART2B.md`
- `HACKATHON_REPORT_PART2C.md`
- `HACKATHON_REPORT_PART2D.md`
- `HEADER_INBOX_HERO_2025_10_22.md` - Daily UI polish note
- `HEADER_LAYOUT_FIX_2025_10_22.md`
- `HEADER_LOGO_ENLARGEMENT.md`
- `IMPLEMENTATION_SUMMARY.md` - Generic summary (non-specific)
- `INCIDENT_2025_10_26_503_RESOLUTION.md` - Incident (consider keeping recent incidents)
- `INFRASTRUCTURE_STATUS.md` - Snapshot
- `JS_READONLY_PROPERTY_FIX.md` - Bugfix narrative
- `LOGIN_BUTTON_FIX.md`
- `LOGO_UPDATE_2025_10_22.md` - UI polish note
- `MAILCHAT_UI_CLEANUP.md` - UI cleanup narrative
- `MANUAL_TEST_PROCEDURE.md` - Redundant with docs/TESTING.md
- `MANUAL_TEST_RESULTS_v0.4.47e.md` - Version-specific test results
- `MANUAL_TESTING_GUIDE_v0.4.4.md`
- `METRICS_ENDPOINT_ADDED.md` - Feature addition note (covered in API docs)
- `MIXED_CONTENT_FIX.md` - Bugfix narrative
- `MONITORING_STATUS.md` - Status snapshot (covered in docs/OPS.md)
- `OAUTH_DB_PASSWORD_FIX_SUMMARY.md` - Bugfix summary
- `OAUTH_QUICK_START.md` - Redundant with infra/docs/OAUTH_SETUP.md
- `OAUTH_REAUTH_GUIDE.md` - Specific procedure (covered in main docs)
- `OAUTH_SETUP_INSTRUCTIONS.md` - Redundant
- `OAUTH_TROUBLESHOOTING_SUMMARY.md` - Troubleshooting snapshot
- `OLLAMA_INTEGRATION_TEST_RESULTS.md` - Test results snapshot
- `PERFORMANCE_OPTIMIZATIONS.md` - Generic optimization notes
- `PHASE_1.4_LLM_INTEGRATION.md` - **DELETE** Phase narrative
- `PHASE_1.5_AUTO_DRAFT_REPLIES.md`
- `PHASE_3_ALIGNMENT_COMPLETE.md`
- `PHASE_3_COMPLETE.md`
- `PHASE_3_IMPLEMENTATION_SUMMARY.md`
- `PHASE_3_QUICK_START.md`
- `PHASE_3_VERIFICATION_RUNBOOK.md`
- `PHASE_4_CHECKLIST.md`
- `PHASE_4_DEMO_SCRIPTS.md` - **DELETE** Demo script
- `PHASE_4_E2E_TEST_RESULTS.md`
- `PHASE_4_FEATURE_FLAGS_SUMMARY.md`
- `PHASE_4_FEATURE_FLAGS.md`
- `PHASE_4_FRONTEND_INTEGRATION.md`
- `PHASE_4_IMPLEMENTATION_SUMMARY.md`
- `PHASE_4_INTEGRATION_SUCCESS.md`
- `PHASE_4_TEST_RESULTS.md`
- `PHASE_5_3_COMPLETION.md`
- `PHASE_5_5_COMPLETE.md`
- `PHASE8_COMPLETION_SUMMARY.md`
- `POST_DEPLOYMENT_ENHANCEMENTS.md`
- `POST_DEPLOYMENT_NEXT_STEPS_COMPLETE.md`
- `PRE_FLIGHT_CHECKLIST_V31.md` - Phase-specific checklist
- `PROD_DOMAIN_QUICK_REF.md` - Redundant
- `PROD_QUICK_REF.md` - Redundant with docs/PRODUCTION_QUICKREF.md
- `PRODUCTION_DEPLOYMENT_CHECKLIST.md` - Redundant
- `PRODUCTION_DEPLOYMENT_COMPLETE.md` - Completion snapshot
- `PRODUCTION_DEPLOYMENT_FINAL.md`
- `PRODUCTION_DEPLOYMENT.md` - Redundant with docs/DEPLOYMENT.md
- `PRODUCTION_DOMAIN_SETUP.md` - Covered in infra docs
- `PRODUCTION_QUICK_START.md` - Redundant
- `PRODUCTION_README.md` - Redundant
- `PRODUCTION_REBUILD_SUMMARY.md` - Build narrative
- `PRODUCTION_STATUS.md` - Status snapshot
- `PROFILE_TESTS_COMPLETE.md` - Test completion note
- `PROFILE_WAREHOUSE_DEBUG_v0.4.51.md` - Version-specific debugging
- `QUICK_REFERENCE_V31.md` - Phase-specific reference
- `QUICK_START.md` - Redundant with docs/GETTING_STARTED.md
- `QUICK_TEST_GUIDE.md` - Redundant with docs/TESTING.md
- `QUICKSTART-ES-API-KEY.md` - Covered in docs
- `RATE_LIMIT_429.md` - Incident narrative
- `READY_TO_DEPLOY_v0.4.26.md` - Deployment readiness snapshot
- `RELEASE_CHECKLIST.md` - Generic checklist (non-specific)
- `RELOAD_FIX_VERIFICATION_REPORT.md` - Verification snapshot
- `RELOAD_LOOP_FIX_SUMMARY.md`
- `RELOAD_LOOP_FIX_VALIDATION.md`
- `RELOAD_PREVENTION_SUMMARY.md`
- `SEARCH_COMPLETE_SUMMARY.md` - Completion snapshot
- `SEARCH_FILTER_FIX_V0.4.19-hotfix2.md` - Hotfix narrative
- `SEARCH_FILTER_FIXES.md`
- `SEARCH_IMPROVEMENTS_V0.4.19.md`
- `SERVICES_STARTED.md` - Startup note
- `SERVICES.md` - Service list (covered in ARCHITECTURE.md)
- `SETTINGS_ACCOUNT_ICON_v0.4.54.md` - **DELETE** UI polish note
- `SETTINGS_LOGOUT_v0.4.52.md`
- `SETTINGS_POLISH_v0.4.55.md`
- `SMOKE_TEST_REPORT.md` - Test report snapshot
- `SMOKE_TEST.md`
- `STAGING_DEPLOYMENT_POST_CHECKLIST.md` - Staging-specific (phase)
- `STAGING_DEPLOYMENT_QUICK_REF.md`
- `STAGING_DEPLOYMENT_V31_SUMMARY.md`
- `STAGING_ENHANCEMENTS_COMPLETE.md`
- `STAGING_POST_CHECKLIST_V31.md`
- `TOKEN_ENCRYPTION_BUG_FIXED.md` - Bugfix narrative
- `UX_HEARTBEAT_CSRF_EXEMPTION.md` - Implementation note
- `v0.4.27_REBUILD_COMPLETE.md` - **DELETE** Version snapshot
- `VERIFICATION_GUIDE.md` - Generic verification (covered in runbooks)
- `WAREHOUSE-QUICK-REF.md` - Redundant with analytics docs

**docs/ folder (200+ files to DELETE):**
- All `docs/PHASE_X_*.md` files (50+ phase narratives)
- All `docs/v0.4.XX-*.md` files (version snapshots)
- All `docs/*_COMPLETE.md` files (completion snapshots)
- All `docs/*_SUMMARY.md` files (phase summaries)
- All `docs/*_STATUS.md` files (status snapshots)
- All `docs/*_IMPLEMENTATION.md` files (implementation narratives)
- All `docs/*_DEPLOYMENT*.md` version-specific files
- All `docs/*_QUICKREF.md` redundant quickrefs (keep main ones)
- All `docs/*_FIX.md` bugfix narratives
- All `docs/*_VERIFICATION*.md` verification snapshots
- All `docs/*_POLISH*.md` UI polish notes
- `docs/hackathon/*.md` - **ALL hackathon narratives (DELETE)**
- `docs/SOFTER_DESIGN_TOKENS.md` - Design discussion note
- `docs/SHADCN_UI_SETUP.md` - Setup note (one-time)
- `docs/SHADCN_LAYOUT_COMPONENTS.md`
- `docs/THEME_TOGGLE_COMPLETE.md` - Feature completion note
- `docs/THEME_TOGGLE_V2.md`
- `docs/TOAST_NOTIFICATIONS_ENHANCED.md` - Enhancement note
- `docs/TOAST_VARIANTS_REFERENCE.md` - Component reference (keep or move to code docs)
- `docs/TRACKER_UI_POLISH_*.md` - UI polish narratives
- `docs/UI_POLISH_*.md`
- `docs/VIEWPORT_AWARE_PANEL_MODE_*.md` - Feature implementation narrative
- `docs/RESIZABLE_THREAD_PANEL.md`
- `docs/SPLIT_PANEL_MODE.md`
- `docs/STICKY_SEARCH_FILTERS_*.md`
- `docs/SORTABLE_TTR_*.md`
- `docs/REPLY_FILTER_*.md` - Feature snapshots
- `docs/REPLY_METRICS_*.md`
- `docs/WEIGHT_TUNING_ANALYSIS.md` - Analysis narrative
- `docs/WEBSITE_FIX.md` - Bugfix narrative
- `docs/SYNC_BUTTON_FIX.md`
- `docs/ROOT_CAUSE_HTML_RESPONSE.md` - Debugging narrative
- `docs/ROTATE_TOKENS.md` - One-off procedure
- `docs/CONNECTION-STATUS-FEATURE.md` - Feature note
- `docs/DARK_HOTFIX_COMPLETE.md` - Hotfix note
- `docs/dark-theme-enhancement.md`
- `docs/DEBUG-SCORE-*.md` - Feature notes
- `docs/EMAIL_DETAILS_PANEL.md` - Feature note
- `docs/EMAIL_EXTRACTION_*.md` - Feature completion notes
- `docs/EMAIL_PARSING_*.md` - Implementation notes
- `docs/EMAIL_RISK_V3*.md` - Version-specific feature notes
- `docs/ADVANCED_INBOX_FEATURES.md` - Feature narrative
- `docs/ADVANCED_EMAIL_AUTOMATION*.md` - Feature completion notes
- `docs/ADVANCED_FILTERING_SUMMARY.md`
- `docs/ACTIONS_BADGE_SYSTEM.md` - Feature note
- `docs/ACTIVE_LEARNING.md` - Feature note (possibly keep if active)
- `docs/ALERT_RESOLUTION_*.md` - Alert resolution snapshots
- `docs/ALERT_STATUS_*.md`
- `docs/ALERT_TESTING_*.md` - Testing snapshots
- `docs/ANALYTICS_PHASE_51_*.md` - Phase narratives
- `docs/APPLICATION_TRACKER_*.md` - Feature snapshots
- `docs/APPLICATIONS_*.md` - Feature notes
- `docs/ARCHIVE_*.md` - Feature notes
- `docs/ARTIFACTS_APPLIED_*.md` - Deployment notes
- `docs/AUTH_IMPLEMENTATION_*.md` - Implementation snapshot
- `docs/AUTO_PROVISIONED_MONITORING.md` - Setup snapshot
- `docs/BACKEND_THREAD_ENDPOINT.md` - Endpoint documentation (possibly move to API_REFERENCE)
- `docs/BROWSER_CACHE_FIX.md` - Bugfix
- `docs/BUGFIXES_*.md` - Bugfix narratives
- `docs/BULLETPROOFING-*.md` - Implementation phase notes
- `docs/CHANGELOG.md` - Redundant (should be at root if needed)
- `docs/CHAOS_TESTING.md` - Testing methodology (possibly keep)
- `docs/CI_STATUS_*.md` - CI snapshots
- `docs/CLEANUP-COMPLETE.md` - Completion note
- `docs/CLI-TOOLS-GUIDE.md` - Tool guide (possibly keep if current)
- `docs/COMMIT_*.md` - Commit narratives
- `docs/COMPLETE_INFRASTRUCTURE_SUMMARY_*.md` - Summaries
- `docs/CONTRIBUTING.md` - **KEEP** if exists (contributor guidelines)
- `docs/DASHBOARD_*.md` - Dashboard setup snapshots
- `docs/DESIGN_TOKEN_MIGRATION_GUIDE.md` - Migration guide (one-time)
- `docs/DOC_INDEX.md` - Index (possibly keep if maintained)
- `docs/DOCKER_NETWORK_FIX.md` - Bugfix
- `docs/DOMAIN_ENRICHMENT_*.md` - Feature notes
- `docs/E2E_AUTH_TESTS_*.md` - Test snapshots
- `docs/e2e-test-improvements.md` - Improvement narrative
- `docs/ERROR_FIXES_SUMMARY.md` - Bugfix summary
- `docs/ERRORS_FIXED_DOCS_ORGANIZED.md`
- `docs/FILTERING_QUICK_START.md` - Possibly redundant
- `docs/final-polish-*.md` - Polish narratives
- `docs/FINALIZATION_*.md` - Phase completion notes
- `docs/FIVETRAN-*.md` - Setup snapshots (covered in analytics/)
- `docs/GCP-*.md` - GCP setup snapshots
- `docs/GITHUB_*.md` - GitHub setup snapshots
- `docs/GMAIL_*.md` - Gmail setup/implementation snapshots
- `docs/GRAFANA_*.md` - Setup snapshots (keep main GRAFANA_SETUP.md)
- `docs/HARDENING_COMPLETE.md` - Completion note
- `docs/HISTORY-CLEANUP.md` - Cleanup note
- `docs/HOTFIX_*.md` - Hotfix narratives
- `docs/HOUSEKEEPING-*.md` - Housekeeping notes
- `docs/ILM-*.md` - ILM implementation notes
- `docs/IMPLEMENTATION_*.md` - Implementation snapshots
- `docs/INLINE_NOTE_*.md` - Feature notes
- `docs/INSTALL_GRAFANA*.md` - Installation snapshots
- `docs/ISSUE_7_*.md` - Issue-specific notes
- `docs/KIBANA_*.md` - Kibana setup snapshots (keep core)
- `docs/looker/*.md` - Looker setup (if unused)
- `docs/manual-testing-guide.md` - Redundant with TESTING.md
- `docs/MIXED_CONTENT_FIX.md` - Bugfix
- `docs/MONITORING_*.md` redundant files (keep main MONITORING_SETUP.md)
- `docs/MULTI_USER_GMAIL*.md` - Feature implementation notes
- `docs/NEXT_STEPS_*.md` - Planning snapshots
- `docs/OAUTH_FIX_*.md` - Bugfix narratives
- `docs/OAUTH_QUICK_REF.md` - Redundant
- `docs/OAUTH_SETUP_COMPLETE.md` - Completion snapshot
- `docs/OLLAMA_*.md` - Integration snapshots (keep main if current)
- `docs/PIPELINE_V2_*.md` - Pipeline implementation snapshots
- `docs/PR_DESCRIPTION.md` - PR narrative
- `docs/PROD_TESTING_SUMMARY.md` - Testing snapshot
- `docs/PRODUCTION_*.md` redundant files (keep main handbook/setup)
- `docs/production-ops-advanced.md` - Possibly keep if unique
- `docs/production-safe-testing.md` - Possibly keep
- `docs/RELEASE.md` - Release process (possibly keep if current)
- `docs/RUN_FULL_STACK.md` - Redundant with QUICK_START
- `docs/SCHEMA_MIGRATION_*.md` - Migration snapshots
- `docs/SEARCH_IMPLEMENTATION_COMPLETE.md` - Completion snapshot
- `docs/SEC_CI_FINALIZATION.md` - Finalization snapshot
- `docs/SECURITY_AUDIT.md` - Audit snapshot (keep recent if useful)
- `docs/SECURITY_DEPLOYMENT_SUMMARY.md` - Deployment snapshot
- `docs/SECURITY_SEARCH_FILTERS*.md` - Feature snapshots
- `docs/SECURITY_SETUP_COMPLETE.md` - Completion snapshot
- `docs/SECURITY_UI_*.md` - UI implementation snapshots
- `docs/SESSION_SUMMARY_*.md` - Session notes
- `docs/SETUP_COMPLETE_SUMMARY.md` - Completion snapshot
- `docs/SETUP_ES_PIPELINE_GRAFANA_DASHBOARD.md` - Setup snapshot
- `docs/SETUP-GUIDE-ADVANCED.md` - Redundant
- `docs/SLA_OVERVIEW.md` - SLA documentation (possibly keep)
- `docs/SLO_BURN_RATE_*.md` - Implementation snapshots
- `docs/SMALL-IMPROVEMENTS.md` - Improvement list
- `docs/SMART_SEARCH_*.md` - Feature snapshots
- `docs/SMOKE_TEST_RESULTS.md` - Test results
- `docs/TEST_*.md` - Test snapshots/results
- `docs/test-auth-fix-summary.md` - Bugfix
- `docs/testing-improvements.md` - Improvement narrative
- `docs/USER_BACKFILL_*.md` - Backfill operation notes

**apps/web/ specific:**
- `apps/web/RELOAD_PREVENTION.md` - Feature note (covered in main docs)
- `apps/web/tests/.auth/README.md` - **KEEP** (test auth setup)
- `apps/web/tests/e2e/README-email-risk.md` - Specific test docs (possibly keep)
- `apps/web/tests/PLAYWRIGHT_AUTH_SETUP.md` - **KEEP** (test setup)
- `apps/web/tests/README.test.md` - **KEEP** (test docs)

**services/api/ specific:**
- `services/api/docs/*_COMPLETE.md` - Completion snapshots
- `services/api/docs/ADVANCED_FEATURES_SUMMARY.md` - Summary (possibly merge into API_REFERENCE)
- `services/api/docs/DASHBOARD_ALERTS.md` - Covered in monitoring docs
- `services/api/docs/ES_INTEGRATION_*.md` - Integration snapshots
- `services/api/docs/MIGRATION_*.md` - Migration notes (one-time)
- `services/api/docs/NEXT_STEPS_COMPLETE.md` - Planning snapshot
- `services/api/docs/PHASE_*.md` - Phase narratives
- `services/api/docs/phase_5_4_progress.md` - Progress snapshot
- `services/api/docs/PHASE4_IMPLEMENTATION_SUMMARY.md` - Phase summary
- `services/api/docs/RUNBOOK_SEVERITY.md` - Possibly keep (operational)
- `services/api/docs/runbooks/*.md` - **KEEP ALL** (operational runbooks)
- `services/api/tests/MIGRATION_ASYNCCLIENT.md` - Migration note (one-time)

**analytics/ specific:**
- `analytics/LOCAL_TESTING_SUCCESS.md` - Testing snapshot
- `analytics/ML_README.md` - ML documentation (possibly keep if active)

**artifact outputs (AUTO-GENERATED - DELETE):**
- `services/api/agent/artifacts/**/*.md` - All agent-generated artifacts (auto-generated reports)

**Other:**
- `apps/web/playwright-report/data/*.md` - Test report artifacts (auto-generated)

---

## Summary

**Total to DELETE:** ~311 files

**Key Deletion Patterns:**
- `v0.4.XX` - All version-specific docs
- `PHASE_XX` - All phase narratives
- `*_COMPLETE.md` - All completion snapshots
- `*_SUMMARY.md` - All phase summaries
- `*_STATUS.md` - All status snapshots
- `*_FIX.md` - All bugfix narratives
- `*_IMPLEMENTATION.md` - All implementation narratives
- `*_DEPLOYMENT*.md` - Version-specific deployment docs
- `*_VERIFICATION*.md` - All verification snapshots
- `*_POLISH*.md` - All UI polish notes
- `HACKATHON_*` - All hackathon narratives
- `STAGING_*` - All staging-specific docs
- `SETTINGS_*` / `HEADER_*` / `LOGO_*` - UI polish snapshots
- `CHANGELOG_v*` - Version-specific changelogs
- `MANUAL_TEST*` / `SMOKE_TEST*` - Test result snapshots
- `docs/hackathon/**` - All hackathon files

**What's Preserved:**
- All README.md files ✅
- Core architecture docs ✅
- Production runbooks & operational guides ✅
- Security & compliance docs ✅
- Testing setup guides (not test results) ✅
- Infrastructure & deployment guides (current state) ✅
- Analytics & data pipeline docs ✅
- API reference & feature capabilities ✅
- Monitoring & observability setup ✅

---

## Next Steps

1. Review this classification
2. Confirm deletion list
3. Execute: `git rm <files>`
4. Commit with message: `chore(docs): remove transient markdown notes and snapshot drafts`
