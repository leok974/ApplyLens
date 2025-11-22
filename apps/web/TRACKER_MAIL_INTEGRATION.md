# Tracker Mail Integration

This document describes the mailbox integration features in the Tracker page, including filtering and metrics.

## Features

### 1. "From Mailbox" Filter

**Purpose**: Allows users to quickly see applications that came from email threads (linked to the Mail / thread viewer).

**Implementation**:
- Filter chip button in the Tracker toolbar
- When enabled: Shows only applications with a `thread_id` field
- When disabled: Shows all applications (default behavior)
- Works in combination with other filters (status, search, etc.)

**UI Elements**:
- Button with Mail icon and "From Mailbox" label
- Yellow accent color when active
- Checkmark indicator when enabled
- `data-testid="filter-from-mailbox"` for testing

**Code Location**:
- Component: `src/pages/Tracker.tsx`
- Tests: `src/tests/Tracker.mailboxFilter.test.tsx`

### 2. "Needs Follow-up" Filter

**Purpose**: Shows applications that likely need follow-up action based on their status and email linkage.

**Heuristic**:
An application needs follow-up if it meets BOTH criteria:
1. Has a linked email thread (`thread_id` is present)
2. Is in an early-stage status:
   - `applied` - Recently submitted
   - `hr_screen` - HR screening in progress
   - `interview` - Interview scheduled or in progress

Applications in later stages (`offer`, `rejected`, `on_hold`, `ghosted`) are excluded from this filter, as they typically don't require immediate follow-up.

**Note**: This is a client-side heuristic for quick filtering. The backend's Followups agent uses more sophisticated logic based on message direction and timestamps to determine which threads truly need replies.

**Implementation**:
- Filter chip button in the Tracker toolbar
- Cyan accent color when active
- Works independently or in combination with "From Mailbox" filter
- Helper text shown when filter is active

**UI Elements**:
- Button with chat bubble icon and "Needs follow-up" label
- Cyan accent color when active
- Checkmark indicator when enabled
- `data-testid="filter-needs-followup"` for testing

**Code Location**:
- Component: `src/pages/Tracker.tsx`
- Helper function: `src/lib/trackerFilters.ts`
- Tests: `src/tests/Tracker.needsFollowup.test.tsx`

### 3. Tracker Summary Tile

**Purpose**: Provides a quick overview of application metrics at the top of the Tracker page.

**Metrics Displayed**:
1. **Total Applications**: Count of all applications currently loaded (respects status/search filters)
2. **From Mailbox**: Count of applications with linked email threads
3. **Needs Follow-up**: Count of applications matching the follow-up heuristic

**Implementation**:
- Computed client-side from the loaded application data
- No additional API calls required
- Automatically updates when filters change
- Hidden when loading or when there are no applications

**UI Elements**:
- Three-column grid layout
- Color-coded metrics:
  - Total: Neutral zinc color
  - From Mailbox: Yellow (matches filter accent)
  - Needs Follow-up: Cyan (matches filter accent)
- `data-testid="tracker-summary-tile"` for testing

**Code Location**:
- Component: `src/pages/Tracker.tsx`
- Tests: `src/tests/Tracker.metricsTile.test.tsx`

## Filter Combination Behavior

Both filters work independently and can be combined:

- **Neither filter active**: Shows all applications
- **Only "From Mailbox"**: Shows applications with `thread_id`
- **Only "Needs follow-up"**: Shows applications with `thread_id` AND early-stage status
- **Both filters active**: Shows applications with `thread_id` AND early-stage status (same as "Needs follow-up" alone)

## Type Safety

All filter logic uses TypeScript for type safety:

```typescript
// Application type
type AppOut = {
  id: number
  company: string
  role?: string
  status: AppStatus
  thread_id?: string  // Link to email thread
  // ... other fields
}

// Status type
type AppStatus =
  | "applied"
  | "hr_screen"
  | "interview"
  | "offer"
  | "rejected"
  | "on_hold"
  | "ghosted"
```

## Helper Functions

**Location**: `src/lib/trackerFilters.ts`

### `needsFollowup(app: AppOut): boolean`
Determines if an application likely needs follow-up based on thread presence and status.

### `isFromMailbox(app: AppOut): boolean`
Checks if an application is linked to a mailbox thread.

### `applyTrackerFilters(applications, filters): AppOut[]`
Applies multiple filters to an application list in a composable way.

## Testing

All features are covered by comprehensive unit tests using Vitest and React Testing Library:

- **mailboxFilter.test.tsx**: 10 tests covering filter on/off, toggling, styling, edge cases
- **needsFollowup.test.tsx**: 10 tests covering filter behavior, status filtering, combination with other filters
- **metricsTile.test.tsx**: 13 tests covering metrics display, edge cases, styling

Run tests with:
```bash
pnpm vitest run src/tests/Tracker
```

## Future Enhancements

Potential improvements for future iterations:

1. **Server-side filtering**: Add API support for filtering by `thread_id` to reduce client-side data transfer
2. **Advanced follow-up detection**: Integrate with backend's message direction logic for more accurate "needs follow-up" detection
3. **Persistent filter state**: Save filter preferences in localStorage or user settings
4. **Badge counts**: Show counts in filter button labels (e.g., "From Mailbox (23)")
5. **Quick actions**: Add "Mark as followed up" or "Dismiss follow-up" actions from the Tracker
6. **Integration with agent**: Link to Followups agent view for mail-linked applications
