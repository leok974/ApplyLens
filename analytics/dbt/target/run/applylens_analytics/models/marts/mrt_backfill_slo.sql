
  
    

    create or replace table `applylens-gmail-1759983601`.`gmail_raw_stg_marts`.`mrt_backfill_slo`
      
    
    

    
    OPTIONS()
    as (
      

-- Placeholder for backfill SLO tracking
-- This will be populated when backfill job logs are exported to BigQuery
-- For now, generate stub data showing 0 backfills

with date_spine as (
  select date_sub(current_date(), interval day_offset day) as d
  from unnest(generate_array(0, 29)) as day_offset
),

-- TODO: Replace with actual backfill job logs
-- Expected structure: job_timestamp, duration_seconds, emails_processed, batch_size, etc.
-- Source: analytics.public_backfill_jobs (when implemented)

backfill_stub as (
  select
    d,
    0 as backfill_count,
    0.0 as avg_duration_seconds,
    0.0 as p50_duration_seconds,
    0.0 as p95_duration_seconds,
    0.0 as p99_duration_seconds,
    0 as total_emails_processed,
    0 as failed_count
  from date_spine
)

select
  d,
  backfill_count,
  ROUND(avg_duration_seconds, 2) as avg_duration_seconds,
  ROUND(p50_duration_seconds, 2) as p50_duration_seconds,
  ROUND(p95_duration_seconds, 2) as p95_duration_seconds,
  ROUND(p99_duration_seconds, 2) as p99_duration_seconds,
  total_emails_processed,
  failed_count,
  
  -- SLO status (p95 < 300 seconds = 5 minutes)
  CASE
    WHEN backfill_count = 0 THEN 'no_data'
    WHEN p95_duration_seconds < 300 THEN 'healthy'
    WHEN p95_duration_seconds < 420 THEN 'warning'  -- 7 minutes
    ELSE 'critical'
  END as slo_status,
  
  -- Success rate
  CASE
    WHEN backfill_count = 0 THEN NULL
    ELSE ROUND((backfill_count - failed_count) * 100.0 / backfill_count, 2)
  END as success_rate_pct

from backfill_stub
order by d DESC

-- IMPLEMENTATION NOTE:
-- To populate this model with real data:
-- 1. Instrument analyze_risk.py to log job metrics
-- 2. Export job logs to BigQuery table: analytics.public_backfill_jobs
-- 3. Update this model to calculate percentiles from actual durations
-- 4. Example instrumentation:
--    from app.metrics import backfill_duration_seconds
--    with backfill_duration_seconds.time():
--        # Run backfill
--        pass
--    # Export prometheus metrics to BigQuery (via remote write or exporter)
    );
  