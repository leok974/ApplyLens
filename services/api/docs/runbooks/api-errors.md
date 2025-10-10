# API Errors — Triage Runbook

## Alert: APIHighErrorRateFast

**Trigger:** 5xx error rate > 5% for 10+ minutes

**Severity:** Page (immediate response required)

---

## Initial Response (5 minutes)

### 1. Verify Alert is Real
```bash
# Check current error rate
curl -s http://localhost:8003/metrics | grep http_requests_total | grep "status=\"5"

# Check health endpoints
curl http://localhost:8003/healthz
curl http://localhost:8003/ready
```

### 2. Check System Status
- Database: Is PostgreSQL responding?
- Elasticsearch: Is ES cluster healthy?
- API Server: Are all instances running?

```powershell
# Windows/PowerShell
cd D:\ApplyLens\infra
docker-compose ps

# Check logs for errors
docker-compose logs --tail=100 api
```

### 3. Identify Error Pattern
```bash
# Query logs for specific errors
docker-compose logs api | grep "ERROR" | tail -n 50

# Check which endpoints are failing
curl -s http://localhost:8003/metrics | grep http_requests_total | grep status=\"5
```

---

## Common Causes & Fixes

### Database Connection Issues
**Symptoms:** 
- `/ready` returns 503
- Logs show "connection refused" or "too many connections"

**Fix:**
```bash
# Restart PostgreSQL
docker-compose restart db

# Check connections
docker-compose exec db psql -U postgres -c "SELECT count(*) FROM pg_stat_activity;"

# Kill idle connections if needed
docker-compose exec db psql -U postgres -c "
  SELECT pg_terminate_backend(pid) 
  FROM pg_stat_activity 
  WHERE state = 'idle' AND state_change < now() - interval '1 hour';"
```

### Elasticsearch Timeouts
**Symptoms:**
- Slow response times on search endpoints
- Logs show "elasticsearch.exceptions.ConnectionTimeout"

**Fix:**
```bash
# Check ES health
curl http://localhost:9200/_cluster/health?pretty

# Check ES disk space
curl http://localhost:9200/_cat/allocation?v

# Restart ES if needed
docker-compose restart elasticsearch
```

### Migration Issues
**Symptoms:**
- Errors mention missing columns or tables
- `/ready` shows old migration version

**Fix:**
```bash
# Check current migration
curl http://localhost:8003/ready | jq .migration

# Run migrations
docker-compose exec api alembic upgrade head

# Verify
curl http://localhost:8003/ready | jq .
```

### Code Bugs (Recent Deploy)
**Symptoms:**
- Errors started after recent deployment
- Specific endpoint consistently failing

**Fix:**
```bash
# Rollback to previous version
git log --oneline -n 5
git checkout <previous-commit>
docker-compose up -d --build api

# Or revert specific file
git checkout HEAD~1 -- services/api/app/routers/<file>.py
docker-compose restart api
```

---

## Escalation

If errors persist after 15 minutes:

1. **Page on-call developer**
2. **Create incident report** with:
   - Time of alert
   - Error rate and affected endpoints
   - Steps taken so far
   - Recent changes (git log)
3. **Consider full rollback** if related to recent deploy

---

## Post-Incident

After resolution:
1. Document root cause in incident report
2. Add regression test if applicable
3. Update this runbook with new learnings
4. Review monitoring thresholds (5% may need adjustment)

---

## Useful Queries

### Grafana (PromQL)
```promql
# Error rate by endpoint
sum(rate(http_requests_total{status=~"5.."}[5m])) by (route)

# Total requests
sum(rate(http_requests_total[5m]))

# Error percentage
sum(rate(http_requests_total{status=~"5.."}[5m])) 
  / sum(rate(http_requests_total[5m])) * 100
```

### Database Diagnostics
```sql
-- Long-running queries
SELECT pid, now() - pg_stat_activity.query_start AS duration, query
FROM pg_stat_activity
WHERE state = 'active'
ORDER BY duration DESC;

-- Table sizes
SELECT schemaname, tablename, 
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

---

## Related Links
- [Grafana Ops Dashboard](http://localhost:3000/d/applylens-ops-overview)
- [Prometheus Alerts](http://localhost:9090/alerts)
- [API Metrics](http://localhost:8003/metrics)
