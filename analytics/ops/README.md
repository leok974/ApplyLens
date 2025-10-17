# Analytics Operations - Fivetran & BigQuery Integration

Complete setup and operational guide for ApplyLens warehouse analytics powered by Fivetran and BigQuery.

## Overview

This integration provides:
- **Real-time Gmail sync** via Fivetran (15-minute intervals)
- **dbt transformations** for clean, tested analytics
- **API endpoints** serving warehouse metrics
- **Automated validation** ensuring ES ↔ BQ consistency
- **Nightly refresh** via GitHub Actions

## Architecture

```
Gmail → Fivetran (15min sync) → BigQuery (gmail_raw)
                                      ↓
                                dbt staging (gmail_raw_stg)
                                      ↓
                                dbt marts (gmail_marts)
                                      ↓
                          API (/api/metrics/profile/*)
                                      ↓
                            Grafana dashboards
```

---

## 1. BigQuery Setup

### Create Dataset

```bash
bq --location=US mk --dataset ${GCP_PROJECT}:gmail_raw

bq --location=US mk --dataset ${GCP_PROJECT}:gmail_raw_stg

bq --location=US mk --dataset ${GCP_PROJECT}:gmail_marts
```

### Create Service Account

```bash
# Create service account for warehouse operations
gcloud iam service-accounts create applylens-warehouse \
  --display-name="ApplyLens Warehouse (read)" \
  --project=${GCP_PROJECT}

# Grant BigQuery permissions
gcloud projects add-iam-policy-binding ${GCP_PROJECT} \
  --member="serviceAccount:applylens-warehouse@${GCP_PROJECT}.iam.gserviceaccount.com" \
  --role="roles/bigquery.dataViewer"

gcloud projects add-iam-policy-binding ${GCP_PROJECT} \
  --member="serviceAccount:applylens-warehouse@${GCP_PROJECT}.iam.gserviceaccount.com" \
  --role="roles/bigquery.jobUser"

# Create and download key
gcloud iam service-accounts keys create applylens-warehouse-key.json \
  --iam-account=applylens-warehouse@${GCP_PROJECT}.iam.gserviceaccount.com

# Store in secrets directory
mv applylens-warehouse-key.json secrets/
```

---

## 2. Fivetran Configuration

### Gmail Connector Setup

1. **Log in to Fivetran** → https://fivetran.com
2. **Create Connector:**
   - Type: **Gmail**
   - OAuth: Authenticate with your Gmail account
   - Destination: **BigQuery** → Dataset: `gmail_raw`
3. **Configure Sync:**
   - Backfill: **60 days** (initial historical data)
   - Frequency: **15 minutes** (near real-time)
   - Tables: Enable `messages`, `threads`, `labels`
4. **Start Initial Sync**

### Expected Tables

After initial sync, you should see:
- `gmail_raw.messages` (~1.94K rows for 60-day backfill)
- `gmail_raw.threads` (conversation groupings)
- `gmail_raw.labels` (Gmail categories and labels)

---

## 3. dbt Setup

### Install dbt

```bash
pip install dbt-bigquery dbt-core
```

### Configure Profile

Create `~/.dbt/profiles.yml`:

```yaml
applylens:
  target: prod
  outputs:
    prod:
      type: bigquery
      method: service-account
      project: your-gcp-project
      dataset: gmail_raw_stg
      threads: 4
      keyfile: /path/to/applylens-warehouse-key.json
      location: US
```

### Install Dependencies

```bash
cd analytics/dbt
dbt deps
```

### Run Models

```bash
# Run staging models
dbt run --select models/staging/fivetran

# Run mart models
dbt run --select models/marts/warehouse

# Run all models
dbt run --target prod

# Run tests
dbt test --target prod
```

---

## 4. API Integration

### Enable Warehouse Metrics

Update `infra/.env.prod`:

```bash
# Fivetran & BigQuery warehouse
USE_WAREHOUSE_METRICS=1
GCP_PROJECT=your-gcp-project
BQ_MARTS_DATASET=gmail_marts
GOOGLE_APPLICATION_CREDENTIALS=/app/secrets/applylens-warehouse-key.json
```

### Mount Service Account Key

Update `docker-compose.prod.yml`:

```yaml
api:
  volumes:
    - ./secrets/applylens-warehouse-key.json:/app/secrets/applylens-warehouse-key.json:ro
  environment:
    USE_WAREHOUSE_METRICS: ${USE_WAREHOUSE_METRICS:-0}
    GCP_PROJECT: ${GCP_PROJECT}
    BQ_MARTS_DATASET: ${BQ_MARTS_DATASET:-gmail_marts}
    GOOGLE_APPLICATION_CREDENTIALS: /app/secrets/applylens-warehouse-key.json
```

### Test Endpoints

```bash
# Daily activity
curl http://localhost/api/metrics/profile/activity_daily

# Top senders
curl http://localhost/api/metrics/profile/top_senders_30d?limit=10

# Categories
curl http://localhost/api/metrics/profile/categories_30d

# Freshness check
curl http://localhost/api/metrics/profile/freshness
```

---

## 5. GitHub Actions Setup

### Configure Secrets

In your GitHub repository settings, add:

```
GCP_PROJECT: your-gcp-project-id
GCP_SA_JSON: <paste contents of applylens-warehouse-key.json>
ES_URL: http://elasticsearch:9200 (or your ES endpoint)
PUSHGATEWAY_URL: http://prometheus-pushgateway:9091
```

### Workflow Schedule

The workflow runs nightly at **4:17 AM UTC**:
- Runs dbt models
- Runs dbt tests
- Validates ES vs BQ consistency
- Pushes metrics to Prometheus

### Manual Trigger

```bash
# Trigger workflow manually
gh workflow run dbt.yml

# Skip validation
gh workflow run dbt.yml -f skip_validation=true
```

---

## 6. Validation & Monitoring

### Run Validation Manually

```bash
cd analytics/ops

# Set environment
export GCP_PROJECT=your-gcp-project
export ES_URL=http://localhost:9200
export PUSHGATEWAY=http://localhost:9091
export GOOGLE_APPLICATION_CREDENTIALS=../../secrets/applylens-warehouse-key.json

# Run validation
python validate_es_vs_bq.py
```

### Expected Output

```
=============================================================
Starting ES vs BQ validation
Timestamp: 2025-10-16T22:00:00
Threshold: 2.0%
=============================================================

Validation Results:
  Elasticsearch: 1,940 documents
  BigQuery:      1,935 documents
  Delta:         5 documents (0.26%)
  Threshold:     2.0%

✅ VALIDATION PASSED (delta 0.26% <= 2.0%)
```

### Prometheus Metrics

Available metrics:
- `applylens_gmail_7d_delta_pct`: Percentage difference between ES and BQ
- `applylens_gmail_7d_es_count`: Elasticsearch document count
- `applylens_gmail_7d_bq_count`: BigQuery document count
- `applylens_gmail_validation_passed`: 1 if passed, 0 if failed

### Alerting Rules

Add to Prometheus:

```yaml
groups:
  - name: warehouse_validation
    interval: 5m
    rules:
      - alert: WarehouseDataDrift
        expr: applylens_gmail_7d_delta_pct > 2
        for: 1h
        annotations:
          summary: "ES vs BQ data drift detected"
          description: "Delta is {{ $value }}% (threshold: 2%)"

      - alert: FivetranSyncStale
        expr: (time() - applylens_fivetran_last_sync_timestamp) / 60 > 30
        for: 15m
        annotations:
          summary: "Fivetran sync is stale"
          description: "Last sync was {{ $value }} minutes ago"
```

---

## 7. Grafana Dashboards

### Import Dashboard

1. Navigate to **Grafana** → http://localhost:3000
2. **Dashboards** → **Import**
3. Use the following panels:

### Panel 1: Daily Email Activity

```json
{
  "datasource": "Prometheus",
  "targets": [{
    "expr": "sum by (day) (applylens_gmail_messages_daily)",
    "legendFormat": "Messages"
  }],
  "title": "Email Activity (Daily)"
}
```

### Panel 2: Top Senders (Table)

Use **Infinity** datasource with:
- URL: `http://api:8000/api/metrics/profile/top_senders_30d?limit=20`
- Type: JSON
- Columns: `from_email`, `messages_30d`, `total_size_mb`

### Panel 3: Category Distribution (Pie Chart)

Use **Infinity** datasource with:
- URL: `http://api:8000/api/metrics/profile/categories_30d`
- Type: JSON
- Columns: `category`, `messages_30d`, `pct_of_total`

---

## 8. Operational Procedures

### Daily Checks

```bash
# Check Fivetran sync status
curl http://localhost/api/metrics/profile/freshness

# Check validation status
curl http://prometheus:9090/api/v1/query?query=applylens_gmail_validation_passed

# Check dbt run status
gh run list --workflow=dbt.yml --limit=1
```

### Monthly Maintenance

1. **Review BigQuery costs** in GCP Console
2. **Check Fivetran MAR usage** (Monthly Active Rows)
3. **Audit dbt model performance** (`dbt run --target prod --profile-path`)
4. **Review validation metrics** (delta trends)

### Troubleshooting

#### Fivetran Sync Failing

```bash
# Check Fivetran logs
# Navigate to Fivetran dashboard → Connector → Logs

# Check BigQuery permissions
gcloud projects get-iam-policy ${GCP_PROJECT} \
  --flatten="bindings[].members" \
  --format="table(bindings.role)" \
  --filter="bindings.members:serviceAccount:fivetran@*"
```

#### dbt Models Failing

```bash
# Run with debug logging
dbt run --target prod --debug

# Test staging models only
dbt run --select models/staging/fivetran --debug

# Check BigQuery query history
bq ls -j -a -n 100 ${GCP_PROJECT}
```

#### API Endpoints Returning Errors

```bash
# Check API logs
docker logs applylens-api-prod -f --tail=100

# Test BigQuery connection
docker exec applylens-api-prod python -c "
from google.cloud import bigquery
import os
client = bigquery.Client(project=os.getenv('GCP_PROJECT'))
print('BQ connected:', client.project)
"

# Check service account permissions
docker exec applylens-api-prod python -c "
import os
print('GOOGLE_APPLICATION_CREDENTIALS:', os.getenv('GOOGLE_APPLICATION_CREDENTIALS'))
print('File exists:', os.path.exists(os.getenv('GOOGLE_APPLICATION_CREDENTIALS')))
"
```

---

## 9. Cost Management

### Expected Costs

| Component | Monthly Cost (Estimate) |
|-----------|------------------------|
| Fivetran (Gmail) | $5-20 (based on MAR) |
| BigQuery Storage | $0.50-2 (for 90-day data) |
| BigQuery Queries | $1-5 (nightly dbt + API) |
| **Total** | **$6.50-27/month** |

### Cost Optimization

1. **Use clustering and partitioning** (already configured)
2. **Limit dbt query bytes** (set in `dbt_project.yml`)
3. **Cache API responses** (5-minute TTL configured)
4. **Monitor Fivetran MAR** (set alerts at 75% of limit)

### Set Budget Alerts

```bash
# Create budget alert
gcloud billing budgets create \
  --billing-account=${BILLING_ACCOUNT_ID} \
  --display-name="ApplyLens Warehouse Budget" \
  --budget-amount=50 \
  --threshold-rule=percent=80 \
  --threshold-rule=percent=100
```

---

## 10. Rollback Plan

### Disable Warehouse Metrics

```bash
# Update environment
echo "USE_WAREHOUSE_METRICS=0" >> infra/.env.prod

# Restart API
docker compose -f docker-compose.prod.yml --env-file infra/.env.prod restart api
```

### Pause Fivetran Sync

1. Navigate to Fivetran dashboard
2. Select Gmail connector
3. Click **Pause Connector**

### Fallback to Elasticsearch

The API automatically falls back to ES when `USE_WAREHOUSE_METRICS=0`.

---

## 11. Success Metrics

- ✅ **Sync Freshness**: <30 minutes (SLO)
- ✅ **Data Drift**: <2% between ES and BQ
- ✅ **dbt Tests**: 100% passing
- ✅ **API Latency**: <500ms p95
- ✅ **Cost**: <$30/month

---

## 12. Resources

- **Fivetran Documentation**: https://fivetran.com/docs/applications/gmail
- **dbt BigQuery Guide**: https://docs.getdbt.com/docs/core/connect-data-platform/bigquery-setup
- **BigQuery Best Practices**: https://cloud.google.com/bigquery/docs/best-practices
- **Prometheus Pushgateway**: https://prometheus.io/docs/practices/pushing/

---

**Last Updated**: October 16, 2025
**Maintainer**: ApplyLens Team
