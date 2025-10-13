# Applications API - Multi-Backend Implementation

**Date**: October 11, 2025  
**Feature**: `/api/applications` endpoint with auto-detection of data source  
**Status**: ✅ Complete and deployed

---

## Overview

The `/api/applications` endpoint now supports **three data sources** with automatic fallback:

1. **BigQuery** (primary) - For production data warehouse integration
2. **Elasticsearch** (secondary) - For search-optimized storage
3. **Demo data** (fallback) - For development without infrastructure

The endpoint auto-detects which source is available based on environment variables and uses the first available option.

---

## Architecture

### Data Source Priority

```text
Request → /api/applications
    ↓
1. Check BigQuery?
   └─ YES → Query BigQuery → Return results
   └─ NO  → Continue
    ↓
2. Check Elasticsearch?
   └─ YES → Query ES → Return results
   └─ NO  → Continue
    ↓
3. Return demo data (always available)
```text

### Detection Logic

```python
def _has_bigquery() -> bool:
    return bool(os.getenv("BQ_PROJECT")) and (
        os.getenv("GOOGLE_APPLICATION_CREDENTIALS") or os.getenv("BQ_SA_JSON")
    )

def _has_es() -> bool:
    return bool(os.getenv("ELASTICSEARCH_URL") or os.getenv("ES_HOST"))
```text

---

## Implementation Details

### File: `services/api/app/routers/applications.py`

**Total lines**: 182  
**Functions**: 4  
**Data sources**: 3

#### Pydantic Model

```python
class Application(BaseModel):
    id: str
    company: Optional[str] = None
    role: Optional[str] = None
    status: Optional[str] = None
    applied_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    source: Optional[str] = None
```text

**Field descriptions**:

- `id`: Unique application identifier (string for compatibility)
- `company`: Company name
- `role`: Job title/role
- `status`: Application status (applied, interview, offer, rejected, etc.)
- `applied_at`: Date/time application was submitted
- `updated_at`: Last update timestamp
- `source`: Where application came from (Greenhouse, Lever, LinkedIn, etc.)

---

## BigQuery Implementation

### Environment Variables

**Required**:

- `BQ_PROJECT` - Google Cloud project ID (e.g., `applylens-gmail-1759983601`)

**Credentials** (one of):

- `GOOGLE_APPLICATION_CREDENTIALS` - Path to service account JSON file
- `BQ_SA_JSON` - Inline JSON content (automatically written to temp file)

**Optional**:

- `BQ_DATASET` - Dataset name (default: `applylens`)
- `BQ_TABLE` - Table name (default: `public_applications`)

### docker-compose.yml Configuration

**Option A: File-based credentials**

```yaml
services:
  api:
    environment:
      - BQ_PROJECT=applylens-gmail-1759983601
      - BQ_DATASET=applylens
      - BQ_TABLE=public_applications
      - GOOGLE_APPLICATION_CREDENTIALS=/run/secrets/bq_sa.json
    secrets:
      - bq_sa

secrets:
  bq_sa:
    file: ./analytics/dbt/applylens-ci.json
```text

**Option B: Inline credentials**

```yaml
services:
  api:
    environment:
      - BQ_PROJECT=applylens-gmail-1759983601
      - BQ_DATASET=applylens
      - BQ_TABLE=public_applications
      - BQ_SA_JSON=${BQ_SA_JSON}  # From .env file
```text

### SQL Query

```sql
SELECT
  CAST(id AS STRING) AS id,
  company,
  role,
  status,
  SAFE.TIMESTAMP(applied_at) AS applied_at,
  SAFE.TIMESTAMP(updated_at) AS updated_at,
  source
FROM `{project}.{dataset}.{table}`
WHERE TRUE
  AND status = @status  -- if status filter provided
ORDER BY updated_at DESC NULLS LAST, applied_at DESC NULLS LAST
LIMIT @limit
```text

**Query features**:

- Parameterized queries (prevents SQL injection)
- Safe timestamp conversion
- NULL-safe sorting
- Dynamic status filtering

### Error Handling

```python
try:
    # BigQuery logic...
    return results
except Exception as e:
    raise HTTPException(status_code=503, detail=f"BigQuery error: {e}")
```text

**Status code**: 503 Service Unavailable  
**Response format**: `{"detail": "BigQuery error: <message>"}`

---

## Elasticsearch Implementation

### Environment Variables

**Connection**:

- `ELASTICSEARCH_URL` - Full URL (e.g., `http://elasticsearch:9200`)
- **OR** `ES_HOST` + `ES_PORT` - Host and port separately

**Authentication** (optional):

- `ES_USER` - Username for basic auth
- `ES_PASS` - Password for basic auth

**Configuration**:

- `ES_APPS_INDEX` - Index name (default: `applications_v1`)

### docker-compose.yml Configuration

```yaml
services:
  api:
    environment:
      - ELASTICSEARCH_URL=http://elasticsearch:9200
      - ES_APPS_INDEX=applications_v1
      # Optional authentication
      - ES_USER=elastic
      - ES_PASS=changeme
```text

### ES Query

```python
{
    "query": {
        "bool": {
            "must": [
                {"term": {"status.keyword": "interview"}}  # if status filter
            ]
        }
    },
    "sort": [
        {"updated_at": {"order": "desc"}},
        {"applied_at": {"order": "desc"}}
    ],
    "size": 100,
    "_source": ["id", "company", "role", "status", "applied_at", "updated_at", "source"]
}
```text

**Features**:

- Keyword field for exact status matching
- Multi-field sorting
- Source filtering (only requested fields)

### Index Mapping Requirements

```json
{
  "mappings": {
    "properties": {
      "id": {"type": "keyword"},
      "company": {"type": "text"},
      "role": {"type": "text"},
      "status": {
        "type": "text",
        "fields": {
          "keyword": {"type": "keyword"}
        }
      },
      "applied_at": {"type": "date"},
      "updated_at": {"type": "date"},
      "source": {"type": "keyword"}
    }
  }
}
```text

### Error Handling

```python
try:
    # Elasticsearch logic...
    return results
except Exception as e:
    raise HTTPException(status_code=503, detail=f"Elasticsearch error: {e}")
```text

---

## Demo Data Implementation

### When Used

- No BigQuery credentials configured
- No Elasticsearch configured
- Development environment
- Local testing without infrastructure

### Demo Applications

```python
[
    {
        "id": "app_demo_1",
        "company": "OpenAI",
        "role": "ML Engineer",
        "status": "applied",
        "applied_at": "2025-09-05T00:00:00",
        "source": "Greenhouse"
    },
    {
        "id": "app_demo_2",
        "company": "Acme Corp",
        "role": "Full-Stack Developer",
        "status": "interview",
        "applied_at": "2025-09-12T00:00:00",
        "source": "Lever"
    },
    {
        "id": "app_demo_3",
        "company": "TechCorp",
        "role": "Senior Backend Engineer",
        "status": "offer",
        "applied_at": "2025-09-20T00:00:00",
        "source": "LinkedIn"
    },
    {
        "id": "app_demo_4",
        "company": "StartupXYZ",
        "role": "DevOps Engineer",
        "status": "rejected",
        "applied_at": "2025-08-15T00:00:00",
        "source": "Indeed"
    }
]
```text

### Filtering

```python
rows = demo[:limit]
if status:
    rows = [r for r in rows if r.status == status]
return rows
```text

---

## API Endpoint

### Route Definition

```python
@router.get("/applications", response_model=List[Application])
def list_applications(
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[str] = None,
):
```text

**Full path**: `/api/applications` (with prefix from `main.py`)

### Query Parameters

| Parameter | Type | Default | Min | Max | Required | Description |
|-----------|------|---------|-----|-----|----------|-------------|
| `limit` | int | 100 | 1 | 1000 | No | Max results to return |
| `status` | string | None | - | - | No | Filter by status |

### Request Examples

**List all applications (limit 5)**:

```bash
GET /api/applications?limit=5
```text

**Filter by status**:

```bash
GET /api/applications?status=interview&limit=10
```text

**Default (100 results)**:

```bash
GET /api/applications
```text

### Response Format

**Success (200 OK)**:

```json
[
  {
    "id": "app_1234",
    "company": "OpenAI",
    "role": "ML Engineer",
    "status": "applied",
    "applied_at": "2025-09-05T00:00:00",
    "updated_at": "2025-09-10T14:30:00",
    "source": "Greenhouse"
  }
]
```text

**Error (503 Service Unavailable)**:

```json
{
  "detail": "BigQuery error: Table not found"
}
```text

---

## Dependencies

### Added to `pyproject.toml`

```toml
dependencies = [
  # ... existing dependencies ...
  "google-auth>=2.30.0",
  "google-cloud-bigquery>=3.25.0",
  # ...
]
```text

**Package versions**:

- `google-auth>=2.30.0` - Already present, version constraint updated
- `google-cloud-bigquery>=3.25.0` - **NEW** - BigQuery Python client

**Installation**:

```bash
pip install google-cloud-bigquery>=3.25.0 google-auth>=2.30.0
```text

---

## Integration with main.py

### Import Statement

```python
from .routers import emails, search, suggest, applications
```text

### Router Registration

```python
app.include_router(applications.router, prefix="/api")
```text

**Full route**: `/api` + `/applications` = `/api/applications`

---

## Vite Proxy Configuration

### File: `apps/web/vite.config.ts`

**Before** (broken):

```typescript
proxy: {
  '/api': {
    target: 'http://api:8003',
    changeOrigin: true,
    rewrite: (path) => path.replace(/^\/api/, '')  // ❌ Strips /api
  }
}
```text

**Problem**: Frontend calls `/api/applications`, proxy rewrites to `/applications`, backend expects `/api/applications`

**After** (fixed):

```typescript
proxy: {
  '/api': {
    target: 'http://api:8003',
    changeOrigin: true,
    // No rewrite - keep /api prefix for the backend
  }
}
```text

**Result**: Frontend calls `/api/applications`, proxy forwards `/api/applications` to backend ✅

---

## Testing

### 1. Direct API Test (Port 8003)

```bash
# List all (demo data by default)
curl "http://localhost:8003/api/applications?limit=5"

# Filter by status
curl "http://localhost:8003/api/applications?status=interview&limit=10"

# JSON formatting
curl "http://localhost:8003/api/applications?limit=3" | python -m json.tool
```text

**Expected response**:

```json
[
  {
    "id": "app_demo_1",
    "company": "OpenAI",
    "role": "ML Engineer",
    "status": "applied",
    "applied_at": "2025-09-05T00:00:00",
    "updated_at": null,
    "source": "Greenhouse"
  }
]
```text

### 2. Through Vite Proxy (Port 5175)

```bash
curl "http://localhost:5175/api/applications?limit=2"
```text

**Expected**: Same format, proxied to API

### 3. Frontend Integration

**JavaScript/TypeScript**:

```typescript
// apps/web/src/lib/api.ts
export async function listApplications(params?: {
  limit?: number;
  status?: string;
}) {
  const qs = new URLSearchParams();
  if (params?.limit) qs.set('limit', String(params.limit));
  if (params?.status) qs.set('status', params.status);
  const url = `/api/applications${qs.toString() ? `?${qs}` : ''}`;
  const r = await fetch(url);
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}
```text

**Usage**:

```typescript
// Tracker.tsx
const data = await listApplications({ limit: 50, status: 'interview' });
setApplications(Array.isArray(data) ? data : []);
```text

---

## Deployment

### Build Process

**1. API Container Build** (57.3s):

```bash
cd D:\ApplyLens\infra
docker compose build api
```text

**Changes**:

- Installed `google-cloud-bigquery>=3.25.0`
- Installed `google-auth>=2.30.0`
- Layer 4/5: `pip install` took 38.1s

**2. Restart API**:

```bash
docker compose up -d api
```text

**3. Restart Web** (to apply Vite config):

```bash
docker compose restart web
```text

### Verification

```bash
docker ps --filter "name=infra-" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```text

**Expected**:

```text
NAMES                 STATUS                    PORTS
infra-web-1           Up X seconds              0.0.0.0:5175->5175/tcp
infra-api-1           Up X seconds              0.0.0.0:8003->8003/tcp
```text

---

## Production Setup

### BigQuery Configuration

**1. Create service account**:

```bash
gcloud iam service-accounts create applylens-api \
  --display-name="ApplyLens API Service Account"
```text

**2. Grant permissions**:

```bash
gcloud projects add-iam-policy-binding applylens-gmail-1759983601 \
  --member="serviceAccount:applylens-api@applylens-gmail-1759983601.iam.gserviceaccount.com" \
  --role="roles/bigquery.dataViewer"
```text

**3. Generate key**:

```bash
gcloud iam service-accounts keys create applylens-ci.json \
  --iam-account=applylens-api@applylens-gmail-1759983601.iam.gserviceaccount.com
```bash

**4. Add to docker-compose.yml**:

```yaml
secrets:
  bq_sa:
    file: ./analytics/dbt/applylens-ci.json
```text

### Elasticsearch Configuration

**1. Create index**:

```bash
curl -X PUT "http://localhost:9200/applications_v1" -H 'Content-Type: application/json' -d'
{
  "mappings": {
    "properties": {
      "id": {"type": "keyword"},
      "company": {"type": "text"},
      "role": {"type": "text"},
      "status": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
      "applied_at": {"type": "date"},
      "updated_at": {"type": "date"},
      "source": {"type": "keyword"}
    }
  }
}
'
```text

**2. Index sample document**:

```bash
curl -X POST "http://localhost:9200/applications_v1/_doc" -H 'Content-Type: application/json' -d'
{
  "id": "app_001",
  "company": "Google",
  "role": "Software Engineer",
  "status": "applied",
  "applied_at": "2025-09-01T10:00:00",
  "source": "LinkedIn"
}
'
```text

---

## Troubleshooting

### Issue 1: "BigQuery error: Could not automatically determine credentials"

**Cause**: Missing or invalid credentials

**Solution**:

```bash
# Check environment variables
docker compose exec api env | grep BQ

# Verify file exists
docker compose exec api ls -la /run/secrets/

# Test credentials
docker compose exec api python -c "from google.cloud import bigquery; print(bigquery.Client())"
```text

### Issue 2: "Elasticsearch error: Connection refused"

**Cause**: ES not running or wrong URL

**Solution**:

```bash
# Check ES is running
docker ps | grep elasticsearch

# Test connection
curl http://localhost:9200

# Check environment
docker compose exec api env | grep ES
```text

### Issue 3: "404 Not Found" on `/api/applications`

**Cause**: Router not registered or Vite proxy rewriting

**Solution**:

```bash
# Check router registration
docker compose exec api grep "applications.router" /app/app/main.py

# Check direct API
curl http://localhost:8003/api/applications

# Check Vite proxy config
grep -A 5 "proxy" apps/web/vite.config.ts
```text

### Issue 4: Empty array `[]` returned

**Cause**: No data in backend, filters too restrictive

**Solution**:

```bash
# Check BigQuery table
bq query --use_legacy_sql=false "SELECT COUNT(*) FROM applylens.public_applications"

# Check ES index
curl "http://localhost:9200/applications_v1/_count"

# Test without filters
curl "http://localhost:8003/api/applications?limit=100"
```text

---

## Performance Considerations

### BigQuery

**Costs**:

- $5 per TB scanned
- This query scans ~7 columns
- 1000 rows ≈ 100 KB
- 10,000 requests/day ≈ 1 GB/month ≈ $0.005/month

**Optimization**:

- Use partitioned tables (`applied_at`, `updated_at`)
- Add clustering on `status`
- Cache results in Redis

### Elasticsearch

**Performance**:

- Sub-second queries for 1M+ documents
- Scales horizontally

**Optimization**:

- Use `size: 100` max
- Disable `_source` for count-only queries
- Use `filter` context instead of `must` for better caching

### Demo Data

**Performance**: Instant (in-memory)  
**Limitation**: Only 4 records  
**Use case**: Development only

---

## Future Enhancements

### 1. Caching Layer

```python
from functools import lru_cache
from datetime import datetime, timedelta

@lru_cache(maxsize=128)
def _cached_applications(status: Optional[str], timestamp: int):
    # Cache for 5 minutes
    return _list_applications_bq(100, status)

@router.get("/applications")
def list_applications(status: Optional[str] = None):
    cache_key = int(datetime.now().timestamp() // 300)  # 5-min buckets
    return _cached_applications(status, cache_key)
```text

### 2. Pagination

```python
@router.get("/applications")
def list_applications(
    limit: int = 100,
    offset: int = 0,  # NEW
    status: Optional[str] = None,
):
    # Add OFFSET to SQL/ES queries
    # Return total count in response
```text

### 3. Search Query

```python
@router.get("/applications")
def list_applications(
    q: Optional[str] = None,  # NEW: search company/role
    status: Optional[str] = None,
):
    # Add WHERE company LIKE %q% OR role LIKE %q%
```text

### 4. Aggregations

```python
@router.get("/applications/stats")
def application_stats():
    return {
        "total": 1234,
        "by_status": {
            "applied": 500,
            "interview": 300,
            "offer": 50,
            "rejected": 384
        }
    }
```text

---

**Status**: ✅ Production ready  
**Data sources**: BigQuery > Elasticsearch > Demo  
**Endpoint**: `/api/applications`  
**Default**: Demo data (no config needed)  
**Backward compatible**: Yes
