# Agent Reading Guide

**Last Updated**: 2025-11-27
**Audience**: AI agents, automation tools, MCP servers, and other programmatic assistants

---

## Overview

This guide helps **AI agents and automated tools** navigate the ApplyLens documentation efficiently. The docs are organized into four main categories, each serving a specific purpose for agents performing different tasks.

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

**Goal**: Deploy, monitor, maintain, and scale the production system.

**Read first** (in order):
1. [`docs/core/DEPLOYMENT.md`](../core/DEPLOYMENT.md) – Production deployment procedures
2. [`docs/core/INFRASTRUCTURE.md`](../core/INFRASTRUCTURE.md) – Infrastructure overview (Cloudflare, Docker, etc.)
3. [`docs/core/MONITORING.md`](../core/MONITORING.md) – Metrics, Grafana, alerts
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
| "How does ApplyLens work?" | `docs/core/OVERVIEW.md`, `docs/core/ARCHITECTURE.md` |
| "How do I run it locally?" | `docs/core/LOCAL_DEV_SETUP.md`, `docs/core/GETTING_STARTED.md` |
| "How do I deploy to production?" | `docs/core/DEPLOYMENT.md`, `docs/core/DEPLOYMENT_GUARDRAILS.md` |
| "What tests exist?" | `docs/core/TESTING_OVERVIEW.md`, `docs/core/testing/` |
| "How do I fix [specific issue]?" | `docs/core/runbooks/`, `docs/core/incidents/` |
| "How should agents interact with the extension?" | `docs/agents/COMPANION_PROTOCOL.md` |
| "What's the learning loop algorithm?" | `docs/agents/BANDIT_LEARNING.md`, `docs/agents/ACTIVE_LEARNING.md` |
| "What's planned for the future?" | `docs/future/` |
| "Why was [past decision] made?" | `docs/archive/` |

---

## Tips for Efficient Agent Reading

1. **Start broad, then narrow**: Begin with `OVERVIEW.md` and `ARCHITECTURE.md`, then dive into component-specific docs.
2. **Follow the hierarchy**: `core/` → `agents/` → `future/` → `archive/` (in that order).
3. **Check README files**: Each major folder has a `README.md` or index doc for navigation.
4. **Use search strategically**: Search for error messages in `runbooks/` and `incidents/` first.
5. **Respect the "archive" boundary**: Don't use archived docs to understand the current system—they represent **past state**, not present.

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
