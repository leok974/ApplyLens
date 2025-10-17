

-- BigQuery ML ARIMA model for average risk score forecasting
-- Trains on historical risk_daily data to predict future avg_risk trends
-- Model automatically handles seasonality and trend components

CREATE OR REPLACE MODEL `applylens-gmail-1759983601.ml.m_avg_risk_arima`
OPTIONS(
  MODEL_TYPE='ARIMA_PLUS',
  TIME_SERIES_TIMESTAMP_COL='d',
  TIME_SERIES_DATA_COL='avg_risk',
  HOLIDAY_REGION='US',
  AUTO_ARIMA=TRUE,
  DATA_FREQUENCY='DAILY'
) AS
SELECT 
  d,
  avg_risk
FROM `applylens-gmail-1759983601.marts.mrt_risk_daily`
WHERE d < CURRENT_DATE()
  AND avg_risk IS NOT NULL
ORDER BY d