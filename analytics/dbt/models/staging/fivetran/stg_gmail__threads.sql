{{ config(materialized='view') }}

/*
  Staging model for Fivetran Gmail threads.
  Groups messages into conversation threads.
  
  Depends on: Fivetran Gmail connector → gmail_raw.threads
*/

with base as (
  select
    t.id as thread_id,
    t.history_id,
    cast(null as string) as thread_snippet,
    cast(null as int64) as message_count,
    t._fivetran_synced as synced_at
  from {{ source('gmail_raw', 'thread') }} t
  where t._fivetran_deleted is false
)

select * from base
