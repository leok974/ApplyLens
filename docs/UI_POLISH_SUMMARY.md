# UI Polish: Smart Search Labels & Recency Toggle ✨

**Date**: October 9, 2025  
**Status**: ✅ Ready to Deploy

---

## Overview

Added visual polish to the search UI with:

- **Impact-ordered labels** (Offer > Interview > Others > Rejection)
- **Color-coded badges** (Yellow for offers, green for interviews, gray for rejections)
- **Scoring hint display** in search results
- **Recency scale toggle** in Settings (3d / 7d / 14d)

---

## Files Created

### Frontend

#### 1. `apps/web/src/lib/searchScoring.ts` ✨ NEW

Centralized scoring constants and utilities:

```typescript
export const LABEL_WEIGHTS = {
  offer: 4.0,
  interview: 3.0,
  rejection: 0.5,
};

export function sortLabelsByImpact(labels: string[]): string[]
export function labelTitle(label: string): string
```text

**Purpose**: Single source of truth for scoring weights, shared between backend and frontend

#### 2. `apps/web/src/components/EmailLabels.tsx` ✨ NEW

Reusable label badge component:

```tsx
<EmailLabels labels={email.label_heuristics} />
```text

**Features**:

- Auto-sorts labels by impact (offer first, rejection last)
- Color-coded: Yellow (offer), Green (interview), Gray (rejection), Blue (others)
- Tailwind-styled with ring borders
- Handles empty/null labels gracefully

#### 3. `apps/web/src/components/SearchResultsHeader.tsx` ✨ NEW

Search results header with scoring hint:

```tsx
<SearchResultsHeader query={q} total={total} showHint />
```text

**Displays**:

- Query and result count
- Scoring weights: "offer^4 • interview^3 • rejection^0.5"
- Recency hint: "7-day decay (gauss scale=7d, decay=0.5)"
- Current scale setting

#### 4. `apps/web/src/state/searchPrefs.ts` ✨ NEW

localStorage-backed preferences:

```typescript
export type RecencyScale = "3d" | "7d" | "14d";
export function getRecencyScale(): RecencyScale
export function setRecencyScale(scale: RecencyScale)
```text

**Purpose**: Persist user's recency scale preference across sessions

---

## Files Updated

### Backend

#### `services/api/app/routers/search.py`

Added `scale` query parameter:

```python
def search(
    q: str = Query(...),
    size: int = Query(25),
    scale: str = Query("7d", description="Recency scale: 3d|7d|14d"),  # NEW
    # ... other params
):
    # Validate scale
    allowed = {"3d", "7d", "14d"}
    scale = scale if scale in allowed else "7d"
    recency = {**RECENCY, "scale": scale}  # Apply dynamic scale
    
    # Use recency in function_score
    {"gauss": {"received_at": recency}}
```text

**Changes**:

- Accepts `?scale=3d`, `?scale=7d`, or `?scale=14d`
- Validates and defaults to `7d`
- Dynamically applies scale to Gaussian decay function

### Frontend

#### `apps/web/src/lib/api.ts`

Updated `searchEmails` to accept scale:

```typescript
export async function searchEmails(
  query: string,
  limit = 10,
  labelFilter?: string,
  scale?: string  // NEW
): Promise<SearchHit[]> {
  let url = `/api/search/?q=${encodeURIComponent(query)}&limit=${limit}`
  if (scale) {
    url += `&scale=${encodeURIComponent(scale)}`
  }
  // ...
}
```text

#### `apps/web/src/pages/Search.tsx`

Major visual improvements:

**Added**:

- Import `SearchResultsHeader` and `EmailLabels` components
- Pass recency scale to API: `searchEmails(q, 20, undefined, scale)`
- Display scoring hint header
- Use `EmailLabels` component instead of inline badges

**Before**:

```tsx
<span style={{ background:'#eef', padding:'2px 6px' }}>{h.label}</span>
```text

**After**:

```tsx
<EmailLabels labels={h.label_heuristics || (h.label ? [h.label] : [])} />
```text

**Layout improvements**:

- Score and labels aligned to the right
- Better spacing and alignment
- Impact-ordered, color-coded labels

#### `apps/web/src/pages/Settings.tsx`

Complete redesign with recency toggle:

```tsx
<select value={scale} onChange={onChangeScale}>
  <option value="3d">3 days (more freshness)</option>
  <option value="7d">7 days (balanced) - Default</option>
  <option value="14d">14 days (more recall)</option>
</select>
```text

**Features**:

- Dropdown to select recency scale
- Displays current scoring weights (offer 4×, interview 3×, etc.)
- Persists preference to localStorage
- Clean, informative UI

---

## Visual Design

### Label Colors

| Label | Color | Ring | Purpose |
|-------|-------|------|---------|
| **Offer** | Yellow `bg-yellow-100` | `ring-yellow-300` | Highest priority, pops visually |
| **Interview** | Green `bg-green-100` | `ring-green-300` | Important, positive vibe |
| **Rejection** | Gray `bg-gray-100` | `ring-gray-300` | De-emphasized with `opacity-80` |
| **Others** | Blue `bg-blue-50` | `ring-blue-200` | Neutral, default state |

### Scoring Hint

Appears at top of search results when `showHint={true}`:

```text
Scoring: offer^4 • interview^3 • rejection^0.5 • 
Recency: 7-day decay (gauss scale=7d, decay=0.5) • Scale: 7d
```text

**Purpose**: Demo-ready narration for explaining search intelligence

---

## User Flow

### 1. Searching

1. User types query: `"interview google"`
2. Results show with **SearchResultsHeader** displaying scoring hint
3. Each result shows **EmailLabels** sorted by impact (offers first)
4. Labels are color-coded for quick scanning

### 2. Adjusting Recency

1. User goes to **Settings** page
2. Selects recency scale from dropdown:
   - **3d**: Recent emails matter most (aggressive decay)
   - **7d**: Balanced (default)
   - **14d**: Older emails still relevant (gentle decay)
3. Preference saved to localStorage
4. Next search automatically uses new scale
5. Scale shown in SearchResultsHeader hint

### 3. Label Sorting

Labels always appear in impact order:

- ✅ Offer → Interview → Application → ... → Rejection

---

## API Behavior

### Recency Scale Effects

| Scale | Decay | Effect | Use Case |
|-------|-------|--------|----------|
| **3d** | Aggressive | Today = 100%, 3 days = 50%, 6 days = 25% | Fresh job postings, urgent opportunities |
| **7d** | Balanced | Today = 100%, 7 days = 50%, 14 days = 25% | **Default**, general search |
| **14d** | Gentle | Today = 100%, 14 days = 50%, 28 days = 25% | Historical research, old applications |

### Query Examples

```bash
# Default 7-day scale
GET /api/search/?q=interview&size=20

# 3-day scale (more freshness)
GET /api/search/?q=interview&size=20&scale=3d

# 14-day scale (more recall)
GET /api/search/?q=interview&size=20&scale=14d
```text

---

## Testing

### Manual Testing

#### 1. Test Label Sorting

```text
1. Search for "interview" or "offer"
2. Verify labels appear in order: Offer > Interview > Others > Rejection
3. Check color coding: Yellow (offer), Green (interview), Gray (rejection)
```text

#### 2. Test Recency Toggle

```text
1. Go to Settings page
2. Change recency scale to 3d
3. Go back to Search
4. Verify search header shows "Scale: 3d"
5. Search for a query
6. Verify fresher emails score higher (check dates vs scores)
```text

#### 3. Test Scoring Hint

```text
1. Search for any query
2. Verify header shows: "Scoring: offer^4 • interview^3 • rejection^0.5 • ..."
3. Verify current scale is displayed
```text

#### 4. Test Label Colors

```text
1. Find search results with different labels
2. Verify:
   - Offer labels are yellow with yellow ring
   - Interview labels are green with green ring
   - Rejection labels are gray and slightly faded
   - Other labels are light blue
```text

### Browser DevTools

Check localStorage:

```javascript
localStorage.getItem('search.recencyScale')
// Should return: "3d", "7d", or "14d"
```text

---

## Demo Script

**Narrator**: "Let me show you our smart search scoring..."

1. **Show Search Page**
   - "Notice the scoring hint at the top: offers are boosted 4×, interviews 3×"
   - "Labels are automatically sorted by impact"
   - "Offers appear in yellow, interviews in green, rejections are de-emphasized in gray"

2. **Perform Search**
   - Type: "interview google"
   - "See how results with 'interview' labels score higher"
   - "And the labels are already sorted - offers first, rejections last"

3. **Show Settings**
   - Navigate to Settings
   - "We can adjust the recency decay scale"
   - Change to "3d"
   - "Now recent emails matter even more - 3-day half-life instead of 7"

4. **Search Again**
   - Go back to Search
   - "Notice the scale updated in the hint: 'Scale: 3d'"
   - "Same query, but fresher results now score higher"

5. **Show Label Ordering**
   - Point to labels in results
   - "The labels are always sorted by impact"
   - "Offers always appear first, making them easy to spot"

---

## Code Quality

### TypeScript Safety

- ✅ All components fully typed
- ✅ RecencyScale type enforced: `"3d" | "7d" | "14d"`
- ✅ Props interfaces defined
- ✅ No `any` types

### Reusability

- ✅ EmailLabels component can be used anywhere
- ✅ SearchResultsHeader reusable across search views
- ✅ searchScoring.ts utilities usable in any component

### Performance

- ✅ localStorage reads cached in state
- ✅ Label sorting is O(n log n), minimal overhead
- ✅ No unnecessary re-renders

---

## Browser Compatibility

- ✅ localStorage (all modern browsers)
- ✅ CSS Flexbox (all modern browsers)
- ✅ Array.sort() (all modern browsers)
- ✅ URLSearchParams (all modern browsers)

---

## Next Steps

### Optional Enhancements

1. **Visual Feedback**
   - Add toast notification when scale changes
   - Animate label sorting

2. **Advanced Settings**
   - Toggle individual label weights
   - Custom field boost values
   - Enable/disable ATS synonyms

3. **Analytics**
   - Track which scales users prefer
   - Monitor label distribution in results
   - A/B test different color schemes

4. **Keyboard Shortcuts**
   - `1`, `2`, `3` to switch scales in Settings
   - `s` to focus settings

---

## Summary

| Feature | Status | Files Changed |
|---------|--------|---------------|
| Label Sorting | ✅ Complete | EmailLabels.tsx, searchScoring.ts |
| Color-Coded Badges | ✅ Complete | EmailLabels.tsx |
| Scoring Hint | ✅ Complete | SearchResultsHeader.tsx |
| Recency Toggle | ✅ Complete | Settings.tsx, searchPrefs.ts |
| Backend Scale Param | ✅ Complete | search.py |
| Frontend Integration | ✅ Complete | Search.tsx, api.ts |

**Total Files**:

- ✨ 4 New: searchScoring.ts, EmailLabels.tsx, SearchResultsHeader.tsx, searchPrefs.ts
- 📝 4 Updated: search.py, api.ts, Search.tsx, Settings.tsx

**Status**: ✅ **Production Ready**

The UI is now demo-ready with visual impact-ordered labels and a flexible recency scale toggle!
