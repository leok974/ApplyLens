# ApplyLens Repository Architecture Reorganization Plan

**Status**: Phase 4 - In Progress
**Created**: 2025-11-27
**Goal**: Clean and normalize repo architecture for human and agent-friendly navigation

## Overview

This document tracks the reorganization of the ApplyLens repository to create a clear, intentional folder structure that serves both human developers and AI agents (LLMs, MCP servers, DevDiag, etc.).

### Guiding Principles

1. **Every file has a clear home** - No random root clutter
2. **Folders grouped by responsibility** - apps, services, infra, docs, scripts
3. **Agent-friendly** - Tools can traverse by "type" (docs/, scripts/cli/, etc.)
4. **Safe migrations** - Using `git mv`, updating all references
5. **Preserve production** - No breaking changes to deployed systems

---

## Current State Inventory

### Top-Level Directories (Before)

```
.github/              # CI/CD workflows, PR templates
.pytest_cache/        # Python test cache (gitignored)
.ruff_cache/          # Python linter cache (gitignored)
.venv/                # Python virtual environment (gitignored)
.vscode/              # VS Code settings
analytics/            # ❓ Unknown - needs inspection
apps/                 # ✅ Frontend applications
  └── extension-applylens/  # Browser extension
backup/               # ❓ Temporary backup folder?
cloudflared/          # ❓ Should be in infra/
deploy/               # ❓ Should be in scripts/ops/ or infra/
docs/                 # ✅ Documentation (needs subfoldering)
grafana/              # ❓ Should be in infra/monitoring/
hackathon/            # ✅ Hackathon-specific assets
infra/                # ✅ Infrastructure & deployment
  ├── cloudflared/
  ├── docker/
  ├── nginx/
  ├── scripts/
  └── tunnel/
kibana/               # ❓ Should be in infra/monitoring/
letsencrypt/          # ❓ Should be in infra/certs/ or secrets/
monitoring/           # ❓ Should be in infra/monitoring/
node_modules/         # Package dependencies (gitignored)
playwright-report/    # Test reports (should be gitignored)
runbooks/             # ❓ Should be in docs/runbooks/
scripts/              # ✅ Scripts (needs categorization)
  ├── legacy/         # ✅ Already organized
  └── [various]
secrets/              # ❓ Should these be in infra/secrets/?
services/             # ✅ Backend services
  └── api/            # FastAPI backend
test-results/         # Test artifacts (should be gitignored)
tests/                # ❓ Root-level tests? Should be in services/api/tests?
tools/                # ❓ Should be in scripts/cli/?
```

### Root-Level Files (Audit)

#### Core Configuration (Keep at Root)
- `README.md` ✅
- `LICENSE` ✅
- `.gitignore` ✅
- `.gitleaks.toml` ✅
- `.markdownlint.json` ✅
- `.pre-commit-config.yaml` ✅
- `codecov.yml` ✅
- `package.json` ✅
- `package-lock.json` ✅
- `pnpm-lock.yaml` ✅
- `pnpm-workspace.yaml` ✅
- `playwright.config.ts` ✅
- `Makefile` ✅
- `applylens.code-workspace` ✅

#### Environment Files (Keep at Root)
- `.env*` files (multiple) ✅

#### Documentation Files (Move to docs/)
- `AGENT_V2_DEPLOYMENT.md` → `docs/archive/agents/`
- `AGENT_V2_FRONTEND_INTEGRATION.md` → `docs/archive/agents/`
- `AGENTS.md` → `docs/architecture/`
- `BUILD_METADATA.md` → `docs/architecture/`
- `CHANGELOG.md` → ✅ Keep at root
- `COMPANION_IMPLEMENTATION.md` → `docs/archive/companion/`
- `DELIVERY_COMPLETE.md` → `docs/archive/`
- `DEV_API_SETUP.md` → `docs/runbooks/`
- `DOCKER_SETUP_COMPLETE.md` → `docs/archive/`
- `DOCS_CLEANUP_CLASSIFICATION.md` → `docs/archive/`
- `E2E_SEEDING_IMPLEMENTATION_COMPLETE.md` → `docs/archive/e2e/`
- `E2E_TEST_SEEDING_SYSTEM.md` → `docs/architecture/testing/`
- `E2E_TESTS_PHASE_5_2.md` → `docs/archive/e2e/`
- `EDGE_DEPLOYMENT_GUIDE.md` → `docs/runbooks/`
- `EDGE_QUICKSTART.md` → `docs/runbooks/`
- `FINAL_IMPLEMENTATION_CHECKLIST.md` → `docs/archive/`
- `HACKATHON.md` → `docs/hackathon/`
- `MAILBOX_AGENT_V2_PRODUCTION.md` → `docs/archive/agents/`
- `MAILBOX_AGENT_V2_SKELETONS.md` → `docs/archive/agents/`
- `MAILBOX_AGENT_V2.md` → `docs/archive/agents/`
- `PHASE_5_2_E2E_COMPLETE.md` → `docs/archive/e2e/`
- `PHASE_5_2_SUMMARY_FEEDBACK.md` → `docs/archive/e2e/`
- `PHASE_5_COMPLETE.md` → `docs/archive/`
- `PHASE_5_PRODUCTION_DEPLOYMENT.md` → `docs/archive/`
- `PLAYWRIGHT_TEST_RUNNER_README.md` → `docs/architecture/testing/`
- `PR_DESCRIPTION_THREAD_VIEWER_V1.md` → `docs/archive/`
- `PR_THREAD_VIEWER.md` → `docs/archive/`
- `TEST_EXECUTION_SUMMARY.md` → `docs/archive/e2e/`
- `TEST_PLAN_THREAD_VIEWER_PHASE_4.md` → `docs/archive/e2e/`
- `TEST_PLAN_THREAD_VIEWER_PHASE_5.md` → `docs/archive/e2e/`
- `THREAD_VIEWER_E2E_FINAL_REPORT.md` → `docs/archive/e2e/`
- `THREAD_VIEWER_E2E_IMPLEMENTATION.md` → `docs/archive/e2e/`
- `THREAD_VIEWER_E2E_TESTS.md` → `docs/archive/e2e/`
- `THREAD_VIEWER_ROADMAP.md` → `docs/archive/`
- `UNIFIED_EDGE_QUICKSTART.md` → `docs/runbooks/`
- `VERIFICATION_CHECKLIST.md` → `docs/archive/`
- `.release-notes-v0.5.0.md` → `docs/releases/`
- `DEPLOYMENT_TODAY_PANEL.md` → `docs/archive/`

#### Scripts (Move to scripts/)
- `applylens.ps1` → `scripts/cli/`
- `build-prod.ps1` → `scripts/ops/`
- `build-prod.sh` → `scripts/ops/`
- `deploy-prod.ps1` → `scripts/ops/`
- `deploy-prod.sh` → `scripts/ops/`
- `DEPLOY_v0.4.26.sh` → `scripts/legacy/`
- `deploy-web-v0.4.21.sh` → `scripts/legacy/`
- `gitleaks.ps1` → `scripts/ci/`
- `launch-applylens-workday.ps1` → `scripts/cli/`
- `playwright.test-run.ps1` → `scripts/ci/`
- `setup-production.sh` → `scripts/ops/`
- `test_draft_reply.ps1` → `scripts/legacy/test/`
- `test_ollama_integration.ps1` → `scripts/legacy/test/`
- `test-ml-endpoints.ps1` → `scripts/legacy/test/`
- `test-profile-endpoints.ps1` → `scripts/legacy/test/`
- `verify-oauth-setup.ps1` → `scripts/ops/`

#### Test Files (Move to appropriate test folders)
- `test_ollama.py` → `services/api/tests/integration/`
- `test_rag.py` → `services/api/tests/integration/`
- `test_reply_filter.py` → `services/api/tests/integration/`
- `test_sort_functionality.py` → `services/api/tests/integration/`

#### Data/Config Files (Move to appropriate locations)
- `nginx-simple.conf` → `infra/nginx/examples/`
- `openapi.json` → `services/api/docs/` or `docs/api/`
- `owner_email_mapping.json` → `services/api/config/` or delete if obsolete
- `update_owner_email.json` → `services/api/config/` or delete if obsolete
- `receipts_test.csv` → `services/api/tests/fixtures/` or delete
- `test_*.json` → `services/api/tests/fixtures/`
- `MAILBOX_AGENT_V2_STATUS.json` → `docs/archive/agents/` or delete

#### Temporary/Audit Files (Delete or Move to docs/archive/)
- `all_markdown_files.txt` → Delete (regenerable)
- `api-logs.txt` → Delete (temporary)
- `deployment-backup.txt` → Delete (temporary)
- `large_blobs_analysis.txt` → Delete or → `docs/archive/audits/`
- `sensitive_files_audit.txt` → Delete or → `docs/archive/audits/`
- `-w` → Delete (looks like a typo/artifact)
- `.e2e-config.txt` → Delete or move to config/

---

## Target Repository Structure

```
ApplyLens/
├── .github/                    # CI/CD, workflows, PR templates
├── apps/                       # Frontend applications
│   └── extension-applylens/   # Browser extension
├── services/                   # Backend services
│   └── api/                   # FastAPI backend
│       ├── app/
│       ├── tests/
│       ├── docs/              # API-specific docs (OpenAPI, etc.)
│       └── config/            # Service-specific config
├── infra/                      # Infrastructure & deployment
│   ├── docker/                # Docker compose files, Dockerfiles
│   ├── nginx/                 # Nginx configs
│   ├── cloudflare/            # Cloudflare tunnel configs
│   ├── monitoring/            # Grafana, Kibana, Prometheus
│   ├── certs/                 # Let's Encrypt, SSL certs
│   └── scripts/               # Infrastructure automation
├── scripts/                    # Development & operational scripts
│   ├── cli/                   # Developer utilities
│   ├── ci/                    # CI/CD scripts (called by workflows)
│   ├── ops/                   # Operations & deployment
│   └── legacy/                # Historical/deprecated scripts
├── docs/                       # Documentation
│   ├── architecture/          # System design, architecture
│   │   ├── testing/          # Test architecture
│   │   └── agents/           # Agent/LLM architecture
│   ├── runbooks/              # Operational runbooks
│   ├── audits/                # Cleanup audits, analysis
│   │   ├── REPO_HISTORY_CLEANUP_PLAN.md
│   │   ├── OBSERVABILITY_STACK_PLAN.md
│   │   └── GITHUB_WORKFLOWS_AUDIT.md
│   ├── hackathon/             # Hackathon-specific docs
│   ├── releases/              # Release notes
│   ├── api/                   # API documentation
│   └── archive/               # Historical/completed docs
│       ├── agents/
│       ├── companion/
│       ├── e2e/
│       └── phases/
├── hackathon/                  # Hackathon-specific code & assets
├── tests/                      # Integration tests (if repo-wide)
├── tools/                      # Development tools (if needed)
├── config files               # Root config (.gitignore, package.json, etc.)
└── README.md, LICENSE, CHANGELOG.md
```

---

## File Move Mapping

### Phase 4.1: Documentation Reorganization

#### Create new doc structure
```bash
mkdir -p docs/architecture/testing
mkdir -p docs/architecture/agents
mkdir -p docs/runbooks
mkdir -p docs/audits
mkdir -p docs/hackathon
mkdir -p docs/releases
mkdir -p docs/api
mkdir -p docs/archive/agents
mkdir -p docs/archive/companion
mkdir -p docs/archive/e2e
mkdir -p docs/archive/phases
mkdir -p docs/archive/audits
```

#### Move documentation files
```bash
# Architecture docs
git mv AGENTS.md docs/architecture/
git mv BUILD_METADATA.md docs/architecture/
git mv E2E_TEST_SEEDING_SYSTEM.md docs/architecture/testing/
git mv PLAYWRIGHT_TEST_RUNNER_README.md docs/architecture/testing/

# Runbooks
git mv DEV_API_SETUP.md docs/runbooks/
git mv EDGE_DEPLOYMENT_GUIDE.md docs/runbooks/
git mv EDGE_QUICKSTART.md docs/runbooks/
git mv UNIFIED_EDGE_QUICKSTART.md docs/runbooks/

# Hackathon
git mv HACKATHON.md docs/hackathon/
# Move runbooks/HACKATHON*.md if they exist

# Releases
git mv .release-notes-v0.5.0.md docs/releases/v0.5.0.md

# Archive - Agents
git mv AGENT_V2_DEPLOYMENT.md docs/archive/agents/
git mv AGENT_V2_FRONTEND_INTEGRATION.md docs/archive/agents/
git mv MAILBOX_AGENT_V2_PRODUCTION.md docs/archive/agents/
git mv MAILBOX_AGENT_V2_SKELETONS.md docs/archive/agents/
git mv MAILBOX_AGENT_V2.md docs/archive/agents/
git mv MAILBOX_AGENT_V2_STATUS.json docs/archive/agents/

# Archive - Companion
git mv COMPANION_IMPLEMENTATION.md docs/archive/companion/

# Archive - E2E
git mv E2E_SEEDING_IMPLEMENTATION_COMPLETE.md docs/archive/e2e/
git mv E2E_TESTS_PHASE_5_2.md docs/archive/e2e/
git mv PHASE_5_2_E2E_COMPLETE.md docs/archive/e2e/
git mv PHASE_5_2_SUMMARY_FEEDBACK.md docs/archive/e2e/
git mv TEST_EXECUTION_SUMMARY.md docs/archive/e2e/
git mv TEST_PLAN_THREAD_VIEWER_PHASE_4.md docs/archive/e2e/
git mv TEST_PLAN_THREAD_VIEWER_PHASE_5.md docs/archive/e2e/
git mv THREAD_VIEWER_E2E_FINAL_REPORT.md docs/archive/e2e/
git mv THREAD_VIEWER_E2E_IMPLEMENTATION.md docs/archive/e2e/
git mv THREAD_VIEWER_E2E_TESTS.md docs/archive/e2e/

# Archive - Phases
git mv DELIVERY_COMPLETE.md docs/archive/phases/
git mv DEPLOYMENT_TODAY_PANEL.md docs/archive/phases/
git mv DOCKER_SETUP_COMPLETE.md docs/archive/phases/
git mv DOCS_CLEANUP_CLASSIFICATION.md docs/archive/phases/
git mv FINAL_IMPLEMENTATION_CHECKLIST.md docs/archive/phases/
git mv PHASE_5_COMPLETE.md docs/archive/phases/
git mv PHASE_5_PRODUCTION_DEPLOYMENT.md docs/archive/phases/
git mv PR_DESCRIPTION_THREAD_VIEWER_V1.md docs/archive/phases/
git mv PR_THREAD_VIEWER.md docs/archive/phases/
git mv THREAD_VIEWER_ROADMAP.md docs/archive/phases/
git mv VERIFICATION_CHECKLIST.md docs/archive/phases/

# Archive - Audits (if needed)
# git mv large_blobs_analysis.txt docs/archive/audits/ (decide if keep)
# git mv sensitive_files_audit.txt docs/archive/audits/ (decide if keep)
```

### Phase 4.2: Scripts Reorganization

#### Create script structure
```bash
mkdir -p scripts/cli
mkdir -p scripts/ci
mkdir -p scripts/ops
mkdir -p scripts/legacy/test
```

#### Move scripts
```bash
# CLI tools
git mv applylens.ps1 scripts/cli/
git mv launch-applylens-workday.ps1 scripts/cli/

# CI scripts
git mv gitleaks.ps1 scripts/ci/
git mv playwright.test-run.ps1 scripts/ci/

# Ops scripts
git mv build-prod.ps1 scripts/ops/
git mv build-prod.sh scripts/ops/
git mv deploy-prod.ps1 scripts/ops/
git mv deploy-prod.sh scripts/ops/
git mv setup-production.sh scripts/ops/
git mv verify-oauth-setup.ps1 scripts/ops/

# Legacy scripts
git mv DEPLOY_v0.4.26.sh scripts/legacy/
git mv deploy-web-v0.4.21.sh scripts/legacy/
git mv test_draft_reply.ps1 scripts/legacy/test/
git mv test_ollama_integration.ps1 scripts/legacy/test/
git mv test-ml-endpoints.ps1 scripts/legacy/test/
git mv test-profile-endpoints.ps1 scripts/legacy/test/
```

### Phase 4.3: Infrastructure Reorganization

#### Consolidate infra folders
```bash
mkdir -p infra/monitoring/grafana
mkdir -p infra/monitoring/kibana
mkdir -p infra/certs
mkdir -p infra/docker

# Move top-level infra folders
git mv grafana/* infra/monitoring/grafana/ (if not empty)
git mv kibana/* infra/monitoring/kibana/ (if not empty)
git mv letsencrypt/* infra/certs/ (if appropriate)
git mv monitoring/* infra/monitoring/ (if not already in infra/)

# Move config files
git mv nginx-simple.conf infra/nginx/examples/
git mv docker-compose.*.yml infra/docker/ (or keep at root, decide)
```

### Phase 4.4: Services Reorganization

#### Move test files to services
```bash
mkdir -p services/api/tests/integration
mkdir -p services/api/tests/fixtures
mkdir -p services/api/docs
mkdir -p services/api/config

# Move Python test files
git mv test_ollama.py services/api/tests/integration/
git mv test_rag.py services/api/tests/integration/
git mv test_reply_filter.py services/api/tests/integration/
git mv test_sort_functionality.py services/api/tests/integration/

# Move test fixtures
git mv test_*.json services/api/tests/fixtures/
git mv receipts_test.csv services/api/tests/fixtures/ (or delete)

# Move API docs
git mv openapi.json services/api/docs/

# Move config files (if still needed)
# git mv owner_email_mapping.json services/api/config/ (or delete)
# git mv update_owner_email.json services/api/config/ (or delete)
```

### Phase 4.5: Cleanup

#### Delete temporary/generated files
```bash
git rm -w
git rm all_markdown_files.txt
git rm api-logs.txt
git rm deployment-backup.txt
# Decide on:
# - large_blobs_analysis.txt
# - sensitive_files_audit.txt
# - .e2e-config.txt
```

#### Consolidate or remove top-level folders
```bash
# Evaluate and potentially move/remove:
# - analytics/ → infra/monitoring/analytics/ or delete
# - backup/ → delete (temporary)
# - cloudflared/ → infra/cloudflare/ (merge with existing)
# - deploy/ → scripts/ops/ or infra/
# - runbooks/ → docs/runbooks/ (merge)
# - tools/ → scripts/cli/ or keep separate
# - tests/ → services/api/tests/ or keep for integration tests
```

---

## Path Updates Required

After moving files, update references in:

### 1. README.md
- Update links to moved documentation
- Update "Repository Structure" section (if exists)

### 2. CI Workflows (.github/workflows/*)
- Update script paths in workflow files
- Search for old paths and update

### 3. Documentation Cross-Links
- Search all .md files for broken links
- Update relative paths

### 4. Scripts
- Update any hardcoded paths in scripts
- Update README files in script folders

### 5. Docker & Compose Files
- Update volume mounts if needed
- Update COPY paths in Dockerfiles

### 6. VS Code Workspace
- Update `applylens.code-workspace` folder paths if needed

---

## Validation Steps

After each phase:

1. **Run smoke tests**:
   ```bash
   pwsh scripts/smoke-applylens.ps1
   ```

2. **Check CI**:
   - Verify workflows still work
   - Check for path errors

3. **Test builds**:
   ```bash
   docker compose -f infra/docker/docker-compose.prod.yml config
   ```

4. **Search for broken links**:
   ```bash
   rg "docs/AGENT" -t md  # Should find no old paths
   rg "scripts/applylens.ps1" -t md
   ```

---

## Implementation Checklist

- [ ] Phase 4.1: Documentation reorganization
  - [ ] Create new doc folders
  - [ ] Move architecture docs
  - [ ] Move runbooks
  - [ ] Move hackathon docs
  - [ ] Move archive docs
  - [ ] Update README links
  - [ ] Update doc cross-links
- [ ] Phase 4.2: Scripts reorganization
  - [ ] Create script folders
  - [ ] Move CLI scripts
  - [ ] Move CI scripts
  - [ ] Move ops scripts
  - [ ] Move legacy scripts
  - [ ] Update CI workflow paths
  - [ ] Create scripts/README.md
- [ ] Phase 4.3: Infrastructure consolidation
  - [ ] Consolidate monitoring folders
  - [ ] Move certs folder
  - [ ] Update docker-compose references
- [ ] Phase 4.4: Services organization
  - [ ] Move test files
  - [ ] Move fixtures
  - [ ] Move API docs
  - [ ] Update import paths
- [ ] Phase 4.5: Cleanup
  - [ ] Delete temp files
  - [ ] Evaluate questionable folders
  - [ ] Remove empty directories
- [ ] Validation
  - [ ] Run smoke tests
  - [ ] Verify CI workflows
  - [ ] Test Docker builds
  - [ ] Check for broken links
- [ ] Documentation
  - [ ] Update README with new structure
  - [ ] Mark this plan as complete
  - [ ] Create PR

---

## Notes & Decisions

### Decisions Made
- Keep `CHANGELOG.md` at root (conventional location)
- Keep docker-compose files at root for now (common pattern, can move later)
- Archive all "PHASE_*" docs (historical context preserved)
- Keep `package.json` and workspace files at root (multi-package repo)

### Questions to Resolve
- [ ] What is in `analytics/`? Move to infra/monitoring?
- [ ] What is in `deploy/`? Consolidate with scripts/ops?
- [ ] Keep `tools/` separate or merge into `scripts/cli/`?
- [ ] Keep `tests/` at root for integration tests or move to services?
- [ ] What's in `backup/`? Temporary, safe to delete?

---

## Status

**Current Phase**: Planning Complete ✅
**Next Step**: Begin Phase 4.1 - Documentation Reorganization

---

*This plan follows the repository cleanup methodology from previous phases and maintains backward compatibility while improving organization.*
