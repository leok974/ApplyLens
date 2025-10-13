

with daily_emails as (
  select
    received_date as d,
    COUNT(*) as emails,
    COUNT(risk_score) as emails_scored,
    AVG(risk_score) as avg_risk,
    MIN(risk_score) as min_risk,
    MAX(risk_score) as max_risk,
    
    -- Risk distribution
    COUNTIF(risk_bucket = 'low') as low_risk_count,
    COUNTIF(risk_bucket = 'medium') as medium_risk_count,
    COUNTIF(risk_bucket = 'high') as high_risk_count,
    COUNTIF(risk_bucket = 'critical') as critical_risk_count,
    COUNTIF(risk_bucket = 'unscored') as unscored_count,
    
    -- Category distribution
    COUNTIF(category = 'recruiter') as recruiter_count,
    COUNTIF(category = 'interview') as interview_count,
    COUNTIF(category = 'offer') as offer_count,
    COUNTIF(category = 'rejection') as rejection_count,
    
    -- Sender domains (top 5 by volume)
    ARRAY_AGG(DISTINCT sender_domain ORDER BY sender_domain LIMIT 5) as top_domains

  from `applylens-gmail-1759983601`.`applylens`.`stg_emails`
  where received_date IS NOT NULL
  group by received_date
)

select
  d,
  emails,
  emails_scored,
  ROUND(avg_risk, 2) as avg_risk,
  min_risk,
  max_risk,
  low_risk_count,
  medium_risk_count,
  high_risk_count,
  critical_risk_count,
  unscored_count,
  recruiter_count,
  interview_count,
  offer_count,
  rejection_count,
  top_domains,
  
  -- Coverage metrics
  ROUND(emails_scored * 100.0 / NULLIF(emails, 0), 2) as coverage_pct,
  ROUND(high_risk_count * 100.0 / NULLIF(emails, 0), 2) as high_risk_pct,
  ROUND(critical_risk_count * 100.0 / NULLIF(emails, 0), 2) as critical_risk_pct

from daily_emails
-- Note: ORDER BY removed for partitioned table compatibility