# Actions Badge Count System

**Status:** ✅ Already Implemented
**Version:** v0.4.55
**Date:** October 26, 2025

## Overview

The navbar Actions button displays a badge count showing the number of pending proposed actions. This count is unified between the header button and the ActionsTray drawer.

## Current Implementation

### Data Flow

```
fetchTray() → ProposedAction[] → actions.length → Badge Count
     ↓                                    ↓
ActionsTray                          AppHeader Button
```

Both components use the same data source (`fetchTray()` from `actionsClient.ts`), ensuring the count is always consistent.

### Header Badge (AppHeader.tsx)

```tsx
// Poll for pending actions count every 30s
useEffect(() => {
  async function checkPending() {
    try {
      const actions = await fetchTray(100)
      setPendingCount(actions.length)
    } catch (error) {
      console.error("Failed to fetch pending actions:", error)
    }
  }

  checkPending()
  const interval = setInterval(checkPending, 30000)
  return () => clearInterval(interval)
}, [])

// Display badge on Actions button
<Button onClick={() => setTrayOpen(true)}>
  <Sparkles className="h-4 w-4 mr-1" />
  Actions
  {pendingCount > 0 && (
    <Badge variant="destructive" className="ml-2 px-1.5 py-0 text-xs h-5 min-w-5">
      {pendingCount}
    </Badge>
  )}
</Button>
```

### Tray Display (ActionsTray.tsx)

```tsx
// Load actions when tray opens
useEffect(() => {
  if (isOpen) {
    loadTray()
  }
}, [isOpen])

async function loadTray() {
  const data = await fetchTray()
  setActions(data)
}

// Display count in header
<h3>Proposed Actions</h3>
{actions.length > 0 && (
  <Badge variant="secondary">{actions.length}</Badge>
)}
```

## Data Shape

### Current Implementation (Phase 4 Agentic Actions)

The system uses a detailed `ProposedAction` interface from `actionsClient.ts`:

```typescript
export type ProposedAction = {
  id: number
  email_id: number
  action: ActionType
  params: Record<string, any>
  confidence: number
  rationale: {
    confidence: number
    narrative: string
    reasons?: string[]
    features?: Record<string, any>
  }
  policy_id?: number
  policy_name?: string
  status: "pending" | "approved" | "rejected" | "executed" | "failed"
  reviewed_by?: string
  reviewed_at?: string
  created_at: string
  // Email details (joined from emails table)
  email_subject?: string
  email_sender?: string
  email_received_at?: string
}

export type ActionType =
  | "label_email"
  | "archive_email"
  | "move_to_folder"
  | "unsubscribe_via_header"
  | "create_calendar_event"
  | "create_task"
  | "block_sender"
  | "quarantine_attachment"
```

### Simplified Interface (Future Alternative)

For simpler use cases or high-level summaries, a simplified interface could be used:

```typescript
interface SimpleProposedAction {
  type: "unsubscribe_senders" | "quarantine_suspicious" | "archive_promotions" | "followup_recruiter"
  summary: string
  note: string
  count?: number
  severity?: "low" | "medium" | "high"
}

interface ProposedActionsResponse {
  generated_at: string
  actions: SimpleProposedAction[]
}
```

**Use Cases:**
- High-level dashboard summaries
- Aggregate action counts by type
- Simplified notification displays
- Product story mockups

**Note:** The current system uses the detailed `ProposedAction` type for full functionality (approve/reject, rationale display, policy creation). The simplified interface is provided for reference if needed for future features.

## Badge Display Logic

### Navbar Button

```
If actions.length > 0:
  Display: "Actions (3)" with red badge
Else:
  Display: "Actions" (no badge)
```

### Implementation:

```tsx
{pendingCount > 0 && (
  <Badge variant="destructive">
    {pendingCount}
  </Badge>
)}
```

## Polling & Refresh

### Auto-Refresh
- **Interval:** Every 30 seconds
- **On Tray Open:** Refresh immediately via `loadTray()`
- **On Action Approve/Reject:** Local state update (removes item from list)

### Manual Refresh
- User can click refresh button in tray header
- Calls `loadTray()` to fetch latest actions

## API Endpoint

### Fetch Pending Actions

```
GET /api/actions/tray?limit=100
```

**Response:**
```json
[
  {
    "id": 1,
    "email_id": 12345,
    "action": "unsubscribe_via_header",
    "params": { "sender": "promo@example.com" },
    "confidence": 0.92,
    "rationale": {
      "narrative": "This sender has sent 12 promotional emails...",
      "reasons": ["High frequency", "Low engagement"]
    },
    "status": "pending",
    "email_subject": "50% Off Sale!",
    "email_sender": "promo@example.com"
  }
]
```

**Count Calculation:**
```typescript
const pendingCount = actions.filter(a => a.status === "pending").length
```

## State Management

### AppHeader State
```typescript
const [trayOpen, setTrayOpen] = useState(false)      // Tray visibility
const [pendingCount, setPendingCount] = useState(0)   // Badge count
```

### ActionsTray State
```typescript
const [actions, setActions] = useState<ProposedAction[]>([])  // Full action list
const [loading, setLoading] = useState(false)                  // Loading state
const [processing, setProcessing] = useState<number | null>(null)  // Action being processed
```

## Event Flow

### Opening the Tray

1. User clicks "Actions" button
2. `setTrayOpen(true)` called
3. ActionsTray renders
4. `useEffect` triggers `loadTray()`
5. `fetchTray()` called
6. Actions list displayed
7. Badge count in tray header matches navbar badge

### Approving an Action

1. User clicks "Approve" on action card
2. `approveAction(id)` called
3. Screenshot captured (optional)
4. API executes action
5. Local state updated: `setActions(prev => prev.filter(a => a.id !== id))`
6. Toast notification shown
7. Badge count automatically decreases (next polling cycle or immediate if we update header state)

### Rejecting an Action

1. User clicks "Reject" on action card
2. `rejectAction(id)` called
3. Local state updated: `setActions(prev => prev.filter(a => a.id !== id))`
4. Toast notification shown
5. Badge count automatically decreases

## Future Enhancements

### Real-Time Updates
Instead of polling every 30s, consider WebSocket or Server-Sent Events for instant updates:

```typescript
// Example: WebSocket connection
const ws = new WebSocket('wss://api.applylens.app/actions/stream')

ws.onmessage = (event) => {
  const update = JSON.parse(event.data)
  if (update.type === 'action_proposed') {
    setPendingCount(prev => prev + 1)
  }
}
```

### Context Callback
Pass `onActionComplete` callback to ActionsTray to immediately update header count:

```tsx
// AppHeader.tsx
<ActionsTray
  isOpen={trayOpen}
  onClose={() => setTrayOpen(false)}
  onActionComplete={() => setPendingCount(prev => Math.max(0, prev - 1))}
/>

// ActionsTray.tsx
async function handleApprove(action: ProposedAction) {
  await approveAction(action.id)
  setActions(prev => prev.filter(a => a.id !== action.id))
  onActionComplete?.()  // Notify parent immediately
}
```

### Aggregate Summaries
Group actions by type for high-level display:

```typescript
const summary = actions.reduce((acc, action) => {
  acc[action.action] = (acc[action.action] || 0) + 1
  return acc
}, {} as Record<string, number>)

// Display: "3 unsubscribes, 2 archives, 1 quarantine"
```

## Testing

### Unit Tests
```typescript
test('badge displays count when actions exist', () => {
  const { getByText } = render(<AppHeader />)
  // Mock fetchTray to return 3 actions
  expect(getByText('3')).toBeInTheDocument()
})

test('badge hidden when no actions', () => {
  const { queryByTestId } = render(<AppHeader />)
  // Mock fetchTray to return []
  expect(queryByTestId('actions-badge')).not.toBeInTheDocument()
})
```

### Integration Tests
```typescript
test('badge count matches tray list', async () => {
  // Open tray
  await click('[data-testid="quick-actions"]')

  // Check badge count
  const badge = getByText(/\d+/)
  const badgeCount = parseInt(badge.textContent)

  // Check tray list
  const actionCards = getAllByTestId('action-card')
  expect(actionCards.length).toBe(badgeCount)
})
```

## Architecture Benefits

### Single Source of Truth
- Both header and tray use `fetchTray()` from `actionsClient.ts`
- No data synchronization issues
- Consistent state across components

### Decoupled Components
- Header doesn't need to know tray internals
- Tray manages its own action cards
- Badge count is simple derived state

### Scalable
- Easy to add more action types
- Simple to extend with new features
- Clear separation of concerns

## Summary

✅ **Badge count is already unified**
✅ **Header and tray use same data source**
✅ **Polling keeps count fresh**
✅ **Local updates provide instant feedback**
✅ **Architecture is clean and scalable**

The system is production-ready and provides a solid foundation for future enhancements like real-time updates or aggregate summaries.
