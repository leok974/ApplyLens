{{ config(
    materialized='table',
    cluster_by=['day'],
    partition_by={
      "field": "day",
      "data_type": "date",
      "granularity": "day"
    }
) }}

/*
  Daily email activity metrics.
  
  Metrics:
  - Total messages received per day
  - Unique senders per day
  - Average message size
  
  Used by: Grafana dashboard, API /metrics/profile/activity_daily
  Updates: Nightly via GitHub Actions
*/

with msgs as (
  select 
    received_ts,
    from_email,
    size_bytes
  from {{ ref('stg_gmail__messages') }}
  where received_ts is not null
    and received_ts >= timestamp_sub(current_timestamp(), interval 90 day)
)

select
  date(received_ts) as day,
  count(*) as messages_count,
  count(distinct from_email) as unique_senders,
  round(avg(size_bytes) / 1024, 2) as avg_size_kb,
  round(sum(size_bytes) / 1024 / 1024, 2) as total_size_mb
from msgs
group by 1
