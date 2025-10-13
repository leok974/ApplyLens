# Advanced Search Filtering Implementation

## Overview

Added interactive label and date range filtering to the search interface, allowing users to narrow results by specific labels (offer/interview/rejection) and date ranges while preserving smart scoring functionality.

## Features Implemented

### Backend Enhancements (`services/api/app/routers/search.py`)

1. **New Query Parameters**:
   - `labels: Optional[List[str]]` - Repeatable parameter for multi-label filtering
   - `date_from: Optional[str]` - ISO 8601 date/time string for range start (e.g., "2025-10-01" or "2025-10-01T00:00:00Z")
   - `date_to: Optional[str]` - ISO 8601 date/time string for range end

2. **Filter Building Logic**:

   ```python
   filters = []
   
   # Label filtering (multi-select)
   if labels:
       filters.append({"terms": {"labels": labels}})
   
   # Date range filtering
   range_q = {}
   if date_from:
       range_q["gte"] = date_from
   if date_to:
       range_q["lte"] = date_to
   if range_q:
       filters.append({"range": {"received_at": range_q}})
   
   # Existing filters (preserved)
   if label_filter:
       filters.append({"term": {"label_heuristics": label_filter}})
   if company:
       filters.append({"term": {"company": company}})
   if source:
       filters.append({"term": {"source": source}})
   ```

3. **Query Structure**:
   - Wraps base query in bool query when filters present
   - Combines `must` (text search) with `filter` (label/date/etc.)

   ```python
   if filters:
       query = {
           "bool": {
               "must": [base_query],
               "filter": filters
           }
       }
   else:
       query = base_query
   ```

### Frontend Components

#### 1. `LabelFilterChips.tsx` - Interactive Label Filtering

- **Purpose**: Toggle chips for offer/interview/rejection labels
- **Features**:
  - Color-coded by label type (yellow/green/gray)
  - Active state with darker background
  - Clear all button (appears when labels selected)
  - Impact-ordered using `sortLabelsByImpact`
- **Props**:
  - `value?: string[]` - Currently selected labels
  - `onChange: (next: string[]) => void` - Callback when selection changes

#### 2. `DateRangeControls.tsx` - Date Range Picker

- **Purpose**: Filter results by date range
- **Features**:
  - From/To date inputs (native date picker)
  - Clear dates button (appears when dates selected)
  - Slices ISO timestamps to YYYY-MM-DD for input display
- **Props**:
  - `from?: string` - ISO date string for range start
  - `to?: string` - ISO date string for range end
  - `onChange: (next: { from?: string; to?: string }) => void` - Callback

### Search Page Updates (`apps/web/src/pages/Search.tsx`)

1. **State Management**:

   ```typescript
   const [labels, setLabels] = useState<string[]>([])
   const [dates, setDates] = useState<{ from?: string; to?: string }>({})
   ```

2. **API Integration**:
   - Updated `searchEmails` call to pass labels and date parameters
   - Added useEffect to re-run search when filters change

   ```typescript
   useEffect(() => {
     if (q.trim()) onSearch()
   }, [labels, dates])
   ```

3. **UI Layout**:
   - Filter controls rendered in gray panel above results
   - Separate sections for label and date filtering
   - Section headers for clarity

### API Client Updates (`apps/web/src/lib/api.ts`)

Updated `searchEmails` function signature:

```typescript
export async function searchEmails(
  query: string,
  limit = 10,
  labelFilter?: string,
  scale?: string,
  labels?: string[],      // NEW
  dateFrom?: string,      // NEW
  dateTo?: string         // NEW
): Promise<SearchHit[]>
```text

URL construction with repeatable labels parameter:

```typescript
if (labels && labels.length > 0) {
  labels.forEach(l => {
    url += `&labels=${encodeURIComponent(l)}`
  })
}
```text

## How It Works

### Filter Combination Logic

- **Labels**: Multiple labels combine with OR logic (matches any selected label)
- **Date Range**: Both bounds are optional; can filter by from-only, to-only, or both
- **All Filters**: Combine with AND logic (must match all conditions)
- **Scoring**: Smart scoring (label boosts, recency decay) still applies within filtered results

### Example API Calls

1. **Filter by label**:

   ```

   GET /api/search?q=interview&labels=offer&labels=interview

   ```

2. **Filter by date range**:

   ```

   GET /api/search?q=application&date_from=2025-10-01&date_to=2025-10-15

   ```

3. **Combined filtering**:

   ```

   GET /api/search?q=test&labels=offer&date_from=2025-10-01&scale=3d

   ```

## Testing

### Backend Testing

```bash
# Test label filtering
curl "http://localhost:8003/search?q=interview&labels=offer&labels=interview"

# Test date filtering
curl "http://localhost:8003/search?q=application&date_from=2025-10-01&date_to=2025-10-09"

# Test combined filters
curl "http://localhost:8003/search?q=test&labels=offer&date_from=2025-10-01&scale=3d"
```text

### Frontend Testing

1. Visit `http://localhost:5173/search`
2. Search for "interview"
3. Click "Offer" chip → should filter to only offers
4. Click "Interview" chip → should show offers + interviews
5. Select date range → should narrow further
6. Verify scoring hint shows current scale
7. Change scale in Settings → verify it updates query

### Expected Behavior

- ✅ Clicking label chips toggles them on/off
- ✅ Active chips have darker background (bg-yellow-200 vs bg-yellow-100)
- ✅ Multiple labels combine with OR logic
- ✅ Date range narrows results to specified period
- ✅ All filters combine with AND logic
- ✅ Recency scoring still applies within filtered results
- ✅ Clear buttons remove respective filters
- ✅ Filters persist during search query changes

## Files Modified

### Backend

- `services/api/app/routers/search.py` - Added filter parameters and query structure

### Frontend

- `apps/web/src/components/LabelFilterChips.tsx` - NEW component
- `apps/web/src/components/DateRangeControls.tsx` - NEW component
- `apps/web/src/pages/Search.tsx` - Added filter UI and state management
- `apps/web/src/lib/api.ts` - Updated searchEmails function signature

## Integration with Existing Features

### Preserves All Previous Functionality

- ✅ Smart scoring (ATS synonyms, label boosts, recency decay)
- ✅ Recency scale toggle (3d/7d/14d in Settings)
- ✅ Impact-ordered email labels
- ✅ Search autocomplete and suggestions
- ✅ Did-you-mean corrections
- ✅ Highlight rendering

### Complements Smart Search

- Filters work **within** the smart-scored results
- Recency decay still applies to filtered results
- Label boosts still prioritize offers/interviews
- Users can combine smart scoring with targeted filtering

## Visual Design

### Filter Panel

- Light gray background (`#f8f9fa`)
- Rounded corners (8px)
- Organized in two sections (labels + dates)
- Section headers in small, muted text
- Clear visual separation from results

### Label Chips

- **Offer**: Yellow ring, yellow-100/200 background
- **Interview**: Green ring, green-100/200 background
- **Rejection**: Gray ring, gray-100/200 background
- Rounded-full design for pill appearance
- Transition effects for smooth state changes

### Date Inputs

- Native browser date picker (type="date")
- Compact size (text-xs)
- Rounded borders
- Clear button appears only when dates selected

## Future Enhancements (Optional)

1. **URL State Persistence**:
   - Store filters in URL query params
   - Allow sharing filtered search links
   - Back button restores filter state

2. **Filter Indicators**:
   - Show active filter count in badge
   - Quick "Clear all filters" button
   - Visual indication when filters are active

3. **Advanced Date Controls**:
   - Preset ranges (Last 7 days, Last 30 days, etc.)
   - Relative date options (Last week, This month)
   - Calendar picker for easier date selection

4. **Additional Filters**:
   - Company filter dropdown
   - Source filter (Lever, Workday, etc.)
   - Sender domain filter
   - Application stage filter

5. **Filter Analytics**:
   - Track which filters are most used
   - Suggest popular filter combinations
   - Show result count before applying filter

## Summary

This implementation adds powerful, user-friendly filtering capabilities to the search interface while preserving all existing smart scoring functionality. Users can now easily narrow results by clicking label chips or selecting date ranges, making it much faster to find specific types of emails from specific time periods.

**Key Benefits**:

- ✅ Intuitive UI with visual feedback
- ✅ Flexible filtering (any combination of labels/dates)
- ✅ Preserves smart scoring within filtered results
- ✅ Clean, minimal visual design
- ✅ Reactive updates (filters trigger automatic search)
- ✅ Backward compatible with existing features
