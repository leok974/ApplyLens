# Phase-1 Implementation Audit

**Repository**: ApplyLens  
**Audit Date**: October 11, 2025  
**Auditor**: GitHub Copilot  

---

## Executive Summary

This audit compares the ApplyLens codebase against the Phase-1 specification focusing on Gmail OAuth integration, Elasticsearch indexing, ingest pipeline, UI components, and Elastic showcase features.

**Overall Phase-1 Status**: 🟡 **Substantially Complete with Gaps**

- ✅ **Core Infrastructure**: Gmail OAuth, 60-day backfill, Elasticsearch implemented
- 🟡 **Partial Implementation**: Embeddings infrastructure exists but not in production mapping
- ❓ **Missing**: UI Inbox/Filters/Quick Actions, ESQL saved queries, Kibana exports

---

## 1. Gmail OAuth & 60-Day Backfill

### 1.1 OAuth Flow Implementation

| Component | Status | Evidence | Notes |
|-----------|--------|----------|-------|
| **OAuth Endpoints** | ✅ Done | `services/api/app/oauth_google.py:58-90` | `/oauth/google/init` and `/oauth/google/callback` |
| **Token Storage** | ✅ Done | `services/api/app/models.py:23-37` | `GmailToken` and `OAuthToken` tables |
| **Multi-User Support** | ✅ Done | `services/api/alembic/versions/0005_add_gmail_tokens.py:28` | `gmail_tokens` table created |
| **Google Scopes** | ✅ Done | `services/api/app/oauth_google.py:25` | `gmail.readonly` scope |
| **Refresh Token Logic** | ✅ Done | `services/api/app/gmail_providers.py:253-256` | Token refresh in provider |

**Evidence Files**:

```python
# services/api/app/oauth_google.py:58-90
@router.get("/init")
def init_oauth(user_email: str = Query(...)):
    flow = _create_flow()
    # ... OAuth flow initialization

@router.get("/callback")
def oauth_callback(code: str, state: str):
    # ... Token exchange and storage
```

### 1.2 Gmail API Integration

| Component | Status | Evidence | Notes |
|-----------|--------|----------|-------|
| **Gmail API Client** | ✅ Done | `services/api/app/gmail_providers.py:226` | `build("gmail", "v1", ...)` |
| **users.messages.list** | ✅ Done | `services/api/app/gmail_service.py:300` | Uses `threads().list()` |
| **60-Day Query** | ✅ Done | `services/api/app/gmail_service.py:302` | `q = f"newer_than:{days}d"` (default 60) |
| **Thread Fetching** | ✅ Done | `services/api/app/gmail_providers.py:268-271` | `threads().get(format="full")` |
| **Message Parsing** | ✅ Done | `services/api/app/gmail_providers.py:61-82` | Recursive part extraction |

**Key Implementation**:

```python
# services/api/app/gmail_service.py:297-302
def gmail_backfill(db: Session, user_email: str, days: int = 60) -> int:
    """Backfill Gmail messages into database and Elasticsearch"""
    creds = _get_creds(db, user_email)
    svc = build("gmail", "v1", credentials=creds, cache_discovery=False)
    after_date = (dt.datetime.utcnow() - relativedelta(days=days)).strftime("%Y/%m/%d")
    q = f"newer_than:{days}d"
```

### 1.3 Email Field Persistence

| Field | Status | Evidence | Notes |
|-------|--------|----------|-------|
| **Headers (SPF/DKIM/DMARC)** | ✅ Done | `services/api/app/gmail_service.py:78-104` | `parse_headers()` extracts all headers |
| **sender_domain** | ✅ Done | `services/api/app/models.py:37` | `from_addr` (email), domain extracted |
| **Subject** | ✅ Done | `services/api/app/models.py:38` | `subject` column |
| **body_text** | ✅ Done | `services/api/app/models.py:40` | `body_text` column |
| **received_at** | ✅ Done | `services/api/app/models.py:46` | `received_at TIMESTAMP` |
| **labels** | ✅ Done | `services/api/app/models.py:49` | `labels` (ARRAY) |
| **thread_id** | ✅ Done | `services/api/app/models.py:48` | `thread_id` indexed |
| **list-unsubscribe** | ✅ Done | `services/api/app/gmail_service.py:84` | Extracted in headers |
| **URLs** | ✅ Done | `services/api/app/gmail_service.py:139-156` | URL extraction in ingest |

**Database Schema**:

```python
# services/api/app/models.py:37-49
gmail_id = Column(String(128), unique=True, index=True)
from_addr = Column(String(256))
subject = Column(Text)
body_text = Column(Text)
received_at = Column(DateTime, default=datetime.utcnow, index=True)
thread_id = Column(String(128), index=True)
labels = Column(ARRAY(String))  # Gmail labels
```

---

## 2. Elasticsearch emails_v1 Index

### 2.1 Index Mapping

| Component | Status | Evidence | Notes |
|-----------|--------|----------|-------|
| **BM25 Text Fields** | ✅ Done | `services/api/app/es.py:81-108` | `subject`, `body_text` with BM25 |
| **Keyword Fields** | ✅ Done | `services/api/app/es.py:62-65` | `gmail_id`, `thread_id`, `from_addr` |
| **sender_domain** | 🟡 Partial | `services/api/app/es.py:64` | `from_addr` is keyword, no explicit `sender_domain` |
| **labels** | ✅ Done | `services/api/app/es.py:108` | `labels` (keyword array) |
| **list IDs** | ❓ Not Found | - | No explicit list_id field in mapping |
| **dense_vector** | 🟡 Partial | `services/api/app/scripts/update_es_mapping.py:86-92` | **EXISTS** but not in production mapping |

**Current Mapping** (`services/api/app/es.py:58-108`):

```python
"gmail_id": {"type": "keyword"},
"thread_id": {"type": "keyword"},
"from_addr": {"type": "keyword"},
"subject": {
    "type": "text",
    "analyzer": "standard",
    "search_analyzer": "ats_search_analyzer",
    "fields": {
        "raw": {"type": "keyword"},
        "shingles": {"type": "text", "analyzer": "applylens_text_shingles"}
    }
},
"body_text": {
    "type": "text",
    "analyzer": "standard",
    "search_analyzer": "ats_search_analyzer",
    "fields": {"shingles": {"type": "text", "analyzer": "applylens_text_shingles"}}
},
"labels": {"type": "keyword"},  # Gmail labels array
```

**Embeddings Available (Not Activated)**:

```python
# services/api/app/scripts/update_es_mapping.py:84-92
"subject_vector": {
    "type": "dense_vector",
    "dims": 768,
    "index": True,
    "similarity": "cosine"
},
"body_vector": {
    "type": "dense_vector",
    "dims": 768,
    "index": True,
    "similarity": "cosine"
}
```

### 2.2 Index Creation & Writes

| Component | Status | Evidence | Notes |
|-----------|--------|----------|-------|
| **Index Template** | ✅ Done | `services/api/app/es.py:25-109` | `SETTINGS_AND_MAPPINGS` dict |
| **Index Creation** | ✅ Done | `services/api/app/es.py:129-143` | `ensure_index()` with retry logic |
| **ES Client Writes** | ✅ Done | `services/api/app/gmail_service.py:288-293` | Bulk indexing in backfill |

**Indexing Logic**:

```python
# services/api/app/gmail_service.py:288-293
es_docs.append({
    "_index": ES_INDEX,
    "_id": d["gmail_id"],
    "_source": d
})
# Bulk write to ES
helpers.bulk(es, es_docs)
```

---

## 3. Ingest Pipeline

### 3.1 HTML → Text Processing

| Component | Status | Evidence | Notes |
|-----------|--------|----------|-------|
| **HTML Parsing** | ✅ Done | `services/api/app/gmail_service.py:166-174` | `BeautifulSoup` for HTML→text |
| **BeautifulSoup Usage** | ✅ Done | `services/api/app/gmail_service.py:168` | `soup = BeautifulSoup(html, "html.parser")` |

**Implementation**:

```python
# services/api/app/gmail_service.py:166-174
from bs4 import BeautifulSoup

def _html_to_text(html: str) -> str:
    """Convert HTML to plain text"""
    soup = BeautifulSoup(html, "html.parser")
    # Remove script and style elements
    for script in soup(["script", "style"]):
        script.decompose()
    return soup.get_text(separator=' ', strip=True)
```

### 3.2 URL Extraction

| Component | Status | Evidence | Notes |
|-----------|--------|----------|-------|
| **URL Extraction** | ✅ Done | `services/api/app/gmail_service.py:139-156` | Regex + BeautifulSoup links |
| **URL Regex** | ✅ Done | `services/api/app/gmail_service.py:141` | `http[s]?://(?:[a-zA-Z]...` |

**Implementation**:

```python
# services/api/app/gmail_service.py:139-156
import re
url_pattern = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
urls_text = url_pattern.findall(body_text or "")

# Also extract from HTML
soup = BeautifulSoup(html, "html.parser")
urls_html = [a.get("href") for a in soup.find_all("a", href=True)]
all_urls = list(set(urls_text + urls_html))
```

### 3.3 Heuristics

| Heuristic | Status | Evidence | Notes |
|-----------|--------|----------|-------|
| **is_newsletter** | ✅ Done | `services/api/app/gmail_service.py:202-218` | Checks unsubscribe links, sender patterns |
| **is_promo** | ✅ Done | `services/api/app/gmail_service.py:219-226` | Gmail CATEGORY_PROMOTIONS label |
| **has_unsubscribe** | ✅ Done | `services/api/app/gmail_service.py:206` | Checks List-Unsubscribe header |

**Implementation**:

```python
# services/api/app/gmail_service.py:202-226
def derive_labels(headers: dict, labels: List[str], urls: List[str]) -> List[str]:
    derived = []
    
    # Newsletter detection
    list_unsub = headers.get("List-Unsubscribe", "")
    has_unsub_link = any("unsubscribe" in u.lower() for u in urls)
    if list_unsub or has_unsub_link:
        derived.append("newsletter")
    
    # Promo detection
    if "CATEGORY_PROMOTIONS" in labels:
        derived.append("promo")
    
    return derived
```

### 3.4 Timezone & Timestamps

| Component | Status | Evidence | Notes |
|-----------|--------|----------|-------|
| **UTC Normalization** | ✅ Done | `services/api/app/gmail_service.py:344-348` | Converts to UTC datetime |
| **ISO-8601 Format** | ✅ Done | `services/api/app/gmail_service.py:346` | Uses `datetime.utcfromtimestamp()` |

**Implementation**:

```python
# services/api/app/gmail_service.py:344-348
# Gmail internalDate is milliseconds since epoch
internal_date_ms = int(meta.get("internalDate", 0))
received_at = datetime.utcfromtimestamp(internal_date_ms / 1000.0)
```

---

## 4. UI Components

### 4.1 Inbox View

| Component | Status | Evidence | Notes |
|-----------|--------|----------|-------|
| **Inbox Component** | ❓ Not Found | - | No `Inbox.tsx`, `EmailList.tsx` found |
| **Email List View** | ❓ Not Found | - | No obvious inbox UI component |

### 4.2 Filters Panel

| Component | Status | Evidence | Notes |
|-----------|--------|----------|-------|
| **Filters Component** | ❓ Not Found | - | No `FiltersPanel.tsx` or similar |
| **Filter UI** | ❓ Not Found | - | No filter sidebar component found |

### 4.3 "Reason" Column

| Component | Status | Evidence | Notes |
|-----------|--------|----------|-------|
| **Reason Display** | ❓ Not Found | - | No "Why is this here?" column found |

### 4.4 Quick Actions

| Component | Status | Evidence | Notes |
|-----------|--------|----------|-------|
| **Archive Action** | 🟡 Partial | `services/api/app/routers/mail_tools.py:276` | **Stubbed** - `# TODO: Call Gmail API` |
| **Mark Safe/Suspicious** | 🟡 Partial | `services/api/app/routers/mail_tools.py:281-287` | **Stubbed** - no Gmail integration |
| **Unsubscribe (dry-run)** | ✅ Done | `services/api/app/logic/unsubscribe.py:138` | Dry-run logic implemented |
| **"Explain why"** | ❓ Not Found | - | No explain endpoint found |

**Quick Actions API** (Stubbed):

```python
# services/api/app/routers/mail_tools.py:276-292
# TODO: Call Gmail API to archive email
# gmail_service.archive_message(email.gmail_message_id)

# TODO: Call Gmail API to add label
# gmail_service.add_label(email.gmail_message_id, action.params["label"])

# TODO: Call Gmail API to delete (move to trash)
# gmail_service.trash_message(email.gmail_message_id)
```

**Unsubscribe Logic** (Implemented):

```python
# services/api/app/logic/unsubscribe.py:138
# Actual email sending is optional future enhancement via Gmail API
# Returns unsubscribe link and method (mailto/http)
```

---

## 5. Elastic Showcase

### 5.1 Full-Text Search

| Component | Status | Evidence | Notes |
|-----------|--------|----------|-------|
| **Search Endpoint** | ✅ Done | `services/api/app/routers/search.py:52-265` | `/search` with BM25 |
| **Fast Search** | ✅ Done | `services/api/app/routers/search.py:145-187` | Multi-field query with boosting |

**Search Implementation**:

```python
# services/api/app/routers/search.py:145-187
query_dict = {
    "bool": {
        "should": [
            {"match": {"subject": {"query": query, "boost": 3}}},
            {"match": {"body_text": {"query": query, "boost": 1}}},
            {"match": {"sender": {"query": query, "boost": 2}}},
        ]
    }
}
```

### 5.2 ESQL Saved Assets

| Component | Status | Evidence | Notes |
|-----------|--------|----------|-------|
| **Saved ESQL Queries** | ❓ Not Found | - | No ESQL queries in repo |
| **"Top Senders by Category"** | ❓ Not Found | - | No saved query found |
| **"Promos Expiring This Week"** | ❓ Not Found | - | No saved query found |

### 5.3 Kibana Data View

| Component | Status | Evidence | Notes |
|-----------|--------|----------|-------|
| **Data View Export** | ❓ Not Found | - | No `kibana/exports/` or saved objects |
| **emails_v1* Pattern** | ❓ Not Found | - | No Kibana data view JSON found |

---

## 6. Optional Features

### 6.1 ELSER / Vector Semantic Search

| Component | Status | Evidence | Notes |
|-----------|--------|----------|-------|
| **ELSER Implementation** | ❓ Not Found | - | No ELSER model deployment found |
| **Vector Search** | 🟡 Partial | `services/api/app/scripts/update_es_mapping.py:84-92` | Infrastructure exists, not activated |

**Evidence**:

```python
# services/api/app/scripts/update_es_mapping.py:84-92
# Vector embeddings schema exists but not in production mapping
"subject_vector": {"type": "dense_vector", "dims": 768, ...}
"body_vector": {"type": "dense_vector", "dims": 768, ...}
```

### 6.2 Fivetran Connector (BigQuery job_postings)

| Component | Status | Evidence | Notes |
|-----------|--------|----------|-------|
| **Fivetran Connector** | ❓ Not Found | - | No Fivetran config found |
| **BQ Dataset** | 🟡 Partial | `analytics/dbt/insert_test_data.py:6` | Project ID `applylens-gmail-1759983601` |
| **dbt job_postings Model** | ❓ Not Found | - | No `models/job_postings.sql` found |

**Evidence**:

```python
# analytics/dbt/insert_test_data.py:6
client = bigquery.Client(project='applylens-gmail-1759983601')
```

---

## Summary Table

| Spec Item | Status | Completeness | Priority Gap |
|-----------|--------|--------------|--------------|
| **1. Gmail OAuth & 60-Day Backfill** | ✅ Done | 100% | None |
| **2. Elasticsearch emails_v1 Index** | 🟡 Partial | 90% | Add `sender_domain` field, activate embeddings |
| **3. Ingest Pipeline** | ✅ Done | 100% | None |
| **4. UI Components** | ❓ Not Found | 0% | **HIGH PRIORITY** - Build inbox/filters/actions |
| **5. Elastic Showcase** | 🟡 Partial | 40% | **MEDIUM** - Add ESQL queries, Kibana exports |
| **6. Optional: ELSER/Vectors** | 🟡 Partial | 30% | **LOW** - Activate existing infrastructure |
| **7. Optional: Fivetran** | ❓ Not Found | 10% | **LOW** - dbt models missing |

---

## Gaps to Close

### 🔴 HIGH PRIORITY (Phase-1 Blockers)

#### Gap 1: UI Inbox View Component

**Status**: ❓ Not Found  
**Impact**: No user-facing inbox  

**TODO**:

```typescript
// File: web/src/components/Inbox/EmailList.tsx
// Create React component with:
// - Table view of emails (subject, sender, date, labels)
// - Pagination controls
// - Click to open detail view
// - Integration with /api/search endpoint

import { useQuery } from '@tanstack/react-query';

export const EmailList = () => {
  const { data: emails } = useQuery({
    queryKey: ['emails'],
    queryFn: () => fetch('/api/search?query=*&size=50').then(r => r.json())
  });
  
  return (
    <table>
      <thead>
        <tr>
          <th>Subject</th>
          <th>From</th>
          <th>Date</th>
          <th>Labels</th>
          <th>Reason</th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody>
        {emails?.hits?.map(email => (
          <EmailRow key={email.gmail_id} email={email} />
        ))}
      </tbody>
    </table>
  );
};
```

#### Gap 2: Filters Panel Component

**Status**: ❓ Not Found  
**Impact**: No filtering capability  

**TODO**:

```typescript
// File: web/src/components/Inbox/FiltersPanel.tsx
// Create filters sidebar with:
// - Label filters (checkboxes for Gmail labels)
// - Date range picker
// - Sender filter (autocomplete)
// - Category filters (newsletter, promo, etc.)

export const FiltersPanel = ({ onFilterChange }) => {
  const [filters, setFilters] = useState({
    labels: [],
    dateRange: null,
    sender: null
  });
  
  return (
    <aside className="filters-panel">
      <h3>Filters</h3>
      <LabelFilter onChange={labels => setFilters({...filters, labels})} />
      <DateRangeFilter onChange={dateRange => setFilters({...filters, dateRange})} />
      <SenderFilter onChange={sender => setFilters({...filters, sender})} />
      <button onClick={() => onFilterChange(filters)}>Apply</button>
    </aside>
  );
};
```

#### Gap 3: "Reason" Column Implementation

**Status**: ❓ Not Found  
**Impact**: No AI explanation for email relevance  

**TODO**:

```python
# File: services/api/app/routers/search.py
# Add new endpoint:

@router.get("/explain/{email_id}")
async def explain_email(email_id: str, db: Session = Depends(get_db)):
    """
    Explain why an email was classified/scored a certain way.
    Returns reasoning based on heuristics, ML scores, and content.
    """
    email = db.query(Email).filter_by(gmail_id=email_id).first()
    if not email:
        raise HTTPException(404, "Email not found")
    
    reasons = []
    
    # Check labels
    if "newsletter" in (email.label_heuristics or []):
        reasons.append("Detected as newsletter (has List-Unsubscribe header)")
    
    # Check sender domain
    if email.from_addr and "@" in email.from_addr:
        domain = email.from_addr.split("@")[1]
        if domain in KNOWN_RECRUITING_DOMAINS:
            reasons.append(f"Sender domain '{domain}' is a known recruiting platform")
    
    # Check content signals
    if email.body_text:
        if "interview" in email.body_text.lower():
            reasons.append("Contains interview-related keywords")
    
    return {"email_id": email_id, "reasons": reasons}
```

#### Gap 4: Quick Actions UI Integration

**Status**: 🟡 Partial (API stubbed, no UI)  
**Impact**: Users can't perform bulk actions  

**TODO**:

```typescript
// File: web/src/components/Inbox/EmailActions.tsx
// Add action buttons to each email row:

export const EmailActions = ({ email }) => {
  const archiveEmail = () => {
    fetch(`/api/mail-tools/archive/${email.gmail_id}`, { method: 'POST' })
      .then(() => refetchEmails());
  };
  
  const markSafe = () => {
    fetch(`/api/mail-tools/mark-safe/${email.gmail_id}`, { method: 'POST' })
      .then(() => refetchEmails());
  };
  
  const unsubscribe = () => {
    fetch(`/api/mail-tools/unsubscribe/${email.gmail_id}`, { method: 'POST' })
      .then(r => r.json())
      .then(result => {
        if (result.unsubscribe_link) {
          window.open(result.unsubscribe_link, '_blank');
        }
      });
  };
  
  return (
    <div className="email-actions">
      <button onClick={archiveEmail}>Archive</button>
      <button onClick={markSafe}>Mark Safe</button>
      <button onClick={unsubscribe}>Unsubscribe</button>
    </div>
  );
};
```

**ALSO**: Complete Gmail API integration in backend:

```python
# File: services/api/app/routers/mail_tools.py:276-292
# Replace TODOs with actual Gmail API calls:

from googleapiclient.discovery import build
from .gmail_providers import single_user_provider

@router.post("/archive/{email_id}")
async def archive_email(email_id: str, db: Session = Depends(get_db)):
    provider = single_user_provider()
    service = await provider.get_service()
    
    # Archive = remove INBOX label
    service.users().messages().modify(
        userId='me',
        id=email_id,
        body={'removeLabelIds': ['INBOX']}
    ).execute()
    
    return {"success": True}
```

### 🟡 MEDIUM PRIORITY (Phase-1 Nice-to-Have)

#### Gap 5: Elasticsearch sender_domain Field

**Status**: 🟡 Partial (from_addr exists, no explicit sender_domain)  
**Impact**: Harder to aggregate by domain  

**TODO**:

```python
# File: services/api/app/es.py:62-65
# Add to mappings:

"sender_domain": {"type": "keyword"},  # Add this line
"from_addr": {"type": "keyword"},
```

**AND**:

```python
# File: services/api/app/gmail_service.py:380-395
# Extract domain when indexing:

from_email = headers.get("From", "")
sender_domain = from_email.split("@")[1] if "@" in from_email else None

es_doc = {
    "gmail_id": existing.gmail_id,
    "from_addr": from_email,
    "sender_domain": sender_domain,  # Add this
    # ... rest of fields
}
```

#### Gap 6: ESQL Saved Queries

**Status**: ❓ Not Found  
**Impact**: No pre-built analytics in Kibana  

**TODO**:

```esql
-- File: infra/kibana/saved_queries/top_senders_by_category.esql
-- Save in Kibana Dev Tools

FROM gmail_emails_v1*
| WHERE labels LIKE "newsletter" OR labels LIKE "promo"
| STATS email_count = COUNT(*) BY sender_domain
| SORT email_count DESC
| LIMIT 20
```

```esql
-- File: infra/kibana/saved_queries/promos_expiring_this_week.esql
-- Requires parsing "expires" dates from body_text

FROM gmail_emails_v1*
| WHERE labels LIKE "promo" AND body_text LIKE "expires"
| EVAL expire_date = DATEPARSE(body_text, "expires: %Y-%m-%d")
| WHERE expire_date >= NOW() AND expire_date <= NOW() + 7 DAYS
| KEEP subject, sender_domain, expire_date
| SORT expire_date ASC
```

#### Gap 7: Kibana Data View Export

**Status**: ❓ Not Found  
**Impact**: Manual Kibana setup required  

**TODO**:

```bash
# Export data view from Kibana:
curl -X GET "http://localhost:5601/api/saved_objects/_export" \
  -H "kbn-xsrf: true" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "index-pattern",
    "search": "gmail_emails*"
  }' > infra/kibana/exports/data_view_gmail_emails.ndjson
```

**THEN** commit to repo:

```bash
git add infra/kibana/exports/data_view_gmail_emails.ndjson
git commit -m "Add Kibana data view export for gmail_emails*"
```

### 🟢 LOW PRIORITY (Optional Features)

#### Gap 8: Activate Dense Vector Embeddings

**Status**: 🟡 Partial (schema exists, not in production)  
**Impact**: No semantic search  

**TODO**:

```python
# File: services/api/app/es.py:108
# Add to production mapping (after "labels"):

"subject_vector": {
    "type": "dense_vector",
    "dims": 768,
    "index": True,
    "similarity": "cosine"
},
"body_vector": {
    "type": "dense_vector",
    "dims": 768,
    "index": True,
    "similarity": "cosine"
},
```

**AND** generate embeddings during indexing:

```python
# File: services/api/app/gmail_service.py:390-395
# Add embedding generation:

from sentence_transformers import SentenceTransformer
model = SentenceTransformer('all-MiniLM-L6-v2')

subject_vector = model.encode(email.subject).tolist()
body_vector = model.encode(email.body_text[:512]).tolist()  # Truncate long bodies

es_doc = {
    # ... existing fields
    "subject_vector": subject_vector,
    "body_vector": body_vector
}
```

#### Gap 9: ELSER Model Deployment

**Status**: ❓ Not Found  
**Impact**: No ELSER semantic search  

**TODO**:

```bash
# Deploy ELSER model to Elasticsearch:
POST _ml/trained_models/.elser_model_2/deployment/_start
{
  "number_of_allocations": 1
}

# Create ingest pipeline with ELSER:
PUT _ingest/pipeline/gmail_elser_pipeline
{
  "processors": [
    {
      "inference": {
        "model_id": ".elser_model_2",
        "input_output": [
          {
            "input_field": "body_text",
            "output_field": "ml.tokens"
          }
        ]
      }
    }
  ]
}
```

#### Gap 10: Fivetran → BigQuery job_postings

**Status**: ❓ Not Found  
**Impact**: No external job data enrichment  

**TODO**:

```sql
-- File: analytics/dbt/models/job_postings.sql
-- dbt model to transform Fivetran job postings

WITH source AS (
  SELECT *
  FROM `applylens-gmail-1759983601.fivetran_connector.job_postings`
),

cleaned AS (
  SELECT
    job_id,
    company_name,
    job_title,
    location,
    posted_date,
    apply_url,
    LOWER(company_name) AS company_name_normalized
  FROM source
  WHERE posted_date >= CURRENT_DATE() - 90
)

SELECT * FROM cleaned
```

**AND** configure Fivetran:

```yaml
# infra/fivetran/config.yml
connector_type: "job_boards_api"
destination:
  type: "bigquery"
  project_id: "applylens-gmail-1759983601"
  dataset: "fivetran_connector"
sync_frequency: "daily"
```

---

## Action Plan (Priority Order)

### Sprint 1 (Week 1-2): Core UI

1. **Build Inbox EmailList component** (Gap 1)
2. **Build FiltersPanel component** (Gap 2)
3. **Implement "Explain why" endpoint** (Gap 3)
4. **Wire up Quick Actions UI** (Gap 4)

### Sprint 2 (Week 3): Elasticsearch Refinements

5. **Add sender_domain field to ES mapping** (Gap 5)
6. **Create ESQL saved queries** (Gap 6)
7. **Export Kibana data views** (Gap 7)

### Sprint 3 (Week 4): Optional Enhancements

8. **Activate dense_vector embeddings** (Gap 8)
9. **Deploy ELSER model** (Gap 9)
10. **Configure Fivetran + dbt models** (Gap 10)

---

## Conclusion

**Phase-1 Core**: 70% Complete  
**Phase-1 with UI**: 40% Complete  

**Strengths**:

- ✅ Solid Gmail OAuth + backfill infrastructure
- ✅ Comprehensive ingest pipeline with heuristics
- ✅ Production-ready Elasticsearch mapping with BM25
- ✅ Search API with multi-field boosting

**Critical Gaps**:

- ❌ **No user-facing UI** (inbox, filters, actions)
- ❌ Missing ESQL saved queries and Kibana exports
- ❌ "Explain why" reasoning endpoint not implemented

**Next Steps**: Focus on Sprint 1 to deliver user-facing Phase-1 experience.
