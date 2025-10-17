# Fivetran Setup Checklist ✅

**Project**: applylens-gmail-1759983601  
**Status**: All GCP resources provisioned, ready for Fivetran connector setup  
**Date**: October 16, 2025

---

## ✅ Prerequisites Complete

### GCP Resources
- ✅ **Project**: applylens-gmail-1759983601
- ✅ **Datasets Created**:
  - `gmail_raw` (Fivetran writes here)
  - `gmail_raw_stg` (dbt staging)
  - `gmail_marts` (dbt marts)
- ✅ **ApplyLens Service Account**: `applylens-warehouse@applylens-gmail-1759983601.iam.gserviceaccount.com`
  - Roles: `bigquery.dataViewer`, `bigquery.jobUser`
  - Key: `./secrets/applylens-warehouse-key.json`
- ✅ **Fivetran Service Account**: `g-twice-taxes@fivetran-production.iam.gserviceaccount.com`
  - Project role: `bigquery.user`
  - Dataset role: `WRITER` on `gmail_raw`

### Environment
- ✅ `infra/.env.prod` updated with warehouse settings
- ✅ `docker-compose.prod.yml` configured for warehouse
- ✅ API code includes warehouse endpoints

---

## 📋 Fivetran Setup Steps

### Step 1: Log In to Fivetran
- [ ] Go to https://fivetran.com
- [ ] Sign in with your account

### Step 2: Create Gmail Connector
- [ ] Click **"+ Connector"** or **"Add Connector"**
- [ ] Search for **"Gmail"**
- [ ] Click **"Set Up"**

### Step 3: Configure Source (Gmail)
- [ ] **Authentication Method**: OAuth
- [ ] Click **"Authorize Gmail"**
- [ ] Sign in with: `leoklemet.pa@gmail.com`
- [ ] Grant Fivetran access to Gmail (read-only)
- [ ] Verify authorization success

### Step 4: Configure Destination (BigQuery)
- [ ] **Destination Type**: BigQuery
- [ ] **Connection Method**: Service Account
- [ ] **Project ID**: `applylens-gmail-1759983601`
- [ ] **Dataset**: `gmail_raw`
- [ ] **Location**: `US`
- [ ] **Service Account**: Should auto-detect `g-twice-taxes@fivetran-production.iam.gserviceaccount.com`
- [ ] Click **"Test Connection"** → Should succeed ✅

### Step 5: Configure Sync Settings
- [ ] **Historical Sync**: 60 days (or custom date range)
- [ ] **Sync Frequency**: 15 minutes
- [ ] **Schema**: Select tables to sync:
  - [ ] ✅ `messages` (most important)
  - [ ] ✅ `threads`
  - [ ] ✅ `labels`
  - [ ] Optional: `message_parts`, `headers` (if available)

### Step 6: Review and Save
- [ ] Review all settings
- [ ] Click **"Save & Test"**
- [ ] Connector should show as **"Connected"**

### Step 7: Start Initial Sync
- [ ] Click **"Start Initial Sync"** or **"Sync Now"**
- [ ] Monitor sync progress in Fivetran dashboard
- [ ] **Expected Duration**: 10-30 minutes for 60-day backfill
- [ ] Wait for status: **"Synced Successfully"**

---

## ✅ Verification After Sync

### Check Data in BigQuery
```powershell
# Check if tables exist
bq ls applylens-gmail-1759983601:gmail_raw

# Expected tables:
# - messages
# - threads
# - labels
# - _fivetran_synced (metadata)

# Count messages
bq query --use_legacy_sql=false --project_id=applylens-gmail-1759983601 "SELECT COUNT(*) as count FROM \`applylens-gmail-1759983601.gmail_raw.messages\`"

# Expected: ~2000-5000 messages for 60-day backfill (depends on email volume)

# Check sync freshness
bq query --use_legacy_sql=false --project_id=applylens-gmail-1759983601 "SELECT MAX(_fivetran_synced) as last_sync FROM \`applylens-gmail-1759983601.gmail_raw.messages\`"

# Should be recent (within last 15-30 minutes)
```

### Check Fivetran Dashboard
- [ ] Status shows **"Synced"** with green checkmark
- [ ] Last sync time is recent
- [ ] No errors in sync logs
- [ ] MAR (Monthly Active Rows) usage displayed

---

## 🔄 Run dbt Models (After Fivetran Sync)

### Local Execution
```powershell
cd D:\ApplyLens\analytics\dbt

# Set environment
$env:GCP_PROJECT = "applylens-gmail-1759983601"
$env:GOOGLE_APPLICATION_CREDENTIALS = "D:\ApplyLens\secrets\applylens-warehouse-key.json"

# Install dependencies
dbt deps

# Run staging models
dbt run --select models/staging/fivetran --target prod

# Expected output:
# Completed successfully
# Done. PASS=3 WARN=0 ERROR=0 SKIP=0 TOTAL=3

# Run mart models
dbt run --select models/marts/warehouse --target prod

# Expected output:
# Completed successfully
# Done. PASS=3 WARN=0 ERROR=0 SKIP=0 TOTAL=3

# Run tests
dbt test --target prod

# Expected output:
# Completed successfully
# Done. PASS=15-20 WARN=0 ERROR=0 SKIP=0 TOTAL=15-20
```

### GitHub Actions Execution
```powershell
# Set secrets (one-time)
gh secret set GCP_PROJECT --body "applylens-gmail-1759983601"
gh secret set GCP_SA_JSON --body "$(Get-Content secrets/applylens-warehouse-key.json -Raw)"
gh secret set ES_URL --body "http://elasticsearch:9200"
gh secret set PUSHGATEWAY_URL --body "http://prometheus-pushgateway:9091"

# Trigger workflow
gh workflow run dbt.yml

# Watch progress
gh run watch

# Check status
gh run list --workflow=dbt.yml --limit=1
```

---

## 🚀 Enable Warehouse Metrics in Production

### Update Environment
```powershell
# Enable warehouse metrics
(Get-Content infra\.env.prod) -replace 'USE_WAREHOUSE_METRICS=0', 'USE_WAREHOUSE_METRICS=1' | Set-Content infra\.env.prod

# Verify change
Get-Content infra\.env.prod | Select-String "USE_WAREHOUSE_METRICS"
# Should show: USE_WAREHOUSE_METRICS=1
```

### Rebuild and Restart API
```powershell
# Rebuild API container (includes BigQuery client)
docker compose -f docker-compose.prod.yml --env-file infra/.env.prod build api

# Restart API with new configuration
docker compose -f docker-compose.prod.yml --env-file infra/.env.prod up -d api

# Check logs
docker logs applylens-api-prod --tail=50 -f
# Should show: "Warehouse metrics enabled" or similar
```

---

## ✅ Smoke Tests

### Test API Endpoints
```powershell
# Test 1: Freshness check
$freshness = Invoke-RestMethod -Uri 'http://localhost/api/metrics/profile/freshness'
Write-Host "Last sync: $($freshness.last_sync_at)"
Write-Host "Minutes since sync: $($freshness.minutes_since_sync)"
Write-Host "Is fresh (< 30 min): $($freshness.is_fresh)"

# Expected:
# - last_sync_at: Recent timestamp
# - minutes_since_sync: < 30
# - is_fresh: true

# Test 2: Daily activity (last 7 days)
$activity = Invoke-RestMethod -Uri 'http://localhost/api/metrics/profile/activity_daily?days=7'
Write-Host "Days returned: $($activity.count)"
Write-Host "Sample day: $($activity.rows[0] | ConvertTo-Json)"

# Expected:
# - count: 7
# - rows with day, messages_count, unique_senders

# Test 3: Top senders (30d)
$senders = Invoke-RestMethod -Uri 'http://localhost/api/metrics/profile/top_senders_30d?limit=5'
Write-Host "Top 5 senders:"
$senders.rows | ForEach-Object { Write-Host "  - $($_.from_email): $($_.messages_30d) messages" }

# Expected:
# - List of top senders with message counts

# Test 4: Categories
$categories = Invoke-RestMethod -Uri 'http://localhost/api/metrics/profile/categories_30d'
Write-Host "Categories:"
$categories.rows | ForEach-Object { Write-Host "  - $($_.category): $($_.messages_30d) messages ($($_.pct_of_total)%)" }

# Expected:
# - promotions, updates, social, forums, primary
# - Percentages sum to ~100%
```

### Test Validation Script
```powershell
cd analytics/ops

# Set environment
$env:GCP_PROJECT = "applylens-gmail-1759983601"
$env:ES_URL = "http://localhost:9200"
$env:PUSHGATEWAY = "http://localhost:9091"
$env:GOOGLE_APPLICATION_CREDENTIALS = "D:\ApplyLens\secrets\applylens-warehouse-key.json"

# Run validation
python validate_es_vs_bq.py

# Expected output:
# ✅ VALIDATION PASSED (delta X.XX% <= 2.0%)
```

---

## 📊 Monitoring Setup

### Grafana Dashboards
- [ ] Import dashboard JSON from `infra/grafana/dashboard-assistant-window-buckets.json`
- [ ] Add warehouse panels:
  - [ ] Daily Email Activity (API endpoint)
  - [ ] Top Senders Table (API endpoint)
  - [ ] Category Pie Chart (API endpoint)
  - [ ] Freshness SLO (API endpoint)
  - [ ] ES ↔ BQ Delta% (Prometheus metric)

### Prometheus Alerts
- [ ] Add alerting rules from `docs/ILM-MONITORING.md`
- [ ] Configure for:
  - [ ] Data drift > 2% (critical)
  - [ ] Fivetran sync stale > 30 min (critical)
  - [ ] BigQuery query cost spike (warning)

---

## 🎯 Success Criteria

### Data Quality
- ✅ Fivetran sync status: "Synced Successfully"
- ✅ dbt tests: 100% passing (no errors)
- ✅ ES ↔ BQ delta: < 2%
- ✅ Data freshness: < 30 minutes

### Performance
- ✅ API endpoint latency: < 500ms p95
- ✅ BigQuery query time: < 5 seconds
- ✅ Cache hit rate: > 80% (after warmup)

### Cost
- ✅ Fivetran MAR: Within expected range
- ✅ BigQuery storage: < $5/month
- ✅ BigQuery queries: < $10/month
- ✅ Total: < $30/month

---

## 🔄 Rollback Plan (If Issues)

### Quick Disable (30 seconds)
```powershell
# Disable warehouse metrics
(Get-Content infra\.env.prod) -replace 'USE_WAREHOUSE_METRICS=1', 'USE_WAREHOUSE_METRICS=0' | Set-Content infra\.env.prod

# Restart API
docker compose -f docker-compose.prod.yml --env-file infra/.env.prod restart api

# Verify fallback
curl http://localhost/api/metrics/profile/freshness
# Should return 412: "Warehouse metrics disabled"
```

### Pause Fivetran (If Needed)
- [ ] Go to Fivetran dashboard
- [ ] Select Gmail connector
- [ ] Click **"Pause"**
- [ ] Confirm

---

## 📚 Resources

- **Provisioning Guide**: `docs/GCP-PROVISIONING-COMPLETE.md`
- **Quick Commands**: `docs/QUICK-COMMANDS-WAREHOUSE.md`
- **Implementation Guide**: `docs/FIVETRAN-BIGQUERY-IMPLEMENTATION.md`
- **Operations Guide**: `analytics/ops/README.md`

---

## ✅ Checklist Summary

**GCP Setup**: ✅ Complete  
**Fivetran Setup**: ⏳ Pending (manual step)  
**dbt Models**: ⏳ Pending (after Fivetran sync)  
**API Enabled**: ⏳ Pending (after dbt)  
**Monitoring**: ⏳ Pending (after API enabled)

**Next Action**: Configure Fivetran connector at https://fivetran.com

---

*Last Updated: October 16, 2025*
