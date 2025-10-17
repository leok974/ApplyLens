# Fivetran & BigQuery - Quick Reference

**Status**: Ready for deployment  
**Estimated Cost**: $6.50-27/month

---

## Quick Start (30 seconds)

```bash
# 1. Enable warehouse metrics
echo "USE_WAREHOUSE_METRICS=1" >> infra/.env.prod
echo "GCP_PROJECT=your-project-id" >> infra/.env.prod

# 2. Restart API
docker compose -f docker-compose.prod.yml --env-file infra/.env.prod restart api

# 3. Test endpoints
curl http://localhost/api/metrics/profile/freshness
curl http://localhost/api/metrics/profile/activity_daily
```

---

## Architecture

```
Gmail → Fivetran (15min) → BigQuery (gmail_raw)
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

## API Endpoints

| Endpoint | Purpose | Cache | Query Params |
|----------|---------|-------|--------------|
| `/api/metrics/profile/activity_daily` | Daily email metrics | 5min | `days` (1-365) |
| `/api/metrics/profile/top_senders_30d` | Top senders | 5min | `limit` (1-100) |
| `/api/metrics/profile/categories_30d` | Category distribution | 5min | - |
| `/api/metrics/profile/freshness` | Sync status | 1min | - |

---

## dbt Commands

```bash
cd analytics/dbt

# Run all models
dbt run --target prod

# Run only warehouse models
dbt run --select models/staging/fivetran models/marts/warehouse

# Run tests
dbt test --target prod

# Generate docs
dbt docs generate --target prod
```

---

## Files Created

```
analytics/
├── dbt/
│   ├── models/
│   │   ├── staging/fivetran/
│   │   │   ├── stg_gmail__messages.sql
│   │   │   ├── stg_gmail__threads.sql
│   │   │   └── stg_gmail__labels.sql
│   │   ├── marts/warehouse/
│   │   │   ├── mart_email_activity_daily.sql
│   │   │   ├── mart_top_senders_30d.sql
│   │   │   └── mart_categories_30d.sql
│   │   └── schema.yml
│   ├── dbt_project.yml (updated)
│   ├── packages.yml (updated)
│   └── profiles.yml (updated)
└── ops/
    ├── validate_es_vs_bq.py
    └── README.md

services/api/app/routers/
└── metrics_profile.py

.github/workflows/
└── dbt.yml

docs/
└── FIVETRAN-BIGQUERY-IMPLEMENTATION.md
```

---

## Environment Variables

```bash
# Required
USE_WAREHOUSE_METRICS=1
GCP_PROJECT=your-project-id

# Optional (defaults shown)
BQ_MARTS_DATASET=gmail_marts
GOOGLE_APPLICATION_CREDENTIALS=/app/secrets/applylens-warehouse-key.json
VALIDATION_THRESHOLD_PCT=2.0
PUSHGATEWAY_URL=http://prometheus-pushgateway:9091
```

---

## Monitoring

### Prometheus Metrics
- `applylens_gmail_7d_delta_pct` - ES vs BQ difference %
- `applylens_gmail_7d_es_count` - Elasticsearch count
- `applylens_gmail_7d_bq_count` - BigQuery count
- `applylens_gmail_validation_passed` - 1=passed, 0=failed

### Health Checks
```bash
# Check Fivetran sync freshness
curl http://localhost/api/metrics/profile/freshness

# Check validation status
curl http://prometheus:9090/api/v1/query?query=applylens_gmail_validation_passed

# Run validation manually
cd analytics/ops
python validate_es_vs_bq.py
```

---

## Troubleshooting

### API Returns 412 Error
```bash
# Check if warehouse enabled
docker exec applylens-api-prod env | grep USE_WAREHOUSE_METRICS

# Enable warehouse
echo "USE_WAREHOUSE_METRICS=1" >> infra/.env.prod
docker compose -f docker-compose.prod.yml --env-file infra/.env.prod restart api
```

### dbt Models Failing
```bash
# Test BigQuery connection
cd analytics/dbt
dbt debug --target prod

# Run with verbose logging
dbt run --target prod --debug

# Check service account permissions
gcloud projects get-iam-policy ${GCP_PROJECT} \
  --flatten="bindings[].members" \
  --filter="bindings.members:applylens-warehouse"
```

### Validation Failing
```bash
# Check both data sources
curl http://localhost:9200/gmail_emails/_count

# BigQuery count
bq query --use_legacy_sql=false \
  "SELECT SUM(messages_count) FROM \`${GCP_PROJECT}.gmail_marts.mart_email_activity_daily\` \
   WHERE day >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)"

# Expected: <2% difference
```

---

## Cost Optimization

```bash
# Monitor BigQuery costs
gcloud logging read "resource.type=bigquery_resource" \
  --limit=50 --format=json \
  | jq '.[] | select(.protoPayload.serviceData.jobCompletedEvent.job.jobStatistics.totalBilledBytes != null) | .protoPayload.serviceData.jobCompletedEvent.job.jobStatistics.totalBilledBytes'

# Monitor Fivetran MAR
# Navigate to: https://fivetran.com/dashboard/connectors → Gmail → Usage

# Set budget alert
gcloud billing budgets create \
  --billing-account=${BILLING_ACCOUNT_ID} \
  --display-name="ApplyLens Warehouse" \
  --budget-amount=50 \
  --threshold-rule=percent=80
```

---

## Rollback (30 seconds)

```bash
# Disable warehouse metrics
echo "USE_WAREHOUSE_METRICS=0" >> infra/.env.prod
docker compose -f docker-compose.prod.yml --env-file infra/.env.prod restart api

# Pause Fivetran (optional)
# Navigate to: https://fivetran.com/dashboard/connectors → Gmail → Pause
```

---

## Success Metrics

| Metric | Target | Current |
|--------|--------|---------|
| Sync Freshness | <30 min | Check `/freshness` |
| Data Drift | <2% | Check Prometheus |
| dbt Tests | 100% pass | Run `dbt test` |
| API Latency | <500ms p95 | Check Grafana |
| Monthly Cost | <$30 | Check GCP billing |

---

## Resources

- **Full Documentation**: `docs/FIVETRAN-BIGQUERY-IMPLEMENTATION.md`
- **Operations Guide**: `analytics/ops/README.md`
- **Validation Script**: `analytics/ops/validate_es_vs_bq.py`
- **GitHub Workflow**: `.github/workflows/dbt.yml`

---

**Last Updated**: October 16, 2025
