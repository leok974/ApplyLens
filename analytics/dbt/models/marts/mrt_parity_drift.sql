{{
  config(
    materialized='table',
    schema='marts'
  )
}}

-- Placeholder for parity drift tracking
-- This will be populated when parity check logs are exported to BigQuery
-- For now, generate stub data showing 0 mismatches

with date_spine as (
  select date_sub(current_date(), interval day_offset day) as d
  from unnest(generate_array(0, 29)) as day_offset
),

-- TODO: Replace with actual parity check results table
-- Expected structure: check_timestamp, total_checked, total_mismatches, field mismatches, etc.
-- Source: analytics.public_parity_checks (when implemented)

parity_stub as (
  select
    d,
    0 as total_checked,
    0 as total_mismatches,
    0.0 as mismatch_ratio,
    0 as risk_score_mismatches,
    0 as expires_at_mismatches,
    0 as category_mismatches,
    TIMESTAMP(d) as last_check_at
  from date_spine
)

select
  d,
  total_checked,
  total_mismatches,
  ROUND(mismatch_ratio, 4) as mismatch_ratio,
  risk_score_mismatches,
  expires_at_mismatches,
  category_mismatches,
  last_check_at,
  
  -- SLO status
  CASE
    WHEN mismatch_ratio = 0 THEN 'healthy'
    WHEN mismatch_ratio < 0.001 THEN 'acceptable'
    WHEN mismatch_ratio < 0.005 THEN 'warning'
    ELSE 'critical'
  END as slo_status

from parity_stub
order by d DESC

-- IMPLEMENTATION NOTE:
-- To populate this model with real data:
-- 1. Export parity check results from check_parity.py to BigQuery
-- 2. Create table: analytics.public_parity_checks
-- 3. Update this model to reference that table
-- 4. Example export command:
--    python scripts/check_parity.py --output parity.json
--    bq load --source_format=NEWLINE_DELIMITED_JSON \
--      applylens.parity_checks parity.json
