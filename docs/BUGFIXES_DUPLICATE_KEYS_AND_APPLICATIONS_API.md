# Bug Fixes: Duplicate Keys & Applications API

**Date**: October 11, 2025  
**Issues Fixed**:

1. React duplicate key warnings in Search.tsx
2. Missing /api/applications endpoint (404 errors)
3. Frontend tolerance for empty API responses

---

## Issue 1: Duplicate Key Warning in Search.tsx

### Problem

React console warning: **"Two children with the same key, null"**

**Root Cause**:

- `.map()` iterations using `key={h.id}` where some documents had `null` or `undefined` ids
- Multiple nested `.map()` calls without stable keys (suggestions, "did you mean", labels)

### Solution

#### A. Main Results List

**Before**:

```tsx
{hits.map(h => {
  return (
    <div key={h.id}>...</div>
  )
})}
```text

**After**:

```tsx
{hits.map((h: any, i: number) => {
  // Ensure unique key even when id is missing/null
  const rawId = h?.id ?? h?._id ?? h?._source?.id ?? null;
  const safeKey = rawId ? String(rawId) : `row-${i}`;
  
  return (
    <div key={safeKey}>...</div>
  )
})}
```text

**Why this works**:

- Checks multiple possible id fields (handles both direct docs and ES hit format)
- Falls back to `row-${index}` when no id exists
- Guarantees uniqueness even with null/undefined ids

#### B. Autocomplete Suggestions

**Before**:

```tsx
{sugs.map((s, i) => (
  <div key={i}>...</div>
))}
```text

**After**:

```tsx
{sugs.map((s: string, i: number) => (
  <div key={`sug-${i}-${s}`}>...</div>
))}
```text

**Why this works**:

- Combines index + text content for stability
- Handles duplicate suggestions (same text appearing twice)
- More descriptive than bare index

#### C. "Did You Mean" Buttons

**Before**:

```tsx
{dym.map((d, i) => (
  <button key={i}>...</button>
))}
```text

**After**:

```tsx
{dym.map((d: string, i: number) => (
  <button key={`dym-${i}-${d}`}>...</button>
))}
```text

#### D. EmailLabels Component

**Before**:

```tsx
{ordered.map((l: string) => (
  <span key={l}>...</span>
))}
```text

**After**:

```tsx
{ordered.map((l: string, idx: number) => (
  <span key={`${l}-${idx}`}>...</span>
))}
```text

**Why this matters**:

- Labels array can contain duplicates
- Same label appearing twice would create duplicate keys
- Index ensures uniqueness

---

## Issue 2: Missing /api/applications Endpoint

### Problem

**Error**: `GET /api/applications → 404 Not Found`

**Symptoms**:

- Tracker page failing to load
- Console errors in frontend
- Empty application list

**Root Cause**:

- Applications router existed (`services/api/app/routers/applications.py`)
- But was never imported or included in `main.py`
- Vite proxy forwarding to API, but endpoint not registered

### Solution

#### Step 1: Import the Router

**File**: `services/api/app/main.py`

**Before**:

```python
from .routers import emails, search, suggest
```text

**After**:

```python
from .routers import emails, search, suggest, applications
```text

#### Step 2: Include the Router

**Before**:

```python
# Include routers
app.include_router(emails.router)
app.include_router(search.router)
app.include_router(suggest.router)
app.include_router(auth_google.router)
```text

**After**:

```python
# Include routers
app.include_router(emails.router)
app.include_router(search.router)
app.include_router(suggest.router)
app.include_router(applications.router, prefix="/api")
app.include_router(auth_google.router)
```text

**Note**: Added `prefix="/api"` to match existing router pattern

### What the Applications Router Provides

**Endpoints now available**:

1. `GET /api/applications/` - List all applications
   - Query params: `status`, `q` (search company/role)

2. `POST /api/applications/` - Create new application
   - Body: `{ company, role, status, source }`

3. `GET /api/applications/{app_id}` - Get single application

4. `PATCH /api/applications/{app_id}` - Update application
   - Body: Partial fields to update

5. `DELETE /api/applications/{app_id}` - Delete application

6. `POST /api/applications/from-email` - Create from Gmail thread
   - Body: `{ thread_id, company?, role?, snippet?, sender?, subject?, body_text?, headers?, source? }`

---

## Issue 3: Frontend Tolerance for Empty Lists

### Problem

**Crash risk**: If API returns `null`, `undefined`, or throws error, frontend could break

**Symptoms**:

- Page crashes when backend is down
- TypeError when iterating over non-array response
- Poor error handling

### Solution

**File**: `apps/web/src/pages/Tracker.tsx`

**Before**:

```tsx
const fetchRows = async () => {
  setLoading(true)
  try {
    const params: any = {}
    if (statusFilter) params.status = statusFilter
    if (search) params.company = search
    const data = await listApplications(params)
    setApplications(data)  // Could be null/undefined!
  } catch (error) {
    console.error('Failed to load applications:', error)
    showToast('Failed to load applications', 'error')
  } finally {
    setLoading(false)
  }
}
```text

**After**:

```tsx
const fetchRows = async () => {
  setLoading(true)
  try {
    const params: any = {}
    if (statusFilter) params.status = statusFilter
    if (search) params.company = search
    const data = await listApplications(params)
    // Ensure we always have an array, even if API returns null/undefined
    setApplications(Array.isArray(data) ? data : [])
  } catch (error) {
    console.error('Failed to load applications:', error)
    showToast('Failed to load applications', 'error')
    // Don't crash the page - set empty array
    setApplications([])
  } finally {
    setLoading(false)
  }
}
```text

**Improvements**:

1. ✅ **Validate response**: `Array.isArray(data) ? data : []`
2. ✅ **Graceful failure**: Set empty array in catch block
3. ✅ **User feedback**: Toast notification shows error
4. ✅ **No crash**: Page remains functional even if API fails

---

## Files Changed

### Frontend Files

1. **apps/web/src/pages/Search.tsx**
   - Fixed main results `.map()` with robust key generation
   - Fixed autocomplete suggestions with `sug-${i}-${s}` keys
   - Fixed "did you mean" buttons with `dym-${i}-${d}` keys

2. **apps/web/src/components/EmailLabels.tsx**
   - Changed from `key={l}` to `key={${l}-${idx}}`
   - Handles duplicate labels in array

3. **apps/web/src/pages/Tracker.tsx**
   - Added `Array.isArray()` validation
   - Set empty array on error
   - Improved error handling

### Backend Files

4. **services/api/app/main.py**
   - Imported `applications` router
   - Included router with `/api` prefix

---

## Testing

### Test 1: Search Results Keys

**Steps**:

1. Open browser console
2. Navigate to `/search`
3. Search for "Interview"
4. Verify no React key warnings

**Expected**: No console warnings about duplicate keys

### Test 2: Applications API

**Steps**:

1. Open browser dev tools → Network tab
2. Navigate to `/tracker`
3. Verify `GET /api/applications` returns 200 OK

**Expected**:

- Status 200
- JSON array response (empty or with demo data)

### Test 3: Empty Response Handling

**Steps**:

1. Stop API container: `docker stop infra-api-1`
2. Navigate to `/tracker`
3. Verify page doesn't crash

**Expected**:

- Error toast appears
- Page shows empty state (not crash)
- "Failed to load applications" message

**Cleanup**:

```bash
docker start infra-api-1
```text

### Test 4: Autocomplete Keys

**Steps**:

1. Navigate to `/search`
2. Type "int" in search box
3. Wait for suggestions to appear
4. Check console for key warnings

**Expected**: No duplicate key warnings

---

## Deployment

### Docker Build

**Command**:

```bash
cd D:\ApplyLens\infra
docker compose up -d --build api web
```text

**Build Time**: 11.5 seconds  
**Status**: ✅ Successful

**Containers**:

- `infra-api-1`: Running on port 8003
- `infra-web-1`: Running on port 5175

### Verification

```bash
docker ps --filter "name=infra-" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```text

**Expected Output**:

```text
NAMES                 STATUS                    PORTS
infra-web-1           Up X seconds              0.0.0.0:5175->5175/tcp
infra-api-1           Up X seconds              0.0.0.0:8003->8003/tcp
...
```text

---

## Best Practices Applied

### 1. Defensive Key Generation

**Pattern**:

```tsx
const rawId = doc?.id ?? doc?._id ?? doc?._source?.id ?? null;
const safeKey = rawId ? String(rawId) : `row-${index}`;
```text

**Benefits**:

- Handles multiple data shapes (direct docs, ES hits)
- Always produces unique key
- Stable across re-renders

### 2. Compound Keys for Duplicates

**Pattern**:

```tsx
{items.map((item, idx) => (
  <div key={`${item.id}-${idx}`}>
))}
```text

**When to use**:

- Arrays can contain duplicates
- Same value appearing multiple times
- Need guaranteed uniqueness

### 3. Array Validation

**Pattern**:

```tsx
const data = await fetchData()
setState(Array.isArray(data) ? data : [])
```text

**Benefits**:

- Prevents TypeErrors on `.map()`, `.filter()`, etc.
- Graceful degradation
- No user-facing crashes

### 4. Error Recovery

**Pattern**:

```tsx
try {
  const data = await riskyOperation()
  setState(data)
} catch (error) {
  console.error('Operation failed:', error)
  setState([])  // Safe default
  showUserFeedback('Something went wrong')
}
```text

**Benefits**:

- User sees error message
- Page remains functional
- Logs help debugging

---

## Related Documentation

- **VIEWPORT_AWARE_PANEL_MODE.md** - Responsive panel implementation
- **SPLIT_PANEL_MODE.md** - Split/overlay panel feature
- **Backend API docs** - Applications router endpoints

---

## Rollback Plan

If issues arise, revert with:

```bash
git revert <commit-hash>
cd D:\ApplyLens\infra
docker compose up -d --build api web
```text

**Or**: Restore from previous container images

---

## Future Improvements

### 1. Centralized Key Generation

**Idea**: Create utility function

```tsx
// utils/keys.ts
export function safeKey(obj: any, index: number, prefix = 'item'): string {
  const rawId = obj?.id ?? obj?._id ?? obj?._source?.id ?? null;
  return rawId ? String(rawId) : `${prefix}-${index}`;
}
```text

**Usage**:

```tsx
{items.map((item, i) => (
  <div key={safeKey(item, i, 'email')}>
))}
```text

### 2. API Response Schema Validation

**Idea**: Use Zod or similar

```tsx
import { z } from 'zod';

const ApplicationSchema = z.object({
  id: z.number(),
  company: z.string(),
  role: z.string(),
  // ...
});

const data = await fetchApplications();
const validated = z.array(ApplicationSchema).parse(data);
```text

**Benefits**:

- Runtime type checking
- Catches API contract changes
- Better error messages

### 3. Global Error Boundary

**Idea**: Catch crashes at root

```tsx
// App.tsx
<ErrorBoundary fallback={<ErrorPage />}>
  <Router>
    {/* app content */}
  </Router>
</ErrorBoundary>
```text

### 4. API Mocking for Development

**Idea**: Mock endpoints when backend is down

```tsx
// lib/api.ts
const DEMO_MODE = import.meta.env.VITE_DEMO_MODE === 'true';

export async function listApplications() {
  if (DEMO_MODE) {
    return DEMO_APPLICATIONS;
  }
  // real fetch...
}
```text

---

**Status**: ✅ All fixes deployed and tested  
**Impact**: High (prevents crashes, fixes console spam)  
**Priority**: Critical (user-facing bugs)  
**Backward Compatible**: Yes
