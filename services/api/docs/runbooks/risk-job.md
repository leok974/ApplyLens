# Risk Job Failures — Triage Runbook

## Alert: RiskJobFailures

**Trigger:** Risk recompute failures detected in last 30 minutes

**Severity:** Page (immediate response required)

---

## Initial Response (5 minutes)

### 1. Check Risk Job Status

```bash
# Check /automation/health endpoint
curl http://localhost:8003/automation/health | jq .

# Check metrics
curl -s http://localhost:8003/metrics | grep applylens_risk
```

### 2. Review Recent Failures

```bash
# Check API logs for risk job errors
docker-compose logs api | grep -i "risk" | grep -i "error" | tail -n 50

# Check for specific error patterns
docker-compose logs api | grep "analyze_risk\|compute_risk_score" | tail -n 100
```

---

## Common Causes & Fixes

### 1. Missing Risk Score Column

**Symptoms:**

- Logs show "column emails.risk_score does not exist"
- Migration version < 0010

**Fix:**

```bash
# Check migration status
curl http://localhost:8003/ready | jq .migration

# Run migrations
docker-compose exec api alembic upgrade head

# Verify risk_score column exists
docker-compose exec db psql -U postgres -d applylens -c "
  SELECT column_name, data_type 
  FROM information_schema.columns 
  WHERE table_name = 'emails' AND column_name IN ('risk_score', 'expires_at', 'category');"
```

### 2. Elasticsearch Sync Issues

**Symptoms:**

- Risk scores computed but not visible in UI
- Parity check shows high mismatch ratio

**Fix:**

```bash
# Check ES connectivity
curl http://localhost:9200/_cat/indices?v | grep emails

# Reindex with risk scores
cd D:\ApplyLens\services\api
python scripts/analyze_risk.py --backfill --batch-size 50

# Verify parity
python scripts/check_parity.py --fields risk_score --sample 100
```

### 3. Dry Run Test (Safe)

**Symptoms:**

- Unsure if job will work without breaking production

**Fix:**

```bash
# Run in dry-run mode (no DB writes)
cd D:\ApplyLens\services\api
$env:DRY_RUN="1"
python scripts/analyze_risk.py --batch-size 10

# Check output
# Should show: "DRY RUN: would update X emails"
```

### 4. Timeout/Performance Issues

**Symptoms:**

- Jobs start but don't complete
- Logs show timeout errors
- Backfill duration > 5 minutes (alert threshold)

**Fix:**

```bash
# Reduce batch size
python scripts/analyze_risk.py --batch-size 25

# Check database load
docker-compose exec db psql -U postgres -c "
  SELECT count(*) AS active_queries
  FROM pg_stat_activity
  WHERE state = 'active';"

# Optimize with smaller scope
python scripts/analyze_risk.py --batch-size 10 --max-batches 5
```

### 5. Configuration Issues

**Symptoms:**

- Risk scores all 0 or all 100
- Logs show "weight sum != 1.0"

**Fix:**

```python
# Check risk weights (in scripts/analyze_risk.py)
# Should sum to 1.0:
# WEIGHT_DOMAIN = 0.4
# WEIGHT_KEYWORDS = 0.4
# WEIGHT_CONFIDENCE = 0.2

# Verify configuration
cd D:\ApplyLens\services\api
python -c "
from scripts.analyze_risk import (
    WEIGHT_DOMAIN, WEIGHT_KEYWORDS, WEIGHT_CONFIDENCE
)
total = WEIGHT_DOMAIN + WEIGHT_KEYWORDS + WEIGHT_CONFIDENCE
print(f'Weight sum: {total}')
assert abs(total - 1.0) < 0.001, 'Weights must sum to 1.0'
"
```

---

## Manual Recompute

If automatic job is failing, run manually:

```powershell
# Windows/PowerShell
cd D:\ApplyLens\services\api

# Small test batch
python scripts/analyze_risk.py --batch-size 10 --max-batches 1

# Full recompute (takes time)
python scripts/analyze_risk.py --backfill --batch-size 50

# Check results
curl http://localhost:8003/automation/health | jq .coverage_percentage
```

---

## Verify Fix

After resolution:

```bash
# 1. Check health endpoint
curl http://localhost:8003/automation/health | jq .

# 2. Trigger recompute via API
curl -X POST http://localhost:8003/automation/recompute \
  -H "Content-Type: application/json" \
  -d '{"batch_size": 10, "dry_run": false}'

# 3. Check metrics
curl -s http://localhost:8003/metrics | grep applylens_risk_requests_total

# 4. Verify parity
cd D:\ApplyLens\services\api
python scripts/check_parity.py --fields risk_score --sample 100
```

---

## Monitoring Queries

### Grafana (PromQL)

```promql
# Failure rate
rate(applylens_risk_requests_total{outcome="failure"}[30m])

# Success rate
rate(applylens_risk_requests_total{outcome="success"}[30m])

# Avg batch duration
sum(rate(applylens_risk_batch_duration_seconds_sum[5m])) 
  / sum(rate(applylens_risk_batch_duration_seconds_count[5m]))

# p95 batch duration
histogram_quantile(0.95, 
  sum(rate(applylens_risk_batch_duration_seconds_bucket[15m])) by (le)
)
```

### Database Queries

```sql
-- Check risk score distribution
SELECT 
  CASE 
    WHEN risk_score IS NULL THEN 'null'
    WHEN risk_score = 0 THEN '0 (safe)'
    WHEN risk_score < 30 THEN '1-29 (low)'
    WHEN risk_score < 60 THEN '30-59 (medium)'
    WHEN risk_score < 90 THEN '60-89 (high)'
    ELSE '90-100 (critical)'
  END as risk_bucket,
  COUNT(*) as count,
  ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as percentage
FROM emails
GROUP BY risk_bucket
ORDER BY risk_bucket;

-- Find emails never scored
SELECT id, sender, subject, created_at
FROM emails
WHERE risk_score IS NULL
ORDER BY created_at DESC
LIMIT 10;
```

---

## Post-Incident

1. **Document root cause** in incident report
2. **Update unit tests** if logic bug found
3. **Adjust batch size** in automation if timeouts occurred
4. **Review alert threshold** (30m window may need adjustment)

---

## Related Links

- [Risk Scoring Logic Tests](../../tests/unit/test_risk_scoring.py)
- [Parity Check Script](../../scripts/check_parity.py)
- [Automation Health Endpoint](http://localhost:8003/automation/health)
- [Phase 12.2 Documentation](../PHASE_12.2_PLAN.md)
