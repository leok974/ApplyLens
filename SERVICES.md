# ApplyLens Services Guide

## Overview

ApplyLens consists of multiple services working together to provide intelligent email and application management.

---

## Agents System (Phase 2 - Production Ready)

The agents system provides production-ready autonomous operations with real provider integrations, comprehensive observability, and auto-remediation capabilities.

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Agent Execution                          │
└─────┬──────────┬──────────┬──────────┬───────────┬─────────┘
      │          │          │          │           │
      ▼          ▼          ▼          ▼           ▼
┌──────────┐ ┌──────┐ ┌─────────┐ ┌────────┐ ┌─────────┐
│ Provider │ │ Audit│ │EventBus │ │Metrics │ │ Planner │
│ Factory  │ │ Log  │ │  (SSE)  │ │(Prom.) │ │         │
└──────────┘ └──────┘ └─────────┘ └────────┘ └─────────┘
      │
      ├─ ESProvider (Elasticsearch queries)
      ├─ BQProvider (BigQuery SQL)
      ├─ DbtProvider (dbt Cloud API)
      └─ GmailProvider (Gmail API)
```

**Key Components**:
- **Planner**: Creates execution plans from objectives
- **Executor**: Runs plans with dependency injection, audit logging, metrics
- **ProviderFactory**: Manages real provider instances (ES, BQ, dbt, Gmail)
- **AgentAuditor**: Logs all runs to PostgreSQL for compliance
- **EventBus**: AsyncIO pub/sub for real-time SSE streaming
- **Metrics**: Prometheus counters and histograms for observability

### Available Agents

#### Warehouse Health Agent v2.0.0 (`warehouse_health`)

**Purpose**: Monitor data warehouse health with real-time parity checks, freshness SLO enforcement, and auto-remediation.

**Capabilities**:
- ✅ Real parity computation (ES vs BQ count comparison with 5% threshold)
- ✅ Freshness SLO enforcement (30-minute maximum data age)
- ✅ Auto-remediation (conditional dbt run when data is stale or out of sync)
- ✅ Enhanced error reporting (severity-based issues list)
- ✅ Daily breakdown analysis (7-day trend)

**Configuration**:
```json
{
  "es": {
    "index": "emails-production-*",
    "days": 7
  },
  "bq": {
    "dataset": "analytics_prod",
    "table": "emails",
    "project": "applylens-prod"
  },
  "dbt": {
    "target": "prod",
    "models": ["tag:daily", "tag:critical"]
  }
}
```

**Thresholds**:
- Parity threshold: 5.0% (max acceptable ES/BQ difference)
- Freshness SLO: 30 minutes (max acceptable data age)

**See**: [RUNBOOK_WAREHOUSE_HEALTH.md](./docs/RUNBOOK_WAREHOUSE_HEALTH.md)

### API Endpoints

#### Execute Agent
```bash
POST /agents/execute
Content-Type: application/json

{
  "agent_type": "warehouse_health",
  "objective": "Monitor warehouse health with auto-remediation",
  "dry_run": false,
  "allow_actions": true,
  "config": {
    "es": {"index": "emails-*"},
    "bq": {"dataset": "analytics", "table": "emails"},
    "dbt": {"target": "prod", "models": ["tag:daily"]}
  }
}
```

**Response:**
```json
{
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "success",
  "started_at": "2025-10-17T10:00:00Z",
  "completed_at": "2025-10-17T10:00:15Z",
  "duration_seconds": 15.2,
  "artifacts": {
    "parity": {
      "status": "ok",
      "es_count": 1500000,
      "bq_count": 1505000,
      "difference_percent": 0.33,
      "threshold_percent": 5.0,
      "daily_breakdown": [...]
    },
    "freshness": {
      "status": "ok",
      "latest_event_ts": "2025-10-17T09:55:00Z",
      "age_minutes": 5.0,
      "slo_minutes": 30,
      "within_slo": true
    },
    "dbt": {
      "success": true,
      "models_run": 3,
      "duration_sec": 45.2
    },
    "remediation": {
      "triggered": false
    },
    "summary": {
      "status": "healthy",
      "checks_passed": 3,
      "total_checks": 3,
      "issues": []
    }
  }
}
```

#### Query Agent History
```bash
GET /agents/history?agent_type=warehouse_health&limit=20
```

**Response:**
```json
{
  "runs": [
    {
      "id": "...",
      "run_id": "...",
      "agent_type": "warehouse_health",
      "objective": "Scheduled warehouse health check",
      "status": "success",
      "user_email": "ops@applylens.com",
      "started_at": "2025-10-17T10:00:00Z",
      "completed_at": "2025-10-17T10:00:15Z",
      "duration_seconds": 15.2
    }
  ],
  "total": 42
}
```

#### Stream Real-Time Events (SSE)
```bash
GET /agents/events
Accept: text/event-stream
```

**Response** (streaming):
```
event: run_started
data: {"run_id": "...", "agent_type": "warehouse_health", "objective": "...", "plan": {...}}

event: run_finished
data: {"run_id": "...", "status": "success", "duration_seconds": 15.2, "artifacts": {...}}
```

#### Metrics Endpoint (Prometheus)
```bash
GET /metrics
```

**Metrics**:
- `agent_runs_total{agent_type, status}` - Total runs by type and status
- `agent_run_duration_seconds{agent_type}` - Execution duration histogram

### Quickstart Examples

#### Using curl
```bash
# Execute warehouse health check (dry run)
curl -X POST http://localhost:8000/agents/execute \
  -H "Content-Type: application/json" \
  -d '{
    "agent_type": "warehouse_health",
    "objective": "Check warehouse health",
    "dry_run": true,
    "config": {
      "es": {"index": "emails-*"},
      "bq": {"dataset": "analytics", "table": "emails"},
      "dbt": {"target": "dev", "models": ["tag:daily"]}
    }
  }'

# Query agent history
curl "http://localhost:8000/agents/history?agent_type=warehouse_health&limit=10"

# Stream real-time events
curl -N "http://localhost:8000/agents/events"

# Get Prometheus metrics
curl "http://localhost:8000/metrics" | grep agent_
```

#### Using JavaScript (SSE)
```javascript
// Subscribe to real-time agent events
const eventSource = new EventSource('http://localhost:8000/agents/events');

eventSource.addEventListener('run_started', (e) => {
  const data = JSON.parse(e.data);
  console.log('Agent started:', data.agent_type, data.objective);
});

eventSource.addEventListener('run_finished', (e) => {
  const data = JSON.parse(e.data);
  console.log('Agent finished:', data.run_id, 'Status:', data.status);
  console.log('Artifacts:', data.artifacts);
});

eventSource.addEventListener('run_failed', (e) => {
  const data = JSON.parse(e.data);
  console.error('Agent failed:', data.run_id, 'Error:', data.error);
});
```

#### Using Python
```python
import requests
import json

# Execute agent
response = requests.post(
    'http://localhost:8000/agents/execute',
    json={
        "agent_type": "warehouse_health",
        "objective": "Monitor warehouse health",
        "dry_run": True,
        "config": {
            "es": {"index": "emails-*"},
            "bq": {"dataset": "analytics", "table": "emails"},
            "dbt": {"target": "dev", "models": ["tag:daily"]}
        }
    }
)

result = response.json()
print(f"Status: {result['status']}")
print(f"Duration: {result['duration_seconds']}s")
print(f"Health: {result['artifacts']['summary']['status']}")
print(f"Parity: {result['artifacts']['parity']['status']} "
      f"({result['artifacts']['parity']['difference_percent']}% diff)")
print(f"Freshness: {result['artifacts']['freshness']['status']} "
      f"({result['artifacts']['freshness']['age_minutes']} min old)")

# Query history
history = requests.get(
    'http://localhost:8000/agents/history',
    params={'agent_type': 'warehouse_health', 'limit': 10}
).json()

for run in history['runs']:
    print(f"{run['started_at']}: {run['status']} ({run['duration_seconds']}s)")
```

### Observability

#### Prometheus Metrics

**Queries**:
```promql
# Success rate (last 5 minutes)
sum(rate(agent_runs_total{status="success"}[5m])) /
sum(rate(agent_runs_total[5m]))

# Average duration
rate(agent_run_duration_seconds_sum[5m]) /
rate(agent_run_duration_seconds_count[5m])

# 95th percentile duration
histogram_quantile(0.95,
  rate(agent_run_duration_seconds_bucket[5m])
)
```

**Grafana Dashboards**:
- Agent Overview: Success rates, run counts, duration trends
- Warehouse Health: Parity status, freshness SLO, remediation triggers

#### Audit Logs (PostgreSQL)

**Table**: `agent_audit_log`

**Query Examples**:
```sql
-- Recent runs
SELECT * FROM agent_audit_log
WHERE agent_type = 'warehouse_health'
ORDER BY started_at DESC
LIMIT 10;

-- Failed runs
SELECT run_id, error_message, started_at
FROM agent_audit_log
WHERE agent_type = 'warehouse_health'
  AND status = 'failed'
ORDER BY started_at DESC;

-- Success rate (last 7 days)
SELECT 
  COUNT(*) FILTER (WHERE status = 'success') * 100.0 / COUNT(*) AS success_rate
FROM agent_audit_log
WHERE agent_type = 'warehouse_health'
  AND started_at > NOW() - INTERVAL '7 days';
```

#### Real-Time Streaming (SSE)

**Event Types**:
- `run_started` - Agent execution begins
- `run_finished` - Agent completes successfully
- `run_failed` - Agent fails with error

**Client Example** (Browser):
```javascript
const eventSource = new EventSource('http://localhost:8000/agents/events');

eventSource.addEventListener('run_started', (e) => {
  const data = JSON.parse(e.data);
  updateDashboard({ status: 'running', ...data });
});

eventSource.addEventListener('run_finished', (e) => {
  const data = JSON.parse(e.data);
  updateDashboard({ status: 'success', ...data });
  showNotification('Agent completed', data.artifacts);
});
```

### Development

#### Run API Server
```bash
# Development mode with auto-reload
uvicorn services.api.app.main:app --reload --port 8000

# Production mode
uvicorn services.api.app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

#### Run Tests
```bash
# Unit tests (fast, mocked providers)
pytest -m "not integration" services/api/tests/

# Integration tests (requires Elasticsearch)
export ES_ENABLED=true
pytest -m integration services/api/tests/integration/

# All tests
pytest services/api/tests/
```

#### Run Migrations
```bash
cd services/api
alembic upgrade head  # Apply latest migrations (includes agent_audit_log table)
```

### Safety & Design Principles

1. **Dry-run by default**: All agents default to `dry_run=True` for safety
2. **Typed interfaces**: Pydantic models ensure data validation
3. **Real provider integration**: Uses actual Elasticsearch, BigQuery, dbt, Gmail APIs
4. **Dependency injection**: ProviderFactory manages service instances
5. **Comprehensive audit**: All runs logged to database for compliance
6. **Observable**: Prometheus metrics + SSE streaming for real-time monitoring
7. **Auto-remediation**: Optional `allow_actions` flag enables corrective actions
8. **Safe defaults**: Tools default to read-only operations unless explicitly enabled

### Production Features (Phase 2 Complete)

✅ **Real Provider Integration**
- ESProvider: Elasticsearch queries (aggregate_daily, latest_event_ts, count)
- BQProvider: BigQuery SQL execution
- DbtProvider: dbt Cloud API integration
- GmailProvider: Gmail API access

✅ **Audit Logging**
- All runs logged to `agent_audit_log` table
- Stores plan, artifacts, errors, duration
- Queryable via SQL or API

✅ **Prometheus Metrics**
- `agent_runs_total` counter (by type, status)
- `agent_run_duration_seconds` histogram

✅ **Server-Sent Events (SSE)**
- Real-time event streaming to frontend
- W3C SSE protocol compatible
- Event types: run_started, run_finished, run_failed

✅ **Production Monitoring**
- Warehouse Health Agent v2.0.0
- Real parity computation (ES vs BQ)
- Freshness SLO enforcement (30-minute threshold)
- Auto-remediation (conditional dbt run)

✅ **CI Integration Testing**
- Split unit/integration test jobs
- Real Elasticsearch service container
- Validates provider interactions

### Documentation

- **[Agents Quickstart Guide](./docs/AGENTS_QUICKSTART.md)** - Get started in 5 minutes
- **[Agents Observability Guide](./docs/AGENTS_OBSERVABILITY.md)** - Metrics, logs, SSE, dashboards
- **[Warehouse Health Runbook](./docs/RUNBOOK_WAREHOUSE_HEALTH.md)** - Operational procedures
- **[Phase 2 PR1: Providers](./docs/PHASE2-PR1-PROVIDERS.md)** - Provider architecture
- **[Phase 2 PR2: Audit & Metrics](./docs/PHASE2-PR2-AUDIT-METRICS.md)** - Observability design
- **[Phase 2 PR3: SSE Events](./docs/PHASE2-PR3-SSE-EVENTS.md)** - Real-time streaming
- **[Phase 2 PR4: Warehouse Health v2](./docs/PHASE2-PR4-WAREHOUSE-HEALTH-V2.md)** - Production monitoring
- **[Phase 2 PR5: CI Integration](./docs/PHASE2-PR5-CI-INTEGRATION.md)** - Testing infrastructure

---

## Phase 3: Safety, Budgets & Practical Agents

Phase 3 adds core safety controls, resource limits, and three production-ready agents for practical automation workflows.

### New Features

#### 1. Budget Enforcement

**Purpose**: Prevent agents from consuming excessive resources

**Usage**:
```json
{
  "agent_type": "inbox_triage",
  "budget_ms": 30000,      // Max 30 seconds
  "budget_ops": 100        // Max 100 operations
}
```

**Tracking**:
- `budget_ms` - Maximum execution time in milliseconds
- `budget_ops` - Maximum number of operations (queries, API calls)
- Checked before and after execution
- Warning logged if exceeded (execution not aborted in Phase 3)

**API Response**:
```json
{
  "status": "success",
  "ops_count": 52,
  "duration_ms": 15234,
  "budget_status": {
    "exceeded": false,
    "time_limit": 30000,
    "time_used": 15234,
    "ops_limit": 100,
    "ops_used": 52
  }
}
```

#### 2. Approval Gates

**Purpose**: Require approval for high-risk actions

**Policy Levels**:

**Always Allowed** (no approval):
- Read-only operations: `query`, `fetch`, `read`, `get`, `list`, `search`

**Always Denied** (Phase 3):
- High-risk operations: `quarantine`, `delete`, `purge`, `drop`
- Phase 4 will add human approval workflow

**Conditional Approval**:
- Size limits: Operations affecting > 1000 items
- Budget limits: Operations exceeding budget
- Risk thresholds: Actions with risk score > 95

**API Usage**:
```json
{
  "agent_type": "inbox_triage",
  "allow_actions": true,  // Enable action execution
  "dry_run": false        // Required for actions
}
```

**Python API**:
```python
from app.utils.approvals import Approvals

# Check if action is allowed
allowed = Approvals.allow(
    agent_name='inbox_triage',
    action='label',
    context={'email_count': 50}
)

# Check budget status
budget_status = Approvals.check_budget(
    elapsed_ms=15000,
    ops_count=52,
    budget_ms=30000,
    budget_ops=100
)
```

#### 3. Artifacts Storage

**Purpose**: Persist agent outputs for review and auditing

**File Structure**:
```
agent/artifacts/
├── inbox_triage/
│   ├── report_2025-10-17_103045.md
│   └── results_2025-10-17_103045.json
├── knowledge_update/
│   ├── synonyms.diff.json
│   └── synonyms.diff.md
└── insights_writer/
    ├── email_activity_2025-W42.md
    └── email_activity_2025-W42.json
```

**Python API**:
```python
from app.utils.artifacts import artifacts_store

# Write markdown report
artifacts_store.write(
    path='report.md',
    content=report_text,
    agent_name='inbox_triage'
)

# Write JSON data
artifacts_store.write_json(
    path='results.json',
    data={'total': 100, 'processed': 95},
    agent_name='inbox_triage'
)

# Read artifact
content = artifacts_store.read(
    path='report.md',
    agent_name='inbox_triage'
)

# List artifacts
files = artifacts_store.list_files(
    agent_name='inbox_triage',
    pattern='*.json'
)

# Generate timestamped path
path = artifacts_store.get_timestamped_path(
    prefix='report',
    extension='md',
    agent_name='inbox_triage'
)  # → "report_2025-10-17_103045.md"

# Generate weekly path (ISO 8601)
path = artifacts_store.get_weekly_path(
    prefix='insights',
    extension='md'
)  # → "insights_2025-W42.md"
```

**REST API** (planned):
```bash
# List artifacts
GET /agents/artifacts/{agent_name}

# Download artifact
GET /agents/artifacts/{agent_name}/{filename}

# Delete artifact
DELETE /agents/artifacts/{agent_name}/{filename}
```

### New Agents

#### Inbox Triage Agent (`inbox_triage`)

**Purpose**: Automatically triage incoming emails by risk level

**Capabilities**:
- Risk scoring 0-100 based on multiple signals
- Phishing detection (keywords, TLDs, patterns)
- Gmail label application
- Quarantine high-risk emails (with approval)
- Markdown report generation

**API Usage**:
```bash
curl -X POST http://localhost:8000/agents/execute \
  -H "Content-Type: application/json" \
  -d '{
    "agent_type": "inbox_triage",
    "objective": "Triage last 24 hours of inbox emails",
    "dry_run": true,
    "budget_ms": 30000,
    "budget_ops": 100,
    "params": {
      "max_emails": 50,
      "hours_back": 24
    }
  }'
```

**Response**:
```json
{
  "total_emails": 50,
  "by_risk_level": {
    "SAFE": 30,
    "LOW": 10,
    "MEDIUM": 5,
    "HIGH": 3,
    "CRITICAL": 2
  },
  "actions_taken": 8,
  "artifacts": {
    "report": "inbox_triage_2025-10-17.md",
    "results": "inbox_triage_2025-10-17.json"
  },
  "ops_count": 52
}
```

**Risk Scoring**:
- Suspicious keywords: 15 points each (max 40)
- Suspicious TLDs (.ru, .cn, .tk, etc.): 20 points
- Phishing patterns (verify + account): 20 points
- Gmail spam labels: 50 points
- Safe domains (google.com, github.com): 0 points

**Risk Levels**:
- SAFE: 0-19
- LOW: 20-39
- MEDIUM: 40-59
- HIGH: 60-79
- CRITICAL: 80-100

#### Knowledge Updater Agent (`knowledge_update`)

**Purpose**: Sync Elasticsearch configuration from BigQuery data marts

**Capabilities**:
- Query BigQuery marts for configuration data
- Generate diffs (added/removed/unchanged)
- Preview changes in dry-run mode
- Apply changes with approval gates
- Write JSON diff artifacts

**API Usage**:
```bash
curl -X POST http://localhost:8000/agents/execute \
  -H "Content-Type: application/json" \
  -d '{
    "agent_type": "knowledge_update",
    "objective": "Update ES synonyms from warehouse",
    "dry_run": true,
    "budget_ops": 10,
    "params": {
      "config_type": "synonyms",
      "mart_table": "knowledge.synonyms",
      "apply_changes": false
    }
  }'
```

**Response**:
```json
{
  "config_type": "synonyms",
  "added_count": 15,
  "removed_count": 3,
  "unchanged_count": 42,
  "applied": false,
  "artifacts": {
    "diff_json": "synonyms.diff.json",
    "diff_report": "synonyms.diff.md"
  },
  "ops_count": 2
}
```

**Supported Config Types**:
- `synonyms` - Search synonyms for Elasticsearch
- `routing_rules` - Pattern-based routing rules

**Workflow**:
1. Query BigQuery mart for new configuration
2. Fetch current Elasticsearch configuration
3. Generate diff (added, removed, unchanged)
4. (Optional) Apply changes with approval check
5. Write diff artifacts for review

#### Insights Writer Agent (`insights_writer`)

**Purpose**: Generate weekly insights reports from warehouse metrics

**Capabilities**:
- Query warehouse for weekly aggregations
- Calculate week-over-week trends
- Generate markdown reports with tables
- Include ASCII sparkline charts
- Write to ISO week paths (2025-W42.md)

**API Usage**:
```bash
curl -X POST http://localhost:8000/agents/execute \
  -H "Content-Type: application/json" \
  -d '{
    "agent_type": "insights_writer",
    "objective": "Generate weekly email activity report",
    "budget_ops": 5,
    "params": {
      "report_type": "email_activity",
      "week_offset": 0,
      "include_charts": true
    }
  }'
```

**Response**:
```json
{
  "report_type": "email_activity",
  "week": "2025-W42",
  "artifacts": {
    "report": "email_activity_2025-W42.md",
    "data": "email_activity_2025-W42.json"
  },
  "metrics_summary": {
    "current": {
      "total_emails": 1250,
      "unique_senders": 450,
      "spam_emails": 125
    },
    "trends": {
      "total_emails": {
        "current": 1250,
        "previous": 1100,
        "change": 150,
        "change_pct": 13.6,
        "direction": "📈"
      }
    }
  },
  "ops_count": 2
}
```

**Report Types**:
- `email_activity` - Weekly email processing metrics
- `applications` - Job application pipeline metrics

**Sample Report**:
```markdown
# Weekly Insights Report: Email Activity
**Week**: 2025-W42
**Generated**: 2025-10-17 10:30:00

---

## Executive Summary

- Processed **1,250** emails this week
- From **450** unique senders
- Spam rate: **10.0%** (125 spam emails)
- Emails with attachments: **320**

## Week-Over-Week Trends

| Metric | Current | Previous | Change | % Change |
|--------|---------|----------|--------|----------|
| Total Emails | 1,250 | 1,100 | +150 | 📈 +13.6% |
| Unique Senders | 450 | 420 | +30 | 📈 +7.1% |
| Spam Emails | 125 | 150 | -25 | 📉 -16.7% |

## Visual Trends

```
Total Emails                   Prev: ████████████████████
                               Curr: ████████████████████████

Unique Senders                 Prev: ███████████████
                               Curr: ████████████████
```

## Key Insights

- 📈 **Total Emails** increased significantly by **13.6%**
- 📉 **Spam Emails** decreased by **16.7%**
```

### Testing

Phase 3 includes comprehensive golden tests (34 tests total):

```bash
# Unit tests (core utilities)
python services/api/tests/unit/test_phase3_core.py
# 10 tests: approvals, artifacts, executor

# Golden tests (agents with mocked providers)
python services/api/tests/golden/test_inbox_triage.py
# 8 tests: risk scoring, dry-run, live mode, reports

python services/api/tests/golden/test_knowledge_update.py
# 8 tests: diffs, dry-run, large changes

python services/api/tests/golden/test_insights_writer.py
# 8 tests: reports, trends, charts, formatting
```

### Documentation

- **[Agents Quickstart Guide](./docs/AGENTS_QUICKSTART.md)** - Updated with Phase 3 features
- **[Architecture](./docs/ARCHITECTURE.md)** - Phase 3 architecture diagrams
- **Phase 3 PRs**:
  - PR1: Core Infrastructure (budgets, approvals, artifacts)
  - PR2: Inbox Triage Agent
  - PR3: Knowledge Updater & Insights Writer Agents

### Production Features (Phase 3 Complete)

✅ **Budget Enforcement**
- Time limits (budget_ms)
- Operation limits (budget_ops)
- Budget tracking and warnings

✅ **Approval Gates**
- Policy checks for actions
- Always allow read-only
- Always deny high-risk (Phase 3)
- Conditional approval for moderate-risk

✅ **Artifacts Storage**
- JSON and markdown persistence
- Agent-specific paths
- Timestamped and weekly paths
- Singleton instance for global access

✅ **Inbox Triage Agent**
- Multi-signal risk scoring (0-100)
- Phishing detection
- Gmail label application
- Quarantine workflow (with approval)
- Markdown reports

✅ **Knowledge Updater Agent**
- BigQuery mart queries
- Elasticsearch config diffs
- Dry-run and live modes
- JSON diff artifacts

✅ **Insights Writer Agent**
- Warehouse metrics aggregation
- Week-over-week trend calculation
- Markdown reports with tables
- ASCII sparkline charts
- ISO week paths

### Next Phase (Phase 4 - Planned)

- Human approval workflow (Approvals Tray UI)
- Interactive agent execution (user prompts)
- Multi-agent orchestration (agent calls agent)
- Advanced scheduling (cron, triggers)
- Artifact versioning and history

---

## Other Services

(Other service documentation goes here...)

