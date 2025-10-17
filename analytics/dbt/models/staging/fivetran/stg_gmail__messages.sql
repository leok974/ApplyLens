{{ config(materialized='view') }}

/*
  Staging model for Fivetran Gmail messages.
  Maps raw Fivetran schema to ApplyLens analytics schema.
  
  Depends on: Fivetran Gmail connector → gmail.message, gmail.payload_header
  
  Note: Fivetran stores email headers in a separate payload_header table.
  We pivot the key-value pairs to extract From, To, Subject, etc.
*/

with msg_base as (
  select
    msg.id as message_id,
    msg.thread_id,
    timestamp_millis(cast(msg.internal_date as int64)) as received_ts,
    msg.snippet,
    msg.size_estimate as size_bytes,
    msg._fivetran_synced as synced_at
  from {{ source('gmail_raw', 'message') }} as msg
  where msg._fivetran_deleted is false
),

-- Pivot headers from key-value pairs to columns
headers as (
  select
    message_id,
    max(case when lower(name) = 'from' then value end) as from_email,
    max(case when lower(name) = 'to' then value end) as to_emails,
    max(case when lower(name) = 'cc' then value end) as cc_emails,
    max(case when lower(name) = 'bcc' then value end) as bcc_emails,
    max(case when lower(name) = 'subject' then value end) as subject
  from {{ source('gmail_raw', 'payload_header') }}
  where lower(name) in ('from', 'to', 'cc', 'bcc', 'subject')
  group by 1
),

-- Join labels (simplified for now - just concatenate label IDs)
msg_labels as (
  select
    message_id,
    string_agg(label_id, ',') as label_ids
  from {{ source('gmail_raw', 'message_label') }}
  group by 1
)

select
  msg.message_id,
  msg.thread_id,
  msg.received_ts,
  msg.snippet,
  h.from_email,
  h.to_emails,
  h.cc_emails,
  h.bcc_emails,
  h.subject,
  lbl.label_ids,
  msg.size_bytes,
  msg.synced_at
from msg_base msg
left join headers h on msg.message_id = h.message_id
left join msg_labels lbl on msg.message_id = lbl.message_id
