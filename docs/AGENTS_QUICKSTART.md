# Agents Quickstart Guide

**Get started with ApplyLens Agentic System in 5 minutes**

This guide shows you how to create, execute, and monitor autonomous agents that automate data operations across your warehouse stack.

---

## Table of Contents

1. [What Are Agents?](#what-are-agents)
2. [Quick Start](#quick-start)
3. [Core Concepts](#core-concepts)
4. [Creating Your First Agent](#creating-your-first-agent)
5. [Executing Agents](#executing-agents)
6. [Monitoring & Observability](#monitoring--observability)
7. [Available Agents](#available-agents)
8. [Next Steps](#next-steps)

---

## What Are Agents?

**Agents** are autonomous programs that execute multi-step workflows to achieve objectives:

- **Plan** - Generate execution plan from objective
- **Execute** - Run steps with real providers (Elasticsearch, BigQuery, dbt)
- **Audit** - Log all actions to database for compliance
- **Stream** - Broadcast real-time updates via SSE
- **Monitor** - Track metrics and performance

**Example Use Cases:**
- Monitor warehouse health (parity, freshness, SLO compliance)
- Automate dbt model runs when data quality degrades
- Generate daily reports with cross-service data aggregation
- Detect and remediate data pipeline issues

---

## Quick Start

### 1. Execute Your First Agent (API)

```bash
# Run warehouse health check
curl -X POST http://localhost:8000/agents/execute \
  -H "Content-Type: application/json" \
  -d '{
    "agent_type": "warehouse_health",
    "objective": "Check warehouse health and data quality",
    "dry_run": true,
    "config": {
      "es": {"index": "emails-*"},
      "bq": {"dataset": "analytics", "table": "emails"},
      "dbt": {"target": "dev", "models": ["tag:daily"]}
    }
  }'
```

**Response:**
```json
{
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "success",
  "started_at": "2025-10-17T10:30:00Z",
  "completed_at": "2025-10-17T10:30:15Z",
  "duration_seconds": 15.2,
  "artifacts": {
    "parity": {
      "status": "ok",
      "es_count": 15000,
      "bq_count": 15100,
      "difference_percent": 0.66
    },
    "freshness": {
      "status": "ok",
      "latest_event_ts": "2025-10-17T10:25:00Z",
      "age_minutes": 5.0,
      "within_slo": true
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

### 2. Stream Real-Time Updates (SSE)

```javascript
// Frontend: Subscribe to agent events
const eventSource = new EventSource('http://localhost:8000/agents/events');

eventSource.addEventListener('run_started', (e) => {
  const data = JSON.parse(e.data);
  console.log('Agent started:', data.run_id, data.objective);
});

eventSource.addEventListener('run_finished', (e) => {
  const data = JSON.parse(e.data);
  console.log('Agent finished:', data.run_id, 'Status:', data.status);
});

eventSource.addEventListener('run_failed', (e) => {
  const data = JSON.parse(e.data);
  console.error('Agent failed:', data.run_id, 'Error:', data.error);
});
```

### 3. Check Audit Logs

```bash
# Query agent execution history
curl -X GET http://localhost:8000/agents/history?limit=10
```

**Response:**
```json
{
  "runs": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "agent_type": "warehouse_health",
      "objective": "Check warehouse health",
      "status": "success",
      "user_email": "ops@applylens.com",
      "started_at": "2025-10-17T10:30:00Z",
      "completed_at": "2025-10-17T10:30:15Z",
      "duration_seconds": 15.2
    }
  ],
  "total": 1
}
```

---

## Core Concepts

### Agent Lifecycle

```
┌─────────────┐
│   Request   │  User or scheduler triggers agent
└──────┬──────┘
       │
       ▼
┌─────────────┐
│    Plan     │  Generate execution steps from objective
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Execute   │  Run steps with real providers
│             │  - Elasticsearch queries
│             │  - BigQuery queries
│             │  - dbt runs
└──────┬──────┘
       │
       ▼
┌─────────────┐
│    Audit    │  Log run to database
│             │  - Save plan, artifacts, errors
│             │  - Track duration, status
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Stream    │  Broadcast events to subscribers
│             │  - run_started
│             │  - run_finished / run_failed
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Monitor   │  Track metrics in Prometheus
│             │  - agent_runs_total
│             │  - agent_run_duration_seconds
└─────────────┘
```

### Agent Components

**1. Agent Class** (`app/agents/warehouse.py`)
- `describe()` - Metadata (name, version, description)
- `plan()` - Generate execution plan from request
- `execute()` - Run plan and return artifacts

**2. Executor** (`app/agents/executor.py`)
- Orchestrates agent lifecycle
- Injects dependencies (providers, auditor, event_bus)
- Handles errors and retries

**3. Providers** (`app/providers/`)
- `ESProvider` - Elasticsearch queries (aggregate_daily, latest_event_ts, count)
- `BQProvider` - BigQuery queries (run SQL, fetch results)
- `DbtProvider` - dbt runs (compile, run, test models)
- `GmailProvider` - Gmail API (fetch threads, send emails)

**4. Auditor** (`app/services/agent_auditor.py`)
- Logs all runs to `agent_audit_log` table
- Stores plan, artifacts, errors, duration
- Queryable history for compliance

**5. EventBus** (`app/events/bus.py`)
- AsyncIO pub/sub for real-time updates
- SSE streaming to frontend clients
- Event types: `run_started`, `run_finished`, `run_failed`

---

## Creating Your First Agent

### Step 1: Define Agent Class

```python
# app/agents/my_agent.py
from typing import Dict, Any
from app.agents.core import AgentBase

class MyCustomAgent(AgentBase):
    @staticmethod
    def describe() -> Dict[str, Any]:
        """Agent metadata."""
        return {
            "name": "my_custom_agent",
            "version": "1.0.0",
            "description": "Custom agent for my use case",
            "capabilities": ["data_analysis", "reporting"]
        }
    
    @staticmethod
    def plan(request: Dict[str, Any]) -> Dict[str, Any]:
        """Generate execution plan from request."""
        return {
            "objective": request.get("objective", "Run custom workflow"),
            "steps": [
                "fetch_data",
                "analyze_data",
                "generate_report",
                "send_notification"
            ],
            "dry_run": request.get("dry_run", True),
            "config": request.get("config", {})
        }
    
    @staticmethod
    def execute(plan: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the plan and return artifacts."""
        from app.services.provider_factory import ProviderFactory
        
        factory = ProviderFactory()
        
        # Step 1: Fetch data from ES
        es_provider = factory.es()
        data = es_provider.aggregate_daily(
            index=plan["config"]["es"]["index"],
            days=7
        )
        
        # Step 2: Analyze data
        total_count = sum(day.get("emails", 0) for day in data)
        avg_daily = total_count / len(data)
        
        # Step 3: Generate report
        report = {
            "total_emails": total_count,
            "avg_daily_emails": avg_daily,
            "days_analyzed": len(data)
        }
        
        # Step 4: Send notification (dry_run check)
        if not plan["dry_run"]:
            # TODO: Send email or Slack notification
            pass
        
        return {
            "data": data,
            "analysis": report,
            "status": "success"
        }
```

### Step 2: Register Agent

```python
# app/agents/registry.py
from app.agents.my_agent import MyCustomAgent

AGENT_REGISTRY = {
    "warehouse_health": WarehouseHealthAgent,
    "my_custom_agent": MyCustomAgent,  # Add here
}
```

### Step 3: Test Agent

```python
# tests/test_my_agent.py
import pytest
from app.agents.my_agent import MyCustomAgent

def test_my_agent_plan():
    """Test plan generation."""
    request = {
        "objective": "Test objective",
        "dry_run": True,
        "config": {"es": {"index": "test-*"}}
    }
    
    plan = MyCustomAgent.plan(request)
    
    assert plan["objective"] == "Test objective"
    assert len(plan["steps"]) == 4
    assert plan["dry_run"] is True

def test_my_agent_execute(mocker):
    """Test execution with mocked providers."""
    # Mock ESProvider
    mock_es = mocker.MagicMock()
    mock_es.aggregate_daily.return_value = [
        {"date": "2025-10-17", "emails": 100},
        {"date": "2025-10-16", "emails": 150}
    ]
    
    mocker.patch(
        'app.services.provider_factory.ProviderFactory.es',
        return_value=mock_es
    )
    
    plan = {
        "objective": "Test",
        "dry_run": True,
        "steps": ["fetch_data", "analyze_data", "generate_report"],
        "config": {"es": {"index": "test-*"}}
    }
    
    result = MyCustomAgent.execute(plan)
    
    assert result["status"] == "success"
    assert result["analysis"]["total_emails"] == 250
    assert result["analysis"]["avg_daily_emails"] == 125
```

### Step 4: Execute Agent

```bash
# Via API
curl -X POST http://localhost:8000/agents/execute \
  -H "Content-Type: application/json" \
  -d '{
    "agent_type": "my_custom_agent",
    "objective": "Run my custom workflow",
    "dry_run": true,
    "config": {
      "es": {"index": "emails-*"}
    }
  }'
```

---

## Executing Agents

### Execution Modes

**1. Dry Run (Safe, Default)**
```json
{
  "agent_type": "warehouse_health",
  "dry_run": true  // No mutations (no dbt runs, no emails sent)
}
```

**2. Live Run (Production)**
```json
{
  "agent_type": "warehouse_health",
  "dry_run": false,  // Allows mutations
  "allow_actions": true  // Enables auto-remediation
}
```

### Configuration

**Minimal Config:**
```json
{
  "agent_type": "warehouse_health",
  "objective": "Check warehouse health"
}
```

**Full Config:**
```json
{
  "agent_type": "warehouse_health",
  "objective": "Monitor warehouse and auto-remediate if needed",
  "dry_run": false,
  "allow_actions": true,
  "config": {
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
      "models": ["tag:daily", "tag:critical"],
      "full_refresh": false
    }
  }
}
```

### Error Handling

**Execution Errors:**
```json
{
  "run_id": "...",
  "status": "failed",
  "error": {
    "type": "ProviderError",
    "message": "Elasticsearch connection timeout",
    "step": "query_es_daily",
    "traceback": "..."
  }
}
```

**Validation Errors:**
```json
{
  "error": "Invalid agent_type: 'unknown_agent'. Available: warehouse_health, my_custom_agent"
}
```

---

## Monitoring & Observability

### Metrics (Prometheus)

**Agent Runs Total:**
```promql
# Total runs by agent type and status
agent_runs_total{agent_type="warehouse_health", status="success"}
agent_runs_total{agent_type="warehouse_health", status="failed"}

# Success rate
rate(agent_runs_total{status="success"}[5m]) / 
rate(agent_runs_total[5m])
```

**Agent Run Duration:**
```promql
# Average duration by agent type
rate(agent_run_duration_seconds_sum{agent_type="warehouse_health"}[5m]) /
rate(agent_run_duration_seconds_count{agent_type="warehouse_health"}[5m])

# 95th percentile
histogram_quantile(0.95, 
  rate(agent_run_duration_seconds_bucket{agent_type="warehouse_health"}[5m])
)
```

**Alert Rules:**
```yaml
# High failure rate
- alert: HighAgentFailureRate
  expr: |
    rate(agent_runs_total{status="failed"}[5m]) /
    rate(agent_runs_total[5m]) > 0.1
  for: 10m
  annotations:
    summary: "Agent failure rate above 10%"

# Slow execution
- alert: SlowAgentExecution
  expr: |
    histogram_quantile(0.95,
      rate(agent_run_duration_seconds_bucket[5m])
    ) > 60
  for: 5m
  annotations:
    summary: "Agent p95 duration above 60s"
```

### Audit Logs

**Query History:**
```sql
-- Recent runs
SELECT 
  id, agent_type, objective, status, 
  duration_seconds, started_at
FROM agent_audit_log
ORDER BY started_at DESC
LIMIT 10;

-- Failed runs
SELECT 
  id, agent_type, objective, error_message, started_at
FROM agent_audit_log
WHERE status = 'failed'
ORDER BY started_at DESC;

-- Average duration by agent
SELECT 
  agent_type,
  AVG(duration_seconds) as avg_duration,
  COUNT(*) as total_runs
FROM agent_audit_log
WHERE started_at > NOW() - INTERVAL '7 days'
GROUP BY agent_type;
```

**API Query:**
```bash
# Filter by agent type
curl -X GET "http://localhost:8000/agents/history?agent_type=warehouse_health&limit=20"

# Filter by status
curl -X GET "http://localhost:8000/agents/history?status=failed&limit=10"

# Filter by date range
curl -X GET "http://localhost:8000/agents/history?start_date=2025-10-01&end_date=2025-10-17"
```

### Server-Sent Events (SSE)

**Subscribe to Events:**
```javascript
const eventSource = new EventSource('http://localhost:8000/agents/events');

// Run started
eventSource.addEventListener('run_started', (e) => {
  const { run_id, agent_type, objective, plan } = JSON.parse(e.data);
  console.log(`[${run_id}] Started ${agent_type}: ${objective}`);
});

// Run finished (success)
eventSource.addEventListener('run_finished', (e) => {
  const { run_id, status, duration_seconds, artifacts } = JSON.parse(e.data);
  console.log(`[${run_id}] Finished in ${duration_seconds}s`);
  console.log('Artifacts:', artifacts);
});

// Run failed (error)
eventSource.addEventListener('run_failed', (e) => {
  const { run_id, error } = JSON.parse(e.data);
  console.error(`[${run_id}] Failed:`, error);
});

// Error handling
eventSource.onerror = (err) => {
  console.error('SSE connection error:', err);
  // Auto-reconnect is built-in to EventSource
};
```

**Event Payloads:**

`run_started`:
```json
{
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "agent_type": "warehouse_health",
  "objective": "Check warehouse health",
  "plan": {
    "steps": ["query_es_daily", "query_bq_daily", "check_parity", ...],
    "dry_run": true
  },
  "timestamp": "2025-10-17T10:30:00Z"
}
```

`run_finished`:
```json
{
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "success",
  "duration_seconds": 15.2,
  "artifacts": {
    "parity": {"status": "ok", "es_count": 15000, "bq_count": 15100},
    "freshness": {"status": "ok", "within_slo": true}
  },
  "timestamp": "2025-10-17T10:30:15Z"
}
```

`run_failed`:
```json
{
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "error": "Elasticsearch connection timeout",
  "timestamp": "2025-10-17T10:30:10Z"
}
```

---

## Available Agents

### Warehouse Health Agent (`warehouse_health`)

**Purpose**: Monitor data warehouse health, parity, and freshness

**Capabilities**:
- ✅ Real parity computation (ES vs BQ count comparison with 5% threshold)
- ✅ Freshness SLO enforcement (30-minute maximum data age)
- ✅ Auto-remediation (conditional dbt run when data is stale or out of sync)
- ✅ Enhanced error reporting (severity-based issues list)

**Usage:**
```bash
curl -X POST http://localhost:8000/agents/execute \
  -H "Content-Type: application/json" \
  -d '{
    "agent_type": "warehouse_health",
    "objective": "Monitor warehouse health with auto-remediation",
    "dry_run": false,
    "allow_actions": true,
    "config": {
      "es": {"index": "emails-*"},
      "bq": {"dataset": "analytics", "table": "emails"},
      "dbt": {"target": "prod", "models": ["tag:daily"]}
    }
  }'
```

**Output:**
```json
{
  "parity": {
    "status": "ok",
    "es_count": 15000,
    "bq_count": 15100,
    "difference_percent": 0.66,
    "threshold_percent": 5.0,
    "daily_breakdown": [...]
  },
  "freshness": {
    "status": "ok",
    "latest_event_ts": "2025-10-17T10:25:00Z",
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
```

**See Also**: [RUNBOOK_WAREHOUSE_HEALTH.md](./RUNBOOK_WAREHOUSE_HEALTH.md)

---

## Next Steps

### 📚 Learn More

- **[Agents Observability Guide](./AGENTS_OBSERVABILITY.md)** - Deep dive into metrics, logs, and SSE
- **[Warehouse Health Runbook](./RUNBOOK_WAREHOUSE_HEALTH.md)** - Operations guide for warehouse monitoring
- **[Phase 2 Implementation Docs](./PHASE2-PR1-PROVIDERS.md)** - Architecture and design decisions

### 🏗️ Build Agents

1. **Clone Warehouse Health Agent** - Use as template for new agents
2. **Add Integration Tests** - Use `tests/integration/test_agents_integration.py` pattern
3. **Document Alert Conditions** - Define thresholds and runbooks
4. **Configure Dashboards** - Grafana panels for metrics

### 🔧 Operations

1. **Set Up Monitoring** - Configure Prometheus scraping and Grafana dashboards
2. **Create Alerts** - Define alert rules for failure rates and slow executions
3. **Schedule Runs** - Use cron or Airflow to trigger agents periodically
4. **Review Audit Logs** - Query `agent_audit_log` table for compliance

### 🚀 Production Readiness

- [ ] Configure production provider credentials (ES, BQ, dbt)
- [ ] Set up Prometheus scraping endpoint (`/metrics`)
- [ ] Create Grafana dashboards for agent metrics
- [ ] Define SLOs and alert thresholds
- [ ] Document incident response procedures
- [ ] Test failover and retry logic
- [ ] Set up audit log retention policy

---

## Troubleshooting

### Agent Execution Fails

**Symptom**: `status: "failed"` in response

**Check**:
1. Review error message in response
2. Query audit logs: `SELECT * FROM agent_audit_log WHERE id = '<run_id>'`
3. Check provider credentials (ES_HOST, BQ_PROJECT, etc.)
4. Verify service availability (ping ES, test BQ query)

### SSE Connection Drops

**Symptom**: EventSource `onerror` triggered

**Check**:
1. Verify server is running: `curl http://localhost:8000/health`
2. Check nginx/proxy buffering settings (`X-Accel-Buffering: no`)
3. Review browser console for CORS errors
4. Test direct connection: `curl -N http://localhost:8000/agents/events`

### Metrics Not Appearing

**Symptom**: No data in Prometheus/Grafana

**Check**:
1. Verify metrics endpoint: `curl http://localhost:8000/metrics`
2. Check Prometheus scrape config targets
3. Verify agent execution (metrics only appear after runs)
4. Review Prometheus logs for scrape errors

### Audit Logs Missing

**Symptom**: No rows in `agent_audit_log` table

**Check**:
1. Verify database connection: `SELECT 1 FROM agent_audit_log LIMIT 1`
2. Check migration applied: `alembic current` (should show 0022 or later)
3. Review API logs for database errors
4. Test audit: Run agent and immediately query table

---

## FAQ

**Q: Can agents run in parallel?**  
A: Yes, multiple agents can run simultaneously. The executor is stateless.

**Q: How do I schedule agents?**  
A: Use cron, Airflow, or similar scheduler to POST to `/agents/execute` endpoint.

**Q: Can I retry failed runs?**  
A: Yes, get the run ID from audit logs and POST with same config (or use `retry_run_id` parameter if implemented).

**Q: How long are audit logs retained?**  
A: Indefinitely by default. Set up retention policy based on compliance requirements.

**Q: Can I add custom metrics?**  
A: Yes, use `app.observability.metrics.AGENT_RUNS_TOTAL.labels(...)` in your agent.

**Q: How do I test agents locally?**  
A: Use `dry_run: true` and mock providers in tests. See `tests/test_agent_warehouse.py`.

---

## Summary

**You've learned**:
- ✅ What agents are and how they work
- ✅ How to execute agents via API
- ✅ How to monitor agents with metrics, logs, and SSE
- ✅ How to create custom agents
- ✅ Available agents and their capabilities

**Next**: Dive into [AGENTS_OBSERVABILITY.md](./AGENTS_OBSERVABILITY.md) for advanced monitoring and debugging techniques.
