

with src as (
  select * from `applylens-gmail-1759983601`.`applylens`.`public_emails`
)

select
  -- Primary key
  id,
  
  -- Timestamps
  received_at,
  created_at,
  updated_at,
  
  -- Email metadata
  sender,
  subject,
  REGEXP_EXTRACT(sender, r'@(.+)$') as sender_domain,
  
  -- Risk scoring (Phase 12.1)
  risk_score,
  category,
  expires_at,
  
  -- Features JSON parsing (Phase 12.1)
  JSON_VALUE(features_json, '$.computed_at') as features_computed_at,
  JSON_VALUE(features_json, '$.source') as features_source,
  CAST(JSON_VALUE(features_json, '$.confidence') AS FLOAT64) as source_confidence,
  
  -- Date dimensions
  DATE(received_at) as received_date,
  EXTRACT(YEAR FROM received_at) as received_year,
  EXTRACT(MONTH FROM received_at) as received_month,
  EXTRACT(WEEK FROM received_at) as received_week,
  EXTRACT(DAYOFWEEK FROM received_at) as received_dayofweek,
  
  -- Risk categories
  CASE
    WHEN risk_score IS NULL THEN 'unscored'
    WHEN risk_score < 30 THEN 'low'
    WHEN risk_score < 60 THEN 'medium'
    WHEN risk_score < 90 THEN 'high'
    ELSE 'critical'
  END as risk_bucket

from src