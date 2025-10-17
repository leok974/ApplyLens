

-- BigQuery ML ARIMA model for email count forecasting
-- Trains on historical email volume data to predict future traffic patterns
-- Useful for capacity planning and anomaly detection

SELECT 
  d,
  emails
FROM `applylens-gmail-1759983601.applylens.mrt_risk_daily`
WHERE d < CURRENT_DATE()
  AND emails IS NOT NULL
ORDER BY d