# ApplyLens

[![API Tests](https://github.com/leok974/ApplyLens/actions/workflows/api-tests.yml/badge.svg)](https://github.com/leok974/ApplyLens/actions/workflows/api-tests.yml)
[![Docs Checks](https://github.com/leok974/ApplyLens/actions/workflows/docs-check.yml/badge.svg)](https://github.com/leok974/ApplyLens/actions/workflows/docs-check.yml)
[![codecov](https://codecov.io/gh/leok974/ApplyLens/branch/polish/graph/badge.svg)](https://codecov.io/gh/leok974/ApplyLens)

Agentic job-inbox MVP: classify job/search emails, extract key facts, and populate a tracker.


## 📖 Documentation

**Start here**: [docs/README.md](docs/README.md) - Complete documentation index

### Quick Links
- **[Overview](docs/core/OVERVIEW.md)** - What is ApplyLens
- **[Getting Started](docs/core/GETTING_STARTED.md)** - Quick start guide
- **[Architecture](docs/core/ARCHITECTURE.md)** - System architecture
- **[Deployment](docs/core/DEPLOYMENT.md)** - Production deployment
- **[Testing](docs/core/TESTING_OVERVIEW.md)** - Testing & E2E guide

### Agent-Aware Development

This repo is set up for specialist "agents" (human or AI) to work safely on different parts of ApplyLens.

- **[Agent Quickstart](docs/agents/QUICKSTART.md)** - Agent overview and protocols
- **[Agent Architecture](docs/agents/ARCHITECTURE.md)** - Agent system design
- **GitHub Agent Guides** ([docs/agents/github/](docs/agents/github/)):
  - [api-agent.md](docs/agents/github/api-agent.md) – FastAPI, Gmail ingest, risk scoring, tracker APIs
  - [ui-agent.md](docs/agents/github/ui-agent.md) – React/Vite, Tailwind + shadcn/ui, dark theme
  - [test-agent.md](docs/agents/github/test-agent.md) – Vitest, Playwright, Pytest, contract tests
  - [search-agent.md](docs/agents/github/search-agent.md) – Elasticsearch mappings, boosts, suggest
  - [docs-agent.md](docs/agents/github/docs-agent.md) – Runbooks, architecture, deploy docs
  - [dev-deploy-agent.md](docs/agents/github/dev-deploy-agent.md) – Docker dev, smoke tests, deploys
  - [security-agent.md](docs/agents/github/security-agent.md) – Auth, SSRF/risk policy, secrets

When using GitHub Copilot or other assistants, instruct them to follow the agent guides and protocols.


## 📁 Repository Organization

### Top-Level Structure
```
ApplyLens/
├── apps/                   # Frontend applications
├── services/               # Backend services (API, workers)
├── infra/                  # Infrastructure & deployment
├── docs/                   # Documentation
├── scripts/                # Development & operational scripts
├── hackathon/              # Hackathon-specific assets
└── tests/                  # Integration tests
```

### Documentation Structure
All documentation is now organized under `docs/` with clear categorization:

> **🤖 For AI assistants and tools**, see [`docs/agents/AGENT_READING_GUIDE.md`](docs/agents/AGENT_READING_GUIDE.md) for the recommended reading order.

- **`docs/core/`** - Essential current documentation
  - `docs/core/runbooks/` - Operational procedures
  - `docs/core/playbooks/` - Incident response playbooks
  - `docs/core/incidents/` - Incident history & resolutions
  - `docs/core/api/` - API documentation & runbooks
  - `docs/core/testing/` - Test architecture & guides
  - `docs/core/analytics/` - Analytics & ML documentation
- **`docs/agents/`** - AI agent instructions & protocols
  - `docs/agents/github/` - GitHub-specific agent configs
  - `docs/agents/case-studies/` - Agent implementation case studies
- **`docs/future/`** - Future plans, RFCs, audits
- **`docs/archive/`** - Historical & legacy documentation
  - `docs/archive/audits/` - Historical audits & cleanup records
  - `docs/archive/incidents/` - Resolved incidents
  - `docs/archive/migrations/` - Database migration records
  - `docs/archive/phases/` - Phase completion docs
  - `docs/archive/agents/` - Legacy agent implementations
  - `docs/archive/companion/` - Companion feature archives
  - `docs/archive/e2e/` - E2E test archives
  - `docs/archive/patches/` - Historical patches

See [docs/README.md](docs/README.md) for complete documentation index.

### Scripts Organization
- **`scripts/cli/`** - Developer command-line tools
- **`scripts/ci/`** - CI/CD workflow scripts
- **`scripts/ops/`** - Operations & deployment scripts
- **`scripts/legacy/`** - Archived scripts (historical reference)
  - `scripts/legacy/test/` - Legacy test scripts

See `scripts/README.md` for detailed script documentation.

### Services & Apps
- **`services/api/`** - FastAPI backend
  - `services/api/docs/` - OpenAPI specs & API documentation
  - `services/api/tests/` - Unit & integration tests
  - `services/api/tests/fixtures/` - Test data & fixtures
- **`apps/extension-applylens/`** - Browser extension

### Infrastructure
- **`infra/docker/`** - Docker compose files
- **`infra/nginx/`** - Nginx configurations
- **`infra/cloudflare/`** - Cloudflare tunnel configs
- **`infra/monitoring/`** - Observability stack (Datadog, Grafana)

### Recent Cleanup
- ✅ **Phase 4 (Nov 2025)**: Reorganized 82 files into structured folders (scripts/, infra/, docs/)
- ✅ **Phase 5 (Nov 2025)**: Streamlined documentation - organized 157 docs into core/, agents/, future/, archive/
  - Architecture docs → `docs/architecture/`
  - Runbooks → `docs/runbooks/`
  - Scripts → `scripts/{cli,ci,ops,legacy}/`
  - Tests → `services/api/tests/`
  - API docs → `services/api/docs/`
- ✅ **Cleaned root directory** - removed 15+ temporary/obsolete files
- ✅ **Consolidated infrastructure** - docker-compose → `infra/docker/`, nginx → `infra/nginx/`
- ✅ **Updated tooling** - Fixed pre-commit hooks for new paths
- 📋 See `docs/REPO_ARCHITECTURE_REORG_PLAN.md` for full details

### Previous Cleanup (Phase 2 - Nov 2025)
- ✅ Removed ~800KB of tracked artifacts
- ✅ Organized 19 legacy scripts → `scripts/legacy/`
- ✅ Archived 27 docs → `docs/archive/`
- 📋 See `docs/REPO_CLEANUP_PHASE2_SUMMARY.md` for details

### Phase 3 Planning (Future Work)
See planning documents for future cleanup initiatives:
- **[Git History Cleanup Plan](docs/REPO_HISTORY_CLEANUP_PLAN.md)** - Safe git filter-repo strategy for removing large artifacts from history
- **[Observability Stack Migration](docs/OBSERVABILITY_STACK_PLAN.md)** - Prometheus/Grafana → Datadog decommissioning roadmap
## 🎯 Features

✨ **Gmail Integration** - OAuth 2.0 authentication and automated email backfill
🏷️ **Smart Labeling** - Automatic detection of interviews, offers, rejections, and more
🔍 **Advanced Search** - Full-text search with synonym support and recency boosting
💡 **Autocomplete** - Real-time suggestions with "did you mean" spell correction
📊 **Analytics Dashboard** - Kibana visualizations for job search insights
📧 **Inbox Management** - Filter by label, pagination, and bulk sync

## Gmail Integration Setup

ApplyLens now supports **Gmail OAuth authentication** with intelligent email classification!

### Quick Start

1. **Create Google OAuth Credentials:**
   - Follow the detailed guide in [`GMAIL_SETUP.md`](./GMAIL_SETUP.md)
   - Save your `google.json` to `infra/secrets/`

2. **Configure Environment:**

   ```bash
   cp infra/.env.example infra/.env
   # Edit infra/.env and set OAUTH_STATE_SECRET to a random string
   ```

3. **Start Services:**

   ```bash
   docker compose -f infra/docker-compose.yml up -d
   ```

4. **Connect Gmail:**
   - Visit <http://localhost:8003/auth/google/login>
   - Grant permissions
   - You'll be redirected to the Inbox page

5. **Sync Your Emails:**
   - Click "Sync 60 days" in the Inbox page
   - Or use the API: `curl -X POST "http://localhost:8003/gmail/backfill?days=60&user_email=your@gmail.com"`

### Automatic Email Labeling

Emails are automatically labeled based on content:

- 📅 **interview** - Interview invitations, phone screens, onsite visits
- 🎉 **offer** - Job offers and offer letters
- ❌ **rejection** - Rejection notifications
- ✅ **application_receipt** - Application confirmations
- 📰 **newsletter_ads** - Promotional emails and newsletters

### API Endpoints

```bash
# OAuth Flow
GET  /auth/google/login        # Start OAuth
GET  /auth/google/callback     # OAuth callback

# Gmail Operations
GET  /gmail/status             # Check connection status
GET  /gmail/inbox              # Get paginated emails
POST /gmail/backfill           # Sync emails from Gmail

# Search with label filters
GET  /search?q=interview&label_filter=interview
GET  /suggest?q=interv         # Autocomplete suggestions
```text

For complete documentation, see [`GMAIL_SETUP.md`](./GMAIL_SETUP.md).

## 🤖 Phase-2: Intelligent Email Categorization

ApplyLens now includes **ML-powered email categorization** with automated workflows!

### Features

- **Two-Stage Labeling**: High-precision rules (95% confidence) + ML fallback
- **4 Categories**: newsletter, promo, recruiting, bill
- **Profile Analytics**: Sender analysis, category trends, time-series volume
- **Automated Workflows**: Three automation options (Makefile, npm, PowerShell)
- **TF-IDF + Logistic Regression**: Trained on balanced weak labels

### Quick Start (Choose Your Platform)

```bash
# Unix/Linux/Mac → Makefile
make phase2-all

# Cross-Platform → npm
npm install && npm run phase2:all

# Windows → PowerShell
.\scripts\phase2-all.ps1
```text

### What It Does

1. **Export**: Streams emails from ES, applies rules, exports balanced JSONL
2. **Train**: TF-IDF + Logistic Regression on 12.5k samples (89% accuracy)
3. **Apply**: Labels all emails with category, confidence, expires_at

### API Endpoints

```bash
# Labeling
POST /labels/apply              # Label all emails
POST /labels/apply-batch        # Label filtered emails
GET  /labels/stats              # Aggregated statistics

# Profile Analytics
GET  /profile/summary           # Category distribution + top senders
GET  /profile/senders           # Sender list (filterable by category)
GET  /profile/categories/{cat}  # Category details
GET  /profile/time-series       # Email volume trends
```text

### Documentation

- **Quick Reference**: [`PHASE_2_QUICK_REF.md`](./PHASE_2_QUICK_REF.md) - One-page cheat sheet
- **Automation Guide**: [`PHASE_2_AUTOMATION.md`](./PHASE_2_AUTOMATION.md) - Full automation docs
- **API Reference**: [`PHASE_2_IMPLEMENTATION.md`](./PHASE_2_IMPLEMENTATION.md) - Complete API docs
- **Workflow Details**: [`PHASE_2_WORKFLOW.md`](./PHASE_2_WORKFLOW.md) - Step-by-step guide

## 🛡️ Phase 4: Agent Governance & Safety

ApplyLens now includes **enterprise-grade governance** for autonomous agents with policy enforcement, approval workflows, and execution guardrails!

### Key Features

- **🔐 Policy Engine**: Priority-based authorization with allow/deny rules
- **💰 Budget Tracking**: Track resource usage (time, ops, cost) per agent execution
- **✅ Approval Workflows**: Human-in-the-loop for high-risk actions with HMAC signatures
- **🚧 Execution Guardrails**: Pre/post validation at execution boundaries
- **📊 Audit Trails**: Complete logging of policy decisions and approvals

### Architecture

```
Agent Request → Policy Engine → Guardrails → [Approval?] → Executor → Post-Validation
                     ↓              ↓              ↓           ↓              ↓
                 Allow/Deny    Validate Params  Human Gate  Execute     Check Results
```

### Policy Engine

Define fine-grained policies for agent actions:

```python
from app.policy import PolicyRule

# High-priority deny for dangerous operations
PolicyRule(
    id="deny-large-diffs",
    agent="knowledge_update",
    action="apply",
    conditions={"changes_count": 1000},  # >= 1000 changes
    effect="deny",
    reason="Large diffs require manual review",
    priority=100
)

# Conditional approval for quarantine
PolicyRule(
    id="allow-quarantine-low-risk",
    agent="inbox_triage",
    action="quarantine",
    conditions={"risk_score": 70},  # < 70
    effect="allow",
    priority=50
)
```

**Evaluation Logic:**
- Rules evaluated by **priority** (highest first)
- **Deny overrides allow** for same priority
- Conditions support numeric comparisons and exact matches
- Default: allow if no rules match

### Budget Tracking

Set resource limits per agent:

```python
from app.policy import Budget

Budget(
    ms=30000,        # Max 30 seconds
    ops=100,         # Max 100 operations
    cost_cents=50    # Max $0.50 estimated cost
)
```

Tracked automatically during execution:
- `elapsed_ms`: Execution time
- `ops_count`: API calls, queries, operations
- `cost_cents_used`: Estimated cloud API costs

### Approval Workflows

Require human approval for high-risk actions:

```python
# 1. Agent requests approval
POST /api/v1/approvals
{
    "agent": "knowledge_update",
    "action": "apply",
    "context": {"file": "config.yaml", "changes_count": 1500},
    "reason": "Large configuration change"
}

# 2. Human reviews and signs
POST /api/v1/approvals/{id}/approve
{
    "decision": "approved",
    "signature": "<HMAC-SHA256-signature>",
    "comment": "Verified changes are safe"
}

# 3. Agent executes with approval
POST /api/v1/agents/execute
{
    "plan": {...},
    "approval_id": "appr_123"
}
```

**Security Features:**
- **HMAC-SHA256 signatures** prevent tampering
- **Expiration timestamps** (default 1 hour)
- **Audit logging** of all decisions
- **Replay protection** via signature verification

### Execution Guardrails

Automatic validation at execution boundaries:

**Pre-Execution (Hard Fail):**
- ✅ Policy compliance check
- ✅ Required parameters present
- ✅ Approval verification (if required)
- ❌ Blocks execution on violation

**Post-Execution (Soft Fail):**
- ✅ Result structure validation
- ✅ Resource metric validation (ops, cost)
- ⚠️ Logs warnings (action already executed)

```python
# Example: Quarantine requires email_id
GuardrailViolation: Missing required parameter 'email_id' for action 'quarantine'

# Example: Invalid result
GuardrailViolation: Result must be a dict, got <class 'str'>
```

### API Endpoints

```bash
# Policy Management
GET  /api/v1/policy              # Get current policy
PUT  /api/v1/policy              # Update policy rules

# Approvals
POST /api/v1/approvals           # Request approval
GET  /api/v1/approvals           # List approvals (filterable)
GET  /api/v1/approvals/{id}      # Get approval details
POST /api/v1/approvals/{id}/approve   # Approve/reject
POST /api/v1/approvals/{id}/verify    # Verify signature

# Agent Execution (with guardrails)
POST /api/v1/agents/execute      # Execute with policy checks
POST /api/v1/agents/plan         # Generate execution plan
```

### Configuration

Set policy enforcement level:

```bash
# Environment variables
POLICY_ENFORCEMENT=strict    # strict | permissive | disabled
APPROVAL_REQUIRED=true       # Require approvals for deny rules
APPROVAL_EXPIRY_SECONDS=3600 # 1 hour default
HMAC_SECRET=<your-secret>    # For approval signatures
```

### Testing

Phase 4 includes **78 comprehensive tests** with 100% coverage:

```bash
# Run all Phase 4 tests
pytest tests/test_policy_engine.py      # 30 policy tests
pytest tests/test_approvals_api.py      # 25 approval tests
pytest tests/test_executor_guardrails.py # 23 guardrail tests

# Coverage: policy 100%, approvals high, guardrails 100%
```

### Documentation

- **[Policy Management Runbook](./docs/runbooks/POLICY_MANAGEMENT.md)** - Creating and managing policies
- **[Approval Workflows Runbook](./docs/runbooks/APPROVAL_WORKFLOWS.md)** - Request and verify approvals
- **[Guardrails Configuration](./docs/runbooks/GUARDRAILS_CONFIG.md)** - Tuning validation rules
- **[Troubleshooting Guide](./docs/runbooks/PHASE4_TROUBLESHOOTING.md)** - Common issues and solutions

### Use Cases

**1. Knowledge Base Updates**
- Deny large diffs (>1000 changes) without approval
- Allow small edits automatically

## 🧪 Phase 5: Intelligence & Evaluation

ApplyLens now includes a **comprehensive evaluation system** for measuring and improving agent quality, security, and reliability!

### Key Features

- **📊 Offline Evaluation**: Test agents against golden tasks with multi-dimensional scoring
- **🔴 Online Monitoring**: Real-time production metrics and telemetry
- **🛡️ Red Team Testing**: Adversarial testing for security and robustness
- **💰 Budget Gates**: Quality thresholds that block regressions in CI/CD
- **📈 Intelligence Reports**: Weekly automated reports with trend analysis
- **📉 Prometheus/Grafana**: Real-time dashboards and alerting

### Architecture

```
┌──────────────────────────────────────────────────────────────┐
│              Agent Evaluation System                         │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  Offline Harness          Online Evaluator                  │
│  ┌──────────────┐        ┌──────────────┐                   │
│  │ Golden Tasks │        │  Production  │                   │
│  │ (32 tasks)   │        │   Metrics    │                   │
│  └──────┬───────┘        └──────┬───────┘                   │
│         │                       │                            │
│         └───────┬───────────────┘                            │
│                 │                                            │
│         ┌───────▼─────────┐                                 │
│         │  Judge Pipeline │                                 │
│         │  • Correctness  │                                 │
│         │  • Relevance    │                                 │
│         │  • Safety       │                                 │
│         │  • Efficiency   │                                 │
│         └───────┬─────────┘                                 │
│                 │                                            │
│         ┌───────▼─────────┐                                 │
│         │   Invariants    │                                 │
│         │  • No PII leak  │                                 │
│         │  • Valid format │                                 │
│         │  • Compliance   │                                 │
│         └───────┬─────────┘                                 │
│                 │                                            │
│         ┌───────▼─────────────────┐                         │
│         │   Metrics & Storage     │                         │
│         │  • AgentMetricsDaily    │                         │
│         │  • Prometheus           │                         │
│         │  • Budget Gates         │                         │
│         └─────────────────────────┘                         │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### Offline Evaluation (Eval Harness)

Test agents against **32 golden tasks** across 4 categories:

```bash
# Run evaluation suite
python -m app.eval.runner --agent inbox_triage

# Export results
python -m app.eval.runner --agent inbox_triage --export results.jsonl

# Use specific judges
python -m app.eval.runner --agent inbox_triage --judge correctness
```

**Golden Tasks**: Reference examples with known correct outputs
**Judges**: Multi-dimensional scoring (correctness, relevance, safety, efficiency)
**Invariants**: Boolean checks (no PII leak, valid format, compliance)

### Online Evaluation

Monitor production performance in real-time:

```python
from app.eval.telemetry import OnlineEvaluator

evaluator = OnlineEvaluator(db)
result = evaluator.evaluate_execution(
    agent_id="inbox_triage",
    task_input={"email_id": 12345},
    agent_output={"priority": "high", "labels": ["urgent"]},
    latency_ms=450,
    success=True
)
# Stores metrics in AgentMetricsDaily
```

**Metrics Tracked**:
- Quality score (0-100)
- Success rate (% without errors)
- Latency (p50, p95, p99)
- Invariant pass rate
- Red team detection rate

### Red Team Testing

Test security and robustness against adversarial inputs:

```python
from app.eval.telemetry import RedTeamCatalog

catalog = RedTeamCatalog()
attacks = catalog.get_attacks_for_agent("inbox_triage")

# Test each attack
for attack in attacks:
    result = evaluator.evaluate_execution(..., is_redteam=True)
    if result.has_invariant_violations():
        print(f"✓ Attack {attack.id} was BLOCKED")
    else:
        print(f"✗ Attack {attack.id} was NOT blocked")
```

**Attack Categories**:
- Prompt injection (override instructions)
- Data exfiltration (extract sensitive data)
- Privilege escalation (unauthorized access)
- Resource exhaustion (DoS attempts)
- Business logic abuse
- Social engineering

### Budget Gates

Set quality thresholds to block regressions:

```bash
# Check budget gates (fails if violated)
python -m app.eval.run_gates --agent inbox_triage --fail-on-violation

# Use in CI/CD
python -m app.eval.run_gates --all --fail-on-violation
```

**Default Budgets**:
- Quality score: ≥ 85
- Success rate: ≥ 95%
- p95 latency: ≤ 2000ms
- Invariant pass rate: ≥ 95%

**Regression Detection**:
- Absolute threshold (below budget)
- Relative threshold (5% drop from baseline)
- Trend analysis (quality declining over time)

### Intelligence Reports

Automated weekly reports with insights and recommendations:

```bash
# Generate weekly report
python -m app.eval.generate_report

# Deliver via Slack + Email
python -m app.eval.generate_report --delivery slack,email
```

**Report Contents**:
- Executive summary (pass/fail status)
- Per-agent performance (quality, latency, success rate)
- Trend analysis (week-over-week changes)
- Top issues (ranked by severity)
- Actionable recommendations (prioritized)
- Red team results

### Prometheus & Grafana Dashboards

Real-time monitoring with **13 dashboard panels** and **20+ alerts**:

```bash
# Start monitoring stack
docker-compose -f monitoring/docker-compose.yml up -d

# Access Grafana
open http://localhost:3000

# Import dashboard
# → Dashboards → Import → upload services/api/grafana/agent_evaluation_dashboard.json
```

**Dashboard Panels**:
- Overall quality status
- Success rate by agent
- Budget violations (24h)
- Latency trends (p95)
- Invariant pass rate
- Red team detection rate
- Violation analysis (by type/severity)
- Top failing invariants

**Alerts** (6 categories, 20+ rules):
- Quality: Critical/warning thresholds
- Performance: Latency spikes
- Budgets: Violation tracking
- Invariants: Failure detection
- Red Team: Detection rate monitoring
- Availability: Execution monitoring

### API Endpoints

```bash
# Metrics Export
POST /metrics/export?lookback_days=7  # Export metrics to Prometheus
GET  /metrics/dashboard/status        # Dashboard widget data
GET  /metrics/alerts/summary          # Active alerts summary
GET  /metrics/health                  # Health check

# Budget Gates
POST /budgets/evaluate?agent=inbox_triage  # Check budget gates
GET  /budgets/violations                    # List violations
GET  /budgets/config                        # Get budget configuration

# Intelligence Reports
POST /intelligence/generate?lookback_days=7  # Generate report
GET  /intelligence/reports                   # List reports
GET  /intelligence/reports/{id}              # Get report details
POST /intelligence/deliver?channel=slack     # Deliver report
```

### Configuration

```bash
# Evaluation Settings
EVAL_QUALITY_THRESHOLD=85.0      # Minimum quality score
EVAL_LATENCY_P95_MS=2000         # Maximum p95 latency
EVAL_SUCCESS_RATE=0.95           # Minimum success rate
EVAL_INVARIANT_PASS_RATE=0.95    # Minimum invariant pass rate

# Red Team Settings
REDTEAM_DETECTION_TARGET=0.90    # Target detection rate
REDTEAM_FALSE_POSITIVE_MAX=0.05  # Max false positive rate

# Intelligence Reports
REPORT_SCHEDULE="0 9 * * 1"      # Mondays at 9 AM (cron)
REPORT_DELIVERY=slack,email      # Delivery channels
SLACK_CHANNEL_INTELLIGENCE=#agent-intelligence
SMTP_HOST=smtp.gmail.com

# Prometheus/Grafana
PROMETHEUS_URL=http://localhost:9090
GRAFANA_URL=http://localhost:3000
ALERTMANAGER_URL=http://localhost:9093
```

### Documentation

Comprehensive guides available in `services/api/docs/`:

- **[EVAL_GUIDE.md](./services/api/docs/EVAL_GUIDE.md)** - Complete evaluation system guide
- **[REDTEAM.md](./services/api/docs/REDTEAM.md)** - Red team testing and attack scenarios
- **[BUDGETS_AND_GATES.md](./services/api/docs/BUDGETS_AND_GATES.md)** - Budget configuration and CI integration
- **[INTELLIGENCE_REPORT.md](./services/api/docs/INTELLIGENCE_REPORT.md)** - Weekly reports and trend analysis
- **[DASHBOARD_ALERTS.md](./services/api/docs/DASHBOARD_ALERTS.md)** - Dashboard setup and alert routing
- **[Grafana Setup](./services/api/grafana/README.md)** - Dashboard and Prometheus configuration

### Quick Start

1. **Run Offline Evaluation**:
   ```bash
   cd services/api
   python -m app.eval.runner --agent inbox_triage
   ```

2. **Set Up Budgets**:
   ```bash
   python -m app.eval.run_gates --agent inbox_triage
   ```

3. **Generate Intelligence Report**:
   ```bash
   python -m app.eval.generate_report
   ```

4. **Start Monitoring Stack**:
   ```bash
   docker-compose -f monitoring/docker-compose.yml up -d
   # Access Grafana at http://localhost:3000
   # Import services/api/grafana/agent_evaluation_dashboard.json
   ```

### Testing

Phase 5 includes **67 comprehensive tests**:

```bash
# Evaluation harness tests
pytest tests/test_eval_harness.py        # 25 tests (83-89% coverage)

# Telemetry tests
pytest tests/test_telemetry.py           # 6 tests

# Budget gates tests
pytest tests/test_budgets.py             # 6 tests

# Intelligence report tests
pytest tests/test_intelligence_report.py # 15 tests (HTML formatting)

# Metrics tests
pytest tests/test_metrics_eval.py        # 19 tests (10 passing, 9 require DB)
```

### Use Cases

**1. Pre-Deployment Quality Gates**
- Run eval harness before merging code
- Check budget gates in CI/CD
- Block deployment if quality < 85

**2. Production Monitoring**
- Real-time dashboards in Grafana
- Alerts for quality degradation
- Weekly intelligence reports to team

**3. Security Testing**
- Red team testing for all agents
- Target 90% attack detection rate
- Monitor false positive rate

**4. Continuous Improvement**
- Track quality trends over time
- Identify top failure modes
- Prioritize improvements based on impact
- Track cost of embedding API calls

**2. Email Quarantine**
- Require approval for high-risk emails (score >70)
- Auto-allow low-risk quarantine
- Validate email_id present before execution

**3. Database Queries**
- Budget ops count for expensive queries
- Require approval for DELETE operations
- Validate SQL injection attempts

**4. External API Calls**
- Track cost_cents for cloud API usage
- Budget max time to prevent runaway jobs
- Require approval for billing-related actions

## 🤖 Phase 5.3: Active Learning & Judge Reliability

ApplyLens now includes a **continuous learning loop** that automatically improves agent performance through labeled data, heuristic training, and safe canary deployment!

### Key Features

- **📊 Labeled Data Collection**: Aggregate feedback from approvals, ratings, and gold sets
- **🎯 Heuristic Training**: Train deterministic ML models to update planner configs
- **⚖️ Judge Reliability Weighting**: Assign trust scores to LLM judges based on calibration
- **🔍 Uncertainty Sampling**: Identify edge cases for human review
- **🚀 Safe Bundle Deployment**: Gradual canary rollout (10% → 50% → 100%) with auto-rollback

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Active Learning Loop                      │
└─────────────────────────────────────────────────────────────┘

  [Data Sources]           [Training]          [Deployment]
       │                       │                    │
   ┌───┴────┐           ┌──────┴──────┐      ┌────┴─────┐
   │Approvals│           │  Heuristic  │      │  Bundle  │
   │Feedback │──────────▶│   Trainer   │─────▶│ Manager  │
   │Gold Sets│           │             │      │          │
   └─────────┘           └──────────────┘     └────┬─────┘
                                                    │
  [Uncertainty]                                     ▼
       │                                      [Canary 10%]
   ┌───┴────┐                                       │
   │ Sampler│                                  ┌────┴─────┐
   │  Edge  │                                  │Regression│
   │  Cases │                                  │ Detector │
   └───┬────┘                                  └────┬─────┘
       │                                            │
       ▼                                            ▼
  [Human Review]                            [Promote/Rollback]
                                                    │
  [Judge Weights]                                   ▼
       │                                       [Canary 50%]
   ┌───┴────┐                                       │
   │ Nightly│                                       ▼
   │ Weight │                                  [Full Deploy]
   │ Update │
   └────────┘
```

### Components

**1. Labeled Example Store**
- Central repository for training data
- Sources: approvals (explicit decisions), feedback (thumbs up/down), gold sets (curated tasks)
- Confidence scoring (0-100)
- Deduplication via source + source_id

**2. Heuristic Trainer**
- Per-agent feature extraction (7/5/4 features depending on agent)
- Logistic regression & decision tree models
- Config bundle generation with updated thresholds
- Diff generation for approval workflow
- No external LLM calls (deterministic)

**3. Judge Reliability Weighting**
- Agreement rate with exponential time decay (7-day half-life)
- Calibration error: abs(confidence - accuracy)
- Combined weight = agreement - 0.5 * calibration_error
- Nightly updates per agent (30-day lookback)

**4. Uncertainty Sampler**
- Three methods: disagreement, low confidence, variance
- Entropy-based disagreement detection
- Filter already-labeled examples
- Top N candidates per agent (default 50)

**5. Bundle Manager**
- Create, propose, approve, apply workflow
- Automatic backup before apply
- Canary deployment at X% traffic
- Rollback to backup bundle

**6. Online Learning Guardrails**
- Integrate with Phase 5.1 RegressionDetector
- Auto-rollback on >5% quality drop
- Auto-promote on >2% quality gain
- Gradual rollout (10% → 50% → 100%)
- Nightly guard check for all canaries

### Quick Start

```bash
# 1. Load labeled data
python -m app.active.feeds load_all_feeds

# 2. Train bundle
python -m app.active.bundles create --agent inbox_triage

# 3. Propose for approval
python -m app.active.bundles propose --agent inbox_triage --bundle-id <id>

# 4. Approve (manual)
curl -X POST /api/active/approvals/{id}/approve

# 5. Deploy as 10% canary
python -m app.active.bundles apply --approval-id {id} --canary-percent 10

# 6. Monitor (automatic nightly checks will promote/rollback)
python -m app.active.guards check_canaries
```

### Scheduled Jobs

Add to `app/scheduler.py`:

```python
# Daily at 2 AM: Load labeled data
@scheduler.scheduled_job('cron', hour=2)
def load_labeled_data():
    load_all_feeds(session)

# Daily at 3 AM: Update judge weights
@scheduler.scheduled_job('cron', hour=3)
def update_judge_weights():
    nightly_update_weights(session)

# Daily at 4 AM: Sample review queue
@scheduler.scheduled_job('cron', hour=4)
def sample_review_queue():
    daily_sample_review_queue(session, top_n_per_agent=20)

# Daily at 5 AM: Check canary deployments
@scheduler.scheduled_job('cron', hour=5)
def check_canaries():
    guard = OnlineLearningGuard(session)
    guard.nightly_guard_check()
```

### Documentation

Comprehensive guides available in `docs/`:

- **[ACTIVE_LEARNING.md](./docs/ACTIVE_LEARNING.md)** - Complete technical guide
- **[RUNBOOK_ACTIVE.md](./docs/RUNBOOK_ACTIVE.md)** - Operational runbook
- **[PHASE_5_3_COMPLETION_SUMMARY.md](./docs/PHASE_5_3_COMPLETION_SUMMARY.md)** - Implementation summary

### Testing

Phase 5.3 includes **57 comprehensive tests**:

```bash
pytest tests/test_active_feeds.py       # 7 tests (feed loading)
pytest tests/test_heur_trainer.py       # 10 tests (training)
pytest tests/test_weights.py            # 8 tests (judge weights)
pytest tests/test_sampler.py            # 10 tests (uncertainty)
pytest tests/test_bundles.py            # 11 tests (bundle lifecycle)
pytest tests/test_guards.py             # 11 tests (guardrails)
```

### Integration with Phase 5 & 5.1

- ✅ Uses Phase 5 GoldenTask for training data
- ✅ Extends Phase 5 EvaluationResult with judge_scores
- ✅ Uses Phase 5.1 PlannerSwitchboard for traffic split
- ✅ Integrates with Phase 5.1 RegressionDetector for safety

### Success Metrics

**Target Metrics Post-Deploy**:
- 80%+ bundles reach 100% deploy
- <5% canary rollback rate
- 100+ labeled examples/week
- Judge weights stable (±0.1/week)
- 2-5% agent quality improvement per quarter

## Quickstart (Docker) - Minimal Setup

Fast start without Elasticsearch/Kibana:

```bash
cp infra/.env.example infra/.env
docker compose -f infra/docker-compose.minimal.yml up -d

# Seed the database
docker compose -f infra/docker-compose.minimal.yml exec api python -m app.seeds.seed_emails

# Check the ports in infra/.env (defaults: API=8002, Web=5174)
```text

**Access:**

- Web: <http://localhost:5174> (check `.env` for actual port)
- API: <http://localhost:8002>
- API Docs: <http://localhost:8002/docs>

## Full Setup (with Elasticsearch + Kibana)

Includes search and analytics dashboard with synonym support:

```bash
cp infra/.env.example infra/.env
# Optional during dev: force ES index recreation so synonyms/mappings apply
# (already true in .env.example)
# ES_RECREATE_ON_START=true

docker compose -f infra/docker-compose.yml up --build

# In another terminal, seed mock emails and index into Elasticsearch:
docker compose -f infra/docker-compose.yml exec api python -m app.seeds.seed_emails
```text

**Access:**

- Web: <http://localhost:5175>
- API: <http://localhost:8003>
- Elasticsearch: <http://localhost:9200>
- Kibana: <http://localhost:5601>

### Import Kibana Dashboard

Once Kibana is running:

```bash
curl -X POST "http://localhost:5601/api/saved_objects/_import?overwrite=true" \
  -H "kbn-xsrf: true" \
  -F file=@infra/kibana/applylens_dashboard.ndjson
```text

Or manually: **Kibana → Stack Management → Saved Objects → Import** and select `infra/kibana/applylens_dashboard.ndjson`

### Test the Search API & Synonyms

Synonym examples that should match due to the analyzer:

- Query **"talent partner"** should match emails containing **"recruiter"**
- Query **"offer letter"** should match **"offer" / "acceptance"**
- Query **"phone screen"** should match **"interview"** content

```bash
curl "http://localhost:8000/search/?q=Interview"
curl "http://localhost:8000/search/?q=talent%20partner"
```text

Then visit **<http://localhost:5173/search>** and try queries like `Interview`, `talent partner`, or `Greenhouse`.

## Local dev (without Docker)

Backend:

```bash
cd services/api
python -m venv .venv && source .venv/bin/activate
pip install -U pip && pip install .
export ES_ENABLED=false  # disable ES when not running locally
uvicorn app.main:app --reload --port 8003
```text

Frontend:

```bash
cd apps/web
npm install
npm run dev
```text

## Architecture

- **Backend**: FastAPI + SQLAlchemy + PostgreSQL + Elasticsearch
- **Frontend**: React + TypeScript + Vite
- **Search**: Elasticsearch with custom analyzers (synonyms, shingles, completion suggester)
- **Auth**: Google OAuth 2.0 with secure token storage
- **Email Processing**: Gmail API + BeautifulSoup + heuristic labeling
- **Warehouse & Analytics**: BigQuery (via Fivetran) + dbt transformations

## 📊 Google Cloud + Fivetran Integration

ApplyLens integrates with **Google Cloud BigQuery** and **Fivetran** for warehouse analytics and profile metrics.

### Architecture

```
Gmail → Fivetran Connector → BigQuery → dbt Marts → API Endpoints → React Dashboard
```

**Data Flow:**
1. **Fivetran** syncs Gmail messages to BigQuery `gmail_raw` dataset (every 6 hours)
2. **dbt** transforms raw data into analytics-ready marts (`gmail_marts`)
3. **API** queries BigQuery for profile metrics (cached with Redis, 60s TTL)
4. **Frontend** renders ProfileMetrics component with 3 cards (Activity, Top Senders, Categories)

### Warehouse Endpoints

All endpoints require `APPLYLENS_USE_WAREHOUSE=1` environment variable (returns 412 Precondition Failed if disabled).

**Profile Metrics:**
- `GET /api/warehouse/profile/activity-daily?days=14` - Daily email volume (last 14 days)
- `GET /api/warehouse/profile/top-senders?limit=10` - Top 10 email sources (30 days)
- `GET /api/warehouse/profile/categories-30d?limit=10` - Category distribution (30 days)

**Divergence Monitoring:**
- `GET /api/warehouse/profile/divergence-24h` - ES vs BQ count comparison (SLO: <2%)

### Example: Activity Daily

**Request:**
```bash
curl https://applylens.app/api/warehouse/profile/activity-daily?days=7
```

**Response:**
```json
[
  {
    "day": "2025-10-18",
    "messages_count": 35,
    "unique_senders": 12,
    "avg_size_kb": 45.2,
    "total_size_mb": 1.5
  },
  {
    "day": "2025-10-17",
    "messages_count": 42,
    "unique_senders": 15,
    "avg_size_kb": 38.7,
    "total_size_mb": 1.6
  }
]
```

### Frontend Component

The **ProfileMetrics** component displays warehouse analytics in the Settings page (feature-flagged):

```typescript
// Enable warehouse metrics
VITE_USE_WAREHOUSE=1

// Component renders 3 cards:
// 1. Inbox Activity (14-day chart)
// 2. Top Senders (30-day list with message counts)
// 3. Categories (30-day distribution with percentages)
```

### Setup

1. **Activate Fivetran Connector:**
   - Follow guide: `analytics/fivetran/README.md`
   - Configure Gmail → BigQuery sync (every 6 hours)
   - Run historical backfill (90 days recommended)

2. **Verify BigQuery Data:**
   ```powershell
   # Run health check
   .\analytics\bq\health.ps1
   ```

3. **Run dbt Transformations:**
   ```powershell
   cd analytics/dbt
   .\run_all.ps1
   ```

4. **Enable Warehouse Features:**
   ```bash
   # Backend (.env.prod)
   APPLYLENS_USE_WAREHOUSE=1
   APPLYLENS_GCP_PROJECT=applylens-gmail-YOUR_PROJECT_ID

   # Frontend (.env.production)
   VITE_USE_WAREHOUSE=1
   ```

5. **View Metrics:**
   - Visit https://applylens.app/web/settings
   - Scroll to "Inbox Analytics (Last 14 Days)"
   - See Activity chart, Top Senders list, Categories breakdown

### Divergence Monitoring

The divergence endpoint compares Elasticsearch (real-time) vs BigQuery (warehouse) counts to detect sync issues:

- **< 2% divergence**: Healthy (green) ✅
- **2-5% divergence**: Warning (amber) ⚠️
- **> 5% divergence**: Critical (red) 🔴

**Example Response:**
```json
{
  "es_count": 100,
  "bq_count": 98,
  "divergence": 0.02,
  "divergence_pct": 2.0,
  "slo_met": true,
  "status": "healthy",
  "message": "Divergence: 2.00% (within SLO)"
}
```

### dbt Marts

**Location:** `analytics/dbt/models/marts/warehouse/`

1. **mart_email_activity_daily** - Daily volume, unique senders, size metrics
2. **mart_top_senders_30d** - Top 100 email sources (last 30 days)
3. **mart_categories_30d** - Category distribution with percentages

**Run dbt:**
```powershell
# PowerShell
.\analytics\dbt\run_all.ps1

# Bash
./analytics/dbt/run_all.sh
```

### Documentation

- **Evidence Pack:** `docs/hackathon/EVIDENCE.md` - Screenshots, activation checklist
- **Health Checks:** `analytics/README.md` - Troubleshooting guide
- **Fivetran Setup:** `analytics/fivetran/README.md` - Connector configuration
- **API Tests:** `services/api/tests/integration/test_warehouse.py` - 10 test cases
- **E2E Tests:** `apps/web/e2e/warehouse.spec.ts` - 4 scenarios

## Next steps

- ✅ ~~Implement Gmail read-only OAuth and backfill endpoint~~ **DONE!**
- Add Applications table UI + reminders
- Elasticsearch relevance tuning (synonyms, boosts)
- Enhance Kibana dashboard with more visualizations
- Add ML-based email classification
- Implement scheduled email sync (cron jobs)
- Multi-user support with session management

## 📚 Documentation

All documentation has been organized in the [`docs/`](./docs/) folder:

- **[Getting Started](./docs/SETUP_COMPLETE_SUMMARY.md)** - Complete setup guide
- **[Gmail Setup](./docs/GMAIL_SETUP.md)** - OAuth configuration
- **[Reply Metrics](./docs/REPLY_METRICS_QUICKSTART.md)** - Filter & TTR badges (5-min guide)
- **[Advanced Filtering](./docs/ADVANCED_FILTERING_SUMMARY.md)** - Label & date filters
- **[Monitoring](./docs/MONITORING_QUICKREF.md)** - Prometheus & Grafana
- **[Production Deployment](./docs/PRODUCTION_SETUP.md)** - Hardening & security
- **[Testing](./docs/RUNNING_TESTS.md)** - Unit & E2E tests

### 🚨 Incident Runbooks

Production incident response procedures:

- **[503 Upstream Stale IP](./runbooks/503_upstream_stale.md)** - Nginx caching stale container IPs (2-5 min resolution)

📖 **See the [Documentation Index](./docs/README.md) for the complete list of 70+ guides.**

## 🔧 Monitoring & Observability

ApplyLens includes production-ready monitoring infrastructure:

### Prometheus Metrics

- **HTTP metrics:** Request rate, latency, error rate (via starlette-exporter)
- **Risk scoring:** Batch duration, failure rate, email coverage
- **Parity checks:** DB↔ES mismatch detection and ratio
- **System health:** Database and Elasticsearch availability

**Metrics endpoint:** <http://localhost:8003/metrics>

### Health Endpoints

- `/healthz` - Liveness probe (basic check)
- `/live` - Liveness alias
- `/ready` - Readiness probe (DB + ES + migration version)
- `/status` - Graceful degradation status (always returns 200)

### Grafana Dashboards

**API Status & Health Monitoring:**
- Success Rate Gauge (target: ≥99%)
- Request Rate Chart
- Database/Elasticsearch Status
- P50/P95/P99 Latency
- 5xx Error Rate

**Access:** <http://localhost:3000> (Grafana)
**Dashboard JSON:** `infra/grafana/dashboards/api-status-health.json`

**Operations Overview:**
- Error rates, latency, parity, performance
- Dashboard: `services/api/dashboards/ops-overview.json`

### Prometheus Alerts

**Critical alerts configured:**
- **StatusEndpointDegraded** - Service degradation detected
- **StatusEndpointCritical** - Critical service failure
- **DatabaseDown** - Database unavailable
- **ElasticsearchDown** - Search unavailable
- **HighApiErrorRate** - 5xx rate > 5% ([runbook](services/api/docs/runbooks/api-errors.md))
- **StatusEndpointSlowResponse** - High latency detected
- **StatusEndpointRetryStorm** - Too many retries

**Additional production alerts:**
- **RiskJobFailures** - Risk computation failures ([runbook](services/api/docs/runbooks/risk-job.md))
- **ParityDriftTooHigh** - DB↔ES drift > 0.5% ([runbook](services/api/docs/runbooks/parity.md))
- **BackfillDurationSLO** - p95 duration > 5min ([runbook](services/api/docs/runbooks/backfill.md))

**Alert rules:** `infra/prometheus/rules/status-health.yml` + `infra/alerts/prometheus-rules.yml`
**Prometheus UI:** <http://localhost:9090>

### Reload Loop Protection

ApplyLens implements a **4-layer defense** against infinite reload loops:

1. **Frontend:** Exponential backoff (2s→4s→8s→16s→max 60s) with AbortController
2. **Backend:** `/status` always returns HTTP 200 (even when degraded)
3. **Nginx:** JSON error handler + retry logic (no HTML error pages)
4. **Monitoring:** Prometheus alerts for retry storms

**Documentation:** `RELOAD_LOOP_FIX_SUMMARY.md`, `AUTH_CHECK_LOOP_FIX.md`

### Structured Logging

Enable JSON logging for production:

```bash
# Set environment variable
UVICORN_LOG_CONFIG=services/api/app/logging.yaml

# Logs include: timestamp, level, logger, message
```text

### Optional Tracing

Enable OpenTelemetry distributed tracing:

```bash
# Install tracing dependencies
pip install -e ".[tracing]"

# Enable tracing
OTEL_ENABLED=1
OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4318

# Instruments: FastAPI, SQLAlchemy, HTTP clients
```

---

## 🔒 Secrets Hygiene

ApplyLens enforces strict secrets management to prevent credential leaks.

### Pre-commit Scanning

Install pre-commit hooks to scan for secrets before committing:

```bash
# Install pre-commit
pip install pre-commit

# Install hooks (runs automatically on git commit)
pre-commit install

# Run manually on all files
pre-commit run --all-files

# Run gitleaks directly
gitleaks detect --source . --no-git -v
```

### CI/CD Protection

- **GitHub Secret Scanning**: Automatically detects secrets in commits
- **Gitleaks CI**: Runs on every PR and push (`.github/workflows/secret-scan.yml`)
- **SARIF Upload**: Results appear in Security > Code scanning tab

### Best Practices

✅ **DO:**
- Use environment variables for credentials
- Commit `.env.example` with placeholder values
- Redact secrets in documentation: `[REDACTED]` or `YOUR_KEY_HERE`
- Review `git diff --cached` before committing
- Blur API keys/tokens in screenshots

❌ **DON'T:**
- Commit API keys, tokens, or passwords
- Include real credentials in code examples
- Push `.env` files with real values
- Share screenshots with visible secrets

### If You Commit a Secret

1. **Revoke immediately** - Generate new credential
2. **Remove from history** - Use `git commit --amend` or BFG Repo-Cleaner
3. **Report** - Create security incident report

**Full Policy:** [docs/SECRETS_POLICY.md](docs/SECRETS_POLICY.md)

---

**Documentation:**
```text

**Documentation:**

- [📚 Complete Documentation Index](docs/README.md) - All docs in one place
- [Phase 6 Personalization](docs/PHASE_6_PERSONALIZATION.md) - Latest features (learning, metrics, money mode)
- [Quick Start Guide](docs/QUICK_START_E2E.md) - End-to-end setup
- [Run Full Stack](docs/RUN_FULL_STACK.md) - Local development
