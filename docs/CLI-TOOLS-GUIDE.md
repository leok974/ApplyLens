# ApplyLens CLI Tools

Quick reference for local development and operations.

## 🚀 Unified CLI (Recommended)

**Location:** `applylens.ps1` (project root)

**Usage:**
```powershell
.\applylens.ps1 [command]
```

**Commands:**
- `build` - Build & restart API (docker compose)
- `run-dbt` - Run full dbt pipeline (deps + run + test)
- `verify` - Run comprehensive verification checks
- `status` - Show one-line system status
- `all` - Run everything: build → dbt → verify → status
- `help` - Show help message

**Examples:**
```powershell
# Quick status check
.\applylens.ps1 status

# Full rebuild + verification
.\applylens.ps1 all

# Just run dbt models
.\applylens.ps1 run-dbt
```

---

## 📦 Individual Scripts

### 1. **run-all.ps1** / **run-all.sh** - dbt Pipeline Runner

**Location:** `analytics\ops\`

**Purpose:** Run complete dbt pipeline (deps → run → test) for warehouse models only.

**Usage (Windows):**
```powershell
.\analytics\ops\run-all.ps1
```

**Usage (Linux/Mac):**
```bash
./analytics/ops/run-all.sh
```

**What it does:**
- Sets default environment variables (GCP_PROJECT, RAW_DATASET, credentials)
- Installs dbt dependencies
- Runs warehouse models (`marts.warehouse.*` and dependencies)
- Runs all tests
- Reports success/failure

**Environment Variables:**
```powershell
# Optional overrides
$env:GCP_PROJECT = "applylens-gmail-1759983601"  # default
$env:RAW_DATASET = "gmail"                        # default
$env:GOOGLE_APPLICATION_CREDENTIALS = "D:\ApplyLens\secrets\applylens-warehouse-key.json"  # default
```

---

### 2. **run-verification.ps1** - Comprehensive Health Check

**Location:** `analytics\ops\`

**Purpose:** Verify all warehouse components are working correctly.

**Usage:**
```powershell
.\analytics\ops\run-verification.ps1
```

**What it checks:**
- ✅ API Health (4 endpoints: freshness, activity, senders, categories)
- ✅ BigQuery Data Quality (message counts, raw data)
- ✅ GitHub Actions Status (latest workflow run)
- ✅ Docker Services (API, Elasticsearch, Redis)

**Output:**
```
========================================
  WAREHOUSE VERIFICATION
========================================

1. API HEALTH CHECKS
-------------------
  ✅ Freshness: 11 min (Fresh)
  ✅ Activity: 7 days returned
  ✅ Top Senders: 5 senders returned
  ✅ Categories: 4 categories returned

2. BIGQUERY DATA QUALITY
------------------------
  ✅ Raw messages: 3247

3. GITHUB ACTIONS STATUS
------------------------
  ✅ Latest run: Success
     Created: 2025-01-17T04:17:00Z

4. DOCKER SERVICES
------------------
  ✅ applylens-api-prod: Running
  ✅ applylens-elasticsearch-prod: Running
  ✅ applylens-redis-prod: Running

========================================
  SUMMARY
========================================

  ✅ Passed:   11
  ❌ Failed:   0
  ⚠️  Warnings: 0

  Success Rate: 100%

  🎉 All critical checks passed!
========================================
```

---

### 3. **uptime-monitor.ps1** - Prometheus Metrics Exporter

**Location:** `analytics\ops\`

**Purpose:** Monitor API freshness and push metrics to Prometheus Pushgateway.

**Usage (Manual):**
```powershell
.\analytics\ops\uptime-monitor.ps1
```

**Usage (Scheduled - Every 5 Minutes):**
```powershell
$action = New-ScheduledTaskAction -Execute "PowerShell.exe" `
  -Argument "-NoProfile -ExecutionPolicy Bypass -File D:\ApplyLens\analytics\ops\uptime-monitor.ps1"

$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) `
  -RepetitionInterval (New-TimeSpan -Minutes 5) `
  -RepetitionDuration ([TimeSpan]::MaxValue)

Register-ScheduledTask `
  -TaskName "ApplyLens Warehouse Uptime Monitor" `
  -Action $action `
  -Trigger $trigger
```

**Metrics Exported:**
- `warehouse_freshness_minutes` - Minutes since last sync
- `warehouse_freshness_is_fresh` - Boolean (1 = fresh, 0 = stale)
- `warehouse_api_up` - Boolean (1 = up, 0 = down)

**Grafana Query Examples:**
```promql
# Freshness over time
warehouse_freshness_minutes

# Alert if stale (>30 min)
warehouse_freshness_is_fresh == 0
```

---

### 4. **validate_es_vs_bq.py** - Data Consistency Checker

**Location:** `analytics\ops\`

**Purpose:** Compare Elasticsearch vs BigQuery data for drift detection.

**Usage:**
```bash
python analytics/ops/validate_es_vs_bq.py
```

**What it checks:**
- Message counts (ES vs BQ)
- Date ranges (min/max sync dates)
- Drift threshold (warns if >5% difference)

**Environment Variables Required:**
```powershell
$env:GCP_PROJECT = "applylens-gmail-1759983601"
$env:BQ_MARTS_DATASET = "gmail_raw_stg_gmail_marts"
$env:ES_URL = "http://localhost:9200"
$env:PUSHGATEWAY_URL = "http://localhost:9091"
$env:GOOGLE_APPLICATION_CREDENTIALS = "D:\ApplyLens\secrets\applylens-warehouse-key.json"
```

**Note:** This only works when Elasticsearch is reachable (not from GitHub Actions runner).

---

## 📋 Common Workflows

### Fresh Start (After Reboot)
```powershell
# 1. Start services
docker compose -f docker-compose.prod.yml up -d

# 2. Check status
.\applylens.ps1 status

# 3. Run verification
.\applylens.ps1 verify
```

### After Code Changes
```powershell
# 1. Rebuild API
.\applylens.ps1 build

# 2. Run verification
.\applylens.ps1 verify
```

### After dbt Model Changes
```powershell
# 1. Run dbt
.\applylens.ps1 run-dbt

# 2. Verify API returns new data
.\applylens.ps1 verify
```

### Full Production Deploy
```powershell
# 1. Run everything
.\applylens.ps1 all

# 2. Check GitHub Actions
gh workflow run "Warehouse Nightly"
gh run watch

# 3. Monitor Grafana
# Navigate to http://localhost:3000/d/warehouse
```

### Weekly Health Check
```powershell
# Monday morning routine
.\applylens.ps1 status
.\analytics\ops\run-verification.ps1

# Review GitHub Actions
gh run list --workflow "Warehouse Nightly" --limit 5

# Check costs
# Navigate to GCP Console → Billing → Reports
```

---

## 🛠️ Troubleshooting

### API Not Responding
```powershell
# Check container status
docker ps -a | Select-String "applylens"

# Restart
docker compose -f docker-compose.prod.yml restart api

# Check logs
docker compose -f docker-compose.prod.yml logs --tail 100 api

# Full rebuild
.\applylens.ps1 build
```

### dbt Errors
```powershell
# Check credentials
Test-Path $env:GOOGLE_APPLICATION_CREDENTIALS

# Run with verbose output
cd analytics\dbt
dbt run --target prod --select +marts.warehouse.* --log-level debug

# Clear compiled files
Remove-Item -Recurse -Force target\, dbt_packages\
dbt deps
```

### Verification Failures
```powershell
# Check individual components
Invoke-RestMethod 'http://localhost:8003/health'
docker ps
gh run list --workflow "Warehouse Nightly" --limit 1

# Check Fivetran sync
# Navigate to https://fivetran.com/dashboard → Connector → Logs
```

---

## 📚 Related Documentation

- **Production Setup:** `docs/PRODUCTION-HARDENING-COMPLETE.md`
- **GitHub Actions:** `docs/GITHUB-ACTIONS-VERIFICATION.md`
- **Housekeeping:** `docs/HOUSEKEEPING-CHECKLIST.md`
- **Uptime Monitoring:** `docs/UPTIME-MONITORING.md`
- **Cost Monitoring:** `docs/COST-MONITORING.md`
- **Verification Queries:** `docs/VERIFICATION-QUERIES.md`

---

**Quick Links:**
- GitHub Workflow: `.github/workflows/dbt.yml`
- dbt Project: `analytics/dbt/`
- API Code: `api/routes/metrics.py` (warehouse endpoints)
- Grafana Dashboard: `http://localhost:3000/d/warehouse`
- Prometheus: `http://localhost:9090`

---

**Last Updated:** 2025-01-17  
**Maintained By:** ApplyLens Development Team
