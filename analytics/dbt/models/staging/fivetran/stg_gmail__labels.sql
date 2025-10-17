{{ config(materialized='view') }}

/*
  Staging model for Fivetran Gmail labels.
  Provides label metadata for categorization and filtering.
  
  Depends on: Fivetran Gmail connector → gmail_raw.labels
*/

with base as (
  select
    l.id as label_id,
    l.name as label_name,
    l.type as label_type,
    cast(null as string) as message_list_visibility,
    cast(null as string) as label_list_visibility,
    l._fivetran_synced as synced_at
  from {{ source('gmail_raw', 'label') }} l
  where l._fivetran_deleted is false
)

select * from base
