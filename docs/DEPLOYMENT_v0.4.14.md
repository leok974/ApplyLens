# v0.4.14 Deployment Summary: Search Filter UX Improvements

## 🎯 What Was Fixed

**Primary Issues**:
1. ❌ "Clear filters" didn't exist - users got stuck with strict filters showing empty results
2. ❌ URL params accidentally enabled filters (e.g., `hideExpired` was default `true`)
3. ❌ Empty state didn't show WHY there were no results (hidden strict filters)
4. ❌ URL bloat - default values included in URL, causing stale params to persist

**Root Causes**:
- No clear way to reset filters to defaults
- URL param parsing was lenient (truthy checks instead of explicit `=== 'true'`)
- Empty state lacked debugging information
- Query string builder didn't omit default values

## 🛠️ Changes in v0.4.14

### A) Clear All Filters Functionality

**File**: `apps/web/src/pages/Search.tsx`

Added `DEFAULT_FILTERS` constant and `clearAllFilters()` function:

```typescript
const DEFAULT_FILTERS = {
  scale: '60d',
  hideExpired: false,
  quarantinedOnly: false,
  riskMin: undefined,
  labels: [],
  categories: { ats: false, bills: false, banks: false, events: false, promotions: false },
  replied: 'all' as const,
  limit: 50,
}

const clearAllFilters = useCallback(() => {
  setFilters(DEFAULT_FILTERS)
  runSearch()
}, [setFilters, runSearch])
```

**Connected to UI**: "Clear all filters" button in empty state

### B) Strict URL Parameter Parsing

**File**: `apps/web/src/pages/Search.tsx` - `initialState` useMemo

**Before** (Lenient):
```typescript
const hideExpired = searchParams.get("hideExpired") !== "0"  // ❌ Truthy by default!
const riskMin = searchParams.get("risk_min") ? Number(...) : undefined  // ❌ No validation
```

**After** (Strict):
```typescript
// Only enable hideExpired if EXPLICITLY set to "true"
const hideExpired = searchParams.get("hideExpired") === "true"

// Only enable quarantinedOnly if EXPLICITLY set to "true"
const quarantinedOnly = searchParams.get("quarantined") === "true"

// Only set riskMin if it's a VALID number
const riskMinRaw = searchParams.get("risk_min")
const riskMin = riskMinRaw !== null ? Number(riskMinRaw) : undefined
const riskMinValid = typeof riskMin === 'number' && Number.isFinite(riskMin) ? riskMin : undefined

// Friendlier default for scale
const scale = searchParams.get("scale") ?? '60d'  // Was '30d', now '60d'
```

### C) Omit Default Values from URL

**File**: `apps/web/src/pages/Search.tsx` - URL sync effect

**Before**:
```typescript
if (!filters.hideExpired) params.set('hideExpired', '0')  // ❌ Always in URL
if (filters.riskMin) params.set('risk_min', ...)  // ❌ Truthy check
```

**After**:
```typescript
// Only set scale if it's NOT the default
if (filters.scale && filters.scale !== '60d') params.set('scale', filters.scale)

// Only set hideExpired if TRUE (default is false)
if (filters.hideExpired) params.set('hideExpired', 'true')

// Only set quarantinedOnly if TRUE (default is false)
if (filters.quarantinedOnly) params.set('quarantined', 'true')

// Only set riskMin if it's a VALID number
if (typeof filters.riskMin === 'number') params.set('risk_min', String(filters.riskMin))
```

**Same logic applied to**: `apps/web/src/hooks/useSearchModel.ts` - `toQueryParams()`

### D) Debug-Friendly Empty State

**File**: `apps/web/src/pages/Search.tsx` - Empty state component

**Before**:
```typescript
<div>No results found</div>
{query && <p>Query: {query}</p>}
```

**After**:
```typescript
<div data-testid="empty-state">
  <h3>No results found</h3>

  {/* Show active filters for debugging */}
  <div className="flex flex-wrap gap-2">
    <span>Query: <code>{query || '(none)'}</code></span>
    {filters.scale !== '60d' && <Badge>Scale: {filters.scale}</Badge>}
    {filters.hideExpired && <Badge>Hide expired</Badge>}
    {filters.quarantinedOnly && <Badge>Quarantined only</Badge>}
    {typeof filters.riskMin === 'number' && <Badge>Risk ≥ {filters.riskMin}</Badge>}
    {filters.labels?.length > 0 && <Badge>Labels: {filters.labels.join(', ')}</Badge>}
    {/* Show active categories */}
  </div>

  {/* Clear button */}
  <Button onClick={clearAllFilters} data-testid="clear-filters-button">
    Clear all filters
  </Button>
</div>
```

### E) Updated Default Values

**File**: `apps/web/src/hooks/useSearchModel.ts`

Changed defaults to be more user-friendly:

```typescript
const DEFAULT_FILTERS: SearchFilters = {
  scale: '60d',           // Was '30d' → now '60d' (wider window)
  hideExpired: false,     // Was true → now false (show everything by default)
  quarantinedOnly: false,
  riskMin: undefined,
  // ... rest unchanged
}
```

### F) E2E Regression Tests

**File**: `apps/web/tests/e2e/search.interactions.spec.ts` (NEW)

Created comprehensive test suite with `@prodSafe` tag:

```typescript
test.describe('@prodSafe search filters', () => {
  test('strict filters can lead to empty, clearing brings results deterministically', ...)
  test('URL params are parsed strictly (no accidental filter enabling)', ...)
  test('clear filters resets to defaults and runs search', ...)
  test('empty state shows active filters for debugging', ...)
  test('omit default values from URL to avoid stale params', ...)
})
```

## 📊 Behavior Changes

### URL Parameter Handling

| Scenario | v0.4.13 (Before) | v0.4.14 (After) |
|----------|------------------|-----------------|
| `/search?q=test` | `hideExpired=true` (implicit) | `hideExpired=false` (default) |
| `/search?q=test&hideExpired=0` | `hideExpired=false` | `hideExpired=false` |
| `/search?q=test&hideExpired=true` | `hideExpired=true` | `hideExpired=true` ✅ |
| `/search?q=test&scale=60d` | URL: `scale=60d` | URL: (omitted, it's default) |
| `/search?q=test&risk_min=abc` | `riskMin=NaN` ❌ | `riskMin=undefined` ✅ |

### Empty State UX

**Before**:
```
🔍
No results found
Try different keywords or adjust your filters.
Query: "Interview"
```

**After**:
```
🔍
No results found
Try different keywords or adjust your filters.

Query: "Interview" | Scale: 30d | Hide expired | Risk ≥ 80 | Quarantined only

[Clear all filters]  ← NEW!
```

### Filter Reset

**Before**:
- No way to clear filters except manually toggling each one
- Users could get "stuck" with strict filters

**After**:
- "Clear all filters" button visible in empty state
- Resets to `DEFAULT_FILTERS` and re-runs search
- Deterministic behavior (always same defaults)

## 🚀 Deployment Status

- **Version**: v0.4.14
- **Bundle**: `index-1761263230887.qmbag40H.js`
- **Deployed**: 2025-10-23 @ 23:48 UTC
- **Cloudflare Cache**: Purged @ 23:48 UTC

## 📝 Testing

### Manual Testing Steps

1. **Test Strict Filters → Clear**:
   ```
   Navigate to: /search?q=Interview&scale=30d&hideExpired=true&risk_min=80&quarantined=true
   Expected: Empty state with all filters shown
   Action: Click "Clear all filters"
   Expected: Filters cleared, URL updated, new search runs
   ```

2. **Test URL Param Strictness**:
   ```
   Navigate to: /search?q=Interview
   Check URL: Should NOT have hideExpired, quarantined, or risk_min params
   Check UI: "Hide expired" button should say "Hide" (not enabled)
   ```

3. **Test Default Omission**:
   ```
   Navigate to: /search?q=Interview&scale=60d&hideExpired=false
   Wait for search to complete
   Check URL: scale and hideExpired should be OMITTED (they're defaults)
   ```

### E2E Tests

Run with:
```bash
pnpm test:e2e --grep "@prodSafe search filters"
```

Expected: All 5 tests pass
- Strict filters → clear → deterministic
- URL parsing is strict
- Clear button works
- Empty state shows filters
- Defaults omitted from URL

## 🎉 User Experience Improvements

### Problem: User Gets Empty Results

**Before**:
```
User: "Why am I not seeing any results?"
→ No indication of active filters
→ No way to reset filters easily
→ Stuck manually toggling each filter
```

**After**:
```
User: "Why am I not seeing any results?"
→ Empty state shows: "Scale: 30d | Hide expired | Risk ≥ 80"
→ "Clear all filters" button visible
→ One click resets everything and re-searches
```

### Problem: Stale URL Parameters

**Before**:
```
URL: /search?q=test&scale=60d&hideExpired=true&quarantined=false&...
→ URL bloat (6 params, some are defaults)
→ Sharing URL re-applies filters unexpectedly
```

**After**:
```
URL: /search?q=test&hideExpired=true
→ Clean URL (only non-default params)
→ Sharing URL is safe (explicit filters only)
```

### Problem: Accidental Filter Enabling

**Before**:
```
Default hideExpired = true
→ Users don't know it's enabled
→ Missing results by default
```

**After**:
```
Default hideExpired = false
→ Show everything by default
→ Users explicitly enable filters
→ URL must have hideExpired=true to enable
```

## 📚 Files Changed

- ✅ `apps/web/src/pages/Search.tsx` - Clear filters, strict parsing, debug empty state
- ✅ `apps/web/src/hooks/useSearchModel.ts` - Updated defaults, omit defaults in query params
- ✅ `apps/web/src/main.tsx` - Updated version banner
- ✅ `apps/web/tests/e2e/search.interactions.spec.ts` - NEW: E2E regression tests
- ✅ `docker-compose.prod.yml` - Updated to v0.4.14

## 🔄 Rollback Plan

If issues occur:
```powershell
# Rollback to v0.4.13
docker-compose -f docker-compose.prod.yml down web
# Edit docker-compose.prod.yml: change v0.4.14 → v0.4.13
docker-compose -f docker-compose.prod.yml up -d web
docker-compose -f docker-compose.prod.yml restart nginx
.\scripts\Purge-CloudflareCache.ps1
```

## ✅ User Action Required

1. **Clear Browser Cache**:
   - Ctrl+Shift+R (Chrome) or Ctrl+F5 (Firefox)
   - Or: Incognito/Private window

2. **Verify Deployment**:
   - Navigate to https://applylens.app/web/search
   - Console should show: `🔍 ApplyLens Web v0.4.14`
   - Try strict filters: `/search?q=Interview&hideExpired=true&risk_min=80`
   - Should see empty state with filter badges
   - Click "Clear all filters" → filters should reset

3. **Test Default Behavior**:
   - Navigate to: https://applylens.app/web/search?q=Interview
   - Check URL after search - should NOT have hideExpired or quarantined params
   - "Hide expired" button should say "Hide" (not "Show")

## 🐛 Known Issues / Edge Cases

None identified. All tests passing.

## 📖 Related Documentation

- API Route Policy: `docs/API_ROUTE_POLICY.md`
- Search Filter Logic: `apps/web/src/pages/Search.tsx` (inline comments)
- E2E Test Coverage: `apps/web/tests/e2e/search.interactions.spec.ts`

---

**Questions?** Check the empty state - it now shows exactly why you're not seeing results! 🎯
