# Playbooks Guide - Phase 5.4

**Step-by-step remediation procedures for common incidents.**

---

## Overview

**Playbooks** are automated remediation actions that fix common failures. Each playbook has:

- **Dry-run mode**: Preview changes before execution
- **Approval requirement**: High-risk actions need approval
- **Rollback capability**: Some actions can be undone
- **Estimated cost/duration**: Know before you execute

---

## Available Playbooks

### **DBT Playbooks**

#### **1. Rerun DBT Models** (`rerun_dbt`)

**When to use:**
- Invariant failure due to stale data
- DBT run failed (transient error)
- Data quality dropped after missed run

**What it does:**
- Re-runs specified dbt models
- Optional: Include upstream dependencies
- Optional: Full refresh (truncate + rebuild)

**Parameters:**
```json
{
  "task_id": "task-123",
  "models": ["inbox_emails", "triage_results"],
  "full_refresh": false,
  "upstream": false,
  "threads": 4
}
```

**Dry-run output:**
```
Command: dbt run --models inbox_emails triage_results --threads 4
Estimated duration: 10 minutes (5 min per model)
Estimated cost: $0.10
Changes:
  - Will re-run 2 dbt models
  - Models: inbox_emails, triage_results
  - No full refresh (incremental only)
```

**Requires approval:** Yes, if `full_refresh=true`

**Execution steps:**

1. **Dry-run first:**
   ```bash
   POST /api/playbooks/incidents/{id}/actions/dry-run
   {
     "action_type": "rerun_dbt",
     "params": {
       "task_id": "task-123",
       "models": ["inbox_emails"],
       "full_refresh": false
     }
   }
   ```

2. **Review output:**
   - Check estimated duration (fits in maintenance window?)
   - Verify models correct (no typos?)
   - Check cost estimate (within budget?)

3. **Execute:**
   ```bash
   POST /api/playbooks/incidents/{id}/actions/execute
   {
     "action_type": "rerun_dbt",
     "params": {...},
     "approved_by": "engineer@example.com"  # If full_refresh=true
   }
   ```

4. **Monitor:**
   - Watch dbt logs at `result.logs_url`
   - Check eval results after completion
   - Verify quality score recovered

**Rollback:** Not available (use `rollback_dbt` if needed)

**Common issues:**
- **Compilation error**: Check dbt project structure
- **Timeout**: Reduce models or increase threads
- **Permission denied**: Check database credentials

---

#### **2. Refresh DBT Dependencies** (`refresh_dbt_dependencies`)

**When to use:**
- Package version outdated
- Dependency conflict
- Macro not found error

**What it does:**
- Runs `dbt deps` to update packages
- Runs `dbt compile` to verify syntax

**Parameters:**
```json
{
  "task_id": "task-456"
}
```

**Dry-run output:**
```
Commands:
  1. dbt deps
  2. dbt compile
Estimated duration: 2 minutes
Estimated cost: $0.01
```

**Requires approval:** No (low risk)

**Execution steps:**

1. **Dry-run:**
   ```bash
   POST /api/playbooks/incidents/{id}/actions/dry-run
   {
     "action_type": "refresh_dbt_dependencies",
     "params": {"task_id": "task-456"}
   }
   ```

2. **Execute:**
   ```bash
   POST /api/playbooks/incidents/{id}/actions/execute
   {
     "action_type": "refresh_dbt_dependencies",
     "params": {"task_id": "task-456"}
   }
   ```

3. **Verify:**
   - Check `packages.yml` updated
   - Run `dbt compile` succeeds
   - No new errors in logs

**Rollback:** Not needed (idempotent)

---

### **Elasticsearch Playbooks**

#### **3. Clear Elasticsearch Cache** (`clear_cache`)

**When to use:**
- Latency spike (P95 > budget)
- Stale query results
- Memory pressure on ES cluster

**What it does:**
- Clears query/request/fielddata caches
- No data loss (caches rebuild automatically)

**Parameters:**
```json
{
  "index_name": "knowledge_base",
  "cache_types": ["query", "request", "fielddata"]
}
```

**Dry-run output:**
```
Will clear caches for index: knowledge_base
Cache types: query, request, fielddata
Estimated duration: 5 seconds
Estimated cost: $0 (no compute)
Changes:
  - Caches will be cleared
  - May cause temporary latency spike (1-2 seconds)
  - Caches rebuild automatically on next query
```

**Requires approval:** No (safe operation)

**Execution steps:**

1. **Dry-run:**
   ```bash
   POST /api/playbooks/incidents/{id}/actions/dry-run
   {
     "action_type": "clear_cache",
     "params": {
       "index_name": "knowledge_base",
       "cache_types": ["query", "request"]
     }
   }
   ```

2. **Execute immediately:**
   ```bash
   POST /api/playbooks/incidents/{id}/actions/execute
   {
     "action_type": "clear_cache",
     "params": {...}
   }
   ```

3. **Monitor:**
   - Check P95 latency (should drop within 1 minute)
   - Watch for cache rebuild (may cause brief spike)
   - Verify query results still correct

**Rollback:** Not applicable (caches rebuild)

**Best practices:**
- Clear during low traffic periods if possible
- Monitor cache hit rate after clearing
- Consider query optimization if frequent clears needed

---

#### **4. Refresh Synonyms** (`refresh_synonyms`)

**When to use:**
- Synonym file updated
- Search quality dropped
- New domain terms added

**What it does:**
- Closes index (brief downtime)
- Reloads synonym filter settings
- Reopens index
- Optional: Reindex documents

**Parameters:**
```json
{
  "index_name": "knowledge_base",
  "synonym_filter": "synonyms_filter",
  "reindex": false
}
```

**Dry-run output:**
```
Will refresh synonyms for: knowledge_base
Synonym filter: synonyms_filter
Reindex: false (existing docs use old synonyms)
Estimated duration: 30 seconds (6 hours if reindex=true)
Estimated cost: $0 ($10 if reindex=true)
Changes:
  - Index will be closed briefly (1-2 seconds)
  - Synonym filter will be reloaded
  - New queries will use updated synonyms
  - Existing documents NOT reindexed
```

**Requires approval:** Yes, if `reindex=true` (expensive)

**Execution steps:**

1. **Dry-run without reindex** (fast):
   ```bash
   POST /api/playbooks/incidents/{id}/actions/dry-run
   {
     "action_type": "refresh_synonyms",
     "params": {
       "index_name": "knowledge_base",
       "synonym_filter": "synonyms_filter",
       "reindex": false
     }
   }
   ```

2. **Execute:**
   ```bash
   POST /api/playbooks/incidents/{id}/actions/execute
   {
     "action_type": "refresh_synonyms",
     "params": {...}
     # No approval needed if reindex=false
   }
   ```

3. **Optional: Reindex later** (slow, needs approval):
   ```bash
   # Schedule during maintenance window
   POST /api/playbooks/incidents/{id}/actions/execute
   {
     "action_type": "refresh_synonyms",
     "params": {
       "index_name": "knowledge_base",
       "synonym_filter": "synonyms_filter",
       "reindex": true  # Rebuilds all documents
     },
     "approved_by": "engineer@example.com"
   }
   ```

**Rollback:** Revert synonym file, run again

**Important notes:**
- Without reindex: New queries use new synonyms, existing docs don't
- With reindex: All docs updated, but takes hours and costs money
- Consider reindexing during low-traffic hours

---

### **Planner Playbooks**

#### **5. Rollback Planner** (`rollback_planner`)

**When to use:**
- Canary regression detected
- Accuracy drop > 10%
- Latency spike > 50%
- Error rate increase

**What it does:**
- Rolls back to previous stable version
- Optional: Immediate (30 sec) or gradual (15 min)

**Parameters:**
```json
{
  "from_version": "v1.2.3-canary",
  "to_version": "v1.2.2",
  "immediate": false
}
```

**Dry-run output:**
```
Will rollback planner:
  From: v1.2.3-canary
  To: v1.2.2
  Mode: gradual (15 minutes)
Estimated duration: 15 minutes
Estimated cost: $0 (deployment only)
Changes:
  - Traffic will gradually shift from canary to stable
  - Canary will be decommissioned
  - Stable version will handle 100% traffic
```

**Requires approval:** Yes, if `immediate=true` (risky)

**Execution steps:**

1. **Dry-run gradual rollback** (safer):
   ```bash
   POST /api/playbooks/incidents/{id}/actions/dry-run
   {
     "action_type": "rollback_planner",
     "params": {
       "from_version": "v1.2.3-canary",
       "to_version": "v1.2.2",
       "immediate": false
     }
   }
   ```

2. **Execute:**
   ```bash
   POST /api/playbooks/incidents/{id}/actions/execute
   {
     "action_type": "rollback_planner",
     "params": {...}
     # No approval if immediate=false
   }
   ```

3. **Monitor:**
   - Watch accuracy metric (should recover)
   - Check latency P95 (should stabilize)
   - Verify error rate drops

**Rollback available:** Yes (can re-deploy canary via `deploy_planner`)

**When to use immediate:**
- SEV1 incident (customer-impacting)
- Error rate > 10%
- Data corruption risk
- Approval obtained from manager

---

#### **6. Adjust Canary Split** (`adjust_canary_split`)

**When to use:**
- Canary metrics acceptable but not optimal
- Want to increase canary traffic gradually
- Reduce canary traffic without full rollback

**What it does:**
- Adjusts traffic split between stable and canary
- Optional: Gradual (10 min) or immediate (1 min)

**Parameters:**
```json
{
  "version": "v1.2.3-canary",
  "target_percent": 25,
  "gradual": true
}
```

**Dry-run output:**
```
Will adjust canary traffic:
  Version: v1.2.3-canary
  Current: 10%
  Target: 25%
  Mode: gradual (10 minutes)
Estimated duration: 10 minutes
Changes:
  - Traffic will shift from 10% to 25% gradually
  - Stable version traffic: 90% → 75%
  - Monitor for regressions during shift
```

**Requires approval:** Yes, if increasing traffic

**Execution steps:**

1. **Dry-run:**
   ```bash
   POST /api/playbooks/incidents/{id}/actions/dry-run
   {
     "action_type": "adjust_canary_split",
     "params": {
       "version": "v1.2.3-canary",
       "target_percent": 25,
       "gradual": true
     }
   }
   ```

2. **Execute (with approval if increasing):**
   ```bash
   POST /api/playbooks/incidents/{id}/actions/execute
   {
     "action_type": "adjust_canary_split",
     "params": {...},
     "approved_by": "engineer@example.com"  # If increasing
   }
   ```

3. **Monitor during adjustment:**
   - Watch accuracy (should stay stable)
   - Check latency (no spikes)
   - Verify error rate unchanged

**Rollback available:** Yes (adjust back to original percentage)

---

## Playbook Combinations

### **Scenario 1: Data Quality Drop**

**Incident:** Quality score dropped from 95 to 78

**Playbook sequence:**
1. `refresh_dbt_dependencies` (check for stale packages)
2. `rerun_dbt` (rebuild models with fresh deps)
3. Wait 15 min for eval to run
4. If still failing: Escalate to data team

### **Scenario 2: Latency Spike**

**Incident:** P95 latency jumped from 500ms to 1850ms

**Playbook sequence:**
1. `clear_cache` (immediate, no approval)
2. Monitor for 5 minutes
3. If not improved: `refresh_synonyms` (without reindex)
4. If still bad: Check for inefficient queries (manual investigation)

### **Scenario 3: Planner Canary Regression**

**Incident:** Canary accuracy dropped 13% from baseline

**Playbook sequence:**
1. **DO NOT** run `rerun_eval` (won't help)
2. `adjust_canary_split` → reduce to 5% (contain blast radius)
3. Monitor for 10 minutes
4. If still regressing: `rollback_planner` (immediate, with approval)
5. Post-rollback: Investigate root cause before re-deploying

---

## Best Practices

### **Always Dry-Run First**

```bash
# ALWAYS do this first
POST /api/playbooks/incidents/{id}/actions/dry-run

# Review output, then execute
POST /api/playbooks/incidents/{id}/actions/execute
```

### **Check Approval Requirements**

High-risk actions need approval:
- `rerun_dbt` with `full_refresh=true`
- `refresh_synonyms` with `reindex=true`
- `rollback_planner` with `immediate=true`
- `adjust_canary_split` when increasing traffic

### **Monitor During Execution**

- Watch logs at `result.logs_url`
- Check metrics dashboards
- Set 15-minute timer (typical duration)
- Be ready to rollback if issues arise

### **Document Actions Taken**

```bash
# Add notes when resolving
POST /api/incidents/{id}/resolve
{
  "notes": "Executed: rerun_dbt (models: inbox_emails). Result: Quality recovered to 95%. Duration: 12 minutes."
}
```

### **Learn from Failures**

If playbook doesn't work:
- Check logs for errors
- Try alternative playbook
- Document in incident notes
- Escalate if multiple playbooks fail
- Update runbook with findings

---

## Troubleshooting

### **Dry-Run Fails**

```
Error: Parameter validation failed
```

**Fix:** Check parameter types/values match schema

### **Execution Hangs**

**Possible causes:**
- DBT run stuck (kill and retry)
- Elasticsearch reindex slow (check progress)
- Planner deployment timeout (check deployment logs)

**Actions:**
- Check `result.logs_url` for progress
- Wait for estimated duration before canceling
- If timeout > 2x estimate, escalate

### **Action Fails**

**Common errors:**

**DBT:**
- "Compilation error" → Check models syntax
- "Connection timeout" → Check database
- "Permission denied" → Check credentials

**Elasticsearch:**
- "Index not found" → Check index name spelling
- "Cluster timeout" → ES under load, retry later
- "Forbidden" → Check ES credentials

**Planner:**
- "Deployment failed" → Check deployment logs
- "Version not found" → Check version exists
- "Rollback unavailable" → Can't undo this action

---

## Action History

View all actions taken:

```bash
GET /api/playbooks/incidents/{id}/actions/history
```

**Response:**
```json
[
  {
    "id": 1,
    "action_type": "rerun_dbt",
    "params": {"models": ["inbox_emails"]},
    "dry_run": true,
    "status": "dry_run_success",
    "created_at": "2025-10-17T10:00:00Z"
  },
  {
    "id": 2,
    "action_type": "rerun_dbt",
    "params": {"models": ["inbox_emails"]},
    "dry_run": false,
    "status": "success",
    "approved_by": "engineer@example.com",
    "created_at": "2025-10-17T10:05:00Z",
    "result": {
      "actual_duration": 720,
      "logs_url": "https://logs.example.com/123"
    }
  }
]
```

---

## Summary

**Key takeaways:**

✅ **Always dry-run first** to preview changes  
✅ **Check approval requirements** before executing  
✅ **Monitor during execution** (watch logs and metrics)  
✅ **Document actions taken** in incident notes  
✅ **Escalate if playbooks fail** (don't keep trying blindly)  
✅ **Learn from failures** (update runbooks)  

**For detailed API documentation, see [API_REFERENCE.md](./API_REFERENCE.md)**
