# ApplyLens dbt Analytics

This dbt project transforms raw ApplyLens data from BigQuery into analytical models for Kibana dashboards.

## 📁 Project Structure

```text
analytics/dbt/
├── dbt_project.yml      # Project configuration
├── profiles.yml         # Connection profiles
├── packages.yml         # dbt packages (dbt_utils)
├── models/
│   ├── staging/         # Raw table transformations
│   │   ├── stg_emails.sql
│   │   └── stg_applications.sql
│   └── marts/           # Business logic aggregates
│       ├── mrt_risk_daily.sql
│       ├── mrt_parity_drift.sql
│       └── mrt_backfill_slo.sql
├── tests/               # Data quality tests
├── macros/              # Custom SQL macros
└── analyses/            # Ad-hoc queries
```text

## 🚀 Quick Start

### 1. Install dbt

```bash
pip install dbt-bigquery
```text

### 2. Set Environment Variables

```bash
# Required
export BQ_PROJECT="your-gcp-project-id"
export BQ_SA_JSON='{"type": "service_account", ...}'  # Service account JSON

# Or use keyfile path
export BQ_SA_JSON="/path/to/service-account-key.json"
```text

### 3. Install Dependencies

```bash
cd analytics/dbt
dbt deps
```text

### 4. Run Models

```bash
# Run all models
dbt run

# Run specific model
dbt run --select stg_emails

# Run marts only
dbt run --select marts.*
```text

### 5. Test Data Quality

```bash
dbt test
```text

## 📊 Models

### Staging Models (`staging/`)

Clean and standardize raw BigQuery tables from Fivetran.

**stg_emails.sql:**

- Source: `applylens.public_emails`
- Output: Cleaned email data with parsed features

**stg_applications.sql:**

- Source: `applylens.public_applications`
- Output: Job application tracking data

### Mart Models (`marts/`)

Business logic aggregations ready for Kibana.

**mrt_risk_daily.sql:**

- Daily risk score trends
- Columns: `d` (date), `emails` (count), `avg_risk`, `high_risk_count`

**mrt_parity_drift.sql:**

- DB↔ES consistency tracking
- Columns: `d` (date), `mismatches`, `mismatch_ratio`

**mrt_backfill_slo.sql:**

- Backfill job performance
- Columns: `d` (date), `backfill_count`, `p95_seconds`

## 🔧 Development

### Run in Dev Mode

```bash
# Use dev profile (local testing)
dbt run --target dev

# Use CI profile (GitHub Actions)
dbt run --target ci --profiles-dir .
```text

### Debug Models

```bash
# Compile SQL without running
dbt compile --select mrt_risk_daily

# Show compiled SQL
cat target/compiled/applylens_analytics/models/marts/mrt_risk_daily.sql

# Run with debug logging
dbt --debug run --select mrt_risk_daily
```text

### Test Specific Model

```bash
dbt test --select stg_emails
```text

## 📈 Querying Results

After `dbt run`, query marts in BigQuery:

```sql
-- Risk trends over last 30 days
SELECT *
FROM applylens.marts.mrt_risk_daily
WHERE d >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
ORDER BY d DESC;

-- High-risk email trend
SELECT 
  d,
  high_risk_count,
  ROUND(high_risk_count * 100.0 / emails, 2) as high_risk_pct
FROM applylens.marts.mrt_risk_daily
WHERE d >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
ORDER BY d;
```text

## 🔄 Incremental Models (Future)

For large tables, convert to incremental:

```sql
-- In model config
{{
  config(
    materialized='incremental',
    unique_key='id',
    on_schema_change='sync_all_columns'
  )
}}

SELECT * FROM {{ source('applylens', 'public_emails') }}

{% if is_incremental() %}
  WHERE updated_at > (SELECT MAX(updated_at) FROM {{ this }})
{% endif %}
```text

## 🧪 Testing

Add tests in model YAML:

```yaml
# models/staging/schema.yml
version: 2

models:
  - name: stg_emails
    description: Cleaned email data from Fivetran
    columns:
      - name: id
        description: Primary key
        tests:
          - unique
          - not_null
      - name: risk_score
        description: Risk score (0-100)
        tests:
          - not_null
          - dbt_utils.accepted_range:
              min_value: 0
              max_value: 100
```text

Run tests:

```bash
dbt test --select stg_emails
```text

## 📦 CI/CD Integration

See `.github/workflows/analytics-sync.yml` for automated dbt runs.

**Manual trigger:**

```bash
gh workflow run analytics-sync.yml
```text

## 🔗 Related Documentation

- [Fivetran Setup](../fivetran/README.md)
- [Export to Elasticsearch](../export/README.md)
- [Analytics Runbook](../RUNBOOK.md)
- [dbt Documentation](https://docs.getdbt.com/)

---

*Last Updated: October 2025*
