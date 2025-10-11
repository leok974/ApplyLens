# ApplyLens ML Predictive Analytics

## Overview

This directory contains the **BigQuery ML** predictive analytics system for ApplyLens. The system uses **ARIMA time series forecasting** to predict future values of key operational metrics and automatically detects anomalies when actual values deviate from predictions.

### Purpose

- **Proactive Monitoring**: Predict issues before they become critical
- **Capacity Planning**: Forecast email volume for infrastructure sizing
- **Data Quality**: Detect parity drift degradation early
- **SLO Management**: Predict backfill performance violations

## Architecture

```
Historical Data (marts)
    ↓
BigQuery ML ARIMA Training (weekly)
    ↓
Forecast Generation (daily)
    ↓
Anomaly Detection (compare actual vs predicted)
    ↓
Export to Elasticsearch
    ↓
Kibana Visualization + Prometheus Alerts
```

## Metrics

### 1. Average Risk Score (`avg_risk`)
- **Source**: `mrt_risk_daily.avg_risk`
- **Model**: `ml.m_avg_risk_arima`
- **Predictions**: `ml.pred_avg_risk`
- **Use Case**: Detect unusual shifts in risk calculation patterns

### 2. Email Volume (`email_count`)
- **Source**: `mrt_risk_daily.emails`
- **Model**: `ml.m_email_count_arima`
- **Predictions**: `ml.pred_email_count`
- **Use Case**: Capacity planning, traffic anomaly detection

### 3. Parity Drift Ratio (`parity_ratio`)
- **Source**: `mrt_parity_drift.mismatch_ratio`
- **Model**: `ml.m_parity_ratio_arima`
- **Predictions**: `ml.pred_parity_ratio`
- **Use Case**: Predict data quality degradation before critical thresholds

### 4. Backfill P95 Duration (`backfill_p95`)
- **Source**: `mrt_backfill_slo.p95_duration_seconds`
- **Model**: `ml.m_backfill_p95_arima`
- **Predictions**: `ml.pred_backfill_p95`
- **Use Case**: Predict SLO violations before they occur

## Model Configuration

### ARIMA Parameters

```sql
MODEL_TYPE='ARIMA_PLUS'           -- ARIMA with automatic seasonality
AUTO_ARIMA=TRUE                   -- Automatic parameter selection
HOLIDAY_REGION='US'               -- Account for US holidays
DATA_FREQUENCY='DAILY'            -- Daily time series
```

### Forecast Settings

- **Horizon**: 7 days ahead
- **Confidence Level**: 90% prediction intervals
- **Training Frequency**: Weekly (Sundays at 4:00 AM UTC)
- **Forecasting Frequency**: Daily (4:45 AM UTC)

## Anomaly Detection

### Severity Levels

Anomalies are classified based on their position relative to the 90% prediction interval:

- **high**: Actual value > upper bound
- **low**: Actual value < lower bound
- **normal**: Within prediction interval
- **unknown**: Missing actual or predicted values

### Detection Logic

```sql
CASE
  WHEN actual > upper_bound THEN 'high'
  WHEN actual < lower_bound THEN 'low'
  ELSE 'normal'
END AS severity
```

Only **high** and **low** severity anomalies are exported to Elasticsearch.

### Lookback Window

Anomaly detection analyzes the past **60 days** of data, comparing actuals to predictions.

## CI/CD Workflows

### Weekly Training Job

**Trigger**: Sundays at 4:00 AM UTC (cron: `0 4 * * 0`)

**Steps**:
1. Train all 4 ARIMA models on historical data
2. Models stored in BigQuery `ml.*` schema

```bash
dbt run --select ml:m_* --target prod
```

### Daily Forecasting Job

**Trigger**: Every day at 4:45 AM UTC (cron: `45 4 * * *`)

**Steps**:
1. Generate 7-day forecasts using trained models
2. Detect anomalies (compare actuals to predictions)
3. Export high/low severity anomalies to Elasticsearch

```bash
dbt run --select ml:pred_* --target prod
dbt run --select ml:anomaly_detection --target prod
python analytics/export/export_anomalies_to_es.py
```

### Manual Trigger

You can manually trigger the workflow with a choice of:
- `train`: Train models only
- `forecast`: Forecast and detect anomalies only
- `both`: Full training + forecasting pipeline

## Data Flow

### 1. Training Phase (Weekly)

```
mrt_risk_daily         → m_avg_risk_arima (model)
mrt_risk_daily         → m_email_count_arima (model)
mrt_parity_drift       → m_parity_ratio_arima (model)
mrt_backfill_slo       → m_backfill_p95_arima (model)
```

### 2. Forecasting Phase (Daily)

```
m_avg_risk_arima       → pred_avg_risk (7-day forecast)
m_email_count_arima    → pred_email_count (7-day forecast)
m_parity_ratio_arima   → pred_parity_ratio (7-day forecast)
m_backfill_p95_arima   → pred_backfill_p95 (7-day forecast)
```

### 3. Anomaly Detection (Daily)

```
mrt_risk_daily + pred_avg_risk         → anomaly_detection (avg_risk)
mrt_risk_daily + pred_email_count      → anomaly_detection (email_count)
mrt_parity_drift + pred_parity_ratio   → anomaly_detection (parity_ratio)
mrt_backfill_slo + pred_backfill_p95   → anomaly_detection (backfill_p95)
```

### 4. Export to Elasticsearch (Daily)

```
anomaly_detection (high/low only) → analytics_applylens_anomalies index
```

## Elasticsearch Schema

### Index: `analytics_applylens_anomalies`

**Document Structure**:
```json
{
  "_id": "avg_risk:2024-01-15",
  "_source": {
    "date": "2024-01-15",
    "metric": "avg_risk",
    "actual_value": 0.45,
    "predicted_value": 0.30,
    "lower_bound": 0.25,
    "upper_bound": 0.35,
    "severity": "high",
    "residual": 0.15,
    "exported_at": "2024-01-16T05:00:00Z"
  }
}
```

## Visualization

### Kibana Dashboard: `applylens-anomalies-dashboard`

**Location**: `monitoring/kibana/anomalies.ndjson`

**Panels**:
1. **Total Anomalies (Last 7 Days)** - Metric visualization
2. **Anomalies by Severity** - Pie chart (high/low breakdown)
3. **Anomalies Timeline (All Metrics)** - Line chart over 30 days
4. **Average Risk Anomalies** - Line chart with prediction intervals
5. **Email Volume Anomalies** - Line chart with prediction intervals
6. **Parity Drift Anomalies** - Line chart with prediction intervals
7. **Backfill P95 Duration Anomalies** - Line chart with prediction intervals

### Loading Dashboard

```bash
# Import to Kibana
curl -X POST "http://localhost:5601/api/saved_objects/_import" \
  -H "kbn-xsrf: true" \
  --form file=@monitoring/kibana/anomalies.ndjson
```

## Prometheus Alerts

### Alert Rules

**Location**: `infra/alerts/prometheus-rules.yml`

**Alerts Configured**:

1. **MLAnomalyDetectedAvgRisk**
   - Severity: ticket
   - Trigger: Any high-severity avg_risk anomaly in past hour

2. **MLAnomalyDetectedEmailVolume**
   - Severity: **page** (capacity critical)
   - Trigger: >5 high-severity email_count anomalies in past hour

3. **MLAnomalyDetectedParityDrift**
   - Severity: ticket
   - Trigger: Any high-severity parity_ratio anomaly in past hour

4. **MLAnomalyDetectedBackfillSLO**
   - Severity: **page** (SLO critical)
   - Trigger: Any high-severity backfill_p95 anomaly in past hour

### Metrics Required

Alerts assume you're exporting Elasticsearch document counts as Prometheus metrics:

```
applylens_ml_anomalies_total{metric="avg_risk", severity="high"}
applylens_ml_anomalies_total{metric="email_count", severity="high"}
applylens_ml_anomalies_total{metric="parity_ratio", severity="high"}
applylens_ml_anomalies_total{metric="backfill_p95", severity="high"}
```

## Anomaly Response

### When Alerts Fire

#### 1. Check Kibana Dashboard
- Navigate to **ApplyLens - ML Anomaly Detection** dashboard
- Review the specific metric's visualization
- Identify when anomaly started and severity

#### 2. Query BigQuery for Details

```sql
-- Get recent anomalies for a specific metric
SELECT *
FROM `applylens.ml.anomaly_detection`
WHERE metric = 'avg_risk'
  AND severity IN ('high', 'low')
  AND d >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
ORDER BY d DESC;
```

#### 3. Compare to Forecast

```sql
-- Review forecast accuracy
SELECT
  d,
  predicted_avg_risk,
  lower_bound,
  upper_bound
FROM `applylens.ml.pred_avg_risk`
WHERE d >= CURRENT_DATE()
ORDER BY d;
```

#### 4. Investigate Root Cause

- **avg_risk anomalies**: Check `mrt_risk_daily` for scoring changes
- **email_count anomalies**: Check traffic logs, potential DDoS or marketing campaigns
- **parity_ratio anomalies**: Run parity check, investigate backfill jobs
- **backfill_p95 anomalies**: Check backfill job logs, database performance

#### 5. Adjust if Necessary

If anomalies are due to expected changes (e.g., new feature launch):
- Manually retrain models: Run `analytics-ml.yml` workflow with `train` option
- Update will incorporate new baseline in next weekly training

## Local Development

### Prerequisites

- BigQuery ML API enabled
- Service account with `roles/bigquery.user` permission
- Minimum 30 days of historical data in marts
- Python 3.11+, dbt-bigquery 1.7+

### Setup

```bash
# Set environment variables
export BQ_PROJECT="your-project-id"
export GOOGLE_APPLICATION_CREDENTIALS="path/to/sa.json"
export ES_URL="http://localhost:9200"

# Navigate to dbt directory
cd analytics/dbt
```

### Train Models Locally

```bash
dbt run --select ml:m_* --target dev
```

### Generate Forecasts Locally

```bash
dbt run --select ml:pred_* --target dev
```

### Detect Anomalies Locally

```bash
dbt run --select ml:anomaly_detection --target dev
```

### Export to Elasticsearch Locally

```bash
cd ../..
python analytics/export/export_anomalies_to_es.py
```

### Verify Results

```bash
# Check BigQuery for forecasts
bq query --use_legacy_sql=false '
SELECT metric, d, predicted_value, lower_bound, upper_bound
FROM `applylens.ml.pred_avg_risk`
ORDER BY d DESC
LIMIT 7
'

# Check BigQuery for anomalies
bq query --use_legacy_sql=false '
SELECT metric, COUNT(*) as anomaly_count, severity
FROM `applylens.ml.anomaly_detection`
WHERE d >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
GROUP BY metric, severity
ORDER BY metric, severity
'

# Check Elasticsearch
curl -X GET "$ES_URL/analytics_applylens_anomalies/_search?pretty" \
  -H 'Content-Type: application/json' \
  -d '{"size": 10, "sort": [{"date": "desc"}]}'
```

## Troubleshooting

### Models Not Training

**Symptom**: `dbt run --select ml:m_*` fails

**Possible Causes**:
- BigQuery ML API not enabled
- Service account lacks permissions
- Insufficient historical data (<30 days)

**Resolution**:
```bash
# Enable BigQuery ML API
gcloud services enable bigquerystorage.googleapis.com

# Grant permissions
gcloud projects add-iam-policy-binding $BQ_PROJECT \
  --member="serviceAccount:your-sa@project.iam.gserviceaccount.com" \
  --role="roles/bigquery.user"
```

### Forecasts Not Generating

**Symptom**: `dbt run --select ml:pred_*` fails

**Possible Causes**:
- Models not trained yet
- Model training incomplete

**Resolution**:
```bash
# Check model status
bq query --use_legacy_sql=false '
SELECT * FROM `applylens.ml.INFORMATION_SCHEMA.MODELS`
'

# Retrain models
dbt run --select ml:m_* --target prod
```

### No Anomalies Detected

**Symptom**: `anomaly_detection` table empty or all severity='normal'

**Possible Causes**:
- Predictions very accurate (good!)
- Insufficient actual data
- Forecast period doesn't overlap with actuals

**Resolution**:
- This is expected if predictions are accurate
- Check `mrt_*` tables for recent data
- Anomalies only detected when forecasts overlap with actuals

### Export Script Fails

**Symptom**: `export_anomalies_to_es.py` errors

**Possible Causes**:
- Elasticsearch connection issues
- BigQuery authentication issues
- No high/low severity anomalies to export

**Resolution**:
```bash
# Test ES connectivity
curl $ES_URL

# Test BigQuery query
python -c "
from google.cloud import bigquery
client = bigquery.Client(project='$BQ_PROJECT')
query_job = client.query('SELECT COUNT(*) FROM \`$BQ_PROJECT.ml.anomaly_detection\`')
print(list(query_job.result()))
"
```

## Performance Considerations

### Training Cost

- ARIMA training uses BigQuery ML slots
- Weekly training (4 models) typically costs <$1/week
- Training duration: 5-15 minutes per model (depends on data size)

### Forecasting Cost

- Forecasting is much cheaper than training
- Daily forecasting (4 models) typically costs <$0.10/day
- Forecasting duration: <1 minute per model

### Data Retention

- **Anomaly detection**: 60-day lookback window
- **Forecasts**: 7-day horizon
- **Historical marts**: Recommend 1+ year retention for training

## Model Evaluation

### Checking Forecast Accuracy

```sql
-- Compare predicted vs actual for avg_risk
WITH actuals_with_forecasts AS (
  SELECT
    a.d,
    a.avg_risk AS actual,
    p.predicted_avg_risk AS predicted
  FROM `applylens.marts.mrt_risk_daily` a
  LEFT JOIN `applylens.ml.pred_avg_risk` p ON a.d = p.d
  WHERE a.d >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
    AND p.predicted_avg_risk IS NOT NULL
)
SELECT
  AVG(ABS(actual - predicted)) AS mae,
  SQRT(AVG(POW(actual - predicted, 2))) AS rmse,
  CORR(actual, predicted) AS correlation
FROM actuals_with_forecasts;
```

### Model Performance Metrics

BigQuery ML provides built-in evaluation metrics:

```sql
-- View model evaluation metrics
SELECT * FROM ML.EVALUATE(MODEL `applylens.ml.m_avg_risk_arima`);

-- View ARIMA coefficients
SELECT * FROM ML.ARIMA_COEFFICIENTS(MODEL `applylens.ml.m_avg_risk_arima`);
```

## Future Enhancements

### Potential Improvements

1. **Multi-Variate Models**: Combine metrics for better predictions
2. **Custom Thresholds**: Per-metric severity thresholds instead of prediction intervals
3. **Automated Retraining**: Trigger retraining when forecast accuracy degrades
4. **Anomaly Clustering**: Group related anomalies across metrics
5. **Root Cause Analysis**: Automatic correlation with system events

### Additional Metrics

Consider adding ARIMA models for:
- API response time percentiles
- Database query durations
- Cache hit rates
- Error rates by endpoint

## References

- [BigQuery ML ARIMA_PLUS Documentation](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-create-time-series)
- [ML.FORECAST Function](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-forecast)
- [dbt BigQuery Adapter](https://docs.getdbt.com/reference/warehouse-setups/bigquery-setup)
