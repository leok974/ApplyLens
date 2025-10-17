# Warehouse Health Agent Runbook

**Operational guide for monitoring and troubleshooting the Warehouse Health Agent**

This runbook provides step-by-step procedures for operating the Warehouse Health Agent, responding to alerts, and debugging data quality issues.

---

## Table of Contents

1. [Overview](#overview)
2. [Normal Operations](#normal-operations)
3. [Alert Response](#alert-response)
4. [Troubleshooting](#troubleshooting)
5. [Maintenance](#maintenance)
6. [Escalation](#escalation)

---

## Overview

### What is Warehouse Health Agent?

**Purpose**: Monitor data warehouse health with real-time parity checks, freshness SLO enforcement, and auto-remediation.

**Key Responsibilities**:
- ✅ Compare Elasticsearch vs BigQuery event counts (parity check)
- ✅ Verify data freshness against 30-minute SLO
- ✅ Run dbt health checks (`tag:daily` models)
- ✅ Trigger auto-remediation when data quality degrades (optional)
- ✅ Report detailed issues with severity levels

**Version**: 2.0.0 (production monitoring)

### Architecture

```
┌──────────────────────────────────────────────────────────┐
│         Warehouse Health Agent (v2.0.0)                 │
└───────┬──────────┬──────────┬───────────┬───────────────┘
        │          │          │           │
        ▼          ▼          ▼           ▼
  ┌─────────┐ ┌────────┐ ┌────────┐ ┌──────────┐
  │   ES    │ │   BQ   │ │  dbt   │ │  Audit   │
  │ Count   │ │ Count  │ │  Run   │ │   Log    │
  └────┬────┘ └───┬────┘ └───┬────┘ └─────┬────┘
       │          │          │            │
       └──────────┴──────────┴────────────┘
                     │
                     ▼
           ┌──────────────────┐
           │  Health Report   │
           │ - Parity: OK     │
           │ - Freshness: OK  │
           │ - dbt: Success   │
           │ - Status: Healthy│
           └──────────────────┘
```

### Configuration

**Thresholds**:
- **Parity Threshold**: 5.0% (max acceptable ES/BQ count difference)
- **Freshness SLO**: 30 minutes (max acceptable data age)

**Execution Modes**:
- `dry_run: true` - Safe mode (no dbt runs)
- `dry_run: false, allow_actions: true` - Production mode (auto-remediation enabled)

### Key Metrics

**Prometheus**:
- `agent_runs_total{agent_type="warehouse_health", status="success|failed"}`
- `agent_run_duration_seconds{agent_type="warehouse_health"}`

**Audit Logs**:
- Table: `agent_audit_log`
- Filter: `agent_type = 'warehouse_health'`

---

## Normal Operations

### Daily Health Check (Scheduled)

**Frequency**: Every 30 minutes (via cron or Airflow)

**Command**:
```bash
curl -X POST http://localhost:8000/agents/execute \
  -H "Content-Type: application/json" \
  -d '{
    "agent_type": "warehouse_health",
    "objective": "Scheduled warehouse health check",
    "dry_run": false,
    "allow_actions": true,
    "config": {
      "es": {"index": "emails-production-*"},
      "bq": {"dataset": "analytics_prod", "table": "emails"},
      "dbt": {"target": "prod", "models": ["tag:daily"]}
    }
  }'
```

**Expected Response** (Healthy):
```json
{
  "run_id": "...",
  "status": "success",
  "artifacts": {
    "parity": {
      "status": "ok",
      "es_count": 1500000,
      "bq_count": 1505000,
      "difference_percent": 0.33
    },
    "freshness": {
      "status": "ok",
      "latest_event_ts": "2025-10-17T10:25:00Z",
      "age_minutes": 5.0,
      "within_slo": true
    },
    "dbt": {
      "success": true,
      "models_run": 3
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

**Action**: No action required if `status: "healthy"`

### On-Demand Check (Manual)

**Use Case**: Investigate data quality concerns, post-incident validation

**Command** (Dry Run for Safety):
```bash
curl -X POST http://localhost:8000/agents/execute \
  -H "Content-Type: application/json" \
  -d '{
    "agent_type": "warehouse_health",
    "objective": "Manual investigation of data quality",
    "dry_run": true,
    "config": {
      "es": {"index": "emails-production-*"},
      "bq": {"dataset": "analytics_prod", "table": "emails"},
      "dbt": {"target": "prod", "models": ["tag:daily"]}
    }
  }'
```

**Review**: Check `artifacts` for parity, freshness, and dbt results

### Monitoring Dashboard

**Grafana Panel: Warehouse Health Status**

**Metrics to Monitor**:
1. **Parity Status** - Should be "ok" (green)
2. **Parity Difference** - Should be < 5.0%
3. **Freshness Status** - Should be "ok" (green)
4. **Data Age** - Should be < 30 minutes
5. **Run Success Rate** - Should be > 95%

**SQL Query** (Recent Status):
```sql
SELECT 
  started_at,
  artifacts->'summary'->>'status' AS overall_status,
  artifacts->'parity'->>'status' AS parity_status,
  (artifacts->'parity'->>'difference_percent')::numeric AS parity_diff_pct,
  artifacts->'freshness'->>'within_slo' AS freshness_ok,
  (artifacts->'freshness'->>'age_minutes')::numeric AS data_age_minutes
FROM agent_audit_log
WHERE agent_type = 'warehouse_health'
  AND status = 'success'
ORDER BY started_at DESC
LIMIT 10;
```

---

## Alert Response

### Alert: Parity Degraded

**Trigger**: ES/BQ count difference > 5%

**Severity**: ⚠️ Warning (15-minute grace period)

**Alert Message**:
```
Warehouse Parity Degraded
ES/BQ parity off by 8.2%
ES count: 1,500,000 | BQ count: 1,377,000
```

**Response Procedure**:

#### Step 1: Verify Alert
```bash
# Check recent runs
curl "http://localhost:8000/agents/history?agent_type=warehouse_health&limit=5"

# Look for parity.status == "degraded"
```

#### Step 2: Investigate Cause
```sql
-- Check daily breakdown for divergence pattern
SELECT 
  run_id,
  started_at,
  artifacts->'parity'->'daily_breakdown' AS daily_data
FROM agent_audit_log
WHERE agent_type = 'warehouse_health'
  AND status = 'success'
ORDER BY started_at DESC
LIMIT 1;
```

**Common Causes**:
- **ES indexing lag** - Events in ES but not yet in BQ
- **BQ sync failure** - Fivetran/Airbyte job failed
- **Data deletion** - Events removed from ES but still in BQ
- **Index pattern issue** - Wrong index queried in ES

#### Step 3: Check Data Pipeline
```bash
# Check Fivetran/Airbyte sync status
curl https://api.fivetran.com/v1/connectors/YOUR_CONNECTOR

# Check BQ load jobs
bq ls -j --max_results=10 --format=prettyjson YOUR_PROJECT | grep "state"

# Check ES index health
curl "http://es-host:9200/_cat/indices/emails-*?v"
```

#### Step 4: Manual Remediation (If Auto-Remediation Disabled)
```bash
# Trigger dbt run to refresh BQ tables
curl -X POST http://localhost:8000/agents/execute \
  -H "Content-Type: application/json" \
  -d '{
    "agent_type": "warehouse_health",
    "dry_run": false,
    "allow_actions": true,
    "config": {...}
  }'
```

#### Step 5: Verify Resolution
Wait 30 minutes and check next scheduled run. Parity should return to "ok".

**Escalation**: If parity remains degraded after 2 hours, escalate to Data Engineering team.

---

### Alert: Freshness SLO Violated

**Trigger**: Latest event age > 30 minutes

**Severity**: 🔴 Critical (immediate action required)

**Alert Message**:
```
Warehouse Freshness SLO Violated
Data stale by 45.7 minutes
Latest event: 2025-10-17T09:30:00Z (1 hour 15 minutes ago)
```

**Response Procedure**:

#### Step 1: Verify Alert
```bash
# Check latest event timestamp
curl "http://localhost:8000/agents/history?agent_type=warehouse_health&limit=1" | jq '.runs[0].artifacts.freshness'
```

**Expected Output**:
```json
{
  "status": "degraded",
  "latest_event_ts": "2025-10-17T09:30:00Z",
  "age_minutes": 75.3,
  "slo_minutes": 30,
  "within_slo": false
}
```

#### Step 2: Check Data Sources

**Elasticsearch**:
```bash
# Check latest indexed event
curl -X GET "http://es-host:9200/emails-*/_search" \
  -H "Content-Type: application/json" \
  -d '{
    "size": 1,
    "sort": [{"received_at": "desc"}],
    "query": {"match_all": {}}
  }'
```

**Gmail API**:
```bash
# Check if new emails are being received
curl -X GET "http://localhost:8000/emails/recent?limit=10"
```

#### Step 3: Check Ingestion Pipeline

**Common Causes**:
- **Gmail sync stopped** - OAuth token expired, API quota exceeded
- **ES indexing paused** - Elasticsearch cluster health red/yellow
- **Ingestion service down** - Check service logs

**Diagnostic Commands**:
```bash
# Check Gmail service health
curl "http://localhost:8000/health" | jq '.gmail'

# Check ES cluster health
curl "http://es-host:9200/_cluster/health?pretty"

# Check ingestion service logs
docker logs applylens-ingestion-worker --tail=100
```

#### Step 4: Restart Ingestion (If Service Down)
```bash
# Restart ingestion workers
docker restart applylens-ingestion-worker

# Trigger manual sync
curl -X POST "http://localhost:8000/ingest/trigger"
```

#### Step 5: Trigger Auto-Remediation
```bash
# Run warehouse health with auto-remediation
curl -X POST http://localhost:8000/agents/execute \
  -H "Content-Type: application/json" \
  -d '{
    "agent_type": "warehouse_health",
    "dry_run": false,
    "allow_actions": true,
    "config": {...}
  }'

# Check if remediation triggered
curl "http://localhost:8000/agents/history?limit=1" | jq '.runs[0].artifacts.remediation'
```

#### Step 6: Verify Resolution
```bash
# Wait 5-10 minutes, then check freshness
curl "http://localhost:8000/agents/history?agent_type=warehouse_health&limit=1" | jq '.runs[0].artifacts.freshness'
```

**Expected**: `within_slo: true`, `age_minutes: < 30`

**Escalation**: If freshness not restored within 1 hour, page on-call engineer and Data Platform team.

---

### Alert: Agent Execution Failed

**Trigger**: `status: "failed"` in agent run

**Severity**: ⚠️ Warning (investigate within 1 hour)

**Alert Message**:
```
Warehouse Health Agent Failed
Error: Elasticsearch connection timeout after 30s
Run ID: 550e8400-e29b-41d4-a716-446655440000
```

**Response Procedure**:

#### Step 1: Get Error Details
```sql
-- Query audit log
SELECT 
  run_id,
  error_message,
  plan,
  started_at
FROM agent_audit_log
WHERE id = '550e8400-e29b-41d4-a716-446655440000';
```

#### Step 2: Identify Failure Type

**ES Connection Timeout**:
```
Error: Elasticsearch connection timeout after 30s
```
→ Check ES cluster health: `curl http://es-host:9200/_cluster/health`

**BQ Query Failed**:
```
Error: BigQuery query failed: Access Denied
```
→ Check BQ credentials and permissions

**dbt Run Failed**:
```
Error: dbt run failed with exit code 1
```
→ Review dbt logs for model errors

#### Step 3: Fix Root Cause

**ES Issues**:
```bash
# Check ES cluster status
curl "http://es-host:9200/_cat/health?v"

# Check ES node stats
curl "http://es-host:9200/_cat/nodes?v"

# Restart ES if needed (with approval)
sudo systemctl restart elasticsearch
```

**BQ Issues**:
```bash
# Test BQ connection
bq query --use_legacy_sql=false "SELECT 1"

# Check service account permissions
gcloud projects get-iam-policy YOUR_PROJECT
```

**dbt Issues**:
```bash
# Run dbt locally to debug
cd dbt-project
dbt run --models tag:daily --target prod

# Check model dependencies
dbt ls --models tag:daily
```

#### Step 4: Retry Agent Run
```bash
curl -X POST http://localhost:8000/agents/execute \
  -H "Content-Type: application/json" \
  -d '{
    "agent_type": "warehouse_health",
    "dry_run": true,
    "config": {...}
  }'
```

#### Step 5: Document Incident
```
Incident: Warehouse Health Agent Failed
Cause: [ES timeout / BQ auth failure / dbt model error]
Resolution: [Restarted ES / Refreshed credentials / Fixed model SQL]
Duration: [X minutes]
```

---

### Alert: No Agent Runs (Scheduler Stopped)

**Trigger**: No runs in last hour

**Severity**: 🔴 Critical

**Alert Message**:
```
No Warehouse Health Agent Runs
No executions detected in the last 60 minutes
```

**Response Procedure**:

#### Step 1: Check Scheduler
```bash
# If using cron
crontab -l | grep warehouse_health
sudo systemctl status cron

# If using Airflow
airflow dags list | grep warehouse_health
airflow dags trigger warehouse_health_check
```

#### Step 2: Check API Health
```bash
# Test API endpoint
curl "http://localhost:8000/health"

# Test agent execute endpoint
curl -X POST http://localhost:8000/agents/execute \
  -H "Content-Type: application/json" \
  -d '{
    "agent_type": "warehouse_health",
    "dry_run": true,
    "config": {...}
  }'
```

#### Step 3: Review Logs
```bash
# API logs
docker logs applylens-api --tail=100 | grep warehouse_health

# Scheduler logs (if Airflow)
airflow logs warehouse_health_dag
```

#### Step 4: Restart Scheduler
```bash
# Cron
sudo systemctl restart cron

# Airflow
airflow scheduler restart
```

#### Step 5: Verify Resumption
Wait 30 minutes and check audit logs:
```sql
SELECT COUNT(*) 
FROM agent_audit_log
WHERE agent_type = 'warehouse_health'
  AND started_at > NOW() - INTERVAL '1 hour';
```

**Expected**: Count > 0

---

## Troubleshooting

### Issue: Parity Always Degraded

**Symptoms**:
- Every run shows `parity.status == "degraded"`
- Difference percent consistently > 5%

**Diagnosis**:

1. **Check Index Pattern**:
   ```bash
   # Verify ES index exists
   curl "http://es-host:9200/_cat/indices/emails-*?v"
   
   # Compare count
   curl -X GET "http://es-host:9200/emails-*/_count"
   ```

2. **Check BQ Table**:
   ```sql
   -- Count BQ rows
   SELECT COUNT(*) FROM `analytics_prod.emails`;
   
   -- Check date range
   SELECT MIN(received_at), MAX(received_at) 
   FROM `analytics_prod.emails`;
   ```

3. **Review Daily Breakdown**:
   ```sql
   SELECT artifacts->'parity'->'daily_breakdown'
   FROM agent_audit_log
   WHERE agent_type = 'warehouse_health'
   ORDER BY started_at DESC
   LIMIT 1;
   ```

**Common Fixes**:
- **Wrong index**: Update config to use correct ES index pattern
- **Data retention mismatch**: ES has 7-day retention, BQ has 90 days
- **Incremental load issue**: BQ missing recent days (check Fivetran sync)

---

### Issue: Freshness Always Stale

**Symptoms**:
- `freshness.within_slo == false` on every run
- Data age consistently > 30 minutes

**Diagnosis**:

1. **Check ES Latest Event**:
   ```bash
   curl -X GET "http://es-host:9200/emails-*/_search" \
     -H "Content-Type: application/json" \
     -d '{
       "size": 1,
       "sort": [{"received_at": "desc"}]
     }' | jq '.hits.hits[0]._source.received_at'
   ```

2. **Check Gmail Sync**:
   ```bash
   # Get latest email from Gmail API
   curl "http://localhost:8000/emails/recent?limit=1"
   ```

3. **Check Ingestion Lag**:
   ```sql
   -- Compare Gmail received_at vs ES indexed_at
   SELECT 
     received_at,
     indexed_at,
     EXTRACT(EPOCH FROM (indexed_at - received_at)) AS lag_seconds
   FROM emails
   ORDER BY received_at DESC
   LIMIT 10;
   ```

**Common Fixes**:
- **Gmail sync stopped**: Restart ingestion workers
- **ES indexing backlog**: Scale up ES cluster or reduce ingestion rate
- **Timezone issue**: Verify `received_at` is in UTC

---

### Issue: Auto-Remediation Not Triggering

**Symptoms**:
- `remediation.triggered == false` even when parity degraded or freshness stale
- No dbt runs executed

**Diagnosis**:

1. **Check Configuration**:
   ```bash
   # Verify allow_actions is true
   curl "http://localhost:8000/agents/history?limit=1" | jq '.runs[0].plan'
   ```
   
   **Expected**: `"allow_actions": true`

2. **Check Dry Run Mode**:
   ```bash
   # Verify dry_run is false
   curl "http://localhost:8000/agents/history?limit=1" | jq '.runs[0].plan.dry_run'
   ```
   
   **Expected**: `false`

3. **Review Agent Logic**:
   ```python
   # In warehouse.py
   if plan["allow_actions"] and (not parity_ok or not within_slo):
       remediation["triggered"] = True
   ```

**Fix**: Ensure request has:
```json
{
  "dry_run": false,
  "allow_actions": true
}
```

---

### Issue: dbt Run Fails

**Symptoms**:
- `dbt.success == false`
- Agent run completes but dbt step failed

**Diagnosis**:

1. **Check dbt Logs**:
   ```sql
   SELECT 
     artifacts->'dbt' AS dbt_result
   FROM agent_audit_log
   WHERE agent_type = 'warehouse_health'
     AND status = 'success'
   ORDER BY started_at DESC
   LIMIT 1;
   ```

2. **Run dbt Manually**:
   ```bash
   cd dbt-project
   dbt run --models tag:daily --target prod
   ```

3. **Check Model Dependencies**:
   ```bash
   dbt ls --models tag:daily --resource-type model
   ```

**Common Fixes**:
- **Model SQL error**: Fix model query in `models/` directory
- **Missing dependency**: Run upstream models first
- **BQ permissions**: Grant service account access to datasets

---

## Maintenance

### Weekly Review

**Tasks**:
1. **Review Success Rate** (should be > 95%)
   ```sql
   SELECT 
     COUNT(*) FILTER (WHERE status = 'success') * 100.0 / COUNT(*) AS success_rate
   FROM agent_audit_log
   WHERE agent_type = 'warehouse_health'
     AND started_at > NOW() - INTERVAL '7 days';
   ```

2. **Check Average Duration** (should be < 30s)
   ```sql
   SELECT AVG(duration_seconds) AS avg_duration
   FROM agent_audit_log
   WHERE agent_type = 'warehouse_health'
     AND status = 'success'
     AND started_at > NOW() - INTERVAL '7 days';
   ```

3. **Review Failed Runs**
   ```sql
   SELECT run_id, error_message, started_at
   FROM agent_audit_log
   WHERE agent_type = 'warehouse_health'
     AND status = 'failed'
     AND started_at > NOW() - INTERVAL '7 days'
   ORDER BY started_at DESC;
   ```

4. **Tune Thresholds** (if needed)
   - Increase `PARITY_THRESHOLD_PERCENT` if false positives
   - Decrease `FRESHNESS_SLO_MINUTES` for stricter SLO

### Monthly Cleanup

**Audit Log Retention**:
```sql
-- Archive old logs (optional)
COPY (
  SELECT * FROM agent_audit_log
  WHERE agent_type = 'warehouse_health'
    AND started_at < NOW() - INTERVAL '90 days'
) TO '/backup/agent_audit_archive_YYYYMM.csv' CSV HEADER;

-- Delete old logs (after archiving)
DELETE FROM agent_audit_log
WHERE agent_type = 'warehouse_health'
  AND created_at < NOW() - INTERVAL '90 days';
```

---

## Escalation

### When to Escalate

**Escalate to Data Engineering Team if**:
- Parity degraded for > 2 hours
- Freshness SLO violated for > 1 hour
- Multiple consecutive agent failures (> 3 in 30 minutes)
- Auto-remediation triggered repeatedly (> 5 times in 1 hour)

**Escalate to On-Call Engineer if**:
- Critical data pipeline failure (ES down, BQ unavailable)
- Complete ingestion stopped (no new events for > 1 hour)
- Security incident (unauthorized access, data breach)

### Escalation Contacts

**Data Engineering Team**:
- Slack: `#data-engineering`
- PagerDuty: Data Platform On-Call

**Platform Team**:
- Slack: `#platform-ops`
- PagerDuty: Infrastructure On-Call

**Incident Response**:
- Create incident: `POST /incidents` (internal tool)
- Severity: P1 (critical data issue), P2 (degraded service)
- Include: Run ID, error message, attempted fixes

---

## Quick Reference

### Commands

```bash
# Manual health check (dry run)
curl -X POST http://localhost:8000/agents/execute \
  -d '{"agent_type": "warehouse_health", "dry_run": true, "config": {...}}'

# Manual health check (with auto-remediation)
curl -X POST http://localhost:8000/agents/execute \
  -d '{"agent_type": "warehouse_health", "dry_run": false, "allow_actions": true, "config": {...}}'

# Check recent runs
curl "http://localhost:8000/agents/history?agent_type=warehouse_health&limit=10"

# View metrics
curl "http://localhost:8000/metrics" | grep warehouse_health
```

### SQL Queries

```sql
-- Recent status
SELECT * FROM agent_audit_log 
WHERE agent_type = 'warehouse_health' 
ORDER BY started_at DESC LIMIT 5;

-- Failed runs
SELECT * FROM agent_audit_log 
WHERE agent_type = 'warehouse_health' AND status = 'failed' 
ORDER BY started_at DESC;

-- Remediation history
SELECT 
  started_at,
  artifacts->'remediation'->>'triggered' AS triggered,
  artifacts->'remediation'->>'reason' AS reason
FROM agent_audit_log
WHERE agent_type = 'warehouse_health'
  AND artifacts->'remediation'->>'triggered' = 'true'
ORDER BY started_at DESC;
```

### Thresholds

| Metric | Threshold | Severity |
|--------|-----------|----------|
| Parity Difference | > 5% | Warning |
| Data Age | > 30 min | Critical |
| Success Rate | < 95% | Warning |
| Duration p95 | > 60s | Warning |
| No Runs | > 1 hour | Critical |

---

## Summary

**This runbook covered**:
- ✅ Normal operations and scheduled checks
- ✅ Alert response procedures for parity, freshness, failures
- ✅ Troubleshooting common issues
- ✅ Maintenance tasks and cleanup
- ✅ Escalation paths and contacts
- ✅ Quick reference commands and queries

**For more information**:
- [Agents Quickstart Guide](./AGENTS_QUICKSTART.md)
- [Agents Observability Guide](./AGENTS_OBSERVABILITY.md)
- [Phase 2 PR4 Documentation](./PHASE2-PR4-WAREHOUSE-HEALTH-V2.md)
