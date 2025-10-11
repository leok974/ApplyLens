{{
  config(
    materialized='table',
    schema='ml',
    sql_header="CREATE OR REPLACE MODEL `{{ env_var('BQ_PROJECT') }}.ml.m_email_count_arima`
OPTIONS(
  MODEL_TYPE='ARIMA_PLUS',
  TIME_SERIES_TIMESTAMP_COL='d',
  TIME_SERIES_DATA_COL='emails',
  HOLIDAY_REGION='US',
  AUTO_ARIMA=TRUE,
  DATA_FREQUENCY='DAILY'
) AS"
  )
}}

-- BigQuery ML ARIMA model for email count forecasting
-- Trains on historical email volume data to predict future traffic patterns
-- Useful for capacity planning and anomaly detection

SELECT 
  d,
  emails
FROM `{{ env_var('BQ_PROJECT') }}.applylens.mrt_risk_daily`
WHERE d < CURRENT_DATE()
  AND emails IS NOT NULL
ORDER BY d
