# 🎯 v0.4.4 Deployment - Bulletproof Search

## Deployment Summary

**Version:** v0.4.4
**Date:** October 23, 2025 12:58 PM
**Build Time:** 14.5s
**Status:** ✅ DEPLOYED

## What's New in v0.4.4

### 🛡️ Bulletproofing Improvements

#### 1. **E2E Production Testing Script**
**File:** `apps/web/package.json`

Added dedicated script for testing against production:
```json
"test:e2e:prod": "cross-env E2E_BASE_URL=https://applylens.app/web playwright test --grep @prodSafe --reporter=line"
```

**Usage:**
```bash
cd apps/web
pnpm test:e2e:prod
```

#### 2. **Router basename Support**
**File:** `apps/web/src/main.tsx`

Added proper basename handling for deployment paths:
```typescript
const basename = import.meta.env.BASE_URL && import.meta.env.BASE_URL !== '/'
  ? import.meta.env.BASE_URL
  : ''

<BrowserRouter basename={basename}>
```

**Impact:**
- Supports both root (`/`) and subpath (`/web/`) deployments
- Respects Vite's `BASE_URL` environment variable
- Enables flexible deployment strategies

#### 3. **Enhanced Debug Logging**
**File:** `apps/web/src/hooks/useSearchModel.ts`

Upgraded console logging to show more diagnostic info:
```typescript
console.debug('[search] normalized', {
  q: query,
  filters,
  sort,
  status: res.status,
  total: responseTotal,
  sample: items?.[0],
  rawKeys: Object.keys(raw || {}),
})
```

**What You'll See:**
- Query and filters used
- Response status code
- Total results count
- Sample first result
- Raw response keys (to debug shape issues)

**How to Use:**
1. Open https://applylens.app/web/search
2. Open browser DevTools → Console
3. Type "Interview" and press Enter
4. Look for `[search] normalized` log

#### 4. **Array Guard in Results Rendering**
**File:** `apps/web/src/pages/Search.tsx`

Added defensive programming for results array:
```tsx
{(Array.isArray(results) ? results : []).map((h: any, i: number) => {
  // ... render result
})}
```

**Prevents:**
- Crashes if `results` is undefined
- Crashes if `results` is not an array
- Runtime errors during normalization issues

#### 5. **Smoke Test Suite**
**File:** `apps/web/tests/e2e/search.smoke.spec.ts`

Created focused smoke tests for quick validation:

**Test 1:** Search button updates UI
- Navigate with query param
- Click search button
- Verify loading → results/empty

**Test 2:** Enter key triggers search
- Type query
- Press Enter
- Verify loading → results/empty

**Test 3:** Category filter toggle
- Navigate with query
- Toggle promotions filter
- Verify new search triggered

**All tagged `@prodSafe`** for production testing.

## Technical Details

### Build Info
```
Image: leoklemet/applylens-web:v0.4.4
Bundle: index-[timestamp].js (generated at build time)
BASE_PATH: /web/
API_BASE: /api
```

### Response Normalizer

Handles 3 response formats:

**Format A - Direct items:**
```json
{ "items": [...], "total": 42 }
```

**Format B - Results key:**
```json
{ "results": [...], "total": 42 }
```

**Format C - Elasticsearch:**
```json
{
  "hits": {
    "hits": [{ "_source": {...} }],
    "total": { "value": 42 }
  }
}
```

All normalized to:
```json
{ "items": [...], "total": 42 }
```

### Debug Log Output Example

What you'll see in browser Console:

```javascript
[search] normalized {
  q: "Interview",
  filters: { categories: {}, scale: "30d", ... },
  sort: "relevance",
  status: 200,
  total: 15,
  sample: { id: "...", subject: "...", ... },
  rawKeys: ["items", "total"]
}
```

## Deployment Steps

```powershell
# 1. Build image
docker build -t leoklemet/applylens-web:v0.4.4 \
  --build-arg WEB_BASE_PATH=/web/ \
  --build-arg VITE_API_BASE=/api \
  -f Dockerfile.prod .

# 2. Update docker-compose.prod.yml to v0.4.4

# 3. Deploy
docker-compose -f docker-compose.prod.yml up -d --force-recreate web
docker-compose -f docker-compose.prod.yml restart nginx
```

## Testing Instructions

### Quick Smoke Test
```bash
cd apps/web
pnpm test:e2e:prod
```

**What it tests:**
- ✅ Search button triggers fetch
- ✅ Enter key triggers fetch
- ✅ Category filter triggers fetch
- ✅ Results or empty state appears
- ✅ Loading spinner shows during fetch

### Manual Production Testing

1. **Open search page:**
   https://applylens.app/web/search

2. **Open DevTools Console** (F12 → Console tab)

3. **Test basic search:**
   - Type "Interview"
   - Press Enter
   - Look for `[search] normalized` log
   - Verify `total: N` and `sample: {...}`

4. **Test filter:**
   - Click "promotions" button
   - Look for new `[search] normalized` log
   - Verify URL updates: `?q=Interview&cat=promotions`

5. **Test empty query:**
   - Clear search input
   - Click Search button
   - Should NOT see fetch log (no search triggered)

6. **Test URL hydration:**
   - Navigate to: `/search?q=offer&cat=bills`
   - Should see automatic `[search] normalized` log
   - Verify results load without clicking Search

### Expected Console Logs

**Successful search:**
```
[search] normalized { q: "Interview", ... total: 15, sample: {...} }
```

**Empty results:**
```
[search] normalized { q: "xyzabc123", ... total: 0, sample: undefined }
```

**204 No Content:**
```
[search] 204 No Content { query: "...", filters: {...}, sort: "..." }
```

**Error:**
```
[search] error Error: Search failed: 500 Internal Server Error
```

## Debugging Guide

### Problem: Search triggers but no results

**Check Console:**
1. Look for `[search] normalized` log
2. Check `total` value - is it 0 or >0?
3. Check `sample` - is it defined?
4. Check `rawKeys` - what's in the response?

**If `total: 0` and `sample: undefined`:**
- Backend returned empty results (expected)
- Empty state should show

**If `total: >0` but no results render:**
- Check `rawKeys` - might be wrong response shape
- Normalizer might need adjustment

### Problem: Filter doesn't trigger search

**Check Console:**
1. Click filter
2. Wait 400ms (debounce)
3. Should see new `[search] normalized` log

**If no log appears:**
- Check that filter updates `setFilters()`
- Check `useEffect` dependencies in hook
- Check debounce timer (400ms)

### Problem: Infinite loop / too many fetches

**Check Console:**
1. Count `[search] normalized` logs
2. Should be 1 per user action + 1 on mount

**If many logs:**
- Check `hydratedRef` is preventing re-hydration
- Check `hasSearched` gates URL sync
- Check no other effects calling `setQuery`/`setFilters`

## Files Changed (Summary)

| File | Purpose | Lines |
|------|---------|-------|
| `package.json` | Added `test:e2e:prod` script | +1 |
| `main.tsx` | Added router basename support | +3 |
| `useSearchModel.ts` | Enhanced debug logging | +5 |
| `Search.tsx` | Array guard in results render | +1 |
| `search.smoke.spec.ts` | Smoke tests | +60 (new file) |
| `docker-compose.prod.yml` | Version bump to v0.4.4 | +2 |

**Total:** ~72 lines changed/added

## Version Comparison

| Version | Key Changes |
|---------|-------------|
| v0.4.1 | Fixed heartbeat, wrong BASE_PATH |
| v0.4.2 | Fixed BASE_PATH to `/web/` |
| v0.4.3 | Search improvements + hook refactor |
| v0.4.4 | **Bulletproofing + enhanced debugging** |

## Known Issues

### ✅ RESOLVED
- useNavigate error (v0.4.3)
- 502 Bad Gateway (v0.4.2)
- Mixed content (v0.4.2)
- Stale closures (v0.4.3)
- Hydration loops (v0.4.3)

### ⏳ MONITORING
- Response shape consistency
- Filter debounce timing
- Empty state rendering

## Success Criteria

✅ Build completed (14.5s)
✅ Container deployed
✅ Nginx restarted
✅ Enhanced logging in place
✅ Array guards added
✅ Router basename configured
✅ Smoke tests created
✅ Production test script added

**Status:** ✅ **READY FOR PRODUCTION TESTING**

## Next Steps

### Immediate
1. ✅ Deploy v0.4.4 (DONE)
2. ⏳ Run smoke tests against production
3. ⏳ Check Console logs manually
4. ⏳ Verify normalizer output

### Commands
```bash
# Run production tests
cd apps/web
pnpm test:e2e:prod

# Check specific test
pnpm exec playwright test tests/e2e/search.smoke.spec.ts \
  --grep "@prodSafe" \
  -c "E2E_BASE_URL=https://applylens.app/web"
```

## Rollback

If needed, rollback to v0.4.3:

```powershell
cd d:\ApplyLens

# Edit docker-compose.prod.yml
# Change: image: leoklemet/applylens-web:v0.4.4
# To:     image: leoklemet/applylens-web:v0.4.3

docker-compose -f docker-compose.prod.yml up -d --force-recreate web
docker-compose -f docker-compose.prod.yml restart nginx
```

---

**Deployed by:** GitHub Copilot
**Environment:** applylens.app
**Ready for:** Production smoke testing with enhanced diagnostics
**Documentation:** See SEARCH_COMPLETE_SUMMARY.md for full implementation details
