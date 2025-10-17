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

## Other Services

(Other service documentation goes here...)
