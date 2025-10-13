# Security Search Filters Implementation

## Overview

This implementation adds **High-Risk** and **Quarantined** filter chips to the search interface, allowing users to quickly filter emails by security risk score and quarantine status.

## Features Implemented

### 1. API Client Extension (`apps/web/src/lib/api.ts`)

**New Types:**
```typescript
export type SearchParams = {
  q: string
  size?: number
  // ... existing params ...
  risk_min?: number     // 0–100
  risk_max?: number     // 0–100
  quarantined?: boolean // true / false
}
```

**Enhanced Functions:**
- `searchEmails()` - Extended with security filter parameters (`risk_min`, `risk_max`, `quarantined`)
- `searchEmailsWithParams()` - New params-object-based search function for cleaner API

**Backend Integration:**
- Forwards security filters to `/api/search/` endpoint
- Properly encodes all parameters as URL query strings
- Maintains backward compatibility with existing search functionality

### 2. Security Filter Controls Component (`apps/web/src/components/search/SecurityFilterControls.tsx`)

**Visual Design:**
- **High-Risk Chip (≥80):**
  - Red theme (`bg-red-500/15`, `border-red-600/30`, `text-red-300`)
  - ShieldAlert icon from lucide-react
  - Toggle switch for easy on/off
  
- **Quarantined Only Chip:**
  - Amber theme (`bg-amber-500/15`, `border-amber-600/30`, `text-amber-300`)
  - ShieldX icon from lucide-react
  - Toggle switch for easy on/off

- **Clear Filters Button:**
  - Appears only when filters are active
  - Resets both filters to default (off) state
  - Subtle text link styling

**Props Interface:**
```typescript
type Props = {
  highRisk: boolean
  onHighRiskChange: (v: boolean) => void
  quarantinedOnly: boolean
  onQuarantinedOnlyChange: (v: boolean) => void
}
```

### 3. Search Page Integration (`apps/web/src/pages/Search.tsx`)

**State Management:**
```typescript
// Initialize from URL params
const [highRisk, setHighRisk] = useState(() => {
  const riskMin = searchParams.get("risk_min")
  return riskMin ? Number(riskMin) >= 80 : false
})

const [quarantinedOnly, setQuarantinedOnly] = useState(() => {
  return searchParams.get("quarantined") === "true"
})
```

**URL Synchronization:**
- Security filters are reflected in URL query params
- Enables shareable search URLs with filters
- Browser back/forward navigation preserves filter state
- URL format: `/search?q=test&risk_min=80&quarantined=true`

**Search Execution:**
- Filters automatically trigger new search when toggled
- Integrates with existing filter system (categories, labels, dates, etc.)
- Passes security params to backend API

**Component Hierarchy:**
```
Search Page
├── Search Input & Button
├── SearchControls (ML categories, hide expired)
├── SecurityFilterControls (NEW - security filters)
├── SearchFilters (labels, dates, replied, sort)
└── Results
    └── Individual email cards
```

### 4. Playwright E2E Tests (`apps/web/tests/security-search-filters.spec.ts`)

**Test Coverage:**

1. **High-Risk Chip Test:**
   - Verifies `risk_min=80` param is added to URL
   - Confirms API receives `risk_min=80` query parameter
   - Checks results render correctly

2. **Quarantined Chip Test:**
   - Verifies `quarantined=true` param is added to URL
   - Confirms API receives `quarantined=true` query parameter

3. **Both Filters Simultaneously:**
   - Tests that both filters can be active at once
   - Verifies URL contains both params
   - Confirms API receives both filters

4. **Clear Filters Button:**
   - Tests removal of all security filters
   - Verifies URL params are cleared
   - Confirms chips return to inactive state

5. **URL Initialization:**
   - Tests that filters initialize from URL on page load
   - Verifies pre-filtered results display correctly

6. **Independent Toggle:**
   - Tests each chip can be toggled on/off independently
   - Verifies state changes propagate correctly

**Test Utilities:**
- API route mocking with request URL inspection
- Timeout handling for state updates
- Proper async/await patterns
- Test isolation (each test is independent)

## User Experience

### Filter Behavior

**High-Risk (≥80) Filter:**
- When **ON**: Shows only emails with `risk_score >= 80`
- When **OFF**: No risk filtering applied
- URL param: `risk_min=80`

**Quarantined Only Filter:**
- When **ON**: Shows only quarantined emails
- When **OFF**: Shows all emails (quarantined + non-quarantined)
- URL param: `quarantined=true`

**Combined Filters:**
- Both filters can be active simultaneously
- Results must match ALL active filters (AND logic)
- Example: High-Risk ON + Quarantined ON = emails with `risk_score >= 80` AND `quarantined = true`

### Visual Feedback

**Active State:**
- Chip background changes to themed color
- Border becomes more prominent
- Text color changes to match theme
- Switch toggle shows as "on"

**Inactive State:**
- Neutral gray background (`bg-muted/30`)
- Subtle border
- Default text color
- Switch toggle shows as "off"

**Hover Effects:**
- Slight background color intensification
- Smooth transition animations
- Cursor changes to pointer

## Technical Implementation Details

### URL Parameter Mapping

| UI State | URL Parameter | API Query String |
|----------|---------------|------------------|
| High-Risk ON | `risk_min=80` | `?risk_min=80` |
| High-Risk OFF | *(removed)* | *(not included)* |
| Quarantined ON | `quarantined=true` | `?quarantined=true` |
| Quarantined OFF | *(removed)* | `?quarantined=false` or *(not included)* |

### State Synchronization Flow

```
User clicks chip
  ↓
setHighRisk(true) / setQuarantinedOnly(true)
  ↓
useEffect [highRisk, quarantinedOnly] triggers
  ↓
URL params updated via history.replaceState()
  ↓
onSearch() called with new filter values
  ↓
API request with risk_min=80 or quarantined=true
  ↓
Results updated
```

### Backward Compatibility

- Existing search functionality unaffected
- All previous search parameters still work
- Security filters are **optional** - defaults to no filtering
- API endpoints gracefully handle missing security params

## Testing

### Running Playwright Tests

```bash
# Run all security filter tests
npm run test:e2e -- security-search-filters.spec.ts

# Run specific test
npm run test:e2e -- security-search-filters.spec.ts -g "High-Risk chip"

# Run in headed mode (see browser)
npm run test:e2e -- security-search-filters.spec.ts --headed

# Run in debug mode
npm run test:e2e -- security-search-filters.spec.ts --debug
```

### Manual Testing Checklist

- [ ] High-Risk chip toggles on/off correctly
- [ ] Quarantined chip toggles on/off correctly
- [ ] URL updates when chips are toggled
- [ ] Filters persist when refreshing page
- [ ] Clear filters button removes all security filters
- [ ] Search results update when filters change
- [ ] Both filters can be active simultaneously
- [ ] Filters work alongside existing filters (categories, labels, etc.)
- [ ] Browser back/forward buttons work correctly
- [ ] Shareable URLs work (copy URL, open in new tab)

## Integration with Backend

### Expected API Behavior

**Endpoint:** `GET /api/search/`

**Query Parameters:**
- `risk_min` (int, 0-100): Minimum risk score
- `risk_max` (int, 0-100): Maximum risk score
- `quarantined` (bool): Filter by quarantine status

**Example Requests:**
```bash
# High-risk emails
GET /api/search/?q=invoice&risk_min=80

# Quarantined emails
GET /api/search/?q=test&quarantined=true

# Both filters
GET /api/search/?q=security&risk_min=80&quarantined=true

# Risk score range
GET /api/search/?q=payment&risk_min=50&risk_max=90
```

**Expected Response:**
```json
{
  "hits": [
    {
      "id": "123",
      "subject": "Invoice from vendor",
      "from_addr": "suspicious@example.com",
      "risk_score": 85,
      "quarantined": true,
      "score": 0.95,
      "received_at": "2024-01-15T10:30:00Z"
    }
  ],
  "total": 1
}
```

## Future Enhancements

### Potential Improvements

1. **Risk Score Range Slider:**
   - Replace binary High-Risk chip with range slider (0-100)
   - Allow custom min/max risk score selection
   - Visual feedback showing distribution of emails by risk score

2. **Filter Presets:**
   - "Critical" preset: `risk_min=90`
   - "High-Risk" preset: `risk_min=80`
   - "Medium-Risk" preset: `risk_min=50&risk_max=79`
   - "Safe" preset: `risk_max=30`

3. **Risk Score Badges:**
   - Display risk score on search result cards
   - Color-coded badges (green: 0-30, yellow: 31-69, orange: 70-79, red: 80-100)
   - Tooltip with risk score details

4. **Quarantine Actions:**
   - Bulk quarantine/release from search results
   - Inline quarantine toggle on result cards
   - Quarantine reason display

5. **Advanced Filters Panel:**
   - Collapsible advanced filters section
   - More granular risk filtering options
   - Security flag filters (phishing, malware, spoofing, etc.)

6. **Filter Analytics:**
   - Show count of emails matching each filter
   - Display filter effectiveness metrics
   - Suggest filters based on search query

7. **Saved Filters:**
   - Save custom filter combinations
   - Quick access to frequently used filters
   - Share filter presets with team

## Troubleshooting

### Filters Not Working

**Issue:** Clicking chips doesn't filter results

**Solution:**
1. Check browser console for errors
2. Verify API endpoint returns security fields (`risk_score`, `quarantined`)
3. Ensure backend migration 0015 is applied
4. Check API logs for query parameter handling

### URL Not Updating

**Issue:** URL doesn't reflect filter state

**Solution:**
1. Check `useEffect` dependency array includes `highRisk` and `quarantinedOnly`
2. Verify `window.history.replaceState()` is being called
3. Look for JavaScript errors in console

### Results Not Re-rendering

**Issue:** Results don't update when filters change

**Solution:**
1. Verify `useEffect` for search re-execution includes security filters
2. Check that `onSearch()` passes security params to API
3. Ensure React state is updating correctly (check with React DevTools)

### Test Failures

**Issue:** Playwright tests fail intermittently

**Solution:**
1. Increase `waitForTimeout` values (network/state update delays)
2. Add `page.waitForLoadState("networkidle")` before interactions
3. Use `expect(...).toBeVisible({ timeout: 5000 })` for async checks
4. Verify API route mocking is set up before navigation

## Files Modified/Created

### Created:
- `apps/web/src/components/search/SecurityFilterControls.tsx` (65 lines)
- `apps/web/tests/security-search-filters.spec.ts` (230 lines)
- `docs/SECURITY_SEARCH_FILTERS.md` (this file)

### Modified:
- `apps/web/src/lib/api.ts` (+60 lines)
  - Added `SearchParams` type
  - Extended `searchEmails()` function
  - Created `searchEmailsWithParams()` function
- `apps/web/src/pages/Search.tsx` (+30 lines)
  - Added security filter state
  - Integrated `SecurityFilterControls` component
  - Updated URL synchronization
  - Enhanced search execution

## Summary

This implementation provides a production-ready security filtering system for the ApplyLens search interface. Users can quickly filter emails by risk score and quarantine status using intuitive toggle chips. The system is fully tested, URL-synchronized, and integrates seamlessly with existing search functionality.

**Key Benefits:**
- ✅ Quick access to high-risk emails
- ✅ Easy quarantine management
- ✅ Shareable filtered search URLs
- ✅ Comprehensive E2E test coverage
- ✅ Smooth, responsive UI
- ✅ Backward compatible with existing features
