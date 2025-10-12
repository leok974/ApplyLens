

with src as (
  select * from `applylens-gmail-1759983601`.`applylens`.`public_applications`
)

select
  -- Primary key
  id,
  
  -- Foreign keys
  user_id,
  
  -- Application details
  company,
  role,
  source,
  status,
  
  -- Timestamps
  created_at,
  updated_at,
  
  -- Date dimensions
  DATE(created_at) as application_date,
  EXTRACT(YEAR FROM created_at) as application_year,
  EXTRACT(MONTH FROM created_at) as application_month,
  EXTRACT(WEEK FROM created_at) as application_week,
  
  -- Status categories
  CASE
    WHEN status IN ('accepted', 'offer') THEN 'success'
    WHEN status IN ('rejected', 'closed') THEN 'closed'
    WHEN status IN ('interviewing', 'phone_screen') THEN 'active'
    WHEN status IN ('applied', 'submitted') THEN 'pending'
    ELSE 'other'
  END as status_category

from src
where created_at IS NOT NULL  -- Filter out invalid records