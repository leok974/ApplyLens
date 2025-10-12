

-- BigQuery ML ARIMA model for email count forecasting
-- Trains on historical email volume data to predict future traffic patterns
-- Useful for capacity planning and anomaly detection

CREATE OR REPLACE MODEL `applylens-gmail-1759983601.ml.m_email_count_arima`
OPTIONS(
  MODEL_TYPE='ARIMA_PLUS',
  TIME_SERIES_TIMESTAMP_COL='d',
  TIME_SERIES_DATA_COL='emails',
  HOLIDAY_REGION='US',
  AUTO_ARIMA=TRUE,
  DATA_FREQUENCY='DAILY'
) AS
SELECT 
  d,
  emails
FROM `applylens-gmail-1759983601.marts.mrt_risk_daily`
WHERE d < CURRENT_DATE()
  AND emails IS NOT NULL
ORDER BY d