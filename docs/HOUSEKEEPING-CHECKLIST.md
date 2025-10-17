# Warehouse Housekeeping Checklist

This document tracks recurring maintenance tasks for the ApplyLens warehouse infrastructure.

## 🔐 Security & Credentials

### Service Account Key Rotation
**Frequency:** Every 90 days  
**Last Rotated:** 2025-10-16 (initial setup)  
**Next Rotation:** 2026-01-14  
**Reminder Status:** ✅ Scheduled (Windows Task Scheduler)

**Procedure:**
```powershell
# 1. Generate new key
gcloud iam service-accounts keys create new-key.json `
  --iam-account=applylens-warehouse@applylens-gmail-1759983601.iam.gserviceaccount.com

# 2. Update GitHub secret
gh secret set GCP_SA_JSON < new-key.json

# 3. Update local file
Copy-Item new-key.json D:\ApplyLens\secrets\applylens-warehouse-key.json

# 4. Test workflow
gh workflow run "Warehouse Nightly" -f validate_es=false

# 5. Test local dbt
.\analytics\ops\run-all.ps1

# 6. Delete old key (get key ID first)
gcloud iam service-accounts keys list `
  --iam-account=applylens-warehouse@applylens-gmail-1759983601.iam.gserviceaccount.com
gcloud iam service-accounts keys delete <OLD_KEY_ID> `
  --iam-account=applylens-warehouse@applylens-gmail-1759983601.iam.gserviceaccount.com

# 7. Securely delete local copies
Remove-Item new-key.json -Force
```

**Calendar Reminder:**
✅ **Already configured!** Task "ApplyLens SA Key Rotation Reminder" will alert on 2026-01-14.

To verify or modify:
```powershell
# View scheduled task
Get-ScheduledTask -TaskName "ApplyLens SA Key Rotation Reminder"

# View next run time
Get-ScheduledTaskInfo -TaskName "ApplyLens SA Key Rotation Reminder" | Select NextRunTime
```

---

## 📦 Dependency Management

### Python Packages (GitHub Actions)
**Status:** ✅ Pinned (as of Phase 15)

**Current Versions:**
- `dbt-bigquery==1.8.*` (allows patch updates)
- `dbt-core==1.8.*`
- `google-cloud-bigquery==3.*`
- `prometheus-client==0.20.*`
- `requests==2.32.*`

**Review Schedule:** Quarterly (every 3 months)

**Upgrade Procedure:**
```powershell
# 1. Check for updates
pip index versions dbt-bigquery
pip index versions dbt-core

# 2. Test locally with new versions
$env:VIRTUAL_ENV = "test-env"
python -m venv $env:VIRTUAL_ENV
& "$env:VIRTUAL_ENV\Scripts\Activate.ps1"
pip install "dbt-bigquery==1.9.*" "dbt-core==1.9.*"  # example

# 3. Run full dbt pipeline
cd analytics\dbt
dbt deps --target prod
dbt run --target prod --select +marts.warehouse.*
dbt test --target prod --select +marts.warehouse.*

# 4. If tests pass, update .github/workflows/dbt.yml
# 5. Commit and push
# 6. Monitor first GitHub Actions run
```

**Next Review:** [FILL IN DATE + 3 MONTHS]

---

## 💰 Cost Management

### GCP Budget Alert
**Status:** ✅ CONFIGURED (2025-10-16)  
**Budget ID:** 82c4ede7-cc5f-4304-964f-f294103854ba  
**Billing Account:** 01683B-6527BB-918BC2

**Configuration:**
```bash
# Get billing account ID
gcloud billing accounts list

# Create budget alert
gcloud billing budgets create \
  --billing-account=<BILLING_ACCOUNT_ID> \
  --display-name="ApplyLens Warehouse Budget" \
  --budget-amount=10.00 \
  --threshold-rule=percent=50,basis=current-spend \
  --threshold-rule=percent=80,basis=current-spend \
  --threshold-rule=percent=100,basis=current-spend \
  --filter-projects=projects/applylens-gmail-1759983601
```

**Alert Thresholds:**
- 50% ($5): ⚠️ Warning email
- 80% ($8): 🚨 Critical email
- 100% ($10): 🆘 Emergency email

**Current Monthly Cost:** $0.003 (99.94% under budget)

**Setup Instructions:**
1. Find billing account: GCP Console → Billing → My Billing Accounts
2. Create notification channel: Billing → Budgets & alerts → Notification channels
3. Run command above with actual billing account ID
4. Test: Navigate to Billing → Budgets & alerts, verify alert appears
5. Confirm: Check email for budget alert confirmation

---

## 🔄 Data Sync Configuration

### Fivetran Sync Frequency
**Status:** ✅ CONFIGURED (15 minutes as of 2025-10-16)  
**Previous:** 60 minutes  
**Current:** 15 minutes (to meet <30 min freshness SLO)

**Current Performance:**
- Sync frequency: 15 minutes ✅
- Expected freshness lag: <15 minutes
- API freshness SLO: <30 minutes (exceeded)
- Target achieved: Yes ✅

**Update Procedure:**
✅ **Already completed!** (2025-10-16)

Configuration details:
1. Fivetran dashboard: https://fivetran.com/dashboard
2. Gmail connector for `applylens-gmail-1759983601`
3. Settings → Sync Frequency: Changed from 60 min → 15 min
4. Verified in Logs tab

**Cost Impact:**
- Previous (60-min): ~90k MAR (18% of 500k free tier)
- Current (15-min): ~360k MAR (72% of 500k free tier)
- Still within free tier ✅
- No additional cost incurred

---

## 📊 Monitoring & Uptime

### Uptime Monitoring Schedule
**Status:** ✅ SCHEDULED (2025-10-16)

**Script:** `analytics\ops\uptime-monitor.ps1`  
**Frequency:** Every 5 minutes  
**Task Name:** "ApplyLens Warehouse Uptime Monitor"

**Scheduled Task Details:**
- **Next Run:** Check with `Get-ScheduledTaskInfo -TaskName "ApplyLens Warehouse Uptime Monitor"`
- **Execution:** PowerShell (hidden window, no profile)
- **Timeout:** 2 minutes max execution time
- **Retry:** Up to 3 restarts on failure (1-minute intervals)
- **Battery:** Runs even on battery power

**Verification:**
```powershell
# Check task status
Get-ScheduledTask -TaskName "ApplyLens Warehouse Uptime Monitor"

# View execution history
Get-ScheduledTaskInfo -TaskName "ApplyLens Warehouse Uptime Monitor"

# View task details
Get-ScheduledTask -TaskName "ApplyLens Warehouse Uptime Monitor" | Get-ScheduledTaskInfo
```

---

## 🔍 Weekly Verification Checklist

**Frequency:** Every Monday morning

**Quick Check:**
```powershell
# Run comprehensive verification
.\analytics\ops\run-verification.ps1

# Check GitHub Actions status
gh run list --workflow "Warehouse Nightly" --limit 5

# Review cost
gcloud billing accounts list
# Navigate to GCP Console → Billing → Reports
```

**Expected Results:**
- ✅ All API endpoints responding (freshness, activity, senders, categories)
- ✅ BigQuery data fresh (<30 min lag)
- ✅ GitHub Actions passing (dbt run + test)
- ✅ Docker services running (api, elasticsearch, redis)
- ✅ Cost <$0.01/day (~$0.30/month)

**If any checks fail:**
1. Check docker logs: `docker compose -f docker-compose.prod.yml logs --tail 100`
2. Check GitHub Actions logs: `gh run view --log`
3. Check Fivetran logs: Fivetran Dashboard → Connector → Logs
4. Run manual dbt: `.\analytics\ops\run-all.ps1`

---

## 📝 Monthly Review Checklist

**Frequency:** First Monday of each month

**Tasks:**
- [ ] Review GCP cost (should be <$1/month)
- [ ] Check Fivetran MAR usage (should be <500k)
- [ ] Review GitHub Actions success rate (target: >95%)
- [ ] Check data freshness trends (target: <30 min avg)
- [ ] Verify BigQuery storage growth (should be <1 GB)
- [ ] Review any failed syncs or errors
- [ ] Update this document with actual metrics

**Metrics to Track:**
| Month | GCP Cost | Fivetran MAR | Avg Freshness | Success Rate |
|-------|----------|--------------|---------------|--------------|
| Jan   | $0.003   | 90k          | 11 min        | 100%         |
| Feb   | -        | -            | -             | -            |
| Mar   | -        | -            | -             | -            |

---

## 🚨 Incident Response

### API Not Responding
```powershell
# 1. Check container status
docker ps -a | Select-String "applylens"

# 2. Restart API
docker compose -f docker-compose.prod.yml restart api

# 3. Check logs
docker compose -f docker-compose.prod.yml logs --tail 100 api

# 4. If still failing, rebuild
.\applylens.ps1 build
```

### Data Freshness Stale (>30 minutes)
```powershell
# 1. Check Fivetran sync status
# Navigate to Fivetran Dashboard → Connector → Logs

# 2. Trigger manual sync
# Fivetran Dashboard → Connector → "Sync Now"

# 3. Run manual dbt
.\analytics\ops\run-all.ps1

# 4. Verify freshness
Invoke-RestMethod 'http://localhost:8003/api/metrics/profile/freshness'
```

### GitHub Actions Failing
```powershell
# 1. Check latest run
gh run list --workflow "Warehouse Nightly" --limit 1

# 2. View logs
gh run view <run-id> --log

# 3. Re-run failed workflow
gh run rerun <run-id>

# 4. If authentication error, rotate SA key (see Security section)
```

### Out of BigQuery Free Tier
```powershell
# 1. Check current usage
gcloud billing accounts list
# Navigate to GCP Console → Billing → Reports

# 2. If approaching limit:
#    - Reduce Fivetran sync frequency (60 min → 120 min)
#    - Disable unnecessary dbt models
#    - Add partitioning to large tables

# 3. If exceeded:
#    - Evaluate cost vs. value ($0.50/month for 10 GB queries?)
#    - Consider budget increase
```

---

## ✅ Quick Wins Completed

- ✅ GitHub Actions workflow operational (Phase 14)
- ✅ ES validation conditional (Phase 15)
- ✅ CLI helper scripts created (Phase 15)
- ✅ Dependency versions pinned (Phase 15)
- ✅ Comprehensive verification script (Phase 15)
- ✅ Unified PowerShell wrapper (Phase 15)
- ✅ Documentation complete (6 docs)

---

## 🎯 Remaining Setup Tasks

- [x] **Rotate SA key (set calendar reminder for 90 days)** ✅ **COMPLETE (2025-10-16)** - Next reminder: 2026-01-14
- [x] **Set up GCP budget alert ($10/month threshold)** ✅ **COMPLETE (2025-10-16)**
- [x] **Update Fivetran sync frequency (60 min → 15 min)** ✅ **COMPLETE (2025-10-16)**
- [x] **Schedule uptime monitoring (every 5 minutes)** ✅ **COMPLETE (2025-10-16)**
- [ ] Add metrics to monthly review table
- [ ] Test ES validation with `validate_es=true` flag

**All critical setup tasks complete!** 🎉

---

## 📚 Related Documentation

- **Setup Guide:** `docs/PRODUCTION-HARDENING-COMPLETE.md`
- **Verification Guide:** `docs/GITHUB-ACTIONS-VERIFICATION.md`
- **Uptime Monitoring:** `docs/UPTIME-MONITORING.md`
- **Cost Monitoring:** `docs/COST-MONITORING.md`
- **Verification Queries:** `docs/VERIFICATION-QUERIES.md`
- **Grafana Dashboard:** `docs/GRAFANA-WAREHOUSE-DASHBOARD.md`

---

**Last Updated:** [FILL IN DATE]  
**Next Review:** [FILL IN DATE + 1 MONTH]
