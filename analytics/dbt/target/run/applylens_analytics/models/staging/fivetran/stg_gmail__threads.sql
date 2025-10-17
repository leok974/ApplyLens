

  create or replace view `applylens-gmail-1759983601`.`gmail_raw_stg_gmail_raw_stg`.`stg_gmail__threads`
  OPTIONS()
  as 

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
  from `applylens-gmail-1759983601`.`gmail`.`thread` t
  where t._fivetran_deleted is false
)

select * from base;

