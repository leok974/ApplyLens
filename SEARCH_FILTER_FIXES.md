# Search Filter Interactivity Fixes

## Summary
This document outlines all fixes applied to restore full interactivity of search filters on the Search page.

## Issues Fixed

### ✅ Fix 1: Backdrop pointer-events control
**File**: `apps/web/src/components/ActionsTray.tsx`

**Problem**: Hidden backdrop div may have blocked clicks even when not visible.

**Solution**: Added explicit `pointer-events-auto` and `aria-hidden={false}` to the backdrop when the tray is open:

```tsx
<div
  className="fixed inset-0 bg-black/50 z-40 pointer-events-auto"
  onClick={onClose}
  aria-hidden={false}
/>
```

**Note**: Radix UI overlays (Dialog, Sheet) already handle this automatically via `data-[state]` attributes.

### ✅ Fix 2: Button type attributes
**Problem**: Buttons without explicit `type="button"` inside forms can default to `type="submit"`, causing unwanted form submissions.

**Files Modified**:
- `apps/web/src/pages/Search.tsx` - "Did you mean" suggestion buttons
- `apps/web/src/components/SearchFilters.tsx` - "Clear all filters" button
- `apps/web/src/components/LabelFilterChips.tsx` - Label filter chips
- `apps/web/src/components/DateRangeControls.tsx` - "Clear dates" button
- `apps/web/src/components/RepliedFilterChips.tsx` - Reply status chips
- `apps/web/src/components/search/SearchControls.tsx` - Category and expired filter buttons
- `apps/web/src/components/search/SecurityFilterControls.tsx` - "Clear filters" button

**Solution**: Added `type="button"` to all interactive buttons that should not trigger form submission:

```tsx
<Button type="button" onClick={handleClick}>
  Filter Label
</Button>
```

### ✅ Fix 3: URL parameter handling
**Status**: Already implemented correctly ✅

The Search page already properly handles URL parameters:
- Filters update `searchParams` via `useSearchParams()` hook
- `useEffect` hooks trigger re-fetch when params change
- URL is kept in sync with filter state using `window.history.replaceState()`

**Key Implementation**:
```tsx
const [searchParams, setSearchParams] = useSearchParams()

// Re-run search when filters change
useEffect(() => {
  if (q.trim()) onSearch()
}, [labels, dates, replied, sort, categories, hideExpired, highRisk, quarantinedOnly])

// Keep URL shareable
useEffect(() => {
  const params = new URLSearchParams()
  params.set('q', q)
  // ... add all filter params
  window.history.replaceState(null, '', `/search?${params.toString()}`)
}, [q, labels, dates, replied, sort, ...])
```

### ✅ Fix 4: Z-index sanity
**Status**: Already properly configured ✅

Z-index hierarchy is correct:
- Header: `z-40` (AppHeader.tsx)
- ActionsTray backdrop: `z-40`
- ActionsTray content: `z-50`
- Dialog/Sheet overlays: `z-50`
- Search page content: default (no z-index issues)

No z-index conflicts that would cause filter blocking.

## Additional Improvements

### 🔍 Diagnostics Script
**File**: `apps/web/public/debug-overlay.js`

A diagnostic script to detect stealth overlays blocking UI interactions. Paste in browser DevTools Console to check for:
- Elements with `pointer-events: auto` but low opacity
- High z-index overlays
- Fixed/absolute positioned elements blocking clicks

**Usage**:
```javascript
// Copy content from debug-overlay.js and paste in DevTools Console
```

### 🧪 E2E Tests
**File**: `apps/web/tests/search.interactions.spec.ts`

Comprehensive Playwright tests to catch regressions:
- Label filter clickability and URL updates
- Category filter interactions
- Replied filter chips
- Date range controls
- Clear all filters functionality
- Security filters
- Stealth overlay detection
- Sort control changes
- No disabled fieldsets blocking filters

**Run Tests**:
```bash
npm run test:e2e -- search.interactions.spec.ts
npm run test:e2e:headed -- search.interactions.spec.ts  # with browser
```

## Verification Checklist

### Manual Testing
- [ ] Navigate to `/search?q=Interview`
- [ ] Click "Interview" label filter → URL updates with `labels=interview`
- [ ] Click "ats" category → URL updates with `cat=ats`
- [ ] Click "Replied" status → URL updates with `replied=true`
- [ ] Set date range → URL updates with `date_from` and `date_to`
- [ ] Toggle security filters → URL updates with `risk_min` or `quarantined`
- [ ] Click "Clear all filters" → filters reset, results refresh
- [ ] Change sort order → URL updates, results re-sort
- [ ] All buttons respond to clicks without delay
- [ ] No visual indication of blocking overlays

### Automated Testing
```bash
# Run filter interaction tests
cd apps/web
npm run test:e2e -- search.interactions.spec.ts

# Run with UI (for debugging)
npm run test:e2e:headed -- search.interactions.spec.ts
```

### Browser DevTools Check
```javascript
// Paste debug-overlay.js content in Console
// Should show:
// ✅ No stealth overlays detected
// ✅ Element properly interactive (pointer-events: auto)
// ✅ No high z-index overlays blocking filters
```

## Deployment Status

**Container**: `leoklemet/applylens-web:latest`
**Status**: ✅ Deployed and healthy
**Deployed**: 2025-10-22 21:30 UTC-4

**Verification**:
```bash
docker ps --filter "name=applylens-web-prod"
# Should show: Up X seconds (healthy)

curl -I http://localhost:5175/
# Should return: 200 OK
```

## Prevention Measures

### Code Review Checklist
When adding new filter components or overlays:

1. **Buttons in Forms**
   - [ ] Explicitly set `type="button"` for non-submit actions
   - [ ] Verify button doesn't trigger form submission

2. **Overlays/Backdrops**
   - [ ] Add `pointer-events-none` when hidden/opacity:0
   - [ ] Add `pointer-events-auto` when visible
   - [ ] Add `aria-hidden` attribute matching visibility

3. **Filter Components**
   - [ ] Updates URL params using `setSearchParams()`
   - [ ] Triggers data fetch on param changes
   - [ ] No disabled fieldsets wrapping interactive elements
   - [ ] Visual-only dimming (no `pointer-events-none` on active filters)

4. **Z-index Management**
   - [ ] Header: `z-40`
   - [ ] Overlays: `z-50`
   - [ ] Content: default or lower
   - [ ] No competing z-index values

### Testing Requirements
- [ ] Add E2E test for new filter component
- [ ] Test filter → URL param → data fetch flow
- [ ] Verify no blocking overlays with debug script
- [ ] Test on multiple viewport sizes

## Related Files

### Modified Files
```
apps/web/src/components/ActionsTray.tsx
apps/web/src/pages/Search.tsx
apps/web/src/components/SearchFilters.tsx
apps/web/src/components/LabelFilterChips.tsx
apps/web/src/components/DateRangeControls.tsx
apps/web/src/components/RepliedFilterChips.tsx
apps/web/src/components/search/SearchControls.tsx
apps/web/src/components/search/SecurityFilterControls.tsx
```

### New Files
```
apps/web/public/debug-overlay.js
apps/web/tests/search.interactions.spec.ts
```

## Commit Message
```
fix(search): restore filter interactivity

- Add pointer-events-auto to ActionsTray backdrop when visible
- Standardize type="button" on all filter buttons to prevent form submission
- Ensure URL params drive search fetch (already working, verified)
- Validate z-index hierarchy (header z-40, overlays z-50)
- Add diagnostics script to detect stealth overlays
- Add comprehensive E2E tests for filter interactions

Fixes:
- Label filters now clickable and update URL params
- Category filters trigger proper API calls
- Security filters toggle without blocking
- Date range and sort controls fully functional
- Clear filters button resets state correctly

Test: npm run test:e2e -- search.interactions.spec.ts
```

## Next Steps

1. **Test on Production**
   - Visit https://applylens.app/web/search?q=Interview
   - Verify all filters are clickable
   - Check URL updates as filters change
   - Confirm results refresh on filter changes

2. **Monitor User Feedback**
   - Track filter click events in analytics
   - Monitor error rates for search API calls
   - Check for any reports of non-responsive filters

3. **Performance Optimization** (if needed)
   - Consider debouncing filter changes to reduce API calls
   - Add loading indicators during filter updates
   - Implement optimistic UI updates

## Documentation

For future reference:
- Filters use controlled components with URL param state
- Search fetch is triggered by `useEffect` on param changes
- All overlays must explicitly set `pointer-events` CSS property
- Buttons in forms must have `type="button"` unless submitting

**Contact**: See git blame for this file for questions
