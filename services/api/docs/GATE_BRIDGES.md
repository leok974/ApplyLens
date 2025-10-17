# Gate Bridges - Phase 5.4 PR5

**Bridge between evaluation gates and incident management system.**

Automatically creates incidents when quality gates fail, with deduplication and rate limiting.

---

## Architecture

```
┌─────────────────┐
│  Eval Gates     │
│  (run_gates.py) │
└────────┬────────┘
         │
         │ violations[]
         ▼
┌─────────────────┐      ┌──────────────────┐
│  Gate Bridge    │─────▶│  Incident Model  │
│  (bridges.py)   │      │  (models)        │
└────────┬────────┘      └──────────────────┘
         │
         │ events
         ▼
┌─────────────────┐      ┌──────────────────┐
│  SSE Publisher  │─────▶│  Web UI          │
│  (sse.py)       │      │  (React)         │
└─────────────────┘      └──────────────────┘
```

**Flow:**
1. Gate evaluator runs (CI or cron)
2. Finds budget violations
3. Bridge creates incidents (with deduplication)
4. SSE publishes event to web UI
5. Operators receive notification

---

## Components

### **GateBridge** (`app/intervene/bridges.py`)

Main bridge class with methods:

- `on_budget_violation(violation, budget, context)`: Budget threshold exceeded
- `on_invariant_failure(eval_result, invariant_result, context)`: Invariant failed
- `on_planner_regression(version, metrics, baseline, regression, context)`: Canary regression
- `on_gate_failure(agent, gate_result, violations, budget, context)`: Multiple violations

**Features:**
- **Deduplication**: Reuses watcher's `_has_open_incident()` logic
- **Rate limiting**: Max 3 incidents per key per hour (configurable)
- **SSE publishing**: Real-time notifications if SSE available
- **Playbook suggestions**: Context-aware action recommendations

---

## Usage

### **1. CLI (run_gates.py)**

Run quality gates and auto-create incidents:

```bash
# Check all agents, create incidents on failure
python -m app.eval.run_gates --create-incidents

# Check specific agent
python -m app.eval.run_gates --agent inbox.triage --create-incidents

# Use in CI (fail build on critical, create incidents)
python -m app.eval.run_gates --create-incidents --fail-on-warning
```

**Exit codes:**
- `0`: All gates passed
- `1`: Critical violations (build fails)
- `2`: Warnings (only with `--fail-on-warning`)

### **2. Programmatic Usage**

```python
from app.intervene.bridges import GateBridge, create_budget_incident
from app.eval.budgets import GateEvaluator, BudgetViolation, Budget
from app.db import SessionLocal

db = SessionLocal()

# Evaluate gates
evaluator = GateEvaluator(db)
result = evaluator.evaluate_agent("inbox.triage", lookback_days=7)

# Create incidents for failures
if not result["passed"]:
    bridge = GateBridge(db)
    
    for violation in result["violations"]:
        incident = await bridge.on_budget_violation(
            violation=violation,
            budget=result["budget"],
            context={
                "eval_run_id": "eval-123",
                "triggered_by": "cron",
            }
        )
        
        if incident:
            print(f"Created incident: {incident.id}")
```

### **3. Convenience Functions**

For simple use cases:

```python
from app.intervene.bridges import (
    create_budget_incident,
    create_invariant_incident,
    create_planner_incident,
)

# Budget violation
incident = await create_budget_incident(db, violation, budget)

# Invariant failure
incident = await create_invariant_incident(db, eval_result, invariant_result)

# Planner regression
incident = await create_planner_incident(
    db, version="v1.2.3", metrics={...}, baseline={...}, regression={...}
)
```

---

## Incident Creation Logic

### **Severity Mapping**

Violation severity → Incident severity:

| Violation | Incident | Description |
|-----------|----------|-------------|
| `critical` | `sev1` | Page on-call, immediate action |
| `error` | `sev2` | Alert team, fix within 4h |
| `warning` | `sev3` | Monitor, fix within 24h |

### **Playbook Suggestions**

Context-aware playbook recommendations:

| Violation Type | Agent Pattern | Playbooks |
|----------------|---------------|-----------|
| `quality` | `warehouse.*`, `dbt.*` | `rerun_eval`, `rerun_dbt` |
| `latency` | `knowledge.*`, `elastic.*` | `clear_cache`, `refresh_synonyms` |
| `cost` | any | `rerun_eval`, `adjust_canary_split` |
| `success_rate` | `dbt.*` | `rerun_eval`, `rerun_dbt` |
| `invariants` | any | `rerun_eval`, `rerun_dbt` |
| any | `planner.*` | `rollback_planner` (added) |

### **Deduplication**

Prevents duplicate incidents:

1. **Key generation**: `BUDGET_{agent}_{budget_type}` (e.g., `BUDGET_inbox.triage_quality`)
2. **Open check**: If incident with same key already open, skip
3. **Rate limit**: Max 3 incidents per key per hour

**Why?** Avoid alert fatigue from repeated failures.

### **Rate Limiting**

Max incidents per time window:

- **Default**: 3 incidents per hour per key
- **Budget violations**: 3 per hour
- **Invariant failures**: 3 per hour
- **Planner regressions**: 3 per hour

Configurable via watcher's `_is_rate_limited()` method.

---

## Integration Points

### **1. run_gates.py (CLI)**

Modified to accept `--create-incidents` flag:

```python
# Before: Only report violations
python -m app.eval.run_gates

# After: Report + create incidents
python -m app.eval.run_gates --create-incidents
```

**Implementation:**
```python
if bridge and not result["passed"]:
    incidents = asyncio.run(_create_incidents_for_agent(bridge, result))
    print(f"🚨 Created {len(incidents)} incident(s)")
```

### **2. Watcher (Background Job)**

Watcher can also use bridge for consistency:

```python
# In watcher.py check_budgets()
from app.intervene.bridges import GateBridge

bridge = GateBridge(self.db)
for violation in violations:
    incident = await bridge.on_budget_violation(violation, budget)
```

### **3. Planner Canary Monitor**

Future integration for planner regressions:

```python
# In planner canary monitoring
if regression_detected:
    bridge = GateBridge(db)
    incident = await bridge.on_planner_regression(
        version=canary_version,
        metrics=current_metrics,
        baseline_metrics=stable_metrics,
        regression_details={"metric": "accuracy", "drop": 0.13},
    )
```

### **4. Real-time Evals**

For immediate incident creation on eval failures:

```python
# In eval runner after invariant check
if not invariant_result.passed:
    bridge = GateBridge(db)
    incident = await bridge.on_invariant_failure(eval_result, invariant_result)
```

---

## Testing

Run bridge tests:

```bash
pytest tests/test_bridges.py -v
```

**Test coverage:**
- ✅ Incident creation from budget violations
- ✅ Deduplication (skip if open incident exists)
- ✅ Rate limiting (max 3 per hour)
- ✅ Severity mapping (critical → sev1, error → sev2, warning → sev3)
- ✅ Playbook suggestions (context-aware)
- ✅ Planner regression incidents
- ✅ SSE event publishing
- ✅ Context propagation
- ✅ Convenience functions

---

## Configuration

### **Enable in CI**

Add to `.github/workflows/gates.yml`:

```yaml
- name: Run Quality Gates
  run: |
    python -m app.eval.run_gates \
      --create-incidents \
      --fail-on-warning
  env:
    DATABASE_URL: ${{ secrets.DATABASE_URL }}
```

### **Enable in Cron**

Add to cron job or scheduler:

```bash
# Every hour, check gates and create incidents
0 * * * * cd /app && python -m app.eval.run_gates --create-incidents
```

### **Disable for Testing**

Skip incident creation in tests:

```bash
# No incidents created
python -m app.eval.run_gates

# Or set environment variable
INTERVENTIONS_ENABLED=false python -m app.eval.run_gates
```

---

## Monitoring

### **Incident Creation Metrics**

Track in logs:

```
INFO Created budget incident: 42 (BUDGET_inbox.triage_quality)
INFO Skipping duplicate budget incident: BUDGET_inbox.triage_quality
INFO Rate limited budget incident: BUDGET_warehouse.health_latency
```

### **SSE Event Publishing**

SSE events sent to web UI:

```json
{
  "event": "incident_created",
  "data": {
    "id": 42,
    "kind": "budget",
    "key": "BUDGET_inbox.triage_quality",
    "severity": "sev1",
    "summary": "Budget violation: inbox.triage quality",
    "status": "open",
    "created_at": "2024-01-15T10:30:00Z"
  }
}
```

### **Dashboard**

Monitor incidents in React UI:

- **Live badge**: Green "Live" if SSE connected
- **Filters**: Status (open/ack/resolved), Severity (sev1/sev2)
- **Counters**: SEV1 count, SEV2 count, Open count
- **Notifications**: Browser notifications for new incidents

---

## Production Considerations

### **1. Database Load**

- Bridge queries DB for deduplication (`_has_open_incident`)
- Consider caching open incident keys in Redis
- Or use DB index on `(kind, key, status)` for fast lookups

### **2. SSE Scalability**

- Current in-memory SSE publisher won't work with multiple workers
- **Production**: Use Redis pub/sub or NATS for distributed events
- **Migration**: Replace `SSEPublisher.subscribers` with Redis channels

### **3. Rate Limiting**

- Current rate limiting queries DB for incident history
- Consider Redis counters for better performance:
  ```python
  redis_key = f"incident_rate:{kind}:{key}"
  count = redis.incr(redis_key)
  redis.expire(redis_key, 3600)  # 1 hour
  if count > 3:
      return None  # Rate limited
  ```

### **4. Alert Fatigue**

- If same incident keeps firing, adjust rate limit window
- Or implement exponential backoff (1h → 4h → 12h)
- Or add "acknowledge for 24h" feature

---

## Future Enhancements

### **PR6 (Next): CI & Mocks**

- Mock bridge in CI tests (avoid real incidents)
- Golden snapshot tests for incident payloads
- CI pipeline configuration

### **PR7 (Later): Docs & Runbooks**

- Detailed runbooks for each playbook
- Severity tier documentation
- On-call escalation procedures

### **Production Features**

1. **Slack integration**: Post incidents to Slack channel
2. **PagerDuty integration**: Page on-call for sev1
3. **Auto-remediation**: Execute low-risk playbooks automatically
4. **Incident grouping**: Cluster related incidents
5. **Root cause analysis**: Link incidents to commits/deploys

---

## Troubleshooting

### **"Bridge not available" warning**

```
WARNING Bridge not available - incidents will not be created
```

**Solution**: Ensure `app/intervene/bridges.py` exists and imports correctly.

### **"SSE not available" warning**

```
WARNING SSE not available - incidents will not be published to web UI
```

**Solution**: Check `app/routers/sse.py` exists. SSE is optional, incidents still created.

### **Incidents not created**

1. Check `--create-incidents` flag is set
2. Check watcher not blocking (deduplication)
3. Check rate limit not hit (3 per hour)
4. Check DB transaction committed

### **Duplicate incidents**

1. Verify deduplication logic (`_has_open_incident`)
2. Check incident key format (`BUDGET_{agent}_{type}`)
3. Ensure old incidents marked "resolved" (not "open")

---

## Summary

**Gate Bridges** complete the Phase 5.4 intervention loop:

1. ✅ **Watcher** detects failures (PR1)
2. ✅ **Issue Openers** create external issues (PR2)
3. ✅ **Playbooks** provide remediation actions (PR3)
4. ✅ **SSE** delivers real-time notifications (PR4)
5. ✅ **Bridges** connect eval gates to incidents (PR5) ← **This PR**

**Next**: PR6 (CI & Mocks), PR7 (Docs & Runbooks)
