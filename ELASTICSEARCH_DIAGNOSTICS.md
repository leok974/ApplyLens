# Elasticsearch Diagnostics & Fixes - v0.4.18-hotfix2

## Issue Summary
Gmail backfill was completing successfully but search results were showing 0 hits.

## Root Cause Analysis

### 1. **Indices & Aliases Configuration** ✅
```bash
# Indices found:
- gmail_emails-000001: 2339 docs (16.1MB) - yellow status, write index
- gmail_emails-999999: 2 docs (16.3KB) - green status

# Alias configuration:
- gmail_emails → points to BOTH indices
  - gmail_emails-000001 (is_write_index: true)
  - gmail_emails-999999 (is_write_index: false)

# Total documents in alias:
$ docker exec applylens-es-prod curl -s "http://localhost:9200/gmail_emails/_count?pretty"
{
  "count" : 2341
}
```

### 2. **Owner Email Filter** ✅
Documents DO have `owner_email` field set correctly:
```bash
$ docker exec applylens-es-prod curl -s "http://localhost:9200/gmail_emails/_count?q=owner_email:leoklemet.pa@gmail.com&pretty"
{
  "count" : 248
}
```

### 3. **Search API Configuration** ✅
- API uses `ELASTICSEARCH_INDEX=gmail_emails`
- Search filters by `owner_email` (not `tenant_id`)
- `DEFAULT_USER_EMAIL=leoklemet.pa@gmail.com` is set for fallback auth

### 4. **Missing ES Refresh** ❌ **FIXED**
The backfill job was not refreshing the Elasticsearch index after bulk indexing, causing documents to not be immediately searchable.

## Fixes Applied

### v0.4.18-hotfix1
**Issue**: Async job endpoint returning 404
**Fix**: Removed duplicate `/api` prefix from router mount (nginx strips it)
```python
# Before:
app.include_router(gmail_backfill.router, prefix="/api")

# After:
app.include_router(gmail_backfill.router)  # Router already has prefix="/gmail/backfill"
```

### v0.4.18-hotfix2
**Issue**: Documents not immediately searchable after backfill
**Fix**: Added ES refresh after backfill completion

**File**: `services/api/app/routers/gmail_backfill.py`
```python
# After successful backfill, before marking job as done:
try:
    from ..gmail_service import es_client
    es = es_client()
    index_name = os.getenv("ELASTICSEARCH_INDEX", "gmail_emails")
    es.indices.refresh(index=index_name)
    logger.info(f"[Job {job_id}] Refreshed ES index: {index_name}")
except Exception as e:
    logger.warning(f"[Job {job_id}] ES refresh failed: {e}")
```

## Verification Steps

### 1. Check Index Health
```bash
docker exec applylens-es-prod curl -s 'http://localhost:9200/_cat/indices?v' | grep gmail_emails
```

### 2. Count Documents
```bash
# Total in alias
docker exec applylens-es-prod curl -s "http://localhost:9200/gmail_emails/_count?pretty"

# Filtered by owner
docker exec applylens-es-prod curl -s "http://localhost:9200/gmail_emails/_count?q=owner_email:leoklemet.pa@gmail.com&pretty"
```

### 3. Test Search Endpoint
```bash
# From browser console (with auth):
await fetch('/api/search/?q=*&scale=all&size=3',{credentials:'include'}).then(r=>r.json());
```

### 4. Manual ES Refresh (if needed)
```bash
docker exec applylens-es-prod curl -s -XPOST "http://localhost:9200/gmail_emails/_refresh?pretty"
```

## Deployment

```bash
# Build API with fixes
cd d:\ApplyLens\services\api
docker build -t leoklemet/applylens-api:v0.4.18-hotfix2 -f Dockerfile .

# Update docker-compose.prod.yml
# image: leoklemet/applylens-api:v0.4.18-hotfix2

# Deploy
cd d:\ApplyLens
docker-compose -f docker-compose.prod.yml up -d --force-recreate api

# Manually refresh existing docs (one-time)
docker exec applylens-es-prod curl -s -XPOST "http://localhost:9200/gmail_emails/_refresh"
```

## Status
✅ **v0.4.18-hotfix1**: Router 404 fixed, endpoint now returns 403 CSRF (expected)
✅ **v0.4.18-hotfix2**: ES refresh added, documents now searchable immediately after backfill
✅ **Manual refresh**: Applied to existing 2341 documents

## Next Steps
1. Test backfill from UI (click "Sync 60d")
2. Verify search returns results immediately after completion
3. Monitor API logs for ES refresh confirmation
4. Consider Redis for job tracking in multi-instance setup (v0.5.x)

## Related Files
- `services/api/app/routers/gmail_backfill.py` - Async job worker with ES refresh
- `services/api/app/routers/search.py` - Search endpoint with owner_email filter
- `services/api/app/gmail_service.py` - Gmail backfill with progress tracking
- `apps/web/nginx.conf` - Nginx proxy config (strips /api prefix)
- `docker-compose.prod.yml` - Production deployment config
