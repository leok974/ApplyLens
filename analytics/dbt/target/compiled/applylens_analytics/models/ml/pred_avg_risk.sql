

-- Generate 7-day forecast for average risk score
-- Uses trained ARIMA model to predict future risk trends

SELECT
  forecast_timestamp AS d,
  forecast_value AS predicted_avg_risk,
  prediction_interval_lower_bound AS lower_bound,
  prediction_interval_upper_bound AS upper_bound
FROM ML.FORECAST(
  MODEL `applylens-gmail-1759983601.ml.m_avg_risk_arima`,
  STRUCT(7 AS horizon, 0.9 AS confidence_level)
)
ORDER BY forecast_timestamp