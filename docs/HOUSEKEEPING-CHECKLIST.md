# Warehouse Housekeeping Checklist

This document tracks recurring maintenance tasks for the ApplyLens warehouse infrastructure.

## 🔐 Security & Credentials

### Service Account Key Rotation
**Frequency:** Every 90 days  
**Last Rotated:** [FILL IN CURRENT DATE]  
**Next Rotation:** [FILL IN DATE + 90 DAYS]

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
```powershell
# Set Windows Task Scheduler reminder
$action = New-ScheduledTaskAction -Execute "msg" -Argument "$env:USERNAME /TIME:60 'Rotate SA key for applylens-warehouse'"
$trigger = New-ScheduledTaskTrigger -Once -At ([DateTime]::Now.AddDays(90))
Register-ScheduledTask -TaskName "SA Key Rotation Reminder" -Action $action -Trigger $trigger
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
**Status:** ⏳ NEEDS UPDATE (currently 60 minutes)  
**Target:** 15 minutes (to meet <30 min freshness SLO)

**Current Performance:**
- Freshness lag: 10-12 minutes (with 60-min sync)
- API freshness SLO: <30 minutes
- Target lag: <15 minutes (with 15-min sync)

**Update Procedure:**
1. Navigate to Fivetran dashboard: https://fivetran.com/dashboard
2. Select Gmail connector for `applylens-gmail-1759983601`
3. Settings → Sync Frequency
4. Change from "60 minutes" to "15 minutes"
5. Save changes
6. Monitor first few syncs in Logs tab
7. Verify freshness: `Invoke-RestMethod 'http://localhost:8003/api/metrics/profile/freshness'`
8. Confirm: `minutes_since_sync` should be <15 min

**Cost Impact:**
- Current: 90k MAR (18% of 500k free tier)
- With 15-min sync: ~360k MAR (72% of free tier)
- Still within free tier ✅

---

## 📊 Monitoring & Uptime

### Uptime Monitoring Schedule
**Status:** ✅ Complete (if scheduled)

**Script:** `analytics\ops\uptime-monitor.ps1`

**Scheduled Task Setup:**
```powershell
$action = New-ScheduledTaskAction -Execute "PowerShell.exe" `
  -Argument "-NoProfile -ExecutionPolicy Bypass -File D:\ApplyLens\analytics\ops\uptime-monitor.ps1"

$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) `
  -RepetitionInterval (New-TimeSpan -Minutes 5) `
  -RepetitionDuration ([TimeSpan]::MaxValue)

$settings = New-ScheduledTaskSettingsSet `
  -ExecutionTimeLimit (New-TimeSpan -Minutes 2) `
  -RestartCount 3 `
  -RestartInterval (New-TimeSpan -Minutes 1)

Register-ScheduledTask `
  -TaskName "ApplyLens Warehouse Uptime Monitor" `
  -Action $action `
  -Trigger $trigger `
  -Settings $settings `
  -Description "Monitors warehouse API freshness and pushes metrics to Prometheus"
```

**Verify Task:**
```powershell
Get-ScheduledTask -TaskName "ApplyLens Warehouse Uptime Monitor"
Get-ScheduledTaskInfo -TaskName "ApplyLens Warehouse Uptime Monitor"
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

- [ ] Rotate SA key (set calendar reminder for 90 days)
- [x] **Set up GCP budget alert ($10/month threshold)** ✅ **COMPLETE (2025-10-16)**
- [ ] Update Fivetran sync frequency (60 min → 15 min)
- [ ] Schedule uptime monitoring (every 5 minutes)
- [ ] Add metrics to monthly review table
- [ ] Test ES validation with `validate_es=true` flag

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
