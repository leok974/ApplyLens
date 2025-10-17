# Quick Command Reference - Fivetran & BigQuery

**Project**: applylens-gmail-1759983601  
**Status**: GCP provisioned ✅, Fivetran pending ⏳

---

## Copy-Paste Commands

### Verify GCP Setup
```powershell
# Check datasets
bq ls --project_id=applylens-gmail-1759983601

# Check service account
gcloud iam service-accounts list --project=applylens-gmail-1759983601 --filter="email:applylens-warehouse"

# Verify key file
Test-Path ./secrets/applylens-warehouse-key.json
```

### dbt Local Test
```powershell
cd analytics/dbt

# Set environment
$env:GCP_PROJECT = "applylens-gmail-1759983601"
$env:GOOGLE_APPLICATION_CREDENTIALS = "D:\ApplyLens\secrets\applylens-warehouse-key.json"

# Install and run
dbt deps
dbt run --target prod
dbt test --target prod
```

### GitHub Actions Setup
```powershell
# Set secrets
gh secret set GCP_PROJECT --body "applylens-gmail-1759983601"
gh secret set GCP_SA_JSON --body "$(Get-Content secrets/applylens-warehouse-key.json -Raw)"
gh secret set ES_URL --body "http://elasticsearch:9200"
gh secret set PUSHGATEWAY_URL --body "http://prometheus-pushgateway:9091"

# Trigger workflow
gh workflow run dbt.yml
gh run watch
```

### Enable Warehouse Metrics
```powershell
# Update env file
(Get-Content infra\.env.prod) -replace 'USE_WAREHOUSE_METRICS=0', 'USE_WAREHOUSE_METRICS=1' | Set-Content infra\.env.prod

# Restart API
docker compose -f docker-compose.prod.yml --env-file infra/.env.prod restart api
```

### Test API Endpoints
```powershell
# Freshness check
Invoke-RestMethod -Uri 'http://localhost/api/metrics/profile/freshness'

# Daily activity
Invoke-RestMethod -Uri 'http://localhost/api/metrics/profile/activity_daily?days=7'

# Top senders
Invoke-RestMethod -Uri 'http://localhost/api/metrics/profile/top_senders_30d?limit=10'

# Categories
Invoke-RestMethod -Uri 'http://localhost/api/metrics/profile/categories_30d'
```

### Run Validation
```powershell
cd analytics/ops

# Set environment
$env:GCP_PROJECT = "applylens-gmail-1759983601"
$env:ES_URL = "http://localhost:9200"
$env:PUSHGATEWAY = "http://localhost:9091"
$env:GOOGLE_APPLICATION_CREDENTIALS = "D:\ApplyLens\secrets\applylens-warehouse-key.json"

# Run validation
python validate_es_vs_bq.py
```

### Rollback (Emergency)
```powershell
# Disable warehouse
(Get-Content infra\.env.prod) -replace 'USE_WAREHOUSE_METRICS=1', 'USE_WAREHOUSE_METRICS=0' | Set-Content infra\.env.prod
docker compose -f docker-compose.prod.yml --env-file infra/.env.prod restart api
```

---

## Fivetran Configuration (Manual)

1. Go to: https://fivetran.com
2. **Create Connector** → Gmail
3. **OAuth**: `leoklemet.pa@gmail.com`
4. **Destination**: BigQuery
   - Project: `applylens-gmail-1759983601`
   - Dataset: `gmail_raw`
   - Location: US
5. **Sync Settings**:
   - Historical: 60 days
   - Frequency: 15 minutes
   - Tables: messages, threads, labels
6. **Start Sync** → Wait 10-30 min

---

## Status Checks

```powershell
# Check if Fivetran synced data
bq query --use_legacy_sql=false --project_id=applylens-gmail-1759983601 "SELECT COUNT(*) as count FROM \`applylens-gmail-1759983601.gmail_raw.messages\`"

# Check dbt models
bq ls -d --project_id=applylens-gmail-1759983601 gmail_marts

# Check API status
curl http://localhost/api/metrics/profile/freshness
```

---

**Next Steps**: Configure Fivetran connector (see above)
