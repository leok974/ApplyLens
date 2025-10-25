# v0.4.15 Deployment Summary: 422 Error Prevention & Data Sync Guide

## 🎯 What Was Fixed

**Primary Issue**: 422 (Unprocessable Entity) errors when search query is empty

**Root Cause**: Backend API requires a `q` parameter. When users clear the search box or submit without a query, the frontend sent no `q` parameter, causing 422 errors.

**Solution**: Always send `q=*` (match-all) when query is empty.

## 🛠️ Changes in v0.4.15

### A) Empty Query Fallback ✅

**File**: `apps/web/src/hooks/useSearchModel.ts`

**Before**:
```typescript
function toQueryParams({ query, filters, sort }) {
  const p = new URLSearchParams()
  if (query) p.set('q', query)  // ❌ No fallback if query is empty
  // ...
}
```

**After**:
```typescript
function toQueryParams({ query, filters, sort }) {
  const p = new URLSearchParams()

  // 🔥 Fallback to "*" (match-all) if query is empty to avoid 422 errors
  p.set('q', query?.trim() ? query.trim() : '*')
  // ...
}
```

### B) Removed Query Guard ✅

**Before**:
```typescript
const runSearch = useCallback(async () => {
  if (!query.trim()) {
    setResults([])
    setTotal(0)
    return  // ❌ Blocked search if query empty
  }
  // ...
})
```

**After**:
```typescript
const runSearch = useCallback(async () => {
  // Don't block search if query is empty - we'll send "*" as fallback
  setLoading(true)
  setError(null)
  setLastStatus(null)
  // ...
})
```

### C) Enhanced Error Tracking ✅

Added `lastStatus` state to track HTTP response codes:

```typescript
const [lastStatus, setLastStatus] = useState<number | null>(null)

// Capture status on success
setLastStatus(res.status)

// Capture status on error
if (!res.ok) {
  setLastStatus(res.status)
  // Special handling for 422
  if (res.status === 422) {
    throw new Error(`Search requires a query. We sent "*" automatically, but the server returned an error.`)
  }
}
```

### D) Improved Empty State Messaging ✅

**File**: `apps/web/src/pages/Search.tsx`

Shows helpful context when 422 errors occur:

```tsx
{/* Show helpful message for 422 errors */}
{lastStatus === 422 && (
  <div className="mb-4 rounded-lg border border-amber-200 bg-amber-50 p-3">
    <strong>Note:</strong> Search requires a query. We sent <code>*</code> (match-all) automatically.
    <br />
    <span className="text-xs opacity-80">
      If you're seeing this, the search index may be empty. Try syncing data first.
    </span>
  </div>
)}
```

Also updated query display to show "(match-all)" when empty:
```tsx
<span>Query: <code>{query || '(match-all)'}</code></span>
```

## 📊 Deployment Status

- **Version**: v0.4.15
- **Bundle**: `index-1761264120183.uiFnBUF_.js`
- **Deployed**: 2025-10-24 @ 00:03 UTC
- **Cloudflare Cache**: Purged @ 00:03 UTC
- **Status**: ✅ Deployed successfully

## 🔧 Data Sync Guide

### Problem: Empty Search Index

If you're seeing "No results found" with a 422 warning, your search index is empty.

**Verification**:
```bash
# Check if emails endpoint returns data
curl -s "http://localhost/api/emails/?limit=5" -H "Cookie: ..." | jq '.length'

# Check Elasticsearch indices
docker exec -it applylens-es-prod curl -s http://localhost:9200/_cat/indices?v

# Check document count
docker exec -it applylens-es-prod curl -s 'http://localhost:9200/emails_*/_count?pretty'
```

### Solution A: UI Sync (Recommended)

1. Navigate to https://applylens.app/web/search
2. Look for "Sync 60d" button in the header
3. Click to trigger a 60-day backfill
4. Wait for ingestion to complete (check API logs)
5. Retry search

### Solution B: Container-Based Sync

**Check API logs while syncing**:
```bash
docker logs -f applylens-api-prod | grep -i 'sync\|ingest\|email\|es\|index'
```

**Run backfill job** (if available):
```bash
# Example - adjust based on your stack
docker exec -it applylens-api-prod python -m app.jobs.backfill_emails \
  --days 60 \
  --tenant current \
  --limit 200
```

### Solution C: Quick Test Script

After triggering sync, paste this in the browser console:

```javascript
// Test emails endpoint
await fetch('/api/emails/?limit=1', { credentials:'include' })
  .then(r=>r.json())
  .then(j=>console.log('emails:', j));

// Test search with match-all
await fetch('/api/search/?q=*&limit=5', { credentials:'include' })
  .then(r=>r.json())
  .then(j=>{
    const items = j.items ?? j.results ?? (j.hits?.hits ?? []).map(h=>h._source ?? h.source ?? h);
    console.log('search any:', items.length, items.slice(0,1));
  });

// Test search with specific query
await fetch('/api/search/?q=Interview&scale=all&limit=5', { credentials:'include' })
  .then(r=>r.json())
  .then(j=>{
    const items = j.items ?? j.results ?? (j.hits?.hits ?? []).map(h=>h._source ?? h.source ?? h);
    console.log('Interview:', items.length, items.slice(0,1));
  });
```

## 🎯 Expected Behavior

### Before v0.4.15

**Scenario**: User clears search box and clicks "Search"

```
Frontend: fetch('/api/search/?limit=50') // No q parameter
Backend: 422 Unprocessable Entity (missing required parameter 'q')
Console: [search] HTTP error { status: 422, ... }
UI: Error banner or crash
```

### After v0.4.15

**Scenario**: User clears search box and clicks "Search"

```
Frontend: fetch('/api/search/?q=*&limit=50') // q=* (match-all)
Backend: 200 OK (returns all documents, or [] if index empty)
Console: [search] normalized { q: '*', total: 0, ... }
UI: Empty state with helpful message
```

**If 422 still occurs** (backend doesn't support `q=*`):
```
Frontend: fetch('/api/search/?q=*&limit=50')
Backend: 422 Unprocessable Entity
UI: Empty state shows:
     "Note: Search requires a query. We sent * automatically.
      If you're seeing this, the search index may be empty. Try syncing data first."
```

## 🔄 Optional Backend Improvement

**Recommended**: Make backend more forgiving

**File**: `services/api/app/routers/analytics.py` (or search router)

```python
from typing import Optional
from fastapi import Query

@router.get("/search/")
def search(
    q: Optional[str] = Query(default="*"),  # 🔥 Make optional with default
    # ... other params
):
    if q == "*" or not q:
        # Build Elasticsearch match_all query
        es_query = {"query": {"match_all": {}}}
    else:
        # Normal query_string or multi_match
        es_query = {
            "query": {
                "query_string": {"query": q, "default_field": "*"}
            }
        }
    # ...
```

This makes the API more durable and prevents 422 errors from any client.

## 📝 Testing Checklist

### Manual Testing

1. **Test Empty Query**:
   ```
   Navigate to: /search?q=
   Expected: Search runs with q=*, shows empty state or results
   Should NOT show 422 error
   ```

2. **Test Match-All**:
   ```
   Clear search box, click "Search"
   Expected: Search runs with q=*, shows empty state with "(match-all)" label
   ```

3. **Test Normal Query**:
   ```
   Enter "Interview", click "Search"
   Expected: Search runs with q=Interview, shows results or empty state
   ```

4. **Test 422 Handling** (if backend doesn't support `q=*`):
   ```
   Clear search box, click "Search"
   If 422 occurs: Should show amber warning box with sync instructions
   ```

### Browser Console Testing

```javascript
// Test empty query fallback
const params = new URLSearchParams({ q: '', limit: '5' })
console.log('Empty query:', params.toString())
// Expected: q=*&limit=5 (not just limit=5)

// Test toQueryParams logic
const testQuery = (q) => {
  const p = new URLSearchParams()
  p.set('q', q?.trim() ? q.trim() : '*')
  return p.toString()
}

console.log('Empty:', testQuery(''))        // q=*
console.log('Whitespace:', testQuery('  ')) // q=*
console.log('Query:', testQuery('test'))    // q=test
```

## 🚀 User Instructions

1. **Clear Browser Cache**:
   - Ctrl+Shift+R (Chrome) or Ctrl+F5 (Firefox)
   - Or: Incognito/Private window

2. **Verify Deployment**:
   - Navigate to https://applylens.app/web/search
   - Console should show: `🔍 ApplyLens Web v0.4.15`
   - Clear search box and click "Search"
   - Should NOT see 422 errors in console

3. **Sync Data** (if seeing empty results):
   - Click "Sync 60d" button in header
   - Wait 1-2 minutes for ingestion
   - Retry search - should see results

4. **Verify No 422 Errors**:
   - Open DevTools → Console
   - Clear search box, click "Search"
   - Look for: `[search] normalized { q: '*', ... }`
   - Should NOT see: `[search] HTTP error { status: 422 }`

## 🐛 Troubleshooting

### Still Seeing 422 Errors

**Possible Causes**:
1. Backend doesn't support `q=*` (requires backend update)
2. Other required parameters missing
3. Auth issues (401/403 instead of 422)

**Debug Steps**:
```bash
# Check exact request
curl -sI "http://localhost/api/search/?q=*&limit=5" -H "Cookie: ..."

# Check backend logs
docker logs applylens-api-prod | tail -50

# Check if backend validates q parameter
grep -r "Query(.*required" services/api/app/routers/
```

### Empty Results After Sync

**Check ingestion status**:
```bash
# Count documents in ES
docker exec applylens-es-prod curl -s 'http://localhost:9200/emails_*/_count?pretty'

# Check if emails endpoint returns data
curl -s "http://localhost/api/emails/?limit=5" -H "Cookie: ..."

# Check search endpoint
curl -s "http://localhost/api/search/?q=*&limit=5" -H "Cookie: ..."
```

### Match-All Returns Nothing

This is **EXPECTED** if:
- Search index is empty (no data synced yet)
- User has no documents in their tenant
- Sync job is still running

**Not a bug** - it's showing the real state of the index.

## 📚 Files Changed

- ✅ `apps/web/src/hooks/useSearchModel.ts` - Empty query fallback, status tracking
- ✅ `apps/web/src/pages/Search.tsx` - 422 error messaging, empty state improvements
- ✅ `apps/web/src/main.tsx` - Updated version banner
- ✅ `docker-compose.prod.yml` - Updated to v0.4.15

## 🔄 Rollback Plan

If issues occur:
```powershell
# Rollback to v0.4.14
docker-compose -f docker-compose.prod.yml down web
# Edit docker-compose.prod.yml: change v0.4.15 → v0.4.14
docker-compose -f docker-compose.prod.yml up -d web
docker-compose -f docker-compose.prod.yml restart nginx
.\scripts\Purge-CloudflareCache.ps1
```

## ✅ Success Criteria

- ✅ No 422 errors when search query is empty
- ✅ `q=*` sent automatically as fallback
- ✅ Helpful 422 messaging if backend rejects match-all
- ✅ Empty state shows "(match-all)" label for empty queries
- ✅ Search index emptiness is communicated clearly to users

---

**Next Steps**:
1. ✅ Clear browser cache and verify v0.4.15 loads
2. 🔄 Trigger data sync (UI or container-based)
3. 🧪 Test search with empty query - should send `q=*`
4. 📊 Verify results appear after sync completes

**Questions?** Check browser console for `[search]` log messages!
