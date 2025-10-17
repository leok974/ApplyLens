# ApplyLens

[![API Tests](https://github.com/leok974/ApplyLens/actions/workflows/api-tests.yml/badge.svg)](https://github.com/leok974/ApplyLens/actions/workflows/api-tests.yml)
[![Docs Checks](https://github.com/leok974/ApplyLens/actions/workflows/docs-check.yml/badge.svg)](https://github.com/leok974/ApplyLens/actions/workflows/docs-check.yml)
[![codecov](https://codecov.io/gh/leok974/ApplyLens/branch/polish/graph/badge.svg)](https://codecov.io/gh/leok974/ApplyLens)

Agentic job-inbox MVP: classify job/search emails, extract key facts, and populate a tracker.

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

### Grafana Dashboard

Import the operational dashboard for real-time monitoring:

```bash
# Import ops-overview.json into Grafana
# Location: services/api/dashboards/ops-overview.json
# Panels: Error rates, latency, parity, performance
```text

### Alerts & Runbooks

Production-critical alerts with runbooks:

- **APIHighErrorRateFast** - 5xx rate > 5% ([runbook](services/api/docs/runbooks/api-errors.md))
- **RiskJobFailures** - Risk computation failures ([runbook](services/api/docs/runbooks/risk-job.md))
- **ParityDriftTooHigh** - DB↔ES drift > 0.5% ([runbook](services/api/docs/runbooks/parity.md))
- **BackfillDurationSLO** - p95 duration > 5min ([runbook](services/api/docs/runbooks/backfill.md))

**Alert rules:** `infra/alerts/prometheus-rules.yml`

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
```text

**Documentation:**

- [📚 Complete Documentation Index](docs/README.md) - All docs in one place
- [Phase 6 Personalization](docs/PHASE_6_PERSONALIZATION.md) - Latest features (learning, metrics, money mode)
- [Quick Start Guide](docs/QUICK_START_E2E.md) - End-to-end setup
- [Run Full Stack](docs/RUN_FULL_STACK.md) - Local development
