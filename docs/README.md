# ApplyLens Documentation

**Last Updated**: 2025-11-27
**Audience**: Contributors, maintainers, operators, and AI agents

This documentation has been reorganized for clarity and ease of navigation. All docs are categorized into **core** (essential current docs), **agents** (AI agent instructions), **future** (plans and RFCs), and **archive** (historical records).

---

> **🤖 For AI Agents & Automation Tools**
> See [agents/AGENT_READING_GUIDE.md](agents/AGENT_READING_GUIDE.md) for the recommended reading order and task-specific documentation paths.


## 📚 Quick Navigation

### New to ApplyLens?
1. [Overview](core/OVERVIEW.md) - What is ApplyLens
2. [Getting Started](core/GETTING_STARTED.md) - Quick start guide
3. [Local Dev Setup](core/LOCAL_DEV_SETUP.md) - Set up your development environment
4. [Architecture](core/ARCHITECTURE.md) - System architecture overview

### Deploying to Production?
1. [Deployment Guide](core/DEPLOYMENT.md) - Production deployment
2. [Deployment Guardrails](core/DEPLOYMENT_GUARDRAILS.md) - Safety checks
3. [Production Handbook](core/PRODUCTION_HANDBOOK.md) - Operations guide
4. [On-Call Handbook](core/ONCALL_HANDBOOK.md) - Incident response

### Looking for Runbooks?
- [Runbooks Index](core/runbooks/) - Operational procedures
- [Incident Playbooks](core/playbooks/) - Emergency response
- [Incident History](core/incidents/) - Past incident resolutions

---

## 📁 Documentation Structure

```
docs/
├── core/              # Essential current documentation
├── agents/            # AI agent instructions & protocols
├── future/            # Future plans & RFCs
└── archive/           # Historical docs & completed work
```

---

## 🎯 Core Documentation

### Getting Started
- [Overview](core/OVERVIEW.md) - ApplyLens one-pager and core flows
- [Getting Started](core/GETTING_STARTED.md) - Quick start for new developers
- [Local Dev Setup](core/LOCAL_DEV_SETUP.md) - Local environment setup
- [Development Guide](core/DEVELOPMENT.md) - Development workflows
- [Contributing](core/CONTRIBUTING.md) - How to contribute
- [Security Policy](core/SECURITY.md) - Security guidelines

### Architecture & Infrastructure
- [Architecture](core/ARCHITECTURE.md) - System architecture (backend, frontend, data)
- [Infrastructure](core/INFRASTRUCTURE.md) - Production infrastructure overview
- [Build Metadata](core/BUILD_METADATA.md) - Build and versioning metadata
- [Component Contracts](core/COMPONENT_CONTRACTS.md) - Component interfaces

### Deployment & Operations
- [Deployment](core/DEPLOYMENT.md) - Production deployment guide
- [Deployment Guardrails](core/DEPLOYMENT_GUARDRAILS.md) - Deployment safety checks
- [Operations](core/OPERATIONS.md) - Day-to-day operations
- [Production Handbook](core/PRODUCTION_HANDBOOK.md) - Production operations guide
- [On-Call Handbook](core/ONCALL_HANDBOOK.md) - On-call procedures and incident response

### Monitoring & Observability
- [Monitoring](core/MONITORING.md) - Monitoring setup and Datadog dashboards
- [Testing Overview](core/TESTING_OVERVIEW.md) - Testing strategy, E2E tests, CI/CD

### Integrations
- [Gmail Setup](core/GMAIL_SETUP.md) - Gmail API integration
- [OAuth Setup](core/OAUTH_SETUP.md) - OAuth configuration
- [Ollama](core/OLLAMA.md) - Ollama LLM integration
- [LedgerMind](core/LEDGERMIND.md) - LedgerMind integration
- [Cloudflare](core/CLOUDFLARE.md) - Cloudflare setup and configuration

### Tools & Utilities
- [CLI Tools](core/CLI_TOOLS.md) - CLI tools reference
- [API Route Policy](core/API_ROUTE_POLICY.md) - API standards and conventions

### API Documentation
- [API Reference](core/api/REFERENCE.md) - API endpoints reference
- [API Auth](core/api/AUTH.md) - CSRF and M2M authentication
- [API Runbooks](core/api/runbooks/) - API-specific runbooks

### Runbooks & Playbooks
- [Runbooks](core/runbooks/) - Operational procedures
- [Playbooks](core/playbooks/) - Incident response playbooks
- [Incident History](core/incidents/) - Past incident resolutions

---

## 🤖 Agent Documentation

Documentation specifically for AI agents, protocols, and MCP integrations.

- [Quickstart](agents/QUICKSTART.md) - Agent quick reference
- [Companion Protocol](agents/COMPANION_PROTOCOL.md) - Chrome extension protocol
- [Bandit Learning](agents/BANDIT_LEARNING.md) - Bandit/learning system
- [Active Learning](agents/ACTIVE_LEARNING.md) - Active learning system
- [DevDiag Integration](agents/DEVDIAG_INTEGRATION.md) - DevDiag MCP integration
- [Deploy Metaprompt](agents/DEPLOY_METAPROMPT.md) - Copilot deployment instructions
- [Agents Observability](agents/AGENTS_OBSERVABILITY.md) - Agent monitoring
- [GitHub Agents](agents/github/) - GitHub-specific agent configs

---

## 🔮 Future Plans & RFCs

Roadmaps, audits, and future implementation plans.

- [Repo History Cleanup](future/REPO_HISTORY_CLEANUP.md) - Git history cleanup plan
- [Workflows Audit](future/WORKFLOWS_AUDIT.md) - CI/CD audit & recommendations
- [Observability Migration](future/OBSERVABILITY_MIGRATION.md) - Datadog migration plan

---

## 🗄️ Archive

Historical documentation, completed phases, and resolved incidents.

- [Audits](archive/audits/) - Historical audits and cleanup records
- [Incidents](archive/incidents/) - Resolved incident documentation
- [Migrations](archive/migrations/) - Database migration records
- [Completed Phases](archive/phases/) - Phase completion docs

---

## 🎒 Component Documentation

Component-specific docs remain in their original locations:

- [Analytics](../analytics/README.md)
- [Web App](../apps/web/README.md)
- [Extension](../apps/extension-applylens/README.md)
- [API](../services/api/README.md)
- [Scripts](../scripts/README.md)
- [Hackathon](../hackathon/)

---

## 📖 Documentation Principles

1. **Core** = Essential, current, frequently referenced
2. **Agents** = Machine-readable protocols and instructions
3. **Future** = Plans, RFCs, not yet implemented
4. **Archive** = Historical, completed, or superseded

---

*For questions or improvements to this documentation, see [Contributing](core/CONTRIBUTING.md).*
