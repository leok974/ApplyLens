# Docs Reorg Plan – ApplyLens

**Created**: 2025-11-27  
**Status**: Phase 1 - Classification Complete  
**Goal**: Streamline documentation to keep only core, future implementation, and agent instruction docs.

## Classification Categories

- **CORE**: Essential docs for maintainers/devs/SREs (architecture, setup, testing, ops)
- **FUTURE_IMPLEMENTATION**: Plans, RFCs, roadmaps for future work
- **AGENT_INSTRUCTIONS**: Docs specifically for AI agents, protocols, MCP instructions
- **HACKATHON**: Hackathon-specific docs (kept as-is under hackathon/)
- **LEGACY_AUDIT**: Historical cleanup/audit records
- **PR_NOTES**: Specific PR documentation
- **ARCHIVE**: Already archived historical docs
- **DELETE**: Superseded, trivial, or duplicate docs to remove

## Actions

- **KEEP**: Keep as-is in new location
- **KEEP+MERGE**: Merge into canonical doc
- **ARCHIVE**: Move to docs/archive/
- **DELETE**: Remove entirely (git rm)

---

## Main Repository Docs Classification

### Top-Level Docs

| Path | Category | Action | Notes |
|------|----------|--------|-------|
| README.md | CORE | KEEP | Main entry point |
| CHANGELOG.md | CORE | KEEP | Release history |

### docs/ Root Level (Current)

| Path | Category | Action | Target Location | Notes |
|------|----------|--------|----------------|-------|
| docs/APPLYLENS_OVERVIEW.md | CORE | KEEP | docs/core/OVERVIEW.md | Main overview doc |
| docs/APPLYLENS_ARCHITECTURE.md | CORE | KEEP+MERGE | docs/core/ARCHITECTURE.md | Merge with ARCHITECTURE.md |
| docs/ARCHITECTURE.md | CORE | KEEP+MERGE | docs/core/ARCHITECTURE.md | Merge with APPLYLENS_ARCHITECTURE.md |
| docs/OVERVIEW.md | CORE | KEEP+MERGE | docs/core/OVERVIEW.md | Merge with APPLYLENS_OVERVIEW.md |
| docs/GETTING_STARTED.md | CORE | KEEP | docs/core/GETTING_STARTED.md | Quick start guide |
| docs/LOCAL_DEV_SETUP.md | CORE | KEEP | docs/core/LOCAL_DEV_SETUP.md | Local setup |
| docs/DEVELOPMENT.md | CORE | KEEP | docs/core/DEVELOPMENT.md | Development guide |
| docs/TESTING_AND_E2E_OVERVIEW.md | CORE | KEEP | docs/core/TESTING_OVERVIEW.md | Testing guide |
| docs/TESTING.md | CORE | KEEP+MERGE | docs/core/TESTING_OVERVIEW.md | Merge into main testing doc |
| docs/RUNNING_TESTS.md | CORE | KEEP+MERGE | docs/core/TESTING_OVERVIEW.md | Merge into main testing doc |
| docs/CONTRIBUTING.md | CORE | KEEP | docs/core/CONTRIBUTING.md | Contribution guide |
| docs/SECURITY.md | CORE | KEEP | docs/core/SECURITY.md | Security policy |

### Backend/API Docs

| Path | Category | Action | Target Location | Notes |
|------|----------|--------|----------------|-------|
| docs/BACKEND.md | CORE | KEEP+MERGE | docs/core/ARCHITECTURE.md | Merge into architecture |
| docs/FRONTEND.md | CORE | KEEP+MERGE | docs/core/ARCHITECTURE.md | Merge into architecture |
| docs/API_ROUTE_POLICY.md | CORE | KEEP | docs/core/API_ROUTE_POLICY.md | API standards |

### Infrastructure & Deployment

| Path | Category | Action | Target Location | Notes |
|------|----------|--------|----------------|-------|
| docs/DEPLOY_PROD.md | CORE | KEEP | docs/core/DEPLOYMENT.md | Main deployment doc |
| docs/DEPLOY_PROD_APPLYLENS.md | CORE | KEEP+MERGE | docs/core/DEPLOYMENT.md | Merge into main deployment |
| docs/DEPLOYMENT.md | CORE | KEEP+MERGE | docs/core/DEPLOYMENT.md | Merge into main deployment |
| docs/QUICK_DEPLOY.md | CORE | KEEP+MERGE | docs/core/DEPLOYMENT.md | Merge quick deploy notes |
| docs/PRODUCTION_DEPLOYMENT.md | CORE | KEEP+MERGE | docs/core/DEPLOYMENT.md | Merge production notes |
| docs/DEPLOYMENT_STATUS.md | LEGACY_AUDIT | ARCHIVE | docs/archive/audits/ | Point-in-time status |
| docs/DEPLOYMENT_VALIDATION_GUARDRAILS.md | CORE | KEEP | docs/core/DEPLOYMENT_GUARDRAILS.md | Guardrails reference |
| infra/PROD_INFRA_OVERVIEW.md | CORE | KEEP | docs/core/INFRASTRUCTURE.md | Infrastructure overview |

### Monitoring & Observability

| Path | Category | Action | Target Location | Notes |
|------|----------|--------|----------------|-------|
| docs/MONITORING_SETUP.md | CORE | KEEP | docs/core/MONITORING.md | Main monitoring doc |
| docs/MONITORING_QUICKREF.md | CORE | KEEP+MERGE | docs/core/MONITORING.md | Merge into monitoring |
| docs/METRICS_AND_DASHBOARDS.md | CORE | KEEP+MERGE | docs/core/MONITORING.md | Merge metrics info |
| docs/PROMETHEUS_METRICS.md | CORE | KEEP+MERGE | docs/core/MONITORING.md | Prometheus reference |
| docs/OBSERVABILITY_STACK_PLAN.md | FUTURE_IMPLEMENTATION | KEEP | docs/future/OBSERVABILITY_MIGRATION.md | Migration to Datadog plan |
| docs/AGENTS_OBSERVABILITY.md | AGENT_INSTRUCTIONS | KEEP | docs/agents/AGENTS_OBSERVABILITY.md | Agent monitoring |
| docs/EXTENSION_API_OBSERVABILITY.md | CORE | KEEP+MERGE | docs/core/MONITORING.md | Extension API monitoring |

### Operations & Runbooks

| Path | Category | Action | Target Location | Notes |
|------|----------|--------|----------------|-------|
| docs/OPS.md | CORE | KEEP | docs/core/OPERATIONS.md | Operations guide |
| docs/OPERATIONAL_STATUS.md | LEGACY_AUDIT | ARCHIVE | docs/archive/audits/ | Point-in-time status |
| docs/PRODUCTION_HANDBOOK.md | CORE | KEEP | docs/core/PRODUCTION_HANDBOOK.md | Production handbook |
| docs/PRODUCTION_QUICKREF.md | CORE | KEEP+MERGE | docs/core/PRODUCTION_HANDBOOK.md | Merge into handbook |
| docs/PRODUCTION_RESILIENCE.md | CORE | KEEP+MERGE | docs/core/PRODUCTION_HANDBOOK.md | Merge resilience notes |
| docs/ONCALL_HANDBOOK.md | CORE | KEEP | docs/core/ONCALL_HANDBOOK.md | On-call guide |
| docs/manual-testing-guide.md | CORE | KEEP+MERGE | docs/core/TESTING_OVERVIEW.md | Merge into testing |

### Agent Instructions & Protocols

| Path | Category | Action | Target Location | Notes |
|------|----------|--------|----------------|-------|
| docs/COMPANION_EXTENSION_PROTOCOL.md | AGENT_INSTRUCTIONS | KEEP | docs/agents/COMPANION_PROTOCOL.md | Extension protocol |
| docs/COMPANION_BANDIT_PHASE6.md | AGENT_INSTRUCTIONS | KEEP | docs/agents/BANDIT_LEARNING.md | Bandit/learning system |
| docs/DEVDIAG_INTEGRATION.md | AGENT_INSTRUCTIONS | KEEP | docs/agents/DEVDIAG_INTEGRATION.md | DevDiag MCP integration |
| docs/AGENTS_QUICKSTART.md | AGENT_INSTRUCTIONS | KEEP | docs/agents/QUICKSTART.md | Agent quick reference |
| docs/COPILOT_DEPLOY_METAPROMPT.md | AGENT_INSTRUCTIONS | KEEP | docs/agents/DEPLOY_METAPROMPT.md | Copilot deploy instructions |
| docs/ACTIVE_LEARNING.md | AGENT_INSTRUCTIONS | KEEP | docs/agents/ACTIVE_LEARNING.md | Learning system |

### Future Plans & Audits

| Path | Category | Action | Target Location | Notes |
|------|----------|--------|----------------|-------|
| docs/REPO_HISTORY_CLEANUP_PLAN.md | FUTURE_IMPLEMENTATION | KEEP | docs/future/REPO_HISTORY_CLEANUP.md | Git history cleanup plan |
| docs/GITHUB_WORKFLOWS_AUDIT.md | FUTURE_IMPLEMENTATION | KEEP | docs/future/WORKFLOWS_AUDIT.md | CI/CD audit & recommendations |
| docs/REPO_ARCHITECTURE_REORG_PLAN.md | LEGACY_AUDIT | ARCHIVE | docs/archive/audits/ | Completed reorg plan |
| docs/REPO_AUDIT_PHASE1.md | LEGACY_AUDIT | ARCHIVE | docs/archive/audits/ | Historical audit |
| docs/REPO_CLEANUP_PHASE2_SUMMARY.md | LEGACY_AUDIT | ARCHIVE | docs/archive/audits/ | Completed cleanup |
| docs/PR_NOTES_repo_cleanup_phase2.md | PR_NOTES | ARCHIVE | docs/archive/audits/ | PR-specific notes |

### Specific Features/Components

| Path | Category | Action | Target Location | Notes |
|------|----------|--------|----------------|-------|
| docs/GMAIL_SETUP.md | CORE | KEEP | docs/core/GMAIL_SETUP.md | Gmail integration |
| docs/MULTI_USER_GMAIL.md | CORE | KEEP+MERGE | docs/core/GMAIL_SETUP.md | Multi-user setup |
| docs/OAUTH_QUICK_REF.md | CORE | KEEP | docs/core/OAUTH_SETUP.md | OAuth reference |
| docs/GOOGLE_OAUTH_DEBUG_GUIDE.md | CORE | KEEP+MERGE | docs/core/OAUTH_SETUP.md | Merge debug info |
| docs/OLLAMA_INTEGRATION.md | CORE | KEEP | docs/core/OLLAMA.md | Ollama LLM integration |
| docs/OLLAMA_QUICKREF.md | CORE | KEEP+MERGE | docs/core/OLLAMA.md | Merge quickref |
| docs/LEDGERMIND_INTEGRATION.md | CORE | KEEP | docs/core/LEDGERMIND.md | LedgerMind integration |
| docs/TRACKER_MAIL_INTEGRATION.md | CORE | KEEP | docs/core/TRACKER_MAIL.md | TrackerMail integration |
| docs/MAILBOX_THEME_SYSTEM.md | CORE | KEEP | docs/core/MAILBOX_THEMES.md | Theme system |
| docs/THREAD_VIEWER_IMPLEMENTATION.md | LEGACY_AUDIT | ARCHIVE | docs/archive/phases/ | Completed implementation |
| docs/THREAD_VIEWER_QUICKREF.md | CORE | DELETE | - | Superseded by main docs |
| docs/THREAD_LIST_CARD_CONTRACT.md | CORE | KEEP | docs/core/COMPONENT_CONTRACTS.md | Component contracts |

### Cloudflare & Edge

| Path | Category | Action | Target Location | Notes |
|------|----------|--------|----------------|-------|
| docs/CLOUDFLARE_TOOLKIT_GUIDE.md | CORE | KEEP | docs/core/CLOUDFLARE.md | Cloudflare guide |
| docs/CLOUDFLARE_502_FIX.md | LEGACY_AUDIT | ARCHIVE | docs/archive/incidents/ | Specific incident fix |
| docs/502_EDGE_CACHE_DIAGNOSIS.md | LEGACY_AUDIT | ARCHIVE | docs/archive/incidents/ | Specific diagnosis |
| docs/PROD_502_FIX_SUMMARY.md | LEGACY_AUDIT | ARCHIVE | docs/archive/incidents/ | Fix summary |
| docs/MIXED_CONTENT_FIX.md | LEGACY_AUDIT | ARCHIVE | docs/archive/incidents/ | Specific fix |
| docs/SHARED_TUNNEL_CONNECTOR_NOTES.md | CORE | KEEP+MERGE | docs/core/CLOUDFLARE.md | Tunnel notes |

### Other Tools & Utilities

| Path | Category | Action | Target Location | Notes |
|------|----------|--------|----------------|-------|
| docs/CLI-TOOLS-GUIDE.md | CORE | KEEP | docs/core/CLI_TOOLS.md | CLI tools reference |
| docs/DATABASE_URL_REFACTOR_GUIDE.md | LEGACY_AUDIT | ARCHIVE | docs/archive/migrations/ | Completed refactor |
| docs/EXTENSION_API_RATE_LIMITING.md | CORE | KEEP+MERGE | docs/core/API_ROUTE_POLICY.md | API rate limits |
| docs/ACTIONS_BADGE_SYSTEM.md | CORE | KEEP | docs/core/ACTIONS_BADGES.md | GitHub actions badges |
| docs/RELEASE_v0.5.x.md | LEGACY_AUDIT | ARCHIVE | docs/archive/releases/ | Old release notes |

### docs/README.md

| Path | Category | Action | Target Location | Notes |
|------|----------|--------|----------------|-------|
| docs/README.md | CORE | KEEP | docs/README.md | Docs index (update) |
| docs/CHANGELOG.md | CORE | DELETE | - | Duplicate of root CHANGELOG.md |

---

## Subdirectory Docs

### docs/architecture/

| Path | Category | Action | Notes |
|------|----------|--------|-------|
| docs/architecture/AGENTS.md | AGENT_INSTRUCTIONS | KEEP | Keep in docs/agents/ |
| docs/architecture/BUILD_METADATA.md | CORE | KEEP | Keep in docs/core/ |
| docs/architecture/testing/E2E_TEST_SEEDING_SYSTEM.md | CORE | KEEP | Keep in docs/core/testing/ |
| docs/architecture/testing/PLAYWRIGHT_TEST_RUNNER_README.md | CORE | KEEP | Keep in docs/core/testing/ |

### docs/archive/ (Already archived)

| Path | Category | Action | Notes |
|------|----------|--------|-------|
| docs/archive/agents/* | ARCHIVE | KEEP | Already archived |
| docs/archive/companion/* | ARCHIVE | KEEP | Already archived |
| docs/archive/e2e/* | ARCHIVE | KEEP | Already archived |
| docs/archive/grafana/* | ARCHIVE | KEEP | Already archived |
| docs/archive/patches/* | ARCHIVE | KEEP | Already archived |
| docs/archive/phases/* | ARCHIVE | KEEP | Already archived |

### docs/runbooks/

| Path | Category | Action | Target Location | Notes |
|------|----------|--------|----------------|-------|
| docs/runbooks/DEV_API_SETUP.md | CORE | KEEP | docs/core/runbooks/DEV_API_SETUP.md | Dev setup |
| docs/runbooks/EDGE_DEPLOYMENT_GUIDE.md | CORE | KEEP | docs/core/runbooks/EDGE_DEPLOYMENT.md | Edge deploy |
| docs/runbooks/EDGE_QUICKSTART.md | CORE | KEEP+MERGE | docs/core/runbooks/EDGE_DEPLOYMENT.md | Merge into edge guide |
| docs/runbooks/UNIFIED_EDGE_QUICKSTART.md | CORE | KEEP+MERGE | docs/core/runbooks/EDGE_DEPLOYMENT.md | Merge into edge guide |
| docs/runbooks/APPROVAL_WORKFLOWS.md | CORE | KEEP | docs/core/runbooks/APPROVAL_WORKFLOWS.md | Approval flows |
| docs/runbooks/GUARDRAILS_CONFIG.md | CORE | KEEP | docs/core/runbooks/GUARDRAILS.md | Guardrails |
| docs/runbooks/POLICY_MANAGEMENT.md | CORE | KEEP | docs/core/runbooks/POLICIES.md | Policy management |
| docs/runbooks/RUNBOOK_ROLLBACK.md | CORE | KEEP | docs/core/runbooks/ROLLBACK.md | Rollback procedures |
| docs/runbooks/PHASE4_TROUBLESHOOTING.md | LEGACY_AUDIT | ARCHIVE | docs/archive/phases/ | Phase-specific troubleshooting |

### docs/playbooks/

| Path | Category | Action | Target Location | Notes |
|------|----------|--------|----------------|-------|
| docs/playbooks/PLAYBOOK_API_OUTAGE.md | CORE | KEEP | docs/core/playbooks/API_OUTAGE.md | Incident playbook |
| docs/playbooks/PLAYBOOK_SLO_VIOLATION.md | CORE | KEEP | docs/core/playbooks/SLO_VIOLATION.md | SLO playbook |

### docs/releases/

| Path | Category | Action | Notes |
|------|----------|--------|-------|
| docs/releases/v0.5.0.md | ARCHIVE | KEEP | Already in releases/ |

### docs/case-studies/

| Path | Category | Action | Target Location | Notes |
|------|----------|--------|----------------|-------|
| docs/case-studies/applylens-companion-learning.md | AGENT_INSTRUCTIONS | KEEP | docs/agents/case-studies/ | Learning case study |

### docs/infra/

| Path | Category | Action | Target Location | Notes |
|------|----------|--------|----------------|-------|
| docs/infra/LEDGERMIND_ROUTING.md | CORE | KEEP+MERGE | docs/core/LEDGERMIND.md | Merge into main doc |

### docs/looker/

| Path | Category | Action | Target Location | Notes |
|------|----------|--------|----------------|-------|
| docs/looker/LOOKER_STUDIO_SETUP.md | CORE | KEEP | docs/core/analytics/LOOKER_SETUP.md | Analytics setup |

---

## Infrastructure Docs (infra/)

| Path | Category | Action | Target Location | Notes |
|------|----------|--------|----------------|-------|
| infra/PROD_INFRA_OVERVIEW.md | CORE | KEEP | docs/core/INFRASTRUCTURE.md | Main infra doc |
| infra/NGINX_ROUTING.md | CORE | KEEP+MERGE | docs/core/INFRASTRUCTURE.md | Nginx routing |
| infra/APPLYLENS_TUNNEL_RUNBOOK.md | CORE | KEEP | docs/core/runbooks/TUNNEL.md | Tunnel runbook |
| infra/CLOUDFLARE_TUNNEL_QUICKSTART.md | CORE | KEEP+MERGE | docs/core/runbooks/TUNNEL.md | Merge tunnel docs |
| infra/TUNNEL_CONFIGURATION.md | CORE | KEEP+MERGE | docs/core/runbooks/TUNNEL.md | Merge tunnel config |
| infra/STYLE_TUNING_RUNBOOK.md | CORE | KEEP | docs/core/runbooks/STYLE_TUNING.md | Style tuning |
| infra/PHASE_6_PROD_AUTH_ME_502_FIX.md | LEGACY_AUDIT | ARCHIVE | docs/archive/incidents/ | Specific fix |
| infra/docs/CLOUDFLARE_HARDENING_CHECKLIST.md | CORE | KEEP | docs/core/runbooks/CLOUDFLARE_HARDENING.md | Security checklist |
| infra/docs/CLOUDFLARE_TUNNEL_RUNBOOK.md | CORE | KEEP+MERGE | docs/core/runbooks/TUNNEL.md | Duplicate tunnel doc |
| infra/docs/DEPLOYMENT_COMPLETE_2025-01-10.md | LEGACY_AUDIT | ARCHIVE | docs/archive/phases/ | Deployment completion |
| infra/docs/OAUTH_SETUP.md | CORE | KEEP+MERGE | docs/core/OAUTH_SETUP.md | OAuth setup |

---

## Runbooks (runbooks/)

| Path | Category | Action | Target Location | Notes |
|------|----------|--------|----------------|-------|
| runbooks/503_upstream_stale.md | CORE | KEEP | docs/core/incidents/503_UPSTREAM.md | Incident runbook |
| runbooks/profile-warehouse.md | CORE | KEEP | docs/core/runbooks/PROFILE_WAREHOUSE.md | Profile warehouse |
| runbooks/incidents/* | CORE | KEEP | docs/core/incidents/ | All incident runbooks |

---

## Services API Docs (services/api/)

| Path | Category | Action | Target Location | Notes |
|------|----------|--------|----------------|-------|
| services/api/README.md | CORE | KEEP | docs/core/api/README.md | API main readme |
| services/api/QUICK_START.md | CORE | KEEP+MERGE | docs/core/api/README.md | Merge quickstart |
| services/api/docs/API_REFERENCE.md | CORE | KEEP | docs/core/api/REFERENCE.md | API reference |
| services/api/docs/TESTING_GUIDE.md | CORE | KEEP+MERGE | docs/core/TESTING_OVERVIEW.md | Merge testing |
| services/api/docs/CSRF_AND_M2M_AUTH.md | CORE | KEEP | docs/core/api/AUTH.md | Auth documentation |
| services/api/docs/AGENT_OBSERVABILITY.md | AGENT_INSTRUCTIONS | KEEP | docs/agents/API_OBSERVABILITY.md | Agent observability |
| services/api/docs/GRAFANA_DASHBOARD_SETUP.md | CORE | KEEP+MERGE | docs/core/MONITORING.md | Merge dashboard setup |
| services/api/docs/runbooks/* | CORE | KEEP | docs/core/api/runbooks/ | API runbooks |
| services/api/PHASE_*.md | LEGACY_AUDIT | ARCHIVE | docs/archive/phases/ | Phase completion docs |
| services/api/MIGRATION_STATUS.md | LEGACY_AUDIT | ARCHIVE | docs/archive/migrations/ | Migration status |
| services/api/NEXT_STEPS.md | LEGACY_AUDIT | DELETE | - | Outdated next steps |

---

## Web App Docs (apps/web/)

| Path | Category | Action | Target Location | Notes |
|------|----------|--------|----------------|-------|
| apps/web/README.md | CORE | KEEP | docs/core/web/README.md | Web app docs |
| apps/web/docs/E2E_GUIDE.md | CORE | KEEP+MERGE | docs/core/TESTING_OVERVIEW.md | Merge E2E guide |
| apps/web/tests/PLAYWRIGHT_AUTH_SETUP.md | CORE | KEEP+MERGE | docs/core/TESTING_OVERVIEW.md | Merge auth setup |
| apps/web/tests/QUICK_REFERENCE.md | CORE | KEEP+MERGE | docs/core/TESTING_OVERVIEW.md | Merge test reference |
| apps/web/tests/README.test.md | CORE | KEEP+MERGE | docs/core/TESTING_OVERVIEW.md | Merge test readme |
| apps/web/BACK_TO_APPLYLENS_BUTTON.md | LEGACY_AUDIT | DELETE | - | Trivial feature note |
| apps/web/CARD_UI_POLISH_SUMMARY.md | LEGACY_AUDIT | DELETE | - | Completed polish notes |
| apps/web/FOLLOWUP_DRAFTS.md | LEGACY_AUDIT | DELETE | - | Feature-specific notes |
| apps/web/TRACKER_MAIL_INTEGRATION.md | CORE | KEEP+MERGE | docs/core/TRACKER_MAIL.md | Merge integration |
| apps/web/VERSION_TRACKING.md | CORE | KEEP | docs/core/web/VERSIONING.md | Version tracking |

---

## Extension Docs (apps/extension-applylens/)

| Path | Category | Action | Target Location | Notes |
|------|----------|--------|----------------|-------|
| apps/extension-applylens/README.md | CORE | KEEP | docs/core/extension/README.md | Extension main |
| apps/extension-applylens/DEPLOYMENT.md | CORE | KEEP+MERGE | docs/core/extension/README.md | Merge deployment |
| apps/extension-applylens/DEPLOYMENT_STATUS.md | LEGACY_AUDIT | DELETE | - | Outdated status |
| apps/extension-applylens/PRODUCTION_DEPLOYMENT.md | CORE | KEEP+MERGE | docs/core/extension/README.md | Merge prod deployment |
| apps/extension-applylens/TESTING.md | CORE | KEEP+MERGE | docs/core/TESTING_OVERVIEW.md | Merge testing |
| apps/extension-applylens/SUBMISSION_CHECKLIST.md | CORE | KEEP | docs/core/extension/SUBMISSION.md | Chrome store submission |
| apps/extension-applylens/docs/CHROME_WEB_STORE_SUBMISSION.md | CORE | KEEP+MERGE | docs/core/extension/SUBMISSION.md | Merge submission docs |
| apps/extension-applylens/CONTENT_INTEGRATION.md | AGENT_INSTRUCTIONS | KEEP | docs/agents/CONTENT_INTEGRATION.md | Content script protocol |
| apps/extension-applylens/EXTENSION_INTEGRATION.md | AGENT_INSTRUCTIONS | KEEP+MERGE | docs/agents/CONTENT_INTEGRATION.md | Merge integration |
| apps/extension-applylens/LEARNING_IMPLEMENTATION.md | AGENT_INSTRUCTIONS | KEEP | docs/agents/LEARNING_IMPLEMENTATION.md | Learning system |
| apps/extension-applylens/LEARNING_LOOP.md | AGENT_INSTRUCTIONS | KEEP+MERGE | docs/agents/LEARNING_IMPLEMENTATION.md | Merge learning loop |
| apps/extension-applylens/LOAD_EXTENSION.md | CORE | KEEP+MERGE | docs/core/extension/README.md | Merge load instructions |
| apps/extension-applylens/PHASE_5_*.md | LEGACY_AUDIT | DELETE | - | Phase-specific guides |
| apps/extension-applylens/BANDIT_TEST_FIX.md | LEGACY_AUDIT | DELETE | - | Specific test fix |
| apps/extension-applylens/KILL_SWITCH_SUMMARY.md | LEGACY_AUDIT | DELETE | - | Feature summary |
| apps/extension-applylens/INTEGRATION_TEST.md | LEGACY_AUDIT | DELETE | - | Outdated test notes |

---

## Analytics Docs (analytics/)

| Path | Category | Action | Target Location | Notes |
|------|----------|--------|----------------|-------|
| analytics/README.md | CORE | KEEP | docs/core/analytics/README.md | Analytics overview |
| analytics/ARCHITECTURE.md | CORE | KEEP+MERGE | docs/core/analytics/README.md | Merge architecture |
| analytics/RUNBOOK.md | CORE | KEEP | docs/core/analytics/RUNBOOK.md | Analytics runbook |
| analytics/ML_README.md | CORE | KEEP | docs/core/analytics/ML.md | ML pipeline |
| analytics/LOCAL_TESTING_SUCCESS.md | LEGACY_AUDIT | DELETE | - | Test completion note |
| analytics/ops/COST-MONITORING.md | CORE | KEEP | docs/core/analytics/COST_MONITORING.md | Cost monitoring |
| analytics/ops/UPTIME-MONITORING.md | CORE | KEEP | docs/core/analytics/UPTIME.md | Uptime monitoring |
| analytics/ops/VERIFICATION-QUERIES.md | CORE | KEEP | docs/core/analytics/VERIFICATION.md | Data verification |

---

## Hackathon Docs (hackathon/)

| Path | Category | Action | Notes |
|------|----------|--------|-------|
| hackathon/HACKATHON.md | HACKATHON | KEEP | Hackathon overview |
| hackathon/ARCHITECTURE.md | HACKATHON | KEEP | Hackathon architecture |
| hackathon/DATADOG_SETUP.md | HACKATHON | KEEP | Datadog demo setup |
| hackathon/TRAFFIC_GENERATOR.md | HACKATHON | KEEP | Traffic generator |
| hackathon/SEQUENCE_DIAGRAM.md | HACKATHON | KEEP | Sequence diagrams |

---

## GitHub Agent Docs (.github/agents/)

| Path | Category | Action | Target Location | Notes |
|------|----------|--------|----------------|-------|
| .github/agents/*.md | AGENT_INSTRUCTIONS | KEEP | docs/agents/github/ | GitHub agent configs |

---

## Component/Module READMEs (Keep as-is)

All component-specific READMEs stay in place:
- analytics/dbt/README.md
- analytics/fivetran/README.md
- analytics/ingest/README.md
- apps/web/tests/auth/README.md
- apps/web/tests/e2e/README*.md
- apps/web/tests/smoke/README.md
- apps/extension-applylens/e2e/README.companion.md
- deploy/README.md
- infra/*/README.md (component-specific)
- scripts/*/README.md
- services/api/scripts/README*.md
- tests/e2e/README.md

---

## Final Docs Structure (Target)

```
docs/
├── README.md                           # Docs index (updated)
├── core/                               # CORE - Essential current docs
│   ├── OVERVIEW.md                     # What is ApplyLens
│   ├── ARCHITECTURE.md                 # System architecture
│   ├── INFRASTRUCTURE.md               # Infra & deployment overview
│   ├── GETTING_STARTED.md              # Quick start
│   ├── LOCAL_DEV_SETUP.md              # Local development
│   ├── DEVELOPMENT.md                  # Development guide
│   ├── CONTRIBUTING.md                 # How to contribute
│   ├── SECURITY.md                     # Security policy
│   ├── TESTING_OVERVIEW.md             # Testing & E2E guide
│   ├── DEPLOYMENT.md                   # Production deployment
│   ├── DEPLOYMENT_GUARDRAILS.md        # Deployment safety
│   ├── MONITORING.md                   # Observability & metrics
│   ├── OPERATIONS.md                   # Operations guide
│   ├── PRODUCTION_HANDBOOK.md          # Production operations
│   ├── ONCALL_HANDBOOK.md              # On-call procedures
│   ├── GMAIL_SETUP.md                  # Gmail integration
│   ├── OAUTH_SETUP.md                  # OAuth configuration
│   ├── OLLAMA.md                       # Ollama LLM integration
│   ├── LEDGERMIND.md                   # LedgerMind integration
│   ├── TRACKER_MAIL.md                 # TrackerMail integration
│   ├── CLOUDFLARE.md                   # Cloudflare setup
│   ├── CLI_TOOLS.md                    # CLI tools reference
│   ├── API_ROUTE_POLICY.md             # API standards
│   ├── ACTIONS_BADGES.md               # GitHub actions badges
│   ├── MAILBOX_THEMES.md               # Theme system
│   ├── COMPONENT_CONTRACTS.md          # Component interfaces
│   ├── BUILD_METADATA.md               # Build metadata
│   ├── api/                            # API-specific docs
│   │   ├── README.md                   # API overview
│   │   ├── REFERENCE.md                # API reference
│   │   ├── AUTH.md                     # Auth & CSRF
│   │   └── runbooks/                   # API runbooks
│   ├── web/                            # Web app docs
│   │   ├── README.md                   # Web overview
│   │   └── VERSIONING.md               # Version tracking
│   ├── extension/                      # Extension docs
│   │   ├── README.md                   # Extension overview
│   │   └── SUBMISSION.md               # Chrome store submission
│   ├── analytics/                      # Analytics docs
│   │   ├── README.md                   # Analytics overview
│   │   ├── RUNBOOK.md                  # Analytics runbook
│   │   ├── ML.md                       # ML pipeline
│   │   ├── COST_MONITORING.md          # Cost tracking
│   │   ├── UPTIME.md                   # Uptime monitoring
│   │   ├── VERIFICATION.md             # Data verification
│   │   └── LOOKER_SETUP.md             # Looker Studio
│   ├── testing/                        # Testing details
│   │   ├── E2E_TEST_SEEDING.md         # E2E seeding system
│   │   └── PLAYWRIGHT_RUNNER.md        # Playwright runner
│   ├── runbooks/                       # Operational runbooks
│   │   ├── DEV_API_SETUP.md            # Dev API setup
│   │   ├── EDGE_DEPLOYMENT.md          # Edge deployment
│   │   ├── TUNNEL.md                   # Tunnel configuration
│   │   ├── STYLE_TUNING.md             # Style tuning
│   │   ├── CLOUDFLARE_HARDENING.md     # Security hardening
│   │   ├── APPROVAL_WORKFLOWS.md       # Approval flows
│   │   ├── GUARDRAILS.md               # Guardrails config
│   │   ├── POLICIES.md                 # Policy management
│   │   ├── ROLLBACK.md                 # Rollback procedures
│   │   └── PROFILE_WAREHOUSE.md        # Profile warehouse
│   ├── playbooks/                      # Incident playbooks
│   │   ├── API_OUTAGE.md               # API outage response
│   │   └── SLO_VIOLATION.md            # SLO violation response
│   └── incidents/                      # Incident runbooks
│       ├── 503_UPSTREAM.md             # 503 upstream errors
│       └── [all runbooks/incidents/*]  # Other incidents
├── agents/                             # AGENT_INSTRUCTIONS - For AI agents
│   ├── QUICKSTART.md                   # Agent quick reference
│   ├── COMPANION_PROTOCOL.md           # Extension protocol
│   ├── BANDIT_LEARNING.md              # Bandit/learning system
│   ├── ACTIVE_LEARNING.md              # Active learning
│   ├── LEARNING_IMPLEMENTATION.md      # Learning system impl
│   ├── CONTENT_INTEGRATION.md          # Content script protocol
│   ├── DEVDIAG_INTEGRATION.md          # DevDiag MCP
│   ├── DEPLOY_METAPROMPT.md            # Copilot deploy instructions
│   ├── AGENTS_OBSERVABILITY.md         # Agent monitoring
│   ├── API_OBSERVABILITY.md            # API observability for agents
│   ├── case-studies/                   # Agent case studies
│   │   └── companion-learning.md       # Learning case study
│   └── github/                         # GitHub agent configs
│       └── [.github/agents/*]          # Agent markdown files
├── future/                             # FUTURE_IMPLEMENTATION - Plans & RFCs
│   ├── REPO_HISTORY_CLEANUP.md         # Git history cleanup plan
│   ├── WORKFLOWS_AUDIT.md              # CI/CD audit & recommendations
│   └── OBSERVABILITY_MIGRATION.md      # Datadog migration plan
├── archive/                            # ARCHIVE - Historical docs
│   ├── audits/                         # Audit records
│   │   ├── REPO_AUDIT_PHASE1.md        # Phase 1 audit
│   │   ├── REPO_CLEANUP_PHASE2_SUMMARY.md # Phase 2 summary
│   │   ├── REPO_ARCHITECTURE_REORG_PLAN.md # Reorg plan
│   │   ├── PR_NOTES_repo_cleanup_phase2.md # PR notes
│   │   ├── OPERATIONAL_STATUS.md       # Point-in-time status
│   │   └── DEPLOYMENT_STATUS.md        # Deployment status
│   ├── incidents/                      # Resolved incidents
│   │   ├── CLOUDFLARE_502_FIX.md       # 502 fix
│   │   ├── 502_EDGE_CACHE_DIAGNOSIS.md # Edge cache issue
│   │   ├── PROD_502_FIX_SUMMARY.md     # Fix summary
│   │   ├── MIXED_CONTENT_FIX.md        # Mixed content
│   │   └── PHASE_6_PROD_AUTH_ME_502_FIX.md # Auth fix
│   ├── migrations/                     # Completed migrations
│   │   ├── DATABASE_URL_REFACTOR_GUIDE.md # DB URL refactor
│   │   └── MIGRATION_STATUS.md         # Migration status
│   ├── releases/                       # Old releases
│   │   ├── v0.5.0.md                   # v0.5.0 notes
│   │   └── RELEASE_v0.5.x.md           # v0.5.x notes
│   ├── agents/                         # Old agent docs
│   ├── companion/                      # Old companion docs
│   ├── e2e/                            # Old E2E docs
│   ├── grafana/                        # Old Grafana docs
│   ├── patches/                        # Old patches
│   └── phases/                         # Phase completion docs
│       ├── THREAD_VIEWER_ROADMAP.md    # Thread viewer
│       ├── PHASE4_TROUBLESHOOTING.md   # Phase 4
│       └── [all PHASE_*.md files]      # All phase docs
└── DOCS_REORG_PLAN.md                  # This plan

hackathon/                              # HACKATHON - Kept as-is
├── HACKATHON.md
├── ARCHITECTURE.md
├── DATADOG_SETUP.md
├── TRAFFIC_GENERATOR.md
└── SEQUENCE_DIAGRAM.md
```

---

## Summary Statistics

**Total Markdown files**: ~250
**Files to process**: ~150 (excluding component READMEs)

### By Action:
- **KEEP**: ~40 files (move to new structure)
- **KEEP+MERGE**: ~50 files (merge into ~20 canonical docs)
- **ARCHIVE**: ~30 files (move to docs/archive/)
- **DELETE**: ~30 files (remove entirely)

### Final Core Docs Count:
- **docs/core/**: ~50 files (consolidated)
- **docs/agents/**: ~15 files
- **docs/future/**: ~3 files
- **docs/archive/**: ~80 files (existing + new)
- **hackathon/**: 5 files (unchanged)

---

## Next Steps

1. ✅ **Phase 1 Complete**: Classification done
2. 🔄 **Phase 2**: Create branch and move files
3. 🔄 **Phase 3**: Merge and trim content
4. 🔄 **Phase 4**: Update cross-references and commit
