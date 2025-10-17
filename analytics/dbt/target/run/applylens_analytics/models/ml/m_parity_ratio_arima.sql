
  
    

    create or replace table `applylens-gmail-1759983601`.`gmail_raw_stg_ml`.`m_parity_ratio_arima`
      
    
    

    
    OPTIONS()
    as (
      

-- BigQuery ML ARIMA model for parity drift ratio forecasting
-- Trains on historical DB↔ES consistency metrics to predict drift trends
-- Helps detect data quality degradation before it becomes critical

CREATE OR REPLACE MODEL `applylens-gmail-1759983601.ml.m_parity_ratio_arima`
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
FROM `applylens-gmail-1759983601.marts.mrt_parity_drift`
WHERE d < CURRENT_DATE()
  AND mismatch_ratio IS NOT NULL
ORDER BY d
    );
  