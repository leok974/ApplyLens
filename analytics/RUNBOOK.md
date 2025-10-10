# Analytics Infrastructure Runbook

**Owner**: Data/Platform Team  
**Last Updated**: 2024  
**Related**: Phase 12.4 - Fivetran + BigQuery + dbt + Elasticsearch + Kibana

---

## Overview

This runbook provides operational procedures for the ApplyLens analytics pipeline:

```
PostgreSQL → Fivetran → BigQuery → dbt → Elasticsearch → Kibana
```

**Components**:
- **Fivetran**: Syncs `emails` and `applications` from Postgres to BigQuery hourly
- **BigQuery**: Data warehouse with `applylens` dataset
- **dbt**: Transforms raw data into staging models and mart aggregates
- **Elasticsearch**: Stores daily aggregates in `analytics_applylens_*` indices
- **Kibana**: Visualizes risk trends, parity drift, and backfill SLOs

**Automation**:
- CI workflow runs daily at 3:15 AM UTC (`analytics-sync.yml`)
- Job steps: `dbt deps → dbt run → dbt test → export_to_es.py`

---

## Normal Operations

### Daily Health Check

**What to Monitor**:
1. Fivetran sync status (should complete within 15 minutes of hourly schedule)
2. GitHub Actions workflow success (analytics-sync.yml)
3. Kibana dashboard showing recent data (last 24 hours visible)

**How to Check**:

```bash
# 1. Check Fivetran sync status
# Visit: https://fivetran.com/dashboard/connectors/<connector_id>
# Look for: Green checkmark, "Synced X minutes ago"

# 2. Check GitHub Actions workflow
gh run list --workflow=analytics-sync.yml --limit=5

# 3. Check Elasticsearch indices
curl -s "http://localhost:9200/_cat/indices/analytics_applylens_*?v" | head -20

# 4. Check latest data in ES
curl -s "http://localhost:9200/analytics_applylens_risk_daily/_search" \
  -H 'Content-Type: application/json' \
  -d '{"size": 1, "sort": [{"d": "desc"}]}' | jq '.hits.hits[0]._source.d'
```

**Expected Results**:
- Fivetran: Synced within last hour
- GitHub Actions: Latest run succeeded (green checkmark)
- Elasticsearch: Indices exist with recent data (yesterday's date visible)
- Dashboard: Charts showing data through yesterday

---

## Manual Operations

### Run dbt Locally

**When**: Testing model changes, debugging CI failures, ad-hoc analysis

```bash
cd analytics/dbt

# Set environment variables
export BQ_PROJECT="your-gcp-project-id"
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account.json"

# Install dependencies
pip install dbt-bigquery
dbt deps --profiles-dir .

# Run all models
dbt run --profiles-dir . --target dev

# Run specific model
dbt run --profiles-dir . --target dev --select mrt_risk_daily

# Test models
dbt test --profiles-dir . --target dev

# View compiled SQL
dbt compile --profiles-dir . --select mrt_risk_daily
cat target/compiled/applylens_analytics/models/marts/mrt_risk_daily.sql
```

### Manually Export to Elasticsearch

**When**: CI failure, backfilling historical data, testing export logic

```bash
# Set environment variables
export BQ_PROJECT="your-gcp-project-id"
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account.json"
export ES_URL="http://localhost:9200"
export ES_ANALYTICS_INDEX="analytics_applylens"

# Install dependencies
pip install google-cloud-bigquery elasticsearch

# Run export
python analytics/export/export_to_es.py

# Check output (JSON format)
# Look for: "total_success": <count>, "total_errors": 0
```

### Trigger CI Workflow Manually

**When**: Missed scheduled run, need fresh data immediately

```bash
# Via GitHub CLI
gh workflow run analytics-sync.yml

# Or via GitHub UI:
# 1. Go to Actions tab
# 2. Select "Analytics Sync" workflow
# 3. Click "Run workflow" dropdown
# 4. Click green "Run workflow" button
```

### Query BigQuery Directly

**When**: Validating dbt output, investigating data quality issues

```bash
# Using bq CLI
bq query --project_id=your-project-id --use_legacy_sql=false '
SELECT 
  d,
  emails,
  avg_risk,
  coverage_pct
FROM applylens.marts.mrt_risk_daily
WHERE d >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
ORDER BY d DESC
'

# Using Python
from google.cloud import bigquery
client = bigquery.Client(project='your-project-id')

query = """
SELECT * FROM applylens.marts.mrt_risk_daily
WHERE d = CURRENT_DATE() - 1
"""
df = client.query(query).to_dataframe()
print(df)
```

---

## Troubleshooting

### Fivetran Not Syncing

**Symptoms**: Fivetran dashboard shows "Failed" or "Paused", data not updating in BigQuery

**Diagnosis**:
1. Check connector status in Fivetran UI
2. Review sync logs for error messages
3. Test database connection from Fivetran

**Common Causes & Fixes**:

| Cause | Solution |
|-------|----------|
| Database credentials expired | Rotate password, update in Fivetran |
| IP allowlist out of date | Add new Fivetran egress IPs to Postgres firewall |
| Table schema changed | Re-sync schema in Fivetran, update dbt models |
| Network timeout | Check VPN/firewall, increase timeout settings |
| BigQuery quota exceeded | Check GCP billing, increase quota limits |

**Resolution Steps**:
```bash
# 1. Test database connectivity
psql -h your-db-host -U fivetran_user -d applylens -c "SELECT COUNT(*) FROM emails;"

# 2. Check Fivetran IP allowlist (get current IPs from Fivetran docs)
# Add to pg_hba.conf or cloud firewall rules

# 3. Force re-sync in Fivetran UI
# Connector Settings → Re-sync → Select tables → Start re-sync

# 4. Monitor sync progress
# Wait 10-30 minutes for full table sync
```

### dbt Run Failures

**Symptoms**: GitHub Actions workflow fails at "Run dbt models" step, red X in Actions tab

**Diagnosis**:
1. Check workflow logs in GitHub Actions
2. Look for SQL errors in dbt output
3. Identify failing model(s)

**Common Causes & Fixes**:

| Error Message | Cause | Solution |
|---------------|-------|----------|
| `Relation not found` | Fivetran hasn't synced table yet | Wait for sync, check table name |
| `Syntax error at or near` | SQL typo in model | Fix SQL, test locally with `dbt run` |
| `Exceeded rate limits` | Too many BQ queries | Add `maximum_bytes_billed` limit |
| `Permission denied` | Service account lacks BQ permissions | Grant BigQuery Data Editor role |
| `Timeout` | Query too slow | Add partition pruning, optimize JOIN |

**Resolution Steps**:
```bash
# 1. Download workflow logs
gh run view <run-id> --log

# 2. Test failing model locally
cd analytics/dbt
dbt run --profiles-dir . --target dev --select mrt_risk_daily

# 3. View compiled SQL for debugging
dbt compile --profiles-dir . --select mrt_risk_daily
cat target/compiled/applylens_analytics/models/marts/mrt_risk_daily.sql

# 4. Fix model, commit, and re-trigger workflow
git add analytics/dbt/models/marts/mrt_risk_daily.sql
git commit -m "fix: correct mrt_risk_daily aggregation logic"
git push
gh workflow run analytics-sync.yml
```

### Export to Elasticsearch Failures

**Symptoms**: dbt succeeds, but export script fails with connection/indexing errors

**Diagnosis**:
1. Check export script output in workflow logs
2. Test ES connectivity manually
3. Check ES cluster health

**Common Causes & Fixes**:

| Error Message | Cause | Solution |
|---------------|-------|----------|
| `ConnectionError` | ES not reachable | Check `ES_URL` secret, verify network |
| `AuthenticationException` | ES credentials invalid | Update ES_URL with correct user/pass |
| `RequestError: mapper_parsing_exception` | Schema mismatch | Load ES index template first |
| `Timeout` | ES overloaded | Reduce bulk batch size, scale ES |
| `BQ_PROJECT not set` | Missing env var | Add `BQ_PROJECT` to GitHub secrets |

**Resolution Steps**:
```bash
# 1. Test ES connectivity
curl -I http://localhost:9200

# 2. Check ES cluster health
curl http://localhost:9200/_cluster/health?pretty

# 3. Load index template (if not already loaded)
curl -X PUT "http://localhost:9200/_index_template/analytics_applylens" \
  -H 'Content-Type: application/json' \
  -d @services/api/es/index-templates/analytics_applylens.json

# 4. Run export locally with verbose logging
export BQ_PROJECT="your-project-id"
export ES_URL="http://localhost:9200"
python analytics/export/export_to_es.py 2>&1 | tee export.log

# 5. Check indexed documents
curl "http://localhost:9200/analytics_applylens_risk_daily/_count?pretty"
```

### Kibana Dashboard Shows No Data

**Symptoms**: Dashboard loads but charts are empty or show "No results found"

**Diagnosis**:
1. Check if indices exist in Elasticsearch
2. Verify index pattern in Kibana
3. Check time range filter

**Common Causes & Fixes**:

| Cause | Solution |
|-------|----------|
| Index pattern not created | Create pattern for `analytics_applylens_*` |
| No data exported yet | Wait for nightly sync, or run export manually |
| Time range too narrow | Expand to "Last 90 days" |
| Index template not loaded | Load template, re-export data |
| Wrong index name in dashboard | Update dashboard JSON with correct index |

**Resolution Steps**:
```bash
# 1. Verify indices exist
curl "http://localhost:9200/_cat/indices/analytics_applylens_*?v"

# 2. Check document count
curl "http://localhost:9200/analytics_applylens_risk_daily/_count?pretty"

# 3. Sample documents
curl "http://localhost:9200/analytics_applylens_risk_daily/_search?size=1&pretty"

# 4. Create index pattern in Kibana
# Management → Stack Management → Index Patterns → Create
# Pattern: analytics_applylens_*
# Time field: d

# 5. Re-import dashboard
# Management → Stack Management → Saved Objects → Import
# Upload: services/api/dashboards/analytics-overview.ndjson

# 6. Refresh dashboard and adjust time range
# Top right: Click time picker → Select "Last 90 days"
```

---

## Data Quality Checks

### Verify Row Counts

**Purpose**: Ensure Fivetran sync completeness and dbt aggregation accuracy

```sql
-- In PostgreSQL (source)
SELECT 
  'emails' as table_name,
  COUNT(*) as row_count,
  MAX(received_at) as latest_record
FROM emails
UNION ALL
SELECT 
  'applications',
  COUNT(*),
  MAX(created_at)
FROM applications;

-- In BigQuery (after Fivetran sync)
SELECT 
  'emails' as table_name,
  COUNT(*) as row_count,
  MAX(received_at) as latest_record
FROM `applylens.public_emails`
UNION ALL
SELECT 
  'applications',
  COUNT(*),
  MAX(created_at)
FROM `applylens.public_applications`;

-- In dbt marts
SELECT 
  'mrt_risk_daily' as table_name,
  COUNT(*) as row_count,
  MAX(d) as latest_date
FROM `applylens.marts.mrt_risk_daily`;
```

**Expected**: Row counts match between Postgres and BigQuery (±1% tolerance for sync lag)

### Validate Aggregations

**Purpose**: Spot-check dbt logic for correctness

```sql
-- Verify mrt_risk_daily aggregations
WITH raw AS (
  SELECT 
    DATE(received_at) as d,
    COUNT(*) as email_count,
    AVG(risk_score) as avg_risk
  FROM `applylens.staging.stg_emails`
  WHERE DATE(received_at) = CURRENT_DATE() - 1
  GROUP BY 1
),
mart AS (
  SELECT d, emails, avg_risk
  FROM `applylens.marts.mrt_risk_daily`
  WHERE d = CURRENT_DATE() - 1
)
SELECT 
  raw.email_count as raw_count,
  mart.emails as mart_count,
  raw.avg_risk as raw_avg_risk,
  mart.avg_risk as mart_avg_risk,
  ABS(raw.email_count - mart.emails) as count_diff,
  ABS(raw.avg_risk - mart.avg_risk) as avg_diff
FROM raw
JOIN mart ON raw.d = mart.d;
```

**Expected**: Differences < 0.1% (rounding errors acceptable)

---

## Backfill Procedures

### Backfill Historical Data

**When**: Initial setup, data loss, schema changes requiring full refresh

```bash
# 1. Identify date range to backfill
START_DATE="2024-01-01"
END_DATE="2024-12-31"

# 2. Ensure Fivetran has synced all historical data
# Check Fivetran UI: Connector → Sync History → Verify date range

# 3. Run dbt for full refresh
cd analytics/dbt
dbt run --profiles-dir . --target dev --full-refresh

# 4. Export to Elasticsearch
# Modify export script to query full date range (default: last 90 days)
# Edit: analytics/export/export_to_es.py
# Change: DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY) → '2024-01-01'

python analytics/export/export_to_es.py

# 5. Verify data in Kibana
# Dashboard should now show full historical range
```

---

## Configuration Reference

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `BQ_PROJECT` | Yes | - | GCP project ID |
| `BQ_DATASET` | No | `applylens` | BigQuery dataset name |
| `GOOGLE_APPLICATION_CREDENTIALS` | Yes | - | Path to service account JSON |
| `ES_URL` | Yes | - | Elasticsearch endpoint URL |
| `ES_ANALYTICS_INDEX` | No | `analytics_applylens` | Index name prefix |

### GitHub Secrets

Required secrets for CI workflow:
- `BQ_PROJECT`: GCP project ID
- `BQ_SA_JSON`: Service account JSON content (not path)
- `ES_URL`: Elasticsearch URL (with credentials if auth enabled)

### Service Account Permissions

BigQuery service account needs:
- **BigQuery Data Editor**: Read/write access to `applylens` dataset
- **BigQuery Job User**: Run queries

```bash
# Grant permissions via gcloud
gcloud projects add-iam-policy-binding your-project-id \
  --member="serviceAccount:analytics@your-project.iam.gserviceaccount.com" \
  --role="roles/bigquery.dataEditor"

gcloud projects add-iam-policy-binding your-project-id \
  --member="serviceAccount:analytics@your-project.iam.gserviceaccount.com" \
  --role="roles/bigquery.jobUser"
```

---

## Maintenance

### Weekly Tasks
- [ ] Review Fivetran sync logs for warnings
- [ ] Check dbt test results in CI logs
- [ ] Verify Kibana dashboard metrics match expectations

### Monthly Tasks
- [ ] Review BigQuery storage costs (check `applylens` dataset size)
- [ ] Audit Elasticsearch index sizes (consider ILM policy)
- [ ] Rotate database credentials (fivetran_user password)

### Quarterly Tasks
- [ ] Update dbt packages: `dbt deps --upgrade`
- [ ] Review and optimize slow dbt models
- [ ] Archive old Elasticsearch indices (>90 days)

---

## Escalation

| Issue Type | Contact | SLA |
|------------|---------|-----|
| Fivetran sync failure | Platform team | 4 hours |
| dbt model errors | Data team | 8 hours |
| Elasticsearch down | Infrastructure team | 1 hour |
| Dashboard bugs | Analytics team | 1 business day |

**Emergency Contact**: Create incident in PagerDuty with "analytics" tag

---

## Additional Resources

- [Fivetran Documentation](https://fivetran.com/docs)
- [dbt Documentation](https://docs.getdbt.com)
- [BigQuery Best Practices](https://cloud.google.com/bigquery/docs/best-practices)
- [Elasticsearch Guide](https://www.elastic.co/guide/en/elasticsearch/reference/current/index.html)
- [Kibana Lens Tutorial](https://www.elastic.co/guide/en/kibana/current/lens.html)

**Internal**:
- [Fivetran Setup Guide](analytics/fivetran/README.md)
- [dbt Project README](analytics/dbt/README.md)
- [Phase 12.4 Summary](PHASE_12.4_COMPLETE.md)
