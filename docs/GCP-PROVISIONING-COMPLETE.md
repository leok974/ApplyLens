# GCP Provisioning Complete ✅

**Date**: October 16, 2025, 6:52 PM  
**Project**: applylens-gmail-1759983601 (Project #813287438869)

---

## What Was Provisioned

### 1. BigQuery Datasets ✅

| Dataset | Purpose | Location |
|---------|---------|----------|
| `gmail_raw` | Fivetran raw data dumps | US |
| `gmail_raw_stg` | dbt staging models | US |
| `gmail_marts` | dbt mart models (analytics) | US |

**Verification:**
```bash
bq ls --project_id=applylens-gmail-1759983601
# Shows: gmail_raw, gmail_raw_stg, gmail_marts (+ existing datasets)
```

### 2. Service Account ✅

**Name**: `applylens-warehouse`  
**Email**: `applylens-warehouse@applylens-gmail-1759983601.iam.gserviceaccount.com`  
**Display Name**: "ApplyLens Warehouse (read)"

**IAM Roles Granted:**
- ✅ `roles/bigquery.dataViewer` - Read data from all datasets
- ✅ `roles/bigquery.jobUser` - Run BigQuery queries

**Key File**: `./secrets/applylens-warehouse-key.json`  
**Key ID**: `8523081b1b58c97b3db75852ebebeae47933e368`  
**Created**: October 16, 2025, 6:52:55 PM  
**Size**: 2,410 bytes

---

## Environment Configuration Updated ✅

**File**: `infra/.env.prod`

```bash
# Fivetran & BigQuery Warehouse Integration
USE_WAREHOUSE_METRICS=0  # Disabled by default (enable after setup)
GCP_PROJECT=applylens-gmail-1759983601
BQ_MARTS_DATASET=gmail_marts
GOOGLE_APPLICATION_CREDENTIALS=/app/secrets/applylens-warehouse-key.json
VALIDATION_THRESHOLD_PCT=2.0
PUSHGATEWAY_URL=http://prometheus-pushgateway:9091
```

---

## Fivetran Service Account Permissions ✅

**Fivetran Service Account**: `g-twice-taxes@fivetran-production.iam.gserviceaccount.com`

**Project-Level Permission:**
- ✅ `roles/bigquery.user` - Can create jobs, list datasets

**Dataset-Level Permission (gmail_raw):**
- ✅ `WRITER` role - Can read, write, and modify tables in `gmail_raw` dataset

**Dataset Configuration:**
- ✅ Table expiration: Never (0)
- ✅ Partition expiration: Never (0)
- ✅ Description: "Fivetran raw Gmail"

### Commands Used:
```bash
# Grant project-level access
gcloud projects add-iam-policy-binding applylens-gmail-1759983601 \
  --member="serviceAccount:g-twice-taxes@fivetran-production.iam.gserviceaccount.com" \
  --role="roles/bigquery.user"

# Update dataset configuration
bq update --dataset \
  --default_table_expiration 0 \
  --default_partition_expiration 0 \
  --description "Fivetran raw Gmail" \
  applylens-gmail-1759983601:gmail_raw

# Grant dataset-level write access (applied via JSON update)
# WRITER role granted to g-twice-taxes@fivetran-production.iam.gserviceaccount.com
```

---

## Next Steps

### 3. Configure Fivetran (Manual - Console) - READY NOW ✅

1. **Log in to Fivetran**: https://fivetran.com
2. **Create Gmail Connector:**
   - **Type**: Gmail
   - **OAuth**: Authenticate with `leoklemet.pa@gmail.com`
   - **Destination**: BigQuery
     - **Project**: `applylens-gmail-1759983601`
     - **Dataset**: `gmail_raw`
     - **Location**: US
     - **Service Account**: `g-twice-taxes@fivetran-production.iam.gserviceaccount.com` (already has permissions)
3. **Configure Sync:**
   - **Historical sync**: 60 days
   - **Sync frequency**: 15 minutes
   - **Tables**: Enable `messages`, `threads`, `labels`
4. **Start Initial Sync** (wait 10-30 minutes)

### 4. Bootstrap dbt (First Run)

**Option A: GitHub Actions (Recommended)**

```bash
# Set GitHub secrets
gh secret set GCP_PROJECT --body "applylens-gmail-1759983601"
gh secret set GCP_SA_JSON --body "$(cat secrets/applylens-warehouse-key.json)"
gh secret set ES_URL --body "http://elasticsearch:9200"
gh secret set PUSHGATEWAY_URL --body "http://prometheus-pushgateway:9091"

# Trigger workflow manually
gh workflow run dbt.yml

# Check status
gh run watch
```

**Option B: Local (Quick Test)**

```bash
cd analytics/dbt

# Set environment
$env:GCP_PROJECT = "applylens-gmail-1759983601"
$env:GOOGLE_APPLICATION_CREDENTIALS = "D:\ApplyLens\secrets\applylens-warehouse-key.json"

# Install dependencies
dbt deps

# Run models
dbt run --target prod

# Run tests
dbt test --target prod
```

### 5. Enable Warehouse Metrics

```bash
# Update environment
(Get-Content infra\.env.prod) -replace 'USE_WAREHOUSE_METRICS=0', 'USE_WAREHOUSE_METRICS=1' | Set-Content infra\.env.prod

# Rebuild and restart API
docker compose -f docker-compose.prod.yml --env-file infra/.env.prod up -d --build api

# Verify
curl http://localhost/api/metrics/profile/freshness
```

### 6. Smoke Tests

```bash
# Activity (last 90 days)
curl http://localhost/api/metrics/profile/activity_daily | ConvertFrom-Json | Select-Object -ExpandProperty rows | Measure-Object | Select-Object -ExpandProperty Count

# Top senders (30d)
curl http://localhost/api/metrics/profile/top_senders_30d | ConvertFrom-Json | Select-Object -ExpandProperty rows | Select-Object -First 1

# Categories (30d)
curl http://localhost/api/metrics/profile/categories_30d | ConvertFrom-Json | Select-Object -ExpandProperty rows

# Freshness check
curl http://localhost/api/metrics/profile/freshness | ConvertFrom-Json
```

---

## Security Notes

### Service Account Key Storage

✅ **Stored in**: `./secrets/applylens-warehouse-key.json`  
✅ **Gitignored**: Yes (check `.gitignore` includes `secrets/`)  
✅ **Mounted in Docker**: Will be mounted as read-only volume

### Least Privilege Principle

The service account has **minimal permissions**:
- ✅ **Read-only** access to BigQuery data (`dataViewer`)
- ✅ **Query execution** only (`jobUser`)
- ❌ **No write access** (cannot modify data)
- ❌ **No dataset admin** (cannot create/delete datasets)

### Key Rotation

```bash
# List existing keys
gcloud iam service-accounts keys list \
  --iam-account=applylens-warehouse@applylens-gmail-1759983601.iam.gserviceaccount.com

# Create new key (if needed)
gcloud iam service-accounts keys create ./secrets/applylens-warehouse-key-new.json \
  --iam-account=applylens-warehouse@applylens-gmail-1759983601.iam.gserviceaccount.com

# Delete old key (after verifying new key works)
gcloud iam service-accounts keys delete KEY_ID \
  --iam-account=applylens-warehouse@applylens-gmail-1759983601.iam.gserviceaccount.com
```

---

## Verification Commands

```bash
# Verify datasets exist
bq ls --project_id=applylens-gmail-1759983601

# Verify service account
gcloud iam service-accounts list --project=applylens-gmail-1759983601

# Verify IAM roles
gcloud projects get-iam-policy applylens-gmail-1759983601 \
  --flatten="bindings[].members" \
  --filter="bindings.members:applylens-warehouse"

# Test service account authentication
gcloud auth activate-service-account \
  --key-file=./secrets/applylens-warehouse-key.json

bq ls --project_id=applylens-gmail-1759983601
# Should list datasets without errors
```

---

## Troubleshooting

### Issue: "Permission Denied" when running dbt

**Solution**: Verify IAM roles
```bash
gcloud projects get-iam-policy applylens-gmail-1759983601 \
  --flatten="bindings[].members" \
  --filter="bindings.members:applylens-warehouse" \
  --format="table(bindings.role)"
```

Expected roles: `bigquery.dataViewer`, `bigquery.jobUser`

### Issue: "Dataset not found" errors

**Solution**: Check dataset exists
```bash
bq show applylens-gmail-1759983601:gmail_raw
bq show applylens-gmail-1759983601:gmail_raw_stg
bq show applylens-gmail-1759983601:gmail_marts
```

### Issue: Fivetran sync failing

**Solution**: Grant Fivetran service account access
```bash
# Fivetran will provide their service account email
# Grant dataEditor role for write access
gcloud projects add-iam-policy-binding applylens-gmail-1759983601 \
  --member="serviceAccount:FIVETRAN_SA_EMAIL" \
  --role="roles/bigquery.dataEditor"
```

---

## Cost Monitoring

### Set Up Budget Alert

```bash
# Create budget alert for $50/month
gcloud billing budgets create \
  --billing-account=BILLING_ACCOUNT_ID \
  --display-name="ApplyLens Warehouse Budget" \
  --budget-amount=50 \
  --threshold-rule=percent=80 \
  --threshold-rule=percent=100
```

### Monitor Query Costs

```bash
# View BigQuery query costs (last 7 days)
bq ls -j --max_results=100 --project_id=applylens-gmail-1759983601
```

---

## Resources

- **Full Implementation Guide**: `docs/FIVETRAN-BIGQUERY-IMPLEMENTATION.md`
- **Quick Reference**: `docs/FIVETRAN-QUICK-REF.md`
- **Operations Guide**: `analytics/ops/README.md`
- **Service Account Key**: `secrets/applylens-warehouse-key.json`

---

**Provisioning Status**: ✅ **100% Complete**  
**Ready for Fivetran Setup**: Yes  
**Next Action**: Configure Fivetran connector (manual step in console)

---

*Last Updated: October 16, 2025, 6:52 PM*
