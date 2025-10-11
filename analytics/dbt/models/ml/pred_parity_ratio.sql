{{
  config(
    materialized='table',
    schema='ml'
  )
}}

-- Generate 7-day forecast for parity drift ratio
-- Uses trained ARIMA model to predict data quality degradation

SELECT
  forecast_timestamp AS d,
  forecast_value AS predicted_parity_ratio,
  prediction_interval_lower_bound AS lower_bound,
  prediction_interval_upper_bound AS upper_bound
FROM ML.FORECAST(
  MODEL `{{ env_var('BQ_PROJECT') }}.ml.m_parity_ratio_arima`,
  STRUCT(7 AS horizon, 0.9 AS confidence_level)
)
ORDER BY forecast_timestamp
