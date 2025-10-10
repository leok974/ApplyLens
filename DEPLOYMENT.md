# ApplyLens Deployment Checklist

**Version:** Phase 12.3 (Monitoring & Observability)  
**Date:** October 2025

This document provides a complete deployment checklist for ApplyLens, focusing on the new monitoring and observability features from Phase 12.3.

---

## 📋 Pre-Deployment Checklist

### 1. Dependencies
- [ ] Python 3.10+ installed
- [ ] Docker & Docker Compose available
- [ ] PostgreSQL 15+ accessible
- [ ] Elasticsearch 8.12+ running
- [ ] Prometheus server available
- [ ] Grafana instance accessible

### 2. Configuration Files
- [ ] `infra/.env` created from `.env.example`
- [ ] `infra/secrets/google.json` configured (for Gmail OAuth)
- [ ] Database connection string set in `.env`
- [ ] Elasticsearch URL configured

### 3. Code & Dependencies
```bash
cd services/api

# Install base dependencies
pip install -e .

# Install test dependencies (optional)
pip install -e ".[test]"

# Install tracing dependencies (optional)
pip install -e ".[tracing]"
```

---

## 🚀 Deployment Steps

### Step 1: Database Migrations
```bash
cd services/api

# Check current migration
python -c "from app.utils.schema_guard import get_current_migration; print(get_current_migration())"

# Run migrations
alembic upgrade head

# Verify migration 0012 or higher
curl http://localhost:8003/ready | jq .migration
# Expected: "0012_add_emails_features_json" or higher
```

### Step 2: Load Prometheus Alert Rules
```bash
# Copy alert rules to Prometheus config directory
cp infra/alerts/prometheus-rules.yml /path/to/prometheus/rules/applylens.yml

# Or mount in docker-compose.yml:
# volumes:
#   - ./infra/alerts/prometheus-rules.yml:/etc/prometheus/rules/applylens.yml

# Reload Prometheus configuration
curl -X POST http://localhost:9090/-/reload

# Verify alerts loaded
curl http://localhost:9090/api/v1/rules | jq '.data.groups[].rules[] | select(.name | startswith("API"))'
```

**Expected alerts:**
- APIHighErrorRateFast
- RiskJobFailures
- ParityDriftTooHigh
- BackfillDurationSLO

### Step 3: Configure Structured Logging
```yaml
# infra/docker-compose.yml (or docker-compose.minimal.yml)
services:
  api:
    environment:
      - UVICORN_LOG_CONFIG=/app/app/logging.yaml
    volumes:
      - ./services/api/app/logging.yaml:/app/app/logging.yaml:ro
```

```bash
# Restart API to apply logging config
docker-compose restart api

# Verify JSON logs
docker-compose logs api --tail=10
# Should show JSON formatted logs
```

### Step 4: Import Grafana Dashboard
**Option A: Via API**
```bash
# Using Grafana API
curl -X POST http://localhost:3000/api/dashboards/db \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $GRAFANA_API_KEY" \
  -d @services/api/dashboards/ops-overview.json
```

**Option B: Via UI**
1. Open Grafana: http://localhost:3000
2. Navigate to: **Dashboards** → **Import**
3. Click **Upload JSON file**
4. Select: `services/api/dashboards/ops-overview.json`
5. Choose Prometheus data source
6. Click **Import**
7. Verify all 8 panels load correctly

### Step 5: Configure Synthetic Probes (GitHub Actions)
```bash
# Add GitHub repository secret
# Name: APPLYLENS_BASE_URL
# Value: https://api.applylens.com (or your production URL)

# Navigate to:
# https://github.com/YOUR_ORG/ApplyLens/settings/secrets/actions

# Click "New repository secret"
# Name: APPLYLENS_BASE_URL
# Secret: https://api.applylens.com
```

**Test the workflow:**
```bash
# Trigger manually via GitHub API
curl -X POST \
  -H "Accept: application/vnd.github+json" \
  -H "Authorization: Bearer $GITHUB_TOKEN" \
  https://api.github.com/repos/YOUR_ORG/ApplyLens/actions/workflows/synthetic-probes.yml/dispatches \
  -d '{"ref":"main"}'

# Or use GitHub UI: Actions → Synthetic Probes → Run workflow
```

### Step 6: Enable OpenTelemetry (Optional)
```bash
# Install dependencies (if not already)
pip install -e ".[tracing]"

# Set environment variables in docker-compose.yml or .env
OTEL_ENABLED=1
OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4318
OTEL_SERVICE_NAME=applylens-api
APP_VERSION=1.0.0
ENV=production

# Restart API
docker-compose restart api

# Verify tracing in logs
docker-compose logs api | grep "OpenTelemetry"
# Expected: "✓ OpenTelemetry tracing initialized"
```

### Step 7: Verify Health Endpoints
```bash
# Liveness check
curl http://localhost:8003/healthz
# Expected: {"status":"ok"}

curl http://localhost:8003/live
# Expected: {"status":"alive"}

# Readiness check
curl http://localhost:8003/ready | jq .
# Expected: 
# {
#   "status": "ready",
#   "db": "ok",
#   "es": "ok",
#   "migration": "0012_add_emails_features_json"
# }
```

### Step 8: Test Metrics Endpoint
```bash
# Fetch metrics
curl http://localhost:8003/metrics | head -n 50

# Verify key metrics exist
curl -s http://localhost:8003/metrics | grep -E "(applylens_db_up|applylens_es_up|applylens_parity)"

# Expected metrics:
# - applylens_db_up 1.0
# - applylens_es_up 1.0
# - applylens_parity_checks_total
# - applylens_parity_mismatch_ratio
```

### Step 9: Run Initial Parity Check
```bash
cd services/api

# Run parity check
python scripts/check_parity.py \
  --fields risk_score,expires_at,category \
  --sample 1000 \
  --output parity.json \
  --csv parity.csv \
  --allow 0

# Review results
cat parity.json | jq '.summary'

# Expected on fresh deployment: 0 mismatches
# If mismatches found, see runbooks/parity.md
```

### Step 10: Test Alert Delivery (Optional)
```bash
# Trigger test 5xx error
curl http://localhost:8003/debug/500

# Wait 5-10 minutes for Prometheus to scrape
# Check alert status
curl http://localhost:9090/api/v1/alerts | jq '.data.alerts[] | select(.labels.alertname == "APIHighErrorRateFast")'

# If alert fires, verify notification delivery (Slack/email)
```

---

## ✅ Post-Deployment Verification

### Health Check Matrix

| Endpoint | Expected Response | Verify |
|----------|-------------------|--------|
| `/healthz` | `{"status":"ok"}` | [ ] |
| `/live` | `{"status":"alive"}` | [ ] |
| `/ready` | `{"status":"ready","db":"ok","es":"ok","migration":"0012..."}` | [ ] |
| `/metrics` | Prometheus text format | [ ] |
| `/automation/health` | `{"total_emails":N,"emails_with_scores":M,...}` | [ ] |

### Prometheus Checks

- [ ] Prometheus scraping API metrics (check Targets page)
- [ ] All 4 alert rules loaded and visible
- [ ] No alerts firing (green status)
- [ ] Metrics cardinality within limits (<10k series)

### Grafana Checks

- [ ] Dashboard imported successfully
- [ ] All 8 panels showing data
- [ ] Prometheus data source connected
- [ ] Auto-refresh working (30s interval)
- [ ] No "N/A" or error panels

### Synthetic Probes Checks

- [ ] GitHub Actions workflow visible
- [ ] Secret `APPLYLENS_BASE_URL` configured
- [ ] Manual run succeeds (all checks pass)
- [ ] Scheduled runs occur hourly

### Logging Checks

- [ ] JSON logs visible in `docker-compose logs api`
- [ ] Log level appropriate (INFO in prod, DEBUG in dev)
- [ ] No sensitive data in logs (passwords, tokens)
- [ ] Logs parseable by log aggregator (if used)

---

## 🔐 Security Checklist

### Secrets Management
- [ ] `OAUTH_STATE_SECRET` set to random 32+ character string
- [ ] Database password not committed to git
- [ ] GitHub secrets used for sensitive config (not .env files in repo)
- [ ] Prometheus/Grafana behind authentication

### Access Control
- [ ] Grafana requires login (not anonymous access)
- [ ] Prometheus behind firewall or VPN
- [ ] API rate limiting enabled
- [ ] CORS origins properly restricted

### Monitoring Security
- [ ] Metrics endpoint doesn't expose sensitive data
- [ ] Health endpoints don't leak internal details
- [ ] Runbooks stored securely (not public)
- [ ] Alert notifications go to secure channels

---

## 📊 Monitoring Dashboard URLs

**Bookmark these for operations team:**

| Service | URL | Purpose |
|---------|-----|---------|
| Grafana Dashboard | http://localhost:3000/d/applylens-ops-overview | Real-time metrics |
| Prometheus Alerts | http://localhost:9090/alerts | Alert status |
| Prometheus Targets | http://localhost:9090/targets | Scrape health |
| API Metrics | http://localhost:8003/metrics | Raw metrics |
| API Health | http://localhost:8003/ready | Health check |
| Synthetic Probes | https://github.com/YOUR_ORG/ApplyLens/actions/workflows/synthetic-probes.yml | Probe results |

---

## 📚 Operational Runbooks

**Critical incident response guides:**

1. **[API Errors](services/api/docs/runbooks/api-errors.md)** - 5xx error rate spikes
2. **[Risk Job Failures](services/api/docs/runbooks/risk-job.md)** - Risk computation issues
3. **[Parity Drift](services/api/docs/runbooks/parity.md)** - DB↔ES data inconsistency
4. **[Backfill Performance](services/api/docs/runbooks/backfill.md)** - Slow backfill jobs

**Response times:**
- **Page** severity: Immediate response required
- **Ticket** severity: Investigate within 2-4 hours

---

## 🔄 Rollback Procedure

If deployment fails or alerts fire immediately:

```bash
# 1. Check current commit
git log --oneline -n 5

# 2. Identify last working commit
# (Before Phase 12.3: commit before c452f31)

# 3. Rollback code
git checkout <previous-commit>

# 4. Rebuild and restart
docker-compose up -d --build api

# 5. Verify health
curl http://localhost:8003/ready

# 6. Check metrics
curl http://localhost:8003/metrics | grep applylens_db_up

# 7. Document rollback reason
echo "Rollback due to: <reason>" >> ROLLBACK_LOG.md
```

---

## 🎓 Team Training

Before going live, ensure team is trained on:

- [ ] Reading Grafana dashboard
- [ ] Interpreting Prometheus alerts
- [ ] Using runbooks for incident response
- [ ] Running parity checks manually
- [ ] Accessing synthetic probe results
- [ ] Escalation procedures

**Training materials:**
- [Phase 12.3 Complete Guide](PHASE_12.3_COMPLETE.md)
- [Runbook walkthroughs](services/api/docs/runbooks/)
- Grafana dashboard demo
- Alert simulation exercise

---

## 🐛 Troubleshooting

### Prometheus Not Scraping Metrics
```bash
# Check Prometheus config
curl http://localhost:9090/api/v1/targets

# Verify API metrics endpoint accessible from Prometheus
docker exec prometheus curl http://api:8003/metrics

# Check firewall rules
# Ensure port 8003 accessible from Prometheus container
```

### Grafana Dashboard Shows "N/A"
```bash
# Verify data source connected
# Grafana → Configuration → Data Sources → Prometheus
# Click "Test" button

# Check PromQL queries manually
curl -G http://localhost:9090/api/v1/query \
  --data-urlencode 'query=applylens_db_up'

# Verify metric exists
curl -s http://localhost:8003/metrics | grep applylens_db_up
```

### Synthetic Probes Failing
```bash
# Check GitHub Actions logs
# Navigate to: Actions → Synthetic Probes → Latest run

# Test endpoints manually
curl -v https://api.applylens.com/healthz
curl -v https://api.applylens.com/ready

# Verify APPLYLENS_BASE_URL secret
# Should match production URL exactly
```

### Health Endpoint Returns 503
```bash
# Check readiness response
curl -v http://localhost:8003/ready

# If DB down:
docker-compose ps db
docker-compose restart db

# If ES down:
curl http://localhost:9200/_cluster/health
docker-compose restart elasticsearch

# If migration issue:
cd services/api
alembic current
alembic upgrade head
```

---

## 📝 Deployment Log Template

Document your deployment:

```markdown
## Deployment: Phase 12.3 - [Date]

**Deployer:** [Name]
**Time:** [Start] - [End]
**Environment:** [Production/Staging]
**Git Commit:** c452f31

### Pre-Deployment
- [ ] Backups taken
- [ ] Team notified
- [ ] Rollback plan reviewed

### Deployment Steps
- [ ] Step 1: Database migrations ✅
- [ ] Step 2: Prometheus alerts ✅
- [ ] Step 3: Structured logging ✅
- [ ] Step 4: Grafana dashboard ✅
- [ ] Step 5: Synthetic probes ✅
- [ ] Step 6: OpenTelemetry ⏭️ (skipped)
- [ ] Step 7: Health endpoints ✅
- [ ] Step 8: Metrics ✅
- [ ] Step 9: Parity check ✅
- [ ] Step 10: Alert test ✅

### Verification
- [ ] All health checks passing
- [ ] Prometheus scraping metrics
- [ ] Grafana dashboard loaded
- [ ] No alerts firing
- [ ] Parity check: 0 mismatches

### Issues Encountered
- None

### Notes
- OpenTelemetry deferred to next release
- All monitoring features operational
```

---

## 🎉 Success Criteria

Deployment is successful when:

✅ All health endpoints return 200  
✅ Prometheus scraping metrics without errors  
✅ Grafana dashboard shows live data  
✅ 4 alert rules loaded and not firing  
✅ Synthetic probes running hourly  
✅ Parity check shows <0.1% mismatch ratio  
✅ JSON logs visible in container output  
✅ No 5xx errors in first hour post-deployment  

---

## 📞 Support Contacts

**For deployment issues:**
- Slack: #applylens-ops
- Email: ops@applylens.com
- On-call: [PagerDuty rotation]

**For monitoring questions:**
- Grafana admin: [Name/Email]
- Prometheus admin: [Name/Email]
- Documentation: [Phase 12.3 Complete Guide](PHASE_12.3_COMPLETE.md)

---

*Last Updated: October 2025*  
*Version: Phase 12.3*  
*Maintainer: ApplyLens Team*
