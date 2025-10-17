# 🚀 ApplyLens Warehouse - Quick Reference Card

**Last Updated:** 2025-01-17 | **Status:** ✅ Production Ready

---

## ⚡ One-Liners (Most Common)

```powershell
# Quick status check
.\applylens.ps1 status

# Full verification (health check)
.\applylens.ps1 verify

# Rebuild everything
.\applylens.ps1 all

# Just run dbt
.\applylens.ps1 run-dbt

# Just build API
.\applylens.ps1 build
```

---

## 📊 Current Metrics

| Metric | Value | SLO/Budget | Status |
|--------|-------|------------|--------|
| Freshness | <15 min | <30 min | ✅ |
| Sync Frequency | 15 min | 15 min | ✅ |
| API Response | <2s | <5s | ✅ |
| dbt Duration | 1m 13s | <5 min | ✅ |
| Monthly Cost | $0.003 | <$10 | ✅ |
| CI Success | 100% | >95% | ✅ |
| Fivetran MAR | 360k | <500k | ✅ |

---

## 🔧 Essential Commands

### Local Development
```powershell
# Start services
docker compose -f docker-compose.prod.yml up -d

# Check API health
Invoke-RestMethod 'http://localhost:8003/health'

# Run dbt models
.\analytics\ops\run-all.ps1

# Full verification
.\analytics\ops\run-verification.ps1
```

### GitHub Actions
```powershell
# Trigger workflow manually
gh workflow run "Warehouse Nightly"

# Trigger with ES validation (will check reachability first)
gh workflow run "Warehouse Nightly" -f validate_es=true

# Watch latest run
gh run watch

# View last 5 runs
gh run list --workflow "Warehouse Nightly" --limit 5

# View logs of specific run
gh run view <run-id> --log
```

### Data Checks
```powershell
# API endpoints
Invoke-RestMethod 'http://localhost:8003/api/metrics/profile/freshness'
Invoke-RestMethod 'http://localhost:8003/api/metrics/profile/activity_daily?days=7'
Invoke-RestMethod 'http://localhost:8003/api/metrics/profile/top_senders_30d?limit=5'
Invoke-RestMethod 'http://localhost:8003/api/metrics/profile/categories_30d'

# BigQuery (if bq CLI installed)
bq query --nouse_legacy_sql "SELECT COUNT(*) FROM \`applylens-gmail-1759983601.gmail.message\` WHERE _fivetran_deleted = false"
```

### Docker Management
```powershell
# View running containers
docker ps | Select-String "applylens"

# View logs
docker compose -f docker-compose.prod.yml logs --tail 100 api
docker compose -f docker-compose.prod.yml logs --tail 100 elasticsearch

# Restart service
docker compose -f docker-compose.prod.yml restart api

# Rebuild and restart
.\applylens.ps1 build
```

---

## 📁 Key Files

### Scripts
- `applylens.ps1` - Unified CLI (build/run-dbt/verify/status/all)
- `analytics/ops/run-all.ps1` - dbt runner (Windows)
- `analytics/ops/run-all.sh` - dbt runner (Linux/Mac)
- `analytics/ops/run-verification.ps1` - Health check (11 checks)
- `analytics/ops/uptime-monitor.ps1` - Prometheus exporter
- `analytics/ops/validate_es_vs_bq.py` - Drift checker

### Workflows
- `.github/workflows/dbt.yml` - Nightly warehouse refresh (4:17 AM UTC)

### Configuration
- `analytics/dbt/profiles.yml` - dbt profiles (dev/ci/local_prod/prod)
- `analytics/dbt/dbt_project.yml` - dbt project settings
- `analytics/dbt/sources.yml` - Fivetran Gmail source

### Documentation
- `docs/CLI-TOOLS-GUIDE.md` - Complete CLI reference (300+ lines)
- `docs/HOUSEKEEPING-CHECKLIST.md` - Maintenance tasks (330+ lines)
- `docs/GITHUB-ACTIONS-VERIFICATION.md` - Workflow debugging (250+ lines)
- `docs/PRODUCTION-HARDENING-COMPLETE.md` - Setup summary (300+ lines)
- `docs/PHASE15-COMPLETE.md` - Latest improvements summary

---

## 🌐 URLs

| Service | URL | Purpose |
|---------|-----|---------|
| API | http://localhost:8003 | Warehouse endpoints |
| Health | http://localhost:8003/health | API health check |
| Docs | http://localhost:8003/docs | API documentation |
| Grafana | http://localhost:3000/d/warehouse | Warehouse dashboard |
| Prometheus | http://localhost:9090 | Metrics database |
| Elasticsearch | http://localhost:9200 | Search engine |
| Fivetran | https://fivetran.com/dashboard | Data sync status |
| GCP Console | https://console.cloud.google.com | BigQuery/billing |
| GitHub Actions | https://github.com/leok974/ApplyLens/actions | Workflow runs |

---

## 🔐 Environment Variables

### Local Development
```powershell
$env:GCP_PROJECT = "applylens-gmail-1759983601"
$env:RAW_DATASET = "gmail"
$env:BQ_MARTS_DATASET = "gmail_raw_stg_gmail_marts"
$env:GOOGLE_APPLICATION_CREDENTIALS = "D:\ApplyLens\secrets\applylens-warehouse-key.json"
```

### API (for warehouse endpoints)
```bash
USE_WAREHOUSE_METRICS=1  # Enable BigQuery-backed endpoints
```

---

## 🔄 Common Workflows

### Monday Morning Check
```powershell
# 1. Quick status
.\applylens.ps1 status

# 2. Full verification
.\applylens.ps1 verify

# 3. Review GitHub Actions
gh run list --workflow "Warehouse Nightly" --limit 5

# 4. Check cost (navigate to GCP Console → Billing → Reports)
```

### After Code Changes
```powershell
# 1. Rebuild API
.\applylens.ps1 build

# 2. Verify
.\applylens.ps1 verify
```

### After dbt Model Changes
```powershell
# 1. Run dbt
.\applylens.ps1 run-dbt

# 2. Test API
Invoke-RestMethod 'http://localhost:8003/api/metrics/profile/activity_daily?days=7'

# 3. Verify
.\applylens.ps1 verify
```

### Fresh Start (After Reboot)
```powershell
# 1. Start services
docker compose -f docker-compose.prod.yml up -d

# 2. Wait 30 seconds for services to initialize

# 3. Check status
.\applylens.ps1 status

# 4. Run verification
.\applylens.ps1 verify
```

---

## 🚨 Troubleshooting

### API Not Responding
```powershell
# Check containers
docker ps -a | Select-String "applylens"

# Restart
docker compose -f docker-compose.prod.yml restart api

# Check logs
docker compose -f docker-compose.prod.yml logs --tail 100 api

# Full rebuild
.\applylens.ps1 build
```

### Data Freshness Stale (>30 min)
```powershell
# 1. Check Fivetran status (dashboard → connector → logs)
# 2. Trigger manual sync (dashboard → connector → "Sync Now")
# 3. Run dbt manually
.\applylens.ps1 run-dbt
# 4. Verify freshness
Invoke-RestMethod 'http://localhost:8003/api/metrics/profile/freshness'
```

### GitHub Actions Failing
```powershell
# 1. Check latest run
gh run list --workflow "Warehouse Nightly" --limit 1

# 2. View logs
gh run view <run-id> --log

# 3. Re-run
gh run rerun <run-id>

# 4. If auth error, check secrets:
gh secret list
```

### dbt Errors
```powershell
# Check credentials
Test-Path $env:GOOGLE_APPLICATION_CREDENTIALS

# Run with debug output
cd analytics\dbt
dbt run --target prod --select +marts.warehouse.* --log-level debug

# Clear cache
Remove-Item -Recurse -Force target\, dbt_packages\
dbt deps
```

---

## 📋 Housekeeping Schedule

### ✅ All Critical Tasks Complete!

**Setup Complete (2025-10-16):**
- [x] SA key rotation reminder (next: 2026-01-14)
- [x] GCP budget alert ($10/month)
- [x] Fivetran frequency (15 minutes)
- [x] Uptime monitoring (every 5 minutes)

### Weekly (Monday)
- [ ] Run `.\applylens.ps1 verify`
- [ ] Review GitHub Actions last 5 runs
- [ ] Check GCP cost (<$0.10/week expected)

### Monthly (First Monday)
- [ ] Review cost trends (<$1/month)
- [ ] Check Fivetran MAR usage (<500k)
- [ ] Update metrics in HOUSEKEEPING-CHECKLIST.md
- [ ] Review GitHub Actions success rate (>95%)

### Quarterly (Every 3 Months)
- [ ] Review dbt dependency versions
- [ ] Test dbt upgrades locally
- [ ] Update workflow if compatible

### Every 90 Days
- [ ] Rotate service account key (see HOUSEKEEPING-CHECKLIST.md)

---

## 🎯 Success Criteria

All criteria currently met ✅

- ✅ Freshness: <30 min (actual: 10-12 min)
- ✅ API Response: <5s (actual: <2s)
- ✅ dbt Duration: <5 min (actual: 1m 13s)
- ✅ Monthly Cost: <$5 (actual: $0.003)
- ✅ CI Success: >95% (actual: 100%)
- ✅ Data Coverage: 90 days
- ✅ All endpoints working
- ✅ Validation conditional (no noisy CI)
- ✅ CLI tools complete
- ✅ Documentation comprehensive

---

## 📞 Quick Help

**General Usage:** `.\applylens.ps1 help`  
**CLI Tools Guide:** `docs/CLI-TOOLS-GUIDE.md`  
**Housekeeping:** `docs/HOUSEKEEPING-CHECKLIST.md`  
**Troubleshooting:** `docs/GITHUB-ACTIONS-VERIFICATION.md`  
**Production Setup:** `docs/PRODUCTION-HARDENING-COMPLETE.md`

---

**Version:** Phase 15 Complete  
**Last Run:** Run #18579613903 (Success)  
**Next Scheduled Run:** Nightly 4:17 AM UTC
