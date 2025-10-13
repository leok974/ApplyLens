# Backfill Duration SLO — Triage Runbook

## Alert: BackfillDurationSLO

**Trigger:** Backfill p95 duration > 5 minutes for 30+ minutes

**Severity:** Ticket (investigate within 4 hours)

---

## Initial Response (10 minutes)

### 1. Check Current Performance

```bash
# Query Prometheus metrics
curl -s http://localhost:8003/metrics | grep applylens_backfill_duration

# Check p95 from Grafana
# Navigate to: http://localhost:3000/d/applylens-ops-overview
# Panel: "Backfill p95 Duration"
```

### 2. Review Recent Backfill Jobs

```bash
# Check logs for backfill activity
docker-compose logs api | grep -i "backfill\|analyze_risk" | tail -n 100

# Look for timing information
docker-compose logs api | grep "Processed.*batch.*in.*seconds"
```

---

## Understanding SLO

**Service Level Objective:**

- **p95 Duration:** < 5 minutes (300 seconds)
- **Measurement Window:** 15-minute rolling window
- **Alert Threshold:** Sustained violation for 30+ minutes

**Why This Matters:**

- Slow backfills → delayed risk scores
- Delayed scores → UI lag
- Resource contention → API slowdown

---

## Common Causes & Fixes

### 1. Large Batch Size

**Symptoms:**

- Single batches taking 5+ minutes
- High memory usage during backfill

**Fix:**

```powershell
# Reduce batch size
cd D:\ApplyLens\services\api

# Default is 100, try 50
python scripts/analyze_risk.py --batch-size 50

# Or even smaller for testing
python scripts/analyze_risk.py --batch-size 25 --max-batches 2
```

### 2. Database Lock Contention

**Symptoms:**

- Backfill slows during high traffic periods
- Logs show "waiting for lock" messages

**Investigation:**

```sql
-- Check for locks
SELECT pid, state, wait_event_type, wait_event, query
FROM pg_stat_activity
WHERE state != 'idle'
ORDER BY state;

-- Check long-running queries
SELECT pid, now() - query_start AS duration, query
FROM pg_stat_activity
WHERE state = 'active' AND query NOT LIKE '%pg_stat_activity%'
ORDER BY duration DESC;
```

**Fix:**

```bash
# Run backfill during low-traffic hours
# Add to cron: 2 AM daily
# 0 2 * * * cd /app && python scripts/analyze_risk.py --batch-size 50

# Or use smaller transactions
python scripts/analyze_risk.py --batch-size 25
```

### 3. Elasticsearch Slow Indexing

**Symptoms:**

- DB updates fast, but ES indexing slow
- Logs show ES timeout warnings

**Investigation:**

```bash
# Check ES cluster health
curl http://localhost:9200/_cluster/health?pretty

# Check indexing rate
curl http://localhost:9200/_stats/indexing?pretty

# Check disk space
curl http://localhost:9200/_cat/allocation?v
```

**Fix:**

```bash
# Increase ES heap size (if low)
# Edit: infra/docker-compose.yml
# ES_JAVA_OPTS: "-Xms2g -Xmx2g"  # Increase from 1g to 2g

# Restart ES
docker-compose restart elasticsearch

# Clear old indices if disk full
curl -X DELETE http://localhost:9200/.old_index_*
```

### 4. Too Many Emails to Process

**Symptoms:**

- Backfill processes thousands of emails
- Job runs for hours

**Fix:**

```powershell
# Process in smaller chunks with max-batches
cd D:\ApplyLens\services\api

# Process 500 emails (10 batches of 50)
python scripts/analyze_risk.py --batch-size 50 --max-batches 10

# Schedule incremental updates instead of full backfills
# Update only emails from last 7 days
# TODO: Add --since flag to analyze_risk.py
```

### 5. CPU/Memory Bottleneck

**Symptoms:**

- High CPU usage during backfill
- System sluggish during processing

**Investigation:**

```bash
# Check container resource usage
docker stats --no-stream

# Check API container specifically
docker stats api --no-stream
```

**Fix:**

```yaml
# Increase container resources
# Edit: infra/docker-compose.yml
services:
  api:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
```

---

## Optimization Strategies

### Short-term (Immediate Relief)

1. Reduce batch size: 100 → 50
2. Limit max batches: Add --max-batches 20
3. Run during off-peak hours (2-6 AM)

### Medium-term (This Week)

1. Add batch timing metrics for better observability
2. Implement incremental backfill (--since flag)
3. Optimize DB queries (add indexes if needed)

### Long-term (This Quarter)

1. Implement async job queue (Celery/RQ)
2. Distribute backfill across workers
3. Add progress tracking and resumable jobs

---

## Testing Performance Improvements

```powershell
# Baseline test (current performance)
cd D:\ApplyLens\services\api
Measure-Command { python scripts/analyze_risk.py --batch-size 100 --max-batches 1 }

# After optimization
Measure-Command { python scripts/analyze_risk.py --batch-size 50 --max-batches 1 }

# Compare durations
# Target: < 30 seconds per batch for p95 < 5 min overall
```

---

## Monitoring Queries

### Grafana (PromQL)

```promql
# p95 duration
histogram_quantile(0.95, 
  sum(rate(applylens_backfill_duration_seconds_bucket[15m])) by (le)
)

# p50 duration (median)
histogram_quantile(0.50, 
  sum(rate(applylens_backfill_duration_seconds_bucket[15m])) by (le)
)

# Average duration
sum(rate(applylens_backfill_duration_seconds_sum[5m])) 
  / sum(rate(applylens_backfill_duration_seconds_count[5m]))

# Backfill rate (jobs per minute)
rate(applylens_backfill_duration_seconds_count[5m]) * 60
```

### Database Queries

```sql
-- Check emails needing risk scores
SELECT COUNT(*) 
FROM emails 
WHERE risk_score IS NULL;

-- Check risk score distribution
SELECT 
  COUNT(*) FILTER (WHERE risk_score IS NULL) as null_scores,
  COUNT(*) FILTER (WHERE risk_score IS NOT NULL) as scored,
  COUNT(*) as total,
  ROUND(COUNT(*) FILTER (WHERE risk_score IS NOT NULL) * 100.0 / COUNT(*), 2) as coverage_pct
FROM emails;

-- Find slow queries related to backfill
SELECT 
  query,
  calls,
  total_time,
  mean_time,
  max_time
FROM pg_stat_statements
WHERE query LIKE '%UPDATE emails SET risk_score%'
ORDER BY mean_time DESC;
```

---

## Runbook Execution Checklist

- [ ] Check current p95 duration in Grafana
- [ ] Review recent backfill logs for errors
- [ ] Check DB and ES resource usage
- [ ] Test with reduced batch size
- [ ] Document baseline performance
- [ ] Apply optimization
- [ ] Measure improved performance
- [ ] Update documentation if needed

---

## Post-Incident

1. **Document findings:**
   - What was the root cause?
   - What optimization worked?
   - New baseline performance?

2. **Update configuration:**
   - Adjust default batch size if needed
   - Update SLO threshold if too aggressive

3. **Share learnings:**
   - Update this runbook
   - Brief team on optimization

---

## Related Links

- [Risk Scoring Script](../../scripts/analyze_risk.py)
- [Backfill Metrics](http://localhost:8003/metrics)
- [Grafana Dashboard](http://localhost:3000/d/applylens-ops-overview)
- [Phase 12.1 Documentation](../../docs/PHASE_12.1_PLAN.md)
