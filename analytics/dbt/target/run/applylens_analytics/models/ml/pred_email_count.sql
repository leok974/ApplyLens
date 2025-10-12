
  
    

    create or replace table `applylens-gmail-1759983601`.`applylens`.`pred_email_count`
      
    
    

    OPTIONS()
    as (
      

-- Generate 7-day forecast for email volume
-- Uses trained ARIMA model to predict traffic patterns for capacity planning

SELECT
  forecast_timestamp AS d,
  forecast_value AS predicted_email_count,
  prediction_interval_lower_bound AS lower_bound,
  prediction_interval_upper_bound AS upper_bound
FROM ML.FORECAST(
  MODEL `applylens-gmail-1759983601.applylens.m_email_count_arima`,
  STRUCT(7 AS horizon, 0.9 AS confidence_level)
)
ORDER BY forecast_timestamp
    );
  