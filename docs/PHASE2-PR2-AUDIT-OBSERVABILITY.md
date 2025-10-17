# Phase 2 PR2: Agent Audit Logging & Observability

**Date**: January 2025  
**Status**: ✅ Complete  
**Dependencies**: Phase 2 PR1 (Provider infrastructure)

## What Was Built

This PR adds comprehensive observability to the agent system through database audit logging and Prometheus metrics.

### 1. Agent Audit Log Model

**File**: `services/api/app/models.py`

SQLAlchemy model for persisting agent execution records:

```python
class AgentAuditLog(Base):
    __tablename__ = "agent_audit_log"
    
    # Identifiers
    id: Integer (primary key, autoincrement)
    run_id: String(128) (unique index)
    agent: String(128) (indexed)
    
    # Execution details
    objective: String(512)
    status: String(32) (indexed)  # running, succeeded, failed, canceled
    
    # Timestamps
    started_at: DateTime(tz=True) (indexed)
    finished_at: DateTime(tz=True)
    duration_ms: Float
    
    # Execution data (JSONB)
    plan: JSONB  # Planner output
    artifacts: JSONB  # Handler results
    error: String(2048)  # Error message if failed
    
    # Metadata
    user_email: String(320) (indexed)
    dry_run: Boolean (default=True)
    created_at: DateTime(tz=True) (server_default=now())
```

**Indexes** (7 total):
- `run_id` (unique) - Fast lookup by run ID
- `agent` - Filter by agent name
- `status` - Filter by status
- `user_email` - Track user activity
- `started_at` - Time-based queries
- `agent + status` (composite) - Agent-specific status reports
- `started_at DESC` - Efficient recent runs queries

**File**: `services/api/alembic/versions/0022_agent_audit_log.py`

Alembic migration to create the table with all indexes.

### 2. Audit Service

**File**: `services/api/app/agents/audit.py`

Service module for recording agent executions to database:

```python
class AgentAuditor:
    """Auditor for agent executions."""
    
    def log_start(run_id, agent, objective, plan, user_email=None):
        """Log agent run start with plan details."""
    
    def log_finish(run_id, status, artifacts=None, error=None, duration_ms=None):
        """Log agent run completion with results/errors."""
    
    def get_run(run_id) -> AgentAuditLog | None:
        """Retrieve audit log for a specific run."""
    
    def get_recent_runs(agent=None, limit=100) -> list[AgentAuditLog]:
        """Get recent runs, optionally filtered by agent."""
```

**Key Features**:
- **Environment toggle**: Controlled by `APPLYLENS_AGENT_AUDIT_ENABLED` (default=true)
- **Fail-safe**: Catches exceptions and prints warnings - never fails agent runs
- **Flexible session**: Accepts optional DB session for testing
- **Global instance**: `get_auditor()` returns singleton instance

### 3. Executor Integration

**File**: `services/api/app/agents/executor.py`

Updated executor to automatically record executions:

**Lifecycle**:
1. `execute()` called with plan
2. `auditor.log_start()` - Record start time, plan, user
3. Handler executes
4. `auditor.log_finish()` - Record status, duration, artifacts/error
5. Return run record

**Timing**: Uses `time.perf_counter()` for high-precision duration measurement.

**Parameters**:
- Added `user_email` parameter to `execute()` for audit attribution
- Added `auditor` parameter to `__init__()` (optional, defaults to None)

### 4. Prometheus Metrics

**File**: `services/api/app/observability/metrics.py`

Standard Prometheus metrics for agent monitoring:

```python
# Counter: Total runs by agent and status
agent_runs_total = Counter(
    "agent_runs_total",
    "Total number of agent runs",
    ["agent", "status"]
)

# Histogram: Execution latency distribution
agent_run_latency_ms = Histogram(
    "agent_run_latency_ms",
    "Agent run execution latency in milliseconds",
    ["agent"],
    buckets=(50, 100, 250, 500, 1000, 2500, 5000, 10000, 30000)
)

# Helper function
def record_agent_run(agent, status, duration_ms):
    """Record both counter and histogram."""
```

**Exported via**: `services/api/app/observability/__init__.py`

**Buckets**: Designed for sub-second to 30-second run times (can be adjusted).

### 5. Router Integration

**File**: `services/api/app/routers/agents.py`

Wired auditor into module-level executor:

```python
from ..agents.audit import get_auditor

_auditor = get_auditor()
_executor = Executor(_run_store, _auditor)
```

All agent runs now automatically logged to database and metrics.

---

## Design Principles

### 1. **Observability by Default**

Every agent run is tracked with:
- **Audit Trail**: Persistent records in database
- **Metrics**: Real-time Prometheus counters/histograms
- **Correlation**: Unique `run_id` links logs, audit, and metrics

### 2. **Safe by Default**

- Audit logging enabled by default (`AGENT_AUDIT_ENABLED=true`)
- Failures in audit/metrics **never** fail agent runs
- Database errors logged as warnings, execution continues

### 3. **Performance Optimized**

- High-precision timing with `time.perf_counter()`
- JSONB columns for flexible artifact storage without schema changes
- 7 strategic indexes for common query patterns
- Histogram buckets tuned for typical agent execution times

### 4. **Production Ready**

- Environment-based toggles for audit/metrics
- Optional user attribution for compliance
- Composite indexes for analytics queries
- Error messages truncated to 2048 chars (prevent overflow)

---

## Usage Examples

### Database Queries

**Recent runs across all agents**:
```sql
SELECT run_id, agent, objective, status, duration_ms, started_at
FROM agent_audit_log
ORDER BY started_at DESC
LIMIT 50;
```

**Failed runs for specific agent**:
```sql
SELECT run_id, objective, error, started_at
FROM agent_audit_log
WHERE agent = 'warehouse.health' AND status = 'failed'
ORDER BY started_at DESC;
```

**Average latency by agent**:
```sql
SELECT agent, 
       AVG(duration_ms) as avg_ms,
       COUNT(*) as total_runs,
       SUM(CASE WHEN status = 'succeeded' THEN 1 ELSE 0 END) as successes
FROM agent_audit_log
WHERE started_at > NOW() - INTERVAL '7 days'
GROUP BY agent;
```

**Execution plans for debugging**:
```sql
SELECT run_id, plan, artifacts, error
FROM agent_audit_log
WHERE run_id = 'abc123-def456';
```

### Prometheus Queries

**Success rate by agent** (PromQL):
```promql
rate(agent_runs_total{status="succeeded"}[5m]) 
/ 
rate(agent_runs_total[5m])
```

**P95 latency by agent**:
```promql
histogram_quantile(0.95, 
  rate(agent_run_latency_ms_bucket[5m])
)
```

**Failure spike detection**:
```promql
increase(agent_runs_total{status="failed"}[1h]) > 10
```

**Slow runs alert** (>5 seconds):
```promql
rate(agent_run_latency_ms_bucket{le="5000"}[5m]) < 0.95
```

### Python Usage

**Manual audit logging** (testing):
```python
from app.agents.audit import AgentAuditor

auditor = AgentAuditor(db_session)

# Start run
auditor.log_start(
    run_id="test-123",
    agent="warehouse.health",
    objective="check parity",
    plan={"dry_run": True, "tools": ["es", "bq"]},
    user_email="user@example.com"
)

# Finish successfully
auditor.log_finish(
    run_id="test-123",
    status="succeeded",
    artifacts={"parity_ok": True, "freshness_ok": True},
    duration_ms=1250.5
)

# Or finish with error
auditor.log_finish(
    run_id="test-456",
    status="failed",
    error="ValueError: ES connection timeout",
    duration_ms=5001.2
)
```

**Query audit logs**:
```python
# Get specific run
run = auditor.get_run("test-123")
print(run.status, run.duration_ms, run.artifacts)

# Get recent runs for agent
runs = auditor.get_recent_runs(agent="warehouse.health", limit=10)
for r in runs:
    print(f"{r.started_at}: {r.objective} -> {r.status}")
```

**Disable audit logging** (testing):
```python
# Environment variable
APPLYLENS_AGENT_AUDIT_ENABLED=false

# Or programmatically
from app.agents.audit import set_auditor

set_auditor(None)  # No-op auditor for tests
```

---

## Implementation Stats

| Category | Count | Details |
|----------|-------|---------|
| **Files Created** | 3 | `agents/audit.py`, `observability/__init__.py`, `observability/metrics.py` |
| **Files Modified** | 3 | `models.py`, `agents/executor.py`, `routers/agents.py` |
| **Database Migrations** | 1 | `0022_agent_audit_log.py` (creates table + 7 indexes) |
| **Lines of Code** | ~350 | Audit: 193, Metrics: 36, Executor: 45, Migration: 90 |
| **Model Columns** | 13 | 8 primitive + 2 JSONB + 3 timestamps |
| **Indexes** | 7 | 5 single-column + 2 composite |
| **Prometheus Metrics** | 2 | 1 counter (labels: agent, status) + 1 histogram (label: agent) |

**Database Schema Size**: ~400 bytes/row + JSONB (varies)

---

## Testing Strategy

### Unit Tests

**Audit Service**:
```python
def test_auditor_log_start():
    auditor = AgentAuditor(mock_db_session)
    auditor.log_start("run-1", "test.agent", "objective", {})
    # Assert record created with status="running"

def test_auditor_log_finish_success():
    # Assert status updated, duration_ms set, artifacts stored

def test_auditor_log_finish_failure():
    # Assert error message stored, status="failed"

def test_auditor_disabled():
    # Assert no DB writes when AGENT_AUDIT_ENABLED=false
```

**Executor Integration**:
```python
def test_executor_records_audit():
    auditor = AgentAuditor(mock_session)
    executor = Executor(store, auditor)
    
    run = executor.execute(plan, handler)
    
    # Assert auditor.log_start called with plan
    # Assert auditor.log_finish called with status, duration
```

**Metrics**:
```python
def test_metrics_recorded_on_success():
    # Execute plan
    # Assert agent_runs_total{status="succeeded"} incremented
    # Assert agent_run_latency_ms observed

def test_metrics_recorded_on_failure():
    # Execute failing plan
    # Assert agent_runs_total{status="failed"} incremented
```

### Integration Tests

**Database Persistence**:
```python
def test_audit_log_persisted():
    # Run agent via API
    # Query database for AgentAuditLog record
    # Assert run_id, agent, status, duration_ms match

def test_query_recent_runs():
    # Create multiple runs
    # Query get_recent_runs(agent="test")
    # Assert correct ordering and filtering
```

**End-to-End**:
```python
def test_agent_run_full_observability():
    # Execute agent via API
    # Check audit_log table has record
    # Check /metrics endpoint shows incremented counters
    # Verify plan and artifacts stored in JSONB
```

**Migration**:
```bash
# Apply migration
alembic upgrade head

# Verify table created
psql -c "\d agent_audit_log"

# Verify indexes exist
psql -c "\di agent_audit_log*"

# Rollback test
alembic downgrade -1
```

---

## Configuration

**Environment Variables**:

```bash
# Enable/disable audit logging (default: true)
APPLYLENS_AGENT_AUDIT_ENABLED=true

# Database connection (from main settings)
DATABASE_URL=postgresql://...
```

**Production Recommendations**:

1. **Retention Policy**: Set up table partitioning or scheduled cleanup:
   ```sql
   DELETE FROM agent_audit_log 
   WHERE started_at < NOW() - INTERVAL '90 days';
   ```

2. **Monitoring**: Alert on high error rates:
   ```promql
   rate(agent_runs_total{status="failed"}[5m]) > 0.1
   ```

3. **Dashboard**: Create Grafana dashboard with:
   - Total runs per hour (by agent)
   - Success rate % (last 24h)
   - P50/P95/P99 latency
   - Error count by agent

4. **Database Indexing**: Consider additional indexes if needed:
   ```sql
   CREATE INDEX ix_audit_user_started ON agent_audit_log(user_email, started_at DESC);
   ```

---

## Next Steps (Remaining PRs)

### PR3: Server-Sent Events (SSE)
- Real-time run updates via `/agents/events` endpoint
- Event bus for live log streaming
- Client-side hooks for progress indicators

### PR4: Warehouse Health Agent v2
- Real parity computation (ES vs BQ)
- Freshness SLO checks (30min threshold)
- Auto-remediation with allow_actions flag

### PR5: CI Integration Lane
- Split test jobs: unit (mock) vs integration (real)
- Add Elasticsearch service to CI
- Secrets gating for real provider tests

### PR6: Complete Documentation
- `AGENTS_QUICKSTART.md` - Getting started guide
- `AGENTS_OBSERVABILITY.md` - Metrics, logs, dashboards
- `RUNBOOK_WAREHOUSE_HEALTH.md` - Operations guide

---

## Migration Notes

### Breaking Changes
- **None**: This is a pure addition

### Backward Compatibility
- All existing agents work without changes
- Tests still pass (auditor is optional)
- No API changes

### Dependencies
- **New**: `prometheus-client` (already in requirements.txt)
- **Database**: Requires running migration `0022_agent_audit_log.py`

### Rollout Plan
1. ✅ Deploy code (backward compatible)
2. ✅ Run migration: `alembic upgrade head`
3. ✅ Verify `/metrics` endpoint shows agent metrics
4. ✅ Query `agent_audit_log` table after first agent run
5. ⏳ Set up Grafana dashboard (Phase 2 PR6)
6. ⏳ Configure alerting rules (Phase 2 PR6)

---

## Files Changed

**Created**:
- `services/api/app/agents/audit.py` (193 lines)
- `services/api/app/observability/__init__.py` (10 lines)
- `services/api/app/observability/metrics.py` (36 lines)
- `services/api/alembic/versions/0022_agent_audit_log.py` (90 lines)

**Modified**:
- `services/api/app/models.py` (+45 lines) - AgentAuditLog model
- `services/api/app/agents/executor.py` (+20 lines) - Audit hooks, metrics
- `services/api/app/routers/agents.py` (+3 lines) - Wire auditor

**Total**: 7 files, ~400 lines of code

---

## Success Metrics

**Must Have**:
- [x] AgentAuditLog model with 13 columns
- [x] Migration creates table with 7 indexes
- [x] AgentAuditor service with start/finish hooks
- [x] Executor emits audit logs and metrics
- [x] All existing tests pass
- [x] No breaking changes

**Verification**:
```bash
# Run migration
alembic upgrade head

# Execute agent
curl -X POST http://localhost:8003/agents/warehouse.health/run \
  -d '{"objective":"test audit","dry_run":true}'

# Check database
psql -c "SELECT * FROM agent_audit_log ORDER BY started_at DESC LIMIT 5;"

# Check metrics
curl http://localhost:8003/metrics | grep agent_runs_total
```

**Expected Output**:
```
# Database
run_id | agent            | status    | duration_ms | started_at
-------|------------------|-----------|-------------|------------------------
abc... | warehouse.health | succeeded | 125.5       | 2025-01-XX 10:30:00+00

# Metrics
agent_runs_total{agent="warehouse.health",status="succeeded"} 1.0
agent_run_latency_ms_sum{agent="warehouse.health"} 125.5
```

✅ **PR2 Complete**: Audit logging and metrics operational
