{{
  config(
    materialized='table',
    schema='ml'
  )
}}

-- BigQuery ML ARIMA model for parity drift ratio forecasting
-- Trains on historical DB↔ES consistency metrics to predict drift trends
-- Helps detect data quality degradation before it becomes critical

CREATE OR REPLACE MODEL `{{ env_var('BQ_PROJECT') }}.ml.m_parity_ratio_arima`
OPTIONS(
  MODEL_TYPE='ARIMA_PLUS',
  TIME_SERIES_TIMESTAMP_COL='d',
  TIME_SERIES_DATA_COL='mismatch_ratio',
  HOLIDAY_REGION='US',
  AUTO_ARIMA=TRUE,
  DATA_FREQUENCY='DAILY'
) AS
SELECT 
  d,
  mismatch_ratio
FROM `{{ env_var('BQ_PROJECT') }}.marts.mrt_parity_drift`
WHERE d < CURRENT_DATE()
  AND mismatch_ratio IS NOT NULL
ORDER BY d
