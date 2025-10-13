# UI Quick Fixes - Applied ✅

**Date**: October 11, 2025

## Fixes Applied

### 1. React Router v7 Future Flags ✅

**File**: `apps/web/src/main.tsx`

Added future flags to silence React Router deprecation warnings:

```tsx
<BrowserRouter
  future={{
    v7_startTransition: true,
    v7_relativeSplatPath: true,
  }}
>
```text

This opts into React Router v7 behavior now, preventing console warnings.

---

### 2. Favicon Fix ✅

**Files**:

- `apps/web/public/favicon.svg` (created)
- `apps/web/index.html` (updated)

Created a simple SVG favicon with the 📬 emoji on a purple gradient background.

Added to HTML:

```html
<link rel="icon" type="image/svg+xml" href="/favicon.svg" />
```text

This fixes the 404 error for favicon.ico in the browser console.

---

### 3. Safe Date Formatting ✅

**File**: `apps/web/src/lib/date.ts` (created)

Created utility functions to safely format dates and avoid showing "1969/1970" for invalid dates:

```typescript
export function safeFormatDate(iso?: string | null): string | null
export function relativeTime(iso?: string | null): string | null
```text

Features:

- Returns `null` for invalid/missing dates (renders as "—")
- Avoids epoch-0 timestamps (1969/1970)
- Guards against NaN and invalid date strings
- Provides relative time formatting (e.g., "2h ago", "3d ago")

**Updated Components**:

- `EmailCard.tsx` - Email received dates
- `Search.tsx` - Search result dates
- `InboxWithActions.tsx` - Inbox table dates

---

## Testing

After restarting the web container:

```bash
cd infra
docker compose restart web
```text

Expected results:

1. ✅ No React Router warnings in console
2. ✅ No favicon 404 errors
3. ✅ Dates display properly (no "Dec 31, 1969" or "Jan 1, 1970")
4. ✅ Missing/invalid dates show as "—"

---

## Browser Experience

Open <http://localhost:5175/> and verify:

1. **Console is clean** - No deprecation warnings or errors
2. **Favicon appears** - Purple mailbox icon in browser tab
3. **Dates render correctly** - All email timestamps show actual dates or "—"
4. **No epoch dates** - No 1969/1970 dates visible

---

## Files Changed

```text
apps/web/
├── index.html                           # Added favicon link
├── src/
│   ├── main.tsx                         # Added React Router future flags
│   ├── lib/
│   │   └── date.ts                      # NEW: Safe date utilities
│   ├── components/
│   │   ├── EmailCard.tsx                # Use safeFormatDate()
│   │   └── InboxWithActions.tsx         # Use safeFormatDate()
│   └── pages/
│       └── Search.tsx                   # Use safeFormatDate()
└── public/
    └── favicon.svg                      # NEW: SVG favicon
```text

---

## Next Steps

Optional enhancements:

1. **Use relative time in some places**:

   ```tsx
   import { relativeTime } from '../lib/date'
   
   <span>{relativeTime(email.received_at) ?? 'Unknown'}</span>
   // Shows: "2h ago", "3d ago", etc.
   ```

2. **Customize date format**:

   ```tsx
   const shortFormat = new Intl.DateTimeFormat('en-US', {
     month: 'short',
     day: 'numeric',
     hour: 'numeric',
     minute: 'numeric'
   })
   
   safeFormatDate(date, shortFormat)
   ```

3. **Add tooltip with full timestamp**:

   ```tsx
   <span title={email.received_at}>
     {relativeTime(email.received_at)}
   </span>
   ```
