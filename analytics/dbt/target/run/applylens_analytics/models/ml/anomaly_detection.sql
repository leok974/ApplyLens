
  
    

    create or replace table `applylens-gmail-1759983601`.`gmail_raw_stg_ml`.`anomaly_detection`
      
    
    

    
    OPTIONS()
    as (
      

-- Anomaly detection across all metrics
-- Compares actual values to ARIMA predictions and flags values outside prediction intervals

WITH avg_risk_anomalies AS (
  SELECT
    a.d,
    'avg_risk' AS metric,
    a.avg_risk AS actual_value,
    p.predicted_avg_risk AS predicted_value,
    p.lower_bound,
    p.upper_bound,
    CASE
      WHEN a.avg_risk IS NULL OR p.predicted_avg_risk IS NULL THEN 'unknown'
      WHEN a.avg_risk > p.upper_bound THEN 'high'
      WHEN a.avg_risk < p.lower_bound THEN 'low'
      ELSE 'normal'
    END AS severity,
    ABS(a.avg_risk - p.predicted_avg_risk) AS residual
  FROM `applylens-gmail-1759983601.marts.mrt_risk_daily` a
  LEFT JOIN `applylens-gmail-1759983601.ml.pred_avg_risk` p
    ON a.d = p.d
  WHERE a.d >= DATE_SUB(CURRENT_DATE(), INTERVAL 60 DAY)
),

email_count_anomalies AS (
  SELECT
    a.d,
    'email_count' AS metric,
    a.emails AS actual_value,
    p.predicted_email_count AS predicted_value,
    p.lower_bound,
    p.upper_bound,
    CASE
      WHEN a.emails IS NULL OR p.predicted_email_count IS NULL THEN 'unknown'
      WHEN a.emails > p.upper_bound THEN 'high'
      WHEN a.emails < p.lower_bound THEN 'low'
      ELSE 'normal'
    END AS severity,
    ABS(a.emails - p.predicted_email_count) AS residual
  FROM `applylens-gmail-1759983601.marts.mrt_risk_daily` a
  LEFT JOIN `applylens-gmail-1759983601.ml.pred_email_count` p
    ON a.d = p.d
  WHERE a.d >= DATE_SUB(CURRENT_DATE(), INTERVAL 60 DAY)
),

parity_ratio_anomalies AS (
  SELECT
    a.d,
    'parity_ratio' AS metric,
    a.mismatch_ratio AS actual_value,
    p.predicted_parity_ratio AS predicted_value,
    p.lower_bound,
    p.upper_bound,
    CASE
      WHEN a.mismatch_ratio IS NULL OR p.predicted_parity_ratio IS NULL THEN 'unknown'
      WHEN a.mismatch_ratio > p.upper_bound THEN 'high'
      WHEN a.mismatch_ratio < p.lower_bound THEN 'low'
      ELSE 'normal'
    END AS severity,
    ABS(a.mismatch_ratio - p.predicted_parity_ratio) AS residual
  FROM `applylens-gmail-1759983601.marts.mrt_parity_drift` a
  LEFT JOIN `applylens-gmail-1759983601.ml.pred_parity_ratio` p
    ON a.d = p.d
  WHERE a.d >= DATE_SUB(CURRENT_DATE(), INTERVAL 60 DAY)
),

backfill_p95_anomalies AS (
  SELECT
    a.d,
    'backfill_p95' AS metric,
    a.p95_duration_seconds AS actual_value,
    p.predicted_p95_seconds AS predicted_value,
    p.lower_bound,
    p.upper_bound,
    CASE
      WHEN a.p95_duration_seconds IS NULL OR p.predicted_p95_seconds IS NULL THEN 'unknown'
      WHEN a.p95_duration_seconds > p.upper_bound THEN 'high'
      WHEN a.p95_duration_seconds < p.lower_bound THEN 'low'
      ELSE 'normal'
    END AS severity,
    ABS(a.p95_duration_seconds - p.predicted_p95_seconds) AS residual
  FROM `applylens-gmail-1759983601.marts.mrt_backfill_slo` a
  LEFT JOIN `applylens-gmail-1759983601.ml.pred_backfill_p95` p
    ON a.d = p.d
  WHERE a.d >= DATE_SUB(CURRENT_DATE(), INTERVAL 60 DAY)
)

SELECT * FROM avg_risk_anomalies
UNION ALL
SELECT * FROM email_count_anomalies
UNION ALL
SELECT * FROM parity_ratio_anomalies
UNION ALL
SELECT * FROM backfill_p95_anomalies
ORDER BY d DESC, metric
    );
  