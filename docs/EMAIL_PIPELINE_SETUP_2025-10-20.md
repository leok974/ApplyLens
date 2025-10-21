# Email Ingest Pipeline Setup - ApplyLens

**Date:** October 20, 2025  
**Status:** ✅ Applied Successfully  
**Version:** v1

---

## Overview

Complete Elasticsearch infrastructure for email ingestion with:
- **Ingest Pipeline:** Field normalization, HTML stripping, intelligent flags
- **Index Template:** Automatic pipeline application and lifecycle management
- **Component Template:** Email field mappings with proper types
- **ILM Policy:** Automated rollover and data retention

---

## Files Created

```
infra/elasticsearch/
├── pipelines/
│   ├── emails_v1.json                    ✅ Email ingest pipeline
│   └── emails_test_sample.json           ✅ Test data
├── templates/
│   ├── emails_component_template_mapping.json  ✅ Field mappings
│   └── emails_index_template.json        ✅ Index template
└── ilm/
    └── emails_ilm.json                   ✅ Lifecycle policy
```

---

## Pipeline Features

### 1. Field Normalization

**Email Addresses:**
- `from`, `to`, `cc`, `bcc` → Lowercased
- Example: `Recruiter@Acme.com` → `recruiter@acme.com`

**Subject:**
- Lowercased and trimmed
- Example: `" Interview Invite "` → `"interview invite"`

**Labels:**
- Creates `labels_norm` array with lowercased labels
- Example: `["INBOX", "IMPORTANT"]` → `["inbox", "important"]`

### 2. Content Processing

**HTML Stripping:**
- `body_html` → `body_text` (HTML tags removed)
- Example: `<b>Congrats</b>` → `Congrats`

**Snippet:**
- `snippet` → `snippet_raw` (preserved)

### 3. Intelligent Flags

**Derived Booleans:**
- `archived`: `true` if `archived_at` is set
- `deleted`: `true` if `deleted_at` is set
- `is_interview`: Content contains "interview" or "screen"
- `is_offer`: Content contains "offer"

**Thread Grouping:**
- `thread_key`: Fallback thread identifier (subject + from)
- Used when `thread_id` is missing

### 4. Date Parsing

Supports multiple date formats:
- ISO8601: `2025-10-03T14:12:00Z`
- Email format: `Wed, 03 Oct 2025 14:12:00 +0000`

Fields: `received_at`, `sent_at`, `archived_at`

### 5. Deduplication

**Fingerprint Hash:**
- `doc_hash`: SHA-1 hash of `[gmail_id, thread_id, subject, received_at]`
- Provides stable deduplication across re-syncs

---

## Index Template Configuration

### Pattern Matching
- **Index Pattern:** `gmail_emails-*`
- **Write Alias:** `gmail_emails`
- **Current Index:** `gmail_emails-000001`

### Automatic Features
- **Pipeline:** `applylens_emails_v1` (applied on every write)
- **ILM Policy:** `applylens_emails_ilm` (rollover + retention)
- **Component Template:** `applylens_emails_mapping` (field types)

---

## ILM Policy (Lifecycle Management)

### Hot Phase
**Rollover Conditions:**
- Primary shard size: **25 GB**
- Age: **30 days**

When either condition is met, creates new index (`gmail_emails-000002`, etc.)

### Delete Phase
**Retention:** **365 days**

Emails older than 1 year are automatically deleted.

---

## Field Mappings

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `user_id` | keyword | User identifier | `"user_123"` |
| `gmail_id` | keyword | Gmail message ID | `"18abc..."` |
| `thread_id` | keyword | Gmail thread ID | `"18def..."` |
| `thread_key` | keyword | Fallback thread key | `"interview\|recruiter@..."` |
| `from` | keyword | Sender (lowercase) | `"recruiter@acme.com"` |
| `to` | keyword | Recipient (lowercase) | `"leo@applylens.app"` |
| `cc` | keyword | CC recipients | `"team@acme.com"` |
| `bcc` | keyword | BCC recipients | `"hr@acme.com"` |
| `subject` | text + keyword | Email subject | `"interview invite"` |
| `body_text` | text | Stripped HTML body | Full-text searchable |
| `labels_norm` | keyword | Normalized labels | `["inbox", "important"]` |
| `received_at` | date | Receive timestamp | `2025-10-03T14:12:00Z` |
| `sent_at` | date | Send timestamp | `2025-10-03T14:10:00Z` |
| `archived_at` | date | Archive timestamp | `null` or date |
| `archived` | boolean | Archived flag | `false` |
| `deleted` | boolean | Deleted flag | `false` |
| `is_interview` | boolean | Interview email | `true` |
| `is_offer` | boolean | Job offer email | `false` |
| `doc_hash` | keyword | Dedup fingerprint | `"a1b2c3..."` |

---

## Applied Components

### ✅ Step 1: ILM Policy
```bash
PUT /_ilm/policy/applylens_emails_ilm
```
**Result:** Hot phase rollover (25GB/30d), Delete after 365d

### ✅ Step 2: Component Template
```bash
PUT /_component_template/applylens_emails_mapping
```
**Result:** Field mappings with 1 shard, 0 replicas (dev mode)

### ✅ Step 3: Index Template
```bash
PUT /_index_template/applylens_emails
```
**Result:** Matches `gmail_emails-*`, applies pipeline + ILM

**Note:** Removed conflicting old template `gmail-emails-template`

### ✅ Step 4: Ingest Pipeline
```bash
PUT /_ingest/pipeline/applylens_emails_v1
```
**Result:** 13 processors loaded successfully

**Fixed:** Hash method `sha1` → `SHA-1` (ES requirement)

### ✅ Step 5: Pipeline Test
```json
Input:
  from: "Recruiter@Acme.com"
  subject: " Interview Invite "
  labels: ["INBOX", "IMPORTANT"]
  body_html: "<b>Congrats</b>"

Output:
  from: "recruiter@acme.com"          ✅ Lowercased
  subject: "interview invite"         ✅ Lowercased & trimmed
  body_text: "Congrats"               ✅ HTML stripped
  labels_norm: ["inbox", "important"] ✅ Normalized
  is_interview: true                  ✅ Content flag
  is_offer: false                     ✅ Content flag
  archived: false                     ✅ Derived flag
```

### ✅ Step 6: Alias Verification
```bash
GET /gmail_emails
```
**Result:** Alias already exists, points to active index

---

## Usage

### Indexing Emails

**Option 1: Automatic (via template)**
```python
# Pipeline applied automatically
es.index(
    index='gmail_emails',
    id=email_id,
    document=email_doc
)
```

**Option 2: Explicit**
```python
# Force specific pipeline
es.index(
    index='gmail_emails',
    id=email_id,
    document=email_doc,
    pipeline='applylens_emails_v1'
)
```

### Searching Emails

**By sender:**
```python
es.search(index='gmail_emails', query={
    'term': {'from': 'recruiter@acme.com'}
})
```

**By labels:**
```python
es.search(index='gmail_emails', query={
    'terms': {'labels_norm': ['inbox', 'important']}
})
```

**Interview emails:**
```python
es.search(index='gmail_emails', query={
    'term': {'is_interview': True}
})
```

**Full-text search:**
```python
es.search(index='gmail_emails', query={
    'multi_match': {
        'query': 'software engineer',
        'fields': ['subject', 'body_text']
    }
})
```

---

## Verification Commands

### Check Pipeline Exists
```powershell
docker exec applylens-api-prod curl -s \
  http://elasticsearch:9200/_ingest/pipeline/applylens_emails_v1 | 
  ConvertFrom-Json | 
  Select-Object -ExpandProperty applylens_emails_v1
```

### Check ILM Policy
```powershell
docker exec applylens-api-prod curl -s \
  http://elasticsearch:9200/_ilm/policy/applylens_emails_ilm | 
  ConvertFrom-Json
```

### Check Index Template
```powershell
docker exec applylens-api-prod curl -s \
  http://elasticsearch:9200/_index_template/applylens_emails | 
  ConvertFrom-Json
```

### Check Current Index
```powershell
docker exec applylens-api-prod curl -s \
  http://elasticsearch:9200/_cat/indices/gmail_emails-*?v
```

### Test Pipeline
```powershell
$test = Get-Content infra\elasticsearch\pipelines\emails_test_sample.json -Raw
docker exec -i applylens-api-prod curl -s -X POST \
  http://elasticsearch:9200/_ingest/pipeline/applylens_emails_v1/_simulate \
  -H 'Content-Type: application/json' \
  -d $test | ConvertFrom-Json
```

---

## Troubleshooting

### Pipeline Not Applied

**Symptom:** Emails indexed without processing

**Check:**
```powershell
# Verify template is active
docker exec applylens-api-prod curl -s \
  'http://elasticsearch:9200/gmail_emails-000001/_settings' | 
  ConvertFrom-Json | 
  Select-Object -ExpandProperty * | 
  Select-Object -ExpandProperty settings | 
  Select-Object -ExpandProperty index
```

**Expected:** `default_pipeline: "applylens_emails_v1"`

**Fix:** Manually set pipeline on index:
```powershell
docker exec applylens-api-prod curl -s -X PUT \
  http://elasticsearch:9200/gmail_emails-000001/_settings \
  -H 'Content-Type: application/json' \
  -d '{\"index\":{\"default_pipeline\":\"applylens_emails_v1\"}}'
```

### Processing Errors

**Symptom:** Documents fail to index

**Check for errors:**
```powershell
docker exec applylens-api-prod curl -s \
  'http://elasticsearch:9200/gmail_emails/_search?q=_ingest_error:*' | 
  ConvertFrom-Json | 
  Select-Object -ExpandProperty hits
```

**View error details:**
```powershell
# Get failed document
$doc = (docker exec applylens-api-prod curl -s \
  'http://elasticsearch:9200/gmail_emails/_search?q=_ingest_error:*' | 
  ConvertFrom-Json).hits.hits[0]

# Show error
$doc._source._ingest_error
```

### ILM Not Rolling Over

**Symptom:** Index exceeds size/age limits without rollover

**Check ILM status:**
```powershell
docker exec applylens-api-prod curl -s \
  'http://elasticsearch:9200/gmail_emails-*/_ilm/explain' | 
  ConvertFrom-Json
```

**Manual rollover:**
```powershell
docker exec applylens-api-prod curl -s -X POST \
  http://elasticsearch:9200/gmail_emails/_rollover
```

### Template Priority Conflicts

**Symptom:** Template not matching new indices

**List all templates:**
```powershell
docker exec applylens-api-prod curl -s \
  'http://elasticsearch:9200/_index_template' | 
  ConvertFrom-Json | 
  Select-Object -ExpandProperty index_templates | 
  Where-Object { $_.index_template.index_patterns -like '*gmail*' }
```

**Remove conflicting template:**
```powershell
docker exec applylens-api-prod curl -s -X DELETE \
  http://elasticsearch:9200/_index_template/old-template-name
```

---

## Reprocessing Existing Data

If you have existing emails that need the pipeline applied:

### Option 1: Update by Query
```bash
POST /gmail_emails/_update_by_query?pipeline=applylens_emails_v1
{
  "query": {"match_all": {}}
}
```

### Option 2: Reindex
```bash
POST /_reindex
{
  "source": {"index": "gmail_emails-000001"},
  "dest": {
    "index": "gmail_emails-000002",
    "pipeline": "applylens_emails_v1"
  }
}
```

---

## Production Tuning

### For Single-Node (Current)
- Shards: 1
- Replicas: 0
- Works for development/small deployments

### For Production Cluster
Update component template:
```json
{
  "template": {
    "settings": {
      "index.number_of_shards": 2,      // Increase for larger datasets
      "index.number_of_replicas": 1     // Enable for HA
    }
  }
}
```

### ILM Adjustments

**For high-volume email:**
```json
{
  "policy": {
    "phases": {
      "hot": {
        "actions": {
          "rollover": {
            "max_primary_shard_size": "10gb",  // Smaller shards
            "max_age": "7d"                    // More frequent rollover
          }
        }
      }
    }
  }
}
```

**For long-term retention:**
```json
{
  "delete": {
    "min_age": "2555d"  // 7 years
  }
}
```

---

## Integration with Application

### Email Sync Service

Update email sync to use pipeline:

**File:** `services/api/app/utils/gmail_sync.py` (or similar)

```python
from elasticsearch import Elasticsearch

es = Elasticsearch(['http://elasticsearch:9200'])

def sync_email(gmail_email):
    """Sync email with automatic pipeline processing"""
    
    # Build document
    doc = {
        'user_id': gmail_email.user_id,
        'gmail_id': gmail_email.gmail_id,
        'thread_id': gmail_email.thread_id,
        'from': gmail_email.from_email,
        'to': gmail_email.to_email,
        'cc': gmail_email.cc,
        'bcc': gmail_email.bcc,
        'subject': gmail_email.subject,
        'body_html': gmail_email.body_html,
        'labels': gmail_email.labels,
        'received_at': gmail_email.received_at.isoformat(),
        'sent_at': gmail_email.sent_at.isoformat() if gmail_email.sent_at else None,
        'archived_at': gmail_email.archived_at.isoformat() if gmail_email.archived_at else None,
    }
    
    # Index (pipeline applied automatically via template)
    es.index(
        index='gmail_emails',
        id=gmail_email.gmail_id,
        document=doc
    )
```

---

## Next Steps

### Immediate
- ✅ All components applied successfully
- ✅ Pipeline tested and working
- ✅ Template configured with ILM

### Optional Enhancements

1. **Add More Intelligent Flags**
   - `is_rejection`: Content analysis for rejection emails
   - `has_calendar_invite`: Detect meeting invitations
   - `sentiment`: Basic positive/negative classification

2. **Attachment Processing**
   - Add attachment metadata fields
   - Extract text from PDFs/docs
   - Store attachment checksums

3. **Thread Analytics**
   - Count messages per thread
   - Calculate response times
   - Track conversation participants

4. **Custom Normalizers**
   - Create custom email normalizer in settings
   - Handle domain extraction (`@acme.com` → `acme.com`)
   - Company name normalization

---

## Related Documentation

- **[SETUP_ES_PIPELINE_GRAFANA_DASHBOARD.md](SETUP_ES_PIPELINE_GRAFANA_DASHBOARD.md)** - Applications pipeline
- **[ARTIFACTS_APPLIED_2025-10-20.md](ARTIFACTS_APPLIED_2025-10-20.md)** - Infrastructure artifacts
- **[DOC_INDEX.md](DOC_INDEX.md)** - Documentation index

---

**Status:** ✅ Production Ready  
**Applied:** October 20, 2025  
**Version:** v1
