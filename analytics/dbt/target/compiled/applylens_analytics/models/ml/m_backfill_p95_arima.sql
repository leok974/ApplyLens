

-- BigQuery ML ARIMA model for backfill P95 duration forecasting
-- Trains on historical backfill performance data to predict SLO violations
-- Enables proactive alerting before performance degrades beyond SLO

CREATE OR REPLACE MODEL `applylens-gmail-1759983601.ml.m_backfill_p95_arima`
OPTIONS(
  MODEL_TYPE='ARIMA_PLUS',
  TIME_SERIES_TIMESTAMP_COL='d',
  TIME_SERIES_DATA_COL='p95_duration_seconds',
  HOLIDAY_REGION='US',
  AUTO_ARIMA=TRUE,
  DATA_FREQUENCY='DAILY'
) AS
SELECT 
  d,
  p95_duration_seconds
FROM `applylens-gmail-1759983601.marts.mrt_backfill_slo`
WHERE d < CURRENT_DATE()
  AND p95_duration_seconds IS NOT NULL
ORDER BY d