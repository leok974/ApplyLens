

/*
  Email category distribution in the last 30 days.
  
  Categories:
  - PROMOTIONS: Marketing emails
  - UPDATES: Notifications, receipts
  - SOCIAL: Social network updates
  - FORUMS: Mailing lists, forums
  - PRIMARY: Everything else
  
  Used by: Grafana dashboard, API /metrics/profile/categories_30d
  Updates: Nightly via GitHub Actions
*/

with windowed as (
  select 
    message_id,
    label_ids,
    size_bytes
  from `applylens-gmail-1759983601`.`gmail_raw_stg_gmail_raw_stg`.`stg_gmail__messages`
  where received_ts >= timestamp_sub(current_timestamp(), interval 30 day)
),

-- Join with labels to get label names
msg_with_labels as (
  select
    w.message_id,
    w.size_bytes,
    case
      when w.label_ids is null then 'primary'
      when w.label_ids like '%CATEGORY_PROMOTIONS%' then 'promotions'
      when w.label_ids like '%CATEGORY_UPDATES%' then 'updates'
      when w.label_ids like '%CATEGORY_SOCIAL%' then 'social'
      when w.label_ids like '%CATEGORY_FORUMS%' then 'forums'
      when w.label_ids like '%CATEGORY_PERSONAL%' then 'primary'
      else 'primary'
    end as category
  from windowed w
)

select
  category,
  count(*) as messages_30d,
  round(count(*) * 100.0 / sum(count(*)) over(), 2) as pct_of_total,
  round(sum(size_bytes) / 1024 / 1024, 2) as total_size_mb
from msg_with_labels
group by 1
order by messages_30d desc