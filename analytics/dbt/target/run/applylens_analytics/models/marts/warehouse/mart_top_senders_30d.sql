
  
    

    create or replace table `applylens-gmail-1759983601`.`gmail_raw_stg_gmail_marts`.`mart_top_senders_30d`
      
    
    

    
    OPTIONS()
    as (
      

/*
  Top email senders in the last 30 days.
  
  Metrics:
  - Message count per sender
  - Total size per sender
  - First/last message timestamps
  
  Used by: Grafana dashboard, API /metrics/profile/top_senders_30d
  Updates: Nightly via GitHub Actions
*/

with windowed as (
  select 
    from_email,
    received_ts,
    size_bytes
  from `applylens-gmail-1759983601`.`gmail_raw_stg_gmail_raw_stg`.`stg_gmail__messages`
  where received_ts >= timestamp_sub(current_timestamp(), interval 30 day)
    and from_email is not null
)

select 
  from_email,
  count(*) as messages_30d,
  round(sum(size_bytes) / 1024 / 1024, 2) as total_size_mb,
  min(received_ts) as first_message_at,
  max(received_ts) as last_message_at,
  timestamp_diff(max(received_ts), min(received_ts), day) as active_days
from windowed
group by 1
having messages_30d >= 2  -- Filter noise
order by messages_30d desc
limit 100
    );
  