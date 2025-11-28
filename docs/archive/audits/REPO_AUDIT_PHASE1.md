# ApplyLens Repository Audit - Phase 1: Analysis

**Date**: November 25, 2025
**Branch**: feature/thread-to-tracker-link
**Total Tracked Files**: 1,681

---

## Executive Summary

This is a **comprehensive analysis-only audit** of the ApplyLens repository. No files have been modified or deleted in this phase.

**Key Findings**:
- ✅ Well-structured monorepo with clear separation of concerns
- ⚠️ **3,382 cache/build directories** exist on disk (most properly .gitignored)
- ⚠️ **9 docker-compose files** with some duplicates and backups
- ⚠️ **91 scripts** in `/scripts` directory - many legacy, some active
- ⚠️ Prometheus/Grafana stack still running but **Datadog is now primary observability**
- ⚠️ Multiple documentation files with overlapping content
- ✅ Large files are mostly legitimate assets (icons, model files, coverage reports)

---

## 1. Repository Structure Map

### Top-Level Directory Analysis

```
ApplyLens/
├── .github/          [ACTIVE] - GitHub Actions workflows, pre-commit hooks
├── .pytest_cache/    [GENERATED] - Should be .gitignored ⚠️
├── .ruff_cache/      [GENERATED] - Should be .gitignored ⚠️
├── .venv/            [LOCAL ENV] - Python virtual environment (likely .gitignored)
├── .vscode/          [IDE CONFIG] - VSCode settings
├── analytics/        [UNCLEAR] - Purpose unknown, needs investigation
├── apps/             [ACTIVE] - Frontend (web), Chrome extension
├── backup/           [UNCLEAR] - Backup artifacts, may be legacy
├── cloudflared/      [ACTIVE] - Cloudflare Tunnel configuration
├── deploy/           [LEGACY?] - May be superseded by docker-compose.prod.yml
├── docs/             [ACTIVE] - Extensive documentation (95 files)
├── grafana/          [LEGACY] - Grafana dashboards (Datadog is now primary)
├── hackathon/        [ACTIVE] - Datadog/Gemini hackathon artifacts (4 files)
├── infra/            [ACTIVE] - Docker Compose, Prometheus, Grafana, Elasticsearch
├── kibana/           [ACTIVE] - Kibana dashboards and configuration
├── letsencrypt/      [UNCLEAR] - SSL certificates (should not be in git)
├── monitoring/       [LEGACY?] - May overlap with Prometheus/Grafana
├── node_modules/     [GENERATED] - Should be .gitignored ⚠️
├── playwright-report/[GENERATED] - Test reports (should be .gitignored) ⚠️
├── public/           [UNCLEAR] - Duplicate of apps/web/public?
├── runbooks/         [UNCLEAR] - Operational runbooks (if exists)
├── scripts/          [ACTIVE/LEGACY MIX] - 91 scripts (many legacy)
├── secrets/          [SENSITIVE] - Should NEVER be in git ⚠️⚠️⚠️
├── services/         [ACTIVE] - Backend API (FastAPI)
├── src/              [UNCLEAR] - May be duplicate/legacy frontend code
├── test-results/     [GENERATED] - Playwright test results ⚠️
├── tests/            [UNCLEAR] - Root-level tests (vs apps/web/tests)
└── tools/            [UNCLEAR] - Utility scripts
```

### Purpose Assessment

| Directory | Status | Purpose | Notes |
|-----------|--------|---------|-------|
| `.github/` | ✅ Active | CI/CD workflows | Pre-commit hooks, likely Actions |
| `apps/web` | ✅ Active | React/Vite frontend | Primary web UI |
| `apps/extension-applylens` | ✅ Active | Chrome extension | Inbox companion |
| `services/api` | ✅ Active | FastAPI backend | Core API |
| `infra/` | ✅ Active | Docker infrastructure | Prometheus, Grafana, ES, Redis |
| `docs/` | ✅ Active | Documentation | **95 markdown files** (may have duplicates) |
| `hackathon/` | ✅ Active | Hackathon artifacts | Datadog/Gemini integration docs |
| `scripts/` | ⚠️ Mixed | Deployment/ops scripts | **91 scripts**, many likely legacy |
| `grafana/` | 🟡 Legacy | Grafana dashboards | **Datadog is now primary** |
| `monitoring/` | 🟡 Legacy? | Older monitoring | May overlap with Prometheus |
| `deploy/` | 🟡 Legacy? | Deployment scripts | May be superseded by docker-compose |
| `backup/` | ❓ Unclear | Backup artifacts | Needs investigation |
| `analytics/` | ❓ Unclear | Unknown | Empty or legacy? |
| `public/` | ❓ Unclear | Static assets | Duplicate of apps/web/public? |
| `src/` | ❓ Unclear | Source code | Legacy frontend? |
| `tests/` | ❓ Unclear | Root tests | Duplicate of apps/web/tests? |
| `tools/` | ❓ Unclear | Utilities | Needs investigation |
| `secrets/` | ⚠️ **DANGER** | Secrets | **Should NEVER be committed!** |
| `letsencrypt/` | ⚠️ Sensitive | SSL certs | Should not be in git |

---

## 2. Large / Suspicious Files

### Top 30 Largest Tracked Files

| Size | Type | Path | Assessment |
|------|------|------|------------|
| 487KB | `.joblib` | `services/api/models/label_v1.joblib` | ✅ Legitimate ML model |
| 467KB | `.json` | `services/api/openapi-debug.json` | ⚠️ Debug artifact - could gitignore |
| 376KB | `.png` | `apps/web/public/icon-512x512.png` | ✅ App icon |
| 376KB | `.png` | `apps/web/public/icon-512x512-maskable.png` | ✅ App icon |
| 376KB | `.png` | `apps/extension-applylens/icons/icon128.png` | ✅ Extension icon |
| 296KB | `.lcov` | `services/api/coverage.lcov` | ⚠️ **GENERATED** - should gitignore |
| 245KB | `.png` | `apps/web/public/brand/applylens.png` | ✅ Branding asset |
| 245KB | `.png` | `apps/web/public/ApplyLensLogo.png` | ✅ Logo |
| 234KB | `.png` | `apps/web/public/icon-384x384.png` | ✅ App icon |
| 210KB | `.json` | `apps/web/package-lock.json` | ✅ Dependency lock file |
| 191KB | `.yaml` | `pnpm-lock.yaml` | ✅ Dependency lock file |
| 117KB | `.png` | `apps/web/public/icon-256x256.png` | ✅ App icon |
| 89KB | `.py` | `services/api/app/agent/orchestrator.py` | ✅ Core business logic |
| 69KB | `.png` | Multiple icon variants | ✅ App icons |
| 65KB | `.tsx` | `apps/web/src/components/MailChat.tsx` | ✅ Large UI component |

### Files That Should Be .gitignored

| Path | Reason |
|------|--------|
| `services/api/coverage.lcov` | Coverage report (regenerated on test) |
| `services/api/openapi-debug.json` | Debug artifact (can be regenerated) |
| Any files in `test-results/` | Playwright test outputs |
| Any files in `playwright-report/` | Test HTML reports |

---

## 3. Generated & Cache Folders

### Identified Cache Directories on Disk

**Total count**: 3,382 directories matching:
- `__pycache__/`
- `node_modules/`
- `.pytest_cache/`
- `.ruff_cache/`
- `dist/`
- `build/`
- `.next/`
- `coverage/`

### Git Tracking Status

✅ **Good News**: None of these appear to be committed to git (verified with `git ls-files` filter).

### .gitignore Assessment

**Current Status**: Need to verify root `.gitignore` explicitly includes:

```gitignore
# Python
__pycache__/
*.py[cod]
*.so
*.egg-info/
.pytest_cache/
.ruff_cache/
coverage.lcov
htmlcov/
.coverage

# Node
node_modules/
dist/
build/
.next/
pnpm-lock.yaml  # May want to track this

# Testing
.playwright/
playwright-report/
test-results/
*.spec.ts-snapshots/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Logs
*.log
npm-debug.log*

# Environment
.env
.env.local
.env.*.local

# Certificates
*.pem
*.crt
*.key
letsencrypt/

# Secrets
secrets/
*.secret
```

⚠️ **Action Required**: Verify and harden `.gitignore` in Phase 2.

---

## 4. Docker & Compose Audit

### Docker Compose Files Found

| File | Status | Purpose | Services |
|------|--------|---------|----------|
| `docker-compose.dev.api.yml` | ✅ Active | Dev API only | api, db, es, redis |
| `docker-compose.edge.yml` | ❓ Unclear | Edge deployment? | Unknown (needs inspection) |
| `docker-compose.hackathon.yml` | 🟡 Hackathon | Gemini/Datadog demo | Ollama, Datadog agent |
| `docker-compose.prod.override.yml` | ✅ Active | Prod overrides | Extends prod.yml |
| `docker-compose.prod.yml` | ✅ **PRIMARY PROD** | Full production stack | db, es, kibana, redis, api, web, nginx, prometheus, grafana, cloudflared, autofill, backfill |
| `docker-compose.tunnel.yml` | ✅ Active | Cloudflare Tunnel | cloudflared, tunnel config |
| `docker-compose.prod.yml.20251023-114511.bak` | ❌ **BACKUP FILE** | Delete or move to `/backup` | - |
| `docker-compose.prod.yml.backup` | ❌ **BACKUP FILE** | Delete or move to `/backup` | - |
| `docker-compose.tunnel.yml.backup` | ❌ **BACKUP FILE** | Delete or move to `/backup` | - |

### Services in docker-compose.prod.yml

**Current Production Stack**:
```
✅ db                       (postgres:16-alpine)
✅ elasticsearch            (8.13.4)
✅ kibana                   (8.13.4)
✅ redis                    (7-alpine)
✅ api                      (leoklemet/applylens-api:0.6.5-datadog)
✅ web                      (leoklemet/applylens-web:0.6.4)
✅ nginx                    (nginx:1.27-alpine)
🟡 prometheus               (prom/prometheus:v2.55.1)  # LEGACY - Datadog is primary
🟡 grafana                  (grafana/grafana:11.1.0)   # LEGACY - Datadog is primary
✅ cloudflared              (cloudflare/cloudflared:latest)
✅ autofill-aggregator      (python:3.11-slim)
✅ backfill                 (python:3.11-slim)
✅ agent-feedback-cron      (python:3.11-slim)
```

### Dockerfile Inventory

| File | Purpose | Status |
|------|---------|--------|
| `apps/web/Dockerfile` | Dev web build | ✅ Active |
| `apps/web/Dockerfile.prod` | Prod web build | ✅ Active |
| `services/api/Dockerfile` | Dev API build | ✅ Active |
| `services/api/Dockerfile.prod` | Prod API build | ✅ Active |

### Network Architecture

```
applylens-prod (main network)
├── db
├── elasticsearch
├── redis
├── api
├── web
├── nginx
├── prometheus (LEGACY)
├── grafana (LEGACY)
└── cloudflared

infra_net (external - shared Ollama)
└── ai-finance-agent-oss-clean-ollama-1
```

### Consolidation Opportunities

1. **Backup files**: Move `.bak` and `.backup` files to `/backup` or delete
2. **Edge compose**: Evaluate if `docker-compose.edge.yml` is still needed
3. **Hackathon compose**: Keep but document as temporary/demo only

---

## 5. Scripts & Tooling Inventory

### Scripts Directory (91 files)

#### Active Production Scripts (High Confidence)

| Script | Purpose | Last Referenced |
|--------|---------|-----------------|
| `build-and-tag.ps1` | Build Docker images | Production deployment |
| `build-prod-images.ps1` | Build prod images | Production deployment |
| `deploy-prod.ps1` | Deploy to production | Production deployment |
| `check-applylens-prod.ps1` | Health check prod | Monitoring |
| `prod-health-check.ps1` | Production health | Monitoring |
| `watch-prod-health.ps1` | Continuous health watch | Monitoring |
| `rollback.ps1` | Production rollback | Disaster recovery |
| `Verify-Deployment.ps1` | Post-deploy validation | CI/CD |
| `VerifySystem.ps1` | System verification | Ops |

#### Active Development Scripts

| Script | Purpose |
|--------|---------|
| `start-dev-api.ps1` | Start dev API server |
| `stop-dev-api.ps1` | Stop dev API server |
| `run-e2e-dev.ps1` | Run E2E tests locally |
| `quick-smoke.ps1` | Quick smoke test |
| `ci-smoke-test.ps1` | CI smoke test |

#### Cloudflare Tunnel Scripts (Active)

| Script | Purpose |
|--------|---------|
| `Quick-CloudflareSetup.ps1` | Setup CF tunnel |
| `cf-cache-tools.ps1` | Cache management |
| `cf-create-health-bypass-rule.ps1` | Health check bypass |
| `cf-dns-tools.ps1` | DNS management |
| `cf-nuclear-option.ps1` | Emergency cache purge |
| `cf-rules-inspect.ps1` | Inspect CF rules |
| `cf-verify-502.ps1` | Verify 502 fix |
| `Purge-CloudflareCache.ps1` | Cache purge |
| `Set-CloudflareCredentials.ps1` | CF auth setup |
| `setup-cloudflare-cache.sh` | Cache setup (Linux) |
| `Setup-CloudflareCache.ps1` | Cache setup (Windows) |
| `Verify-CloudflareCacheRules.ps1` | Verify cache rules |
| `get-edge-certificates.ps1` | Get SSL certs |
| `show-tunnel-connectors.ps1` | Show CF connectors |
| `monitor-tunnel-health.ps1` | Monitor tunnel |

#### Elasticsearch Scripts (Active)

| Script | Purpose |
|--------|---------|
| `create-es-api-key-enhanced.ps1` | Create ES API key |
| `create-es-api-key-minimal.ps1` | Minimal ES key |
| `create-es-api-key-minimal.sh` | Minimal ES key (Linux) |
| `create-es-api-key.ps1` | Standard ES key |
| `create-es-api-key.sh` | Standard ES key (Linux) |
| `es_reindex_v2.sh` | Reindex ES data |
| `reindex_to_pipeline_v2_simple.ps1` | Simple reindex |
| `reindex_to_pipeline_v2.ps1` | Full reindex |
| `setup-es-ilm.ps1` | ES lifecycle management |
| `setup-es-ilm.sh` | ES ILM (Linux) |
| `test_pipeline_v2_fixed.ps1` | Test pipeline |
| `test_pipeline_v2_queries.ps1` | Test queries |
| `validate_kibana_dataview.ps1` | Validate Kibana |

#### Testing Scripts (Active)

| Script | Purpose |
|--------|---------|
| `smoke_llm.ps1` | Test LLM endpoints |
| `smoke_llm.sh` | Test LLM (Linux) |
| `smoke_risk_advice.ps1` | Test risk advice |
| `smoke_test_assistant_phase3.ps1` | Test assistant |
| `smoke-applylens.ps1` | Full smoke test |
| `smoke-test-production.ps1` | Prod smoke test |
| `smoke-test.ps1` | Standard smoke |
| `test_assistant_endpoints.ps1` | Test assistant |
| `test-always-feature.ps1` | Test feature flags |
| `test-chat-streaming.ps1` | Test streaming |
| `test-chat.ps1` | Test chat |
| `test-phase1-endpoints.ps1` | Phase 1 tests |
| `test-phase2-endpoints.ps1` | Phase 2 tests |
| `test-phase6.ps1` | Phase 6 tests |
| `verify-api-routes.ps1` | Verify routes |
| `verify-hackathon.ps1` | Verify hackathon |
| `verify-oauth.ps1` | Verify OAuth |

#### Datadog/Hackathon Scripts (Active - Recent)

| Script | Purpose |
|--------|---------|
| `configure-datadog.ps1` | Datadog setup |
| `test-datadog-metrics.py` | Test metrics |
| `traffic_generator.py` | Generate load |

#### Legacy / Unclear Scripts

| Script | Status | Reason |
|--------|--------|--------|
| `BackfillCheck.ps1` | ❓ | 1KB - minimal script |
| `backfill-errors.log` | ❌ **LOG FILE** | Should not be in git! |
| `analyze_weights.py` | ❓ | ML model analysis? |
| `aws_secrets.sh` | 🟡 Legacy? | Using GCP now? |
| `gcp_secrets.sh` | ✅ Active | GCP secrets |
| `ci-smoke-es-email-v2.sh` | ❓ | Old CI script? |
| `ci-smoke-test.sh` | ❓ | Duplicate of .ps1? |
| `create-test-policy.ps1` | ❓ | Test artifact? |
| `deploy_email_risk_v3.sh` | ❓ | Old deployment |
| `deploy_email_risk_v31.sh` | ❓ | Old deployment |
| `deploy-edge.ps1` | ❓ | Edge deployment? |
| `deploy-today-panel.ps1` | ❓ | Specific feature deploy |
| `fix_pipeline_final.py` | ❓ | One-time fix? |
| `fix_pipeline_json.py` | ❓ | One-time fix? |
| `fix_pipeline_triple_quotes.py` | ❓ | One-time fix? |
| `generate_aes_key.py` | ❓ | Crypto utility |
| `generate_test_emails.py` | ✅ Active | Test data gen |
| `hackathon-start.ps1` | 🟡 Hackathon | Temporary |
| `keys.py` | ⚠️ | Crypto keys? Check content |
| `kibana-import.ps1` | ✅ Active | Kibana setup |
| `kibana-import.sh` | ❓ | Duplicate? |
| `phase2-all.ps1` | ❓ | Phase 2 deployment |
| `pre-deploy-check.ps1` | ✅ Active | Pre-deploy validation |
| `pre-deploy-check.sh` | ❓ | Linux version |
| `prometheus_alerts_v31.yml` | 🟡 Legacy | Prometheus config |
| `rotate_secret_aws.sh` | 🟡 Legacy? | AWS secrets |
| `rotate_secret_gcp.sh` | ✅ Active? | GCP secrets |
| `test_es_template.py` | ❓ | ES testing |
| `test-port-forwarding.ps1` | ❓ | Dev utility |
| `upload_pipeline.py` | ❓ | ES pipeline |

### Scripts Referenced in Documentation

**High Confidence Active**:
- `build-and-tag.ps1` - Mentioned in PRODUCTION_DEPLOYMENT.md
- `deploy-prod.ps1` - Core deployment script
- `Verify-Deployment.ps1` - Post-deploy checks
- Cloudflare scripts - Referenced in CLOUDFLARE_TOOLKIT_GUIDE.md
- Smoke test scripts - Referenced in TESTING.md

**Likely Legacy**:
- `deploy_email_risk_v*.sh` - Old feature deployment
- `fix_pipeline_*.py` - One-time migration fixes
- Phase-specific deploy scripts - May be superseded

---

## 6. Dead Code / Unused Modules (First Pass)

### Backend (services/api)

**Potentially Unused** (needs deeper analysis):

| Path | Reason | Confidence |
|------|--------|------------|
| `services/api/models/label_v1.joblib` | ML model - check if still used | Low |
| `services/api/openapi-debug.json` | Debug artifact | High |
| `services/api/prometheus/` | Directory - using Datadog now | Medium |
| `services/api/grafana/` | Directory - using Datadog now | Medium |

**Needs Import Analysis**:
- Old router files if Phase X refactors superseded them
- Deprecated schemas if new versions exist
- Test files for removed features

### Frontend (apps/web)

**Potentially Unused** (needs import graph):

| Pattern | Reason |
|---------|--------|
| Duplicate components in root `src/` vs `apps/web/src/` | Check if root is legacy |
| Old theme components if new theme system exists | Check MAILBOX_THEME_SYSTEM.md |
| Deprecated API client functions | Check if using new endpoints |

**Needs Investigation**:
- Root-level `src/`, `public/`, `tests/` directories
- Whether they're duplicates of `apps/web/*` or separate legacy code

### Chrome Extension

**Status**: Appears active and well-maintained.

---

## 7. Docs & Hackathon Artifacts

### Documentation Structure

**Total**: 95 markdown files in `/docs`

#### Major Documentation Categories

| Category | File Count | Status | Notes |
|----------|------------|--------|-------|
| Monitoring/Observability | ~15 | 🟡 **OVERLAPPING** | MONITORING_*.md, PROMETHEUS_*.md, AGENTS_OBSERVABILITY.md |
| Production/Deployment | ~12 | ✅ Active | PRODUCTION_*.md, DEPLOYMENT*.md, DEPLOY*.md |
| Testing | ~5 | ✅ Active | TESTING*.md, RUNNING_TESTS.md |
| Architecture | ~8 | ⚠️ **MAY CONFLICT** | ARCHITECTURE.md, APPLYLENS_ARCHITECTURE.md |
| Phase Implementation | ~15 | ❓ Historical | PHASE_*.md files |
| Feature-Specific | ~20 | ✅ Active | COMPANION_*.md, THREAD_*.md, etc. |
| Operations | ~10 | ✅ Active | OPS.md, ONCALL_HANDBOOK.md, SECURITY.md |
| Grafana Setup | ~5 | 🟡 Legacy | Grafana dashboard install guides |

#### Duplicate / Overlapping Documentation

**Monitoring Overlap** (🟡 Needs consolidation):
```
docs/MONITORING_AUTO_SETUP_COMPLETE.md (13,983 bytes)
docs/MONITORING_COMPLETE.md            (15,189 bytes)
docs/MONITORING_QUICKREF.md            ( 4,932 bytes)
docs/MONITORING_SETUP.md               (14,327 bytes)
docs/PROMETHEUS_METRICS.md             (10,806 bytes)
docs/METRICS_AND_DASHBOARDS.md         (19,283 bytes)
docs/AGENTS_OBSERVABILITY.md           (28,473 bytes)
docs/EXTENSION_API_OBSERVABILITY.md    ( 7,913 bytes)
```

**Recommendation**: Consolidate into:
- `OBSERVABILITY.md` - High-level overview + Datadog primary
- `OBSERVABILITY_LEGACY_PROMETHEUS.md` - Prometheus/Grafana for reference
- `OBSERVABILITY_METRICS.md` - Metric definitions

**Architecture Overlap** (⚠️ May conflict):
```
docs/ARCHITECTURE.md                   (19,693 bytes)
docs/APPLYLENS_ARCHITECTURE.md         (13,378 bytes)
hackathon/ARCHITECTURE.md              (13,701 bytes)
```

**Recommendation**:
- Keep `docs/ARCHITECTURE.md` as canonical
- Move `APPLYLENS_ARCHITECTURE.md` → `ARCHITECTURE_LEGACY_V1.md`
- Keep `hackathon/ARCHITECTURE.md` (hackathon-specific)

**Deployment Overlap**:
```
docs/DEPLOYMENT.md                     (14,201 bytes)
docs/DEPLOYMENT_STATUS.md              (10,119 bytes)
docs/DEPLOYMENT_VALIDATION_GUARDRAILS.md (6,930 bytes)
docs/PRODUCTION_DEPLOYMENT.md          (35,131 bytes)
docs/PRODUCTION_HANDBOOK.md            (15,199 bytes)
docs/QUICK_DEPLOY.md                   ( 5,302 bytes)
docs/DEPLOY_PROD.md                    ( 1,372 bytes)
docs/DEPLOY_PROD_APPLYLENS.md          ( 1,782 bytes)
```

**Recommendation**:
- `PRODUCTION_DEPLOYMENT.md` - Keep as primary (most comprehensive)
- `DEPLOY_PROD.md` + `DEPLOY_PROD_APPLYLENS.md` - Merge or delete (tiny files)
- `DEPLOYMENT_STATUS.md` - Archive (point-in-time snapshot)
- `QUICK_DEPLOY.md` - Keep (quick reference)

### Hackathon Directory

**Files**:
```
hackathon/ARCHITECTURE.md        (13,701 bytes) - Datadog/Gemini architecture
hackathon/DATADOG_SETUP.md       (22,410 bytes) - Datadog setup guide
hackathon/SEQUENCE_DIAGRAM.md    (15,187 bytes) - Flow diagrams
hackathon/TRAFFIC_GENERATOR.md   ( 6,625 bytes) - Traffic gen usage
```

**Status**: ✅ **Keep** - These are hackathon deliverables, well-organized, current.

### Legacy Documentation Candidates

| File | Reason | Action |
|------|--------|--------|
| `docs/PATCH_*.md` | Historical patch notes | Archive to `/docs/archive/patches/` |
| `docs/PHASE_*_IMPLEMENTATION_*.md` | Point-in-time snapshots | Archive to `/docs/archive/phases/` |
| `docs/*_FIX_*.md` | Incident postmortems | Keep or move to `/docs/incidents/` |
| `docs/*_COMPLETE.md` | Implementation completion docs | Archive (historical) |
| `docs/NEXT_STEPS_*.md` | Old roadmaps | Archive or delete if superseded |

### Grafana Setup Docs (🟡 Legacy - Datadog Primary)

```
docs/GRAFANA_SETUP.md
docs/install_grafana_plugin.ps1
docs/import_grafana_dashboard.ps1
docs/start_grafana_docker.ps1
docs/verify_grafana_setup.ps1
docs/test_dashboard_endpoints.ps1
docs/phase3_grafana_dashboard*.json
docs/phase4_grafana_dashboard.json
grafana/README.md
```

**Recommendation**: Move to `/docs/archive/grafana/` with note:
> "Grafana monitoring deprecated 2025-11. Datadog is now primary observability. Files kept for reference."

---

## 8. Prometheus/Grafana vs Datadog

### Current State

**Prometheus + Grafana**:
- ✅ Still running in `docker-compose.prod.yml`
- ✅ Scraping `/metrics` endpoint every 15s
- ✅ 6 alert rules loaded
- ✅ Grafana dashboards auto-provisioned
- 🟡 **BUT**: Datadog is now **primary observability** (as of hackathon implementation)

**Datadog**:
- ✅ Datadog agent running (`dd-agent` container)
- ✅ API instrumented with Datadog SDK
- ✅ Dashboard created programmatically (vap-jgg-r7t)
- ✅ SLOs configured (d22bff39b3365745bbe3cb7853eaa659)
- ✅ Monitors with incident auto-creation
- ✅ Automation scripts in `services/api/scripts/create_datadog_*.py`

### Infrastructure Files

**Prometheus Files** (🟡 Legacy but still active):
```
infra/prometheus/
├── prometheus.yml              - Scrape config
├── alerts.yml                  - Alert rules
└── agent_alerts.yml            - Agent alerts
services/api/prometheus/
└── agent_alerts.yml            - Duplicate?

scripts/prometheus_alerts_v31.yml - Legacy alert config
```

**Grafana Files** (🟡 Legacy):
```
infra/grafana/
└── provisioning/
    ├── datasources/prom.yml
    └── dashboards/
        ├── applylens.yml
        └── json/applylens-overview.json

grafana/
├── README.md
├── backfill-health-dashboard.json
└── provisioning/...

docs/phase*_grafana_dashboard.json
```

**Docker Compose Services** (🟡 Legacy):
```yaml
# docker-compose.prod.yml
prometheus:
  image: prom/prometheus:v2.55.1
  # Scraping API /metrics every 15s

grafana:
  image: grafana/grafana:11.1.0
  # Auto-provisioned dashboards
```

### Recommendation Matrix

| Component | Status | Recommendation |
|-----------|--------|----------------|
| **Prometheus container** | 🟡 Running | **Keep for now** - Still collecting metrics, may have historical data |
| **Grafana container** | 🟡 Running | **Keep for now** - May be useful for adhoc queries |
| **Prometheus scrape config** | ✅ Active | Keep - API still exposes `/metrics` |
| **Grafana dashboards** | 🟡 Legacy | Mark as legacy, document Datadog is primary |
| **Prometheus alert rules** | 🟡 Legacy | Review if duplicated in Datadog monitors |
| **Grafana setup docs** | 🟡 Legacy | Move to `/docs/archive/grafana/` |
| **Prometheus setup docs** | 🟡 Legacy | Consolidate into single reference doc |

### Decommission Plan (Future Phase)

**Not in this cleanup**, but document for later:

1. **Verify Datadog has all alerts** that Prometheus had
2. **Export historical Prometheus data** if needed
3. **Stop Prometheus + Grafana** services in docker-compose
4. **Archive configs** to `/infra/archive/prometheus-grafana/`
5. **Update docs** to reference Datadog exclusively

---

## 9. Sensitive Files & Security Concerns

### 🚨 CRITICAL: Files That Should NOT Be in Git

| Path | Issue | Action |
|------|-------|--------|
| `secrets/` | Directory name suggests secrets | **Verify contents, add to .gitignore, remove from git history** |
| `letsencrypt/` | SSL certificates | **Should not be in git** - add to .gitignore |
| `scripts/backfill-errors.log` | Log file committed | Delete, add `*.log` to .gitignore |
| `scripts/keys.py` | May contain crypto keys | **Inspect immediately** |
| Any `*.pem`, `*.key`, `*.crt` files | SSL/SSH keys | Check if committed |

### Action Required (Phase 2)

1. **Inspect `secrets/` directory** immediately
2. **Check for committed secrets** in git history:
   ```bash
   git log --all --full-history -- "secrets/*"
   git log --all --full-history -- "*.pem"
   git log --all --full-history -- "*.key"
   ```
3. **Use `git filter-repo`** to remove from history if found
4. **Rotate any exposed secrets**

### .gitignore Hardening Needed

Add these patterns:
```gitignore
# Secrets & Certificates
secrets/
*.secret
*.pem
*.key
*.crt
*.p12
letsencrypt/
.env*.local

# Logs
*.log
logs/
```

---

## 10. .gitignore Current State

**Status**: Cannot read `.gitignore` file directly (outside workspace).

**Evidence from file tracking**:
- ✅ `node_modules/` not tracked (0 files in git)
- ✅ `__pycache__/` not tracked (0 files in git)
- ❓ `coverage.lcov` IS tracked (296KB file)
- ❓ `openapi-debug.json` IS tracked (467KB file)
- ❓ `*.log` files tracked (e.g., `backfill-errors.log`)

**Recommended additions** (Phase 2):

```gitignore
# Testing artifacts
coverage.lcov
htmlcov/
.coverage
playwright-report/
test-results/
*.spec.ts-snapshots/

# Build artifacts
*.pyc
__pycache__/
.pytest_cache/
.ruff_cache/
dist/
build/
.next/

# Debug artifacts
openapi-debug.json
*-debug.json

# Logs
*.log
logs/

# Sensitive
secrets/
*.secret
letsencrypt/
*.pem
*.key
*.crt
```

---

## 11. Backup Files & Duplicates

### Committed Backup Files

| File | Action |
|------|--------|
| `docker-compose.prod.yml.20251023-114511.bak` | Delete or move to `/backup` |
| `docker-compose.prod.yml.backup` | Delete or move to `/backup` |
| `docker-compose.tunnel.yml.backup` | Delete or move to `/backup` |

### Potential Duplicates (Need Investigation)

| Pattern | Files | Investigation |
|---------|-------|---------------|
| Root `src/` vs `apps/web/src/` | Unknown | Check if duplicate frontend code |
| Root `public/` vs `apps/web/public/` | Unknown | Check if duplicate assets |
| Root `tests/` vs `apps/web/tests/` | Unknown | Check if duplicate tests |
| `.ps1` vs `.sh` script pairs | Many | Some legitimate (cross-platform), some may be obsolete |

---

## 12. Recommendations Summary

### Phase 2 Immediate Actions (New Branch: `chore/repo-cleanup-phase2`)

1. **Security** (🚨 HIGHEST PRIORITY):
   - Inspect `secrets/` directory
   - Check for committed secrets in git history
   - Remove sensitive files from tracking
   - Harden `.gitignore`

2. **Cleanup Low-Hanging Fruit**:
   - Delete `.bak` and `.backup` docker-compose files
   - Remove `coverage.lcov` from tracking
   - Remove `openapi-debug.json` from tracking
   - Remove `scripts/backfill-errors.log`
   - Add to `.gitignore` to prevent re-commit

3. **Legacy Scripts Organization**:
   - Create `/scripts/legacy/` directory
   - Move obviously outdated scripts with README
   - Add comments to ambiguous scripts indicating status

4. **Documentation Consolidation**:
   - Create `/docs/archive/` with subdirectories:
     - `/docs/archive/grafana/` - Legacy Grafana setup
     - `/docs/archive/phases/` - Phase implementation snapshots
     - `/docs/archive/patches/` - Historical patches
   - Consolidate overlapping monitoring docs
   - Add deprecation notices to legacy docs

5. **Docker Compose Cleanup**:
   - Document which compose files are active vs legacy
   - Add comments to `docker-compose.prod.yml` marking Prometheus/Grafana as legacy

### Phase 3 Actions (Git History Cleanup)

1. **Analyze Large Blobs**:
   ```bash
   git rev-list --objects --all |
     git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize) %(rest)' |
     sed -n 's/^blob //p' |
     sort --numeric-sort --key=2 |
     tail -n 50
   ```

2. **Create Cleanup Plan Document**:
   - List blobs to remove
   - Document `git filter-repo` commands
   - Outline team coordination steps

---

## 13. Success Criteria

After Phase 2 cleanup, the repo should:

- ✅ No secrets or credentials in git
- ✅ No build artifacts or cache directories tracked
- ✅ Clear separation of active vs legacy components
- ✅ Documented migration path from Prometheus to Datadog
- ✅ Consolidated documentation with clear canonical sources
- ✅ Hardened `.gitignore` preventing future junk commits
- ✅ Legacy files archived with explanatory READMEs

---

## Appendix A: File Count by Directory

```
Directory                File Count   Notes
---------                ----------   -----
docs/                    95           Many overlapping files
scripts/                 91           Mix of active and legacy
apps/web/src/            ~100+        Frontend components
services/api/app/        ~80+         Backend modules
infra/                   ~30          Docker configs, monitoring
hackathon/               4            Recent, well-organized
.github/                 ~10          CI/CD workflows
```

---

## Appendix B: Next Steps

1. **Review this report** with team
2. **Prioritize security cleanup** (secrets, certificates)
3. **Create Phase 2 branch** and begin safe cleanup
4. **Do NOT force-push** or rewrite `main` without explicit approval

---

**End of Phase 1 Analysis Report**
