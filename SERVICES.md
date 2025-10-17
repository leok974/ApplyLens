# ApplyLens Services Guide

## Overview

ApplyLens consists of multiple services working together to provide intelligent email and application management.

---

## Agents System (Phase 1 - Agentic Skeleton)

The agents system provides an extensible framework for autonomous operations with typed tool wrappers and safe defaults.

### Architecture

- **Planner**: Creates execution plans from objectives (deterministic in Phase 1)
- **Executor**: Runs plans with tracking and error handling
- **Registry**: Manages available agents
- **Tools**: Typed wrappers for Gmail, BigQuery, dbt, Elasticsearch

### Available Agents

#### Warehouse Health Agent (`warehouse.health`)

Monitors data pipeline health:
- Email data freshness in Elasticsearch
- BigQuery warehouse freshness  
- ES ↔ BQ parity checks
- dbt run health pulse

### API Endpoints

#### List All Agents
```bash
GET /agents
```

**Response:**
```json
{
  "agents": ["warehouse.health"]
}
```

#### Run an Agent
```bash
POST /agents/{agent_name}/run
Content-Type: application/json

{
  "objective": "check warehouse health",
  "dry_run": true,
  "params": {}
}
```

**Response:**
```json
{
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "succeeded",
  "started_at": "2025-10-17T10:00:00Z",
  "finished_at": "2025-10-17T10:00:05Z",
  "logs": ["start agent=warehouse.health objective=check warehouse health"],
  "artifacts": {
    "parity_ok": true,
    "es_hits_count": 2,
    "bq_rows_count": 2,
    "dbt": {"success": true, "elapsed_sec": 0.123},
    "summary": {
      "status": "healthy",
      "checks_passed": 4,
      "total_checks": 4
    }
  }
}
```

#### List Agent Runs
```bash
GET /agents/{agent_name}/runs
```

**Response:**
```json
{
  "runs": [
    {
      "run_id": "...",
      "status": "succeeded",
      "started_at": "...",
      "artifacts": {...}
    }
  ]
}
```

### Quickstart Examples

#### Using curl
```bash
# List available agents
curl http://localhost:8003/agents

# Run warehouse health check
curl -X POST http://localhost:8003/agents/warehouse.health/run \
  -H "Content-Type: application/json" \
  -d '{"objective":"daily parity check","dry_run":true}'

# List past runs
curl http://localhost:8003/agents/warehouse.health/runs
```

#### Using Python
```python
import httpx

client = httpx.Client(base_url="http://localhost:8003")

# List agents
agents = client.get("/agents").json()
print(agents)

# Run warehouse health agent
result = client.post("/agents/warehouse.health/run", json={
    "objective": "check data freshness",
    "dry_run": True
}).json()

print(f"Status: {result['status']}")
print(f"Health: {result['artifacts']['summary']['status']}")
```

### Development

#### Run API Server
```bash
make api-dev
# or
uvicorn services.api.app.main:app --reload --port 8003
```

#### Run Tests
```bash
make api-test
# or
pytest -q services/api/tests/test_agents_core.py services/api/tests/test_agent_warehouse.py
```

### Safety & Design Principles

1. **Dry-run by default**: All agents default to `dry_run=True` for safety
2. **Typed interfaces**: Pydantic models ensure data validation
3. **Deterministic testing**: Phase 1 uses mock data for reproducible tests
4. **Observability**: All runs are logged and tracked
5. **Safe defaults**: Tools default to read-only operations

### Phase 2 Roadmap

- LLM-based planning (replacing deterministic planner)
- Real provider integration (Gmail API, BigQuery client, dbt Cloud)
- Budget controls (time, cost limits)
- SSE streaming for live run updates
- Audit logging to database
- UI panel for agent monitoring

---

## Other Services

(Other service documentation goes here...)
