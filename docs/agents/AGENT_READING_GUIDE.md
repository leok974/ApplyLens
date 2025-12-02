# Agent Reading Guide

**Last Updated**: 2025-12-02
**Audience**: AI agents, automation tools, MCP servers, and other programmatic assistants

---

## Overview

This guide helps **AI agents and automated tools** navigate the ApplyLens documentation efficiently. The docs are organized into four main categories, each serving a specific purpose for agents performing different tasks.

---

## ⚠️ CRITICAL: Deployment & Infrastructure Rules

**BEFORE deploying, testing, or changing infrastructure, read these MANDATORY rules:**

### Deployment Golden Rules

1. ✅ **ALWAYS use `scripts/deploy-prod.ps1`** for production deployments
2. ✅ **ALWAYS read [`docs/core/DEPLOYMENT_CHEATSHEET.md`](../core/DEPLOYMENT_CHEATSHEET.md)** FIRST when dealing with deployments
3. ✅ **NEVER invent new deployment commands** – prefer existing scripts
4. ✅ **NEVER manually restart containers** without documenting why in logs/incidents
5. ✅ **DO NOT touch Cloudflare tunnel config** unless explicitly requested by user
6. ✅ **DO NOT change nginx routing** without reviewing `infra/nginx/conf.d/` and getting approval
7. ✅ **ALWAYS check `docker-compose.prod.yml`** for canonical service definitions before making changes

### Deployment Quick Reference (Read This First)

When asked to deploy, troubleshoot, or modify infrastructure, **read these in exact order**:

1. **[`docs/core/DEPLOYMENT_CHEATSHEET.md`](../core/DEPLOYMENT_CHEATSHEET.md)** ← START HERE (2 min read)
   - Quick commands & mental model
   - Common fixes for 502/500/401 errors
   - Where to look when confused

2. **[`docs/core/DEPLOYMENT.md`](../core/DEPLOYMENT.md)** ← Full guide (10 min read)
   - Complete dev/prod deployment workflows
   - Environment variables reference
   - Troubleshooting procedures

3. **`docker-compose.prod.yml`** ← Canonical truth
   - Service definitions
   - Environment variables
   - Network topology

4. **`scripts/deploy-prod.ps1`** ← Actual commands
   - What really happens during deploy
   - Build metadata flow
   - Verification steps

**Example Bad Behavior** (DO NOT DO THIS):
```powershell
# ❌ BAD: Inventing new docker run commands
docker run -d --name applylens-api-prod ...

# ❌ BAD: Manually restarting without checking docs
docker restart applylens-api-prod

# ❌ BAD: Guessing environment variables
-e GOOGLE_CLIENT_ID=... # Wrong! Should be APPLYLENS_GOOGLE_CLIENT_ID
```

**Example Good Behavior** (DO THIS):
```powershell
# ✅ GOOD: Read cheatsheet first
cat docs/core/DEPLOYMENT_CHEATSHEET.md

# ✅ GOOD: Use existing script
.\scripts\deploy-prod.ps1 -Version "0.7.12" -Build

# ✅ GOOD: Check docker-compose for env vars
cat docker-compose.prod.yml | Select-String "APPLYLENS_"
```

---

## Documentation Hierarchy (Priority Order)

### 1. `docs/core/` – Primary Source of Truth

**When to read**: Always start here for understanding the current, live system.

**What's inside**:
- System overview & architecture
- How to run locally and in production
- Testing & CI workflows
- Runbooks, playbooks, and incident histories
- API reference and authentication
- Component contracts and interfaces

**Key principle**: This folder contains the **canonical, up-to-date documentation** for how ApplyLens works right now.

---

### 2. `docs/agents/` – Protocols & Contracts for AI Agents

**When to read**: When you need to understand how to interact with ApplyLens components or follow established agent protocols.

**What's inside**:
- Extension/Companion protocol (how the browser extension communicates)
- Bandit/learning loop documentation (active learning system)
- Agent observability and API contracts
- Special message formats and agent APIs
- Deployment metaprompts and agent quickstarts

**Key principle**: This folder defines **how agents should behave** when working with ApplyLens.

---

### 3. `docs/future/` – Future Work & RFCs

**When to read**: When researching planned features, understanding roadmap direction, or evaluating "what should we build next?"

**What's inside**:
- RFCs (Request for Comments)
- Migration plans
- Future architecture proposals
- Audit reports for planned refactors

**Key principle**: This folder describes **what will be**, not what is. Do NOT use this to understand the current production system.

---

### 4. `docs/archive/` – Historical Records

**When to read**: Only when explicitly asked to research history, understand past decisions, or review completed migrations.

**What's inside**:
- Completed phase documentation
- Resolved incidents
- Migration records
- Deprecated audits and retrospectives

**Key principle**: This folder is **historical only**. Safe to ignore unless specifically researching past work.

---

## Task-Specific Reading Guides

### For Deployment & Infrastructure Agents

**Goal**: Deploy services, fix production issues, modify infrastructure, troubleshoot container problems.

**MANDATORY FIRST READS** (in exact order):
1. **[`docs/core/DEPLOYMENT_CHEATSHEET.md`](../core/DEPLOYMENT_CHEATSHEET.md)** ← **READ THIS FIRST** (2 min)
2. **[`docs/core/DEPLOYMENT.md`](../core/DEPLOYMENT.md)** ← Full deployment guide (10 min)
3. **`docker-compose.prod.yml`** ← Canonical service definitions
4. **`scripts/deploy-prod.ps1`** ← Actual deploy script (source of truth)

**Then read**:
5. [`docs/core/INFRASTRUCTURE.md`](../core/INFRASTRUCTURE.md) – Infrastructure overview
6. [`docs/core/CLOUDFLARE.md`](../core/CLOUDFLARE.md) – Tunnel & DNS setup
7. [`docs/core/ONCALL_HANDBOOK.md`](../core/ONCALL_HANDBOOK.md) – Incident response

**Common deployment tasks → where to look**:

| Task | Read |
|------|------|
| Deploy new version | `DEPLOYMENT_CHEATSHEET.md` → `scripts/deploy-prod.ps1` |
| Fix 502 Bad Gateway | `DEPLOYMENT.md` Section 4 (Common Issues table) |
| Fix 500 Server Error | `DEPLOYMENT.md` Section 8 (Troubleshooting) |
| Fix 401 Unauthorized | `DEPLOYMENT.md` Section 5 (Environment Variables) |
| Add environment variable | `docker-compose.prod.yml` + `DEPLOYMENT.md` Section 5 |
| Change container config | `docker-compose.prod.yml` + `scripts/deploy-prod.ps1` |

**CRITICAL deployment restrictions**:
- ❌ **DO NOT** manually `docker run` containers – use `scripts/deploy-prod.ps1`
- ❌ **DO NOT** edit nginx config without reviewing `infra/nginx/conf.d/`
- ❌ **DO NOT** restart Cloudflare tunnel – it runs as separate service
- ❌ **DO NOT** change service ports without updating nginx + Cloudflare config
- ✅ **DO** use `docker-compose.prod.yml` as single source of truth
- ✅ **DO** document any manual container restarts in incidents/

---

### For Debugging/Triage Agents

**Goal**: Diagnose issues, understand system behavior, troubleshoot failures.

**Read first** (in order):
1. [`docs/core/OVERVIEW.md`](../core/OVERVIEW.md) – High-level system architecture
2. [`docs/core/ARCHITECTURE.md`](../core/ARCHITECTURE.md) – Detailed component architecture
3. [`docs/core/runbooks/`](../core/runbooks/) – Operational runbooks for common issues
4. [`docs/core/MONITORING.md`](../core/MONITORING.md) – Metrics, alerts, and dashboards
5. [`docs/core/incidents/`](../core/incidents/) – Past incident resolutions and patterns

**When to read agents/**:
- [`docs/agents/DEVDIAG_INTEGRATION.md`](DEVDIAG_INTEGRATION.md) – If using DevDiag for diagnostics
- [`docs/agents/AGENTS_OBSERVABILITY.md`](AGENTS_OBSERVABILITY.md) – Understanding agent telemetry

---

### For Code-Change Agents

**Goal**: Implement features, fix bugs, refactor code, understand codebase structure.

**Read first** (in order):
1. [`docs/core/ARCHITECTURE.md`](../core/ARCHITECTURE.md) – Component boundaries and data flow
2. [`docs/core/COMPONENT_CONTRACTS.md`](../core/COMPONENT_CONTRACTS.md) – Interface contracts
3. [`docs/core/DEVELOPMENT.md`](../core/DEVELOPMENT.md) – Development workflows and patterns
4. [`docs/core/TESTING_OVERVIEW.md`](../core/TESTING_OVERVIEW.md) – Testing strategy and E2E setup
5. [`docs/core/CONTRIBUTING.md`](../core/CONTRIBUTING.md) – Contribution guidelines

**When to read agents/**:
- [`docs/agents/COMPANION_PROTOCOL.md`](COMPANION_PROTOCOL.md) – If modifying the browser extension
- [`docs/agents/BANDIT_LEARNING.md`](BANDIT_LEARNING.md) – If working on the learning/recommendation system
- [`docs/agents/QUICKSTART.md`](QUICKSTART.md) – Quick reference for agent-aware development

**When to read future/**:
- [`docs/future/`](../future/) – Check if there's an RFC for the feature you're implementing

---

### For Observability/Ops Agents

**Goal**: Monitor, maintain, and scale the production system.

**Read first** (in order):
1. [`docs/core/DEPLOYMENT_CHEATSHEET.md`](../core/DEPLOYMENT_CHEATSHEET.md) – Quick reference
2. [`docs/core/DEPLOYMENT.md`](../core/DEPLOYMENT.md) – Full deployment guide
3. [`docs/core/MONITORING.md`](../core/MONITORING.md) – Metrics, Datadog, alerts
4. [`docs/core/PRODUCTION_HANDBOOK.md`](../core/PRODUCTION_HANDBOOK.md) – Production operations guide
5. [`docs/core/ONCALL_HANDBOOK.md`](../core/ONCALL_HANDBOOK.md) – Incident response procedures

**When to read runbooks/**:
- [`docs/core/runbooks/`](../core/runbooks/) – Step-by-step operational procedures
- [`docs/core/playbooks/`](../core/playbooks/) – Emergency response playbooks

**When to read agents/**:
- [`docs/agents/API_OBSERVABILITY.md`](API_OBSERVABILITY.md) – API observability patterns
- [`docs/agents/DEPLOY_METAPROMPT.md`](DEPLOY_METAPROMPT.md) – Deployment automation guidelines

---

## Quick Reference: Where to Find What

| What you need | Where to look |
|---------------|---------------|
| **"How do I deploy?"** | **[`docs/core/DEPLOYMENT_CHEATSHEET.md`](../core/DEPLOYMENT_CHEATSHEET.md)** ← START HERE |
| **"Container won't start / 502 / 500 error"** | **[`docs/core/DEPLOYMENT.md`](../core/DEPLOYMENT.md)** Section 4 & 8 |
| "How does ApplyLens work?" | `docs/core/OVERVIEW.md`, `docs/core/ARCHITECTURE.md` |
| "How do I run it locally?" | `docs/core/LOCAL_DEV_SETUP.md`, `docs/core/GETTING_STARTED.md` |
| "What environment variables exist?" | `docs/core/DEPLOYMENT.md` Section 5, `docker-compose.prod.yml` |
| "What tests exist?" | `docs/core/TESTING_OVERVIEW.md`, `docs/core/testing/` |
| "How do I fix [specific issue]?" | `docs/core/runbooks/`, `docs/core/incidents/` |
| "How should agents interact with the extension?" | `docs/agents/COMPANION_PROTOCOL.md` |
| "What's the learning loop algorithm?" | `docs/agents/BANDIT_LEARNING.md`, `docs/agents/ACTIVE_LEARNING.md` |
| "What's planned for the future?" | `docs/future/` |
| "Why was [past decision] made?" | `docs/archive/` |

---

## Tips for Efficient Agent Reading

1. **For deployment tasks**: Start with `DEPLOYMENT_CHEATSHEET.md`, not anywhere else
2. **Start broad, then narrow**: Begin with `OVERVIEW.md` and `ARCHITECTURE.md`, then dive into component-specific docs
3. **Follow the hierarchy**: `core/` → `agents/` → `future/` → `archive/` (in that order)
4. **Check README files**: Each major folder has a `README.md` or index doc for navigation
5. **Use search strategically**: Search for error messages in `runbooks/` and `incidents/` first
6. **Respect the "archive" boundary**: Don't use archived docs to understand the current system—they represent **past state**, not present
7. **Never guess commands**: If unsure, read `DEPLOYMENT.md` or `docker-compose.prod.yml`, don't invent commands

---

## For Humans Reading This

This guide is optimized for AI agents, but humans can benefit too. If you're onboarding or trying to understand the docs structure, follow the same hierarchy:

1. **Start with `docs/core/`** for the current system
2. **Refer to `docs/agents/`** if you're building agent integrations
3. **Check `docs/future/`** for planned work
4. **Ignore `docs/archive/`** unless researching history

For a human-friendly index, see [`docs/README.md`](../README.md).

---

**Questions or suggestions?** Open an issue or PR to improve this guide.
