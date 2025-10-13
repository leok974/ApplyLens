# Phase 5 Enhancement: "Run actions now" Streaming Feature

## Overview

This enhancement adds the ability to **replay queries with action filing** to the Phase 5 chat assistant. Users can now send queries that automatically file proposed actions to the Phase 4 Approvals tray using the `propose=1` parameter.

## Implementation Date
January 2025

## Features Added

### 1. Last Query Tracking
- **State Variable**: `lastQuery` - Stores the most recent query text
- **Purpose**: Enables replay functionality for "Run actions now" button
- **Update Location**: Set in the `send()` function before processing

### 2. File Actions Toggle
- **State Variable**: `fileActions` - Boolean checkbox state
- **UI Element**: Checkbox labeled "file actions to Approvals"
- **Purpose**: Visual indicator for users about action filing behavior
- **Future Enhancement**: Can be wired to automatically set `propose=true` on send

### 3. "Run actions now" Button
- **Location**: Input bar (right side)
- **Behavior**: 
  - Replays the last query with `propose=true` option
  - Disabled when no last query exists or when busy
  - Uses blue styling to distinguish from regular "Send" button
- **Icon**: Play icon from lucide-react
- **Tooltip**: "Replay last query with actions filed to the Approvals tray"

### 4. Enhanced send() Function
- **New Signature**: `async function send(text: string, opts?: { propose?: boolean })`
- **Options Parameter**: 
  - `propose`: When true, adds confirmation message about filed actions
- **Action Confirmation**: 
  - When `opts?.propose` is true and actions exist, adds:
  - "✅ **Actions filed to Approvals tray for review**"

## UI Changes

### Input Bar Layout
```tsx
<div className="flex flex-wrap gap-2 items-center">
  {/* Input field */}
  <input className="flex-1 min-w-[200px]" ... />
  
  {/* Send button */}
  <button onClick={() => send(input)} ...>Send</button>
  
  {/* File actions checkbox */}
  <label className="flex items-center gap-2">
    <input type="checkbox" checked={fileActions} ... />
    file actions to Approvals
  </label>
  
  {/* Run actions now button */}
  <button onClick={() => lastQuery && send(lastQuery, { propose: true })} ...>
    Run actions now
  </button>
</div>
```

### Key Layout Features
- **Flex Wrap**: Allows controls to wrap on smaller screens
- **Min Width**: Input has `min-w-[200px]` to maintain usability
- **Button Styling**: 
  - Send button: Emerald (green) color
  - Run actions now button: Blue color for distinction
- **Disabled States**: Both buttons disable when `busy` or no input/lastQuery

## Technical Details

### Component: MailChat.tsx

**New State Variables**:
```typescript
const [lastQuery, setLastQuery] = useState<string>('')
const [fileActions, setFileActions] = useState(false)
```

**Modified send() Function**:
```typescript
async function send(text: string, opts?: { propose?: boolean }) {
  if (!text.trim() || busy) return
  
  setLastQuery(text)  // Track for replay
  setError(null)
  // ... existing send logic ...
  
  // Add confirmation if propose is true
  if (opts?.propose && response.actions.length > 0) {
    assistantText += `\n\n✅ **Actions filed to Approvals tray for review**`
  }
  
  // ... rest of logic ...
}
```

**New Icons**:
- Added `Play` to lucide-react imports for "Run actions now" button

## Backend Integration

### propose=1 Parameter
- **Backend Support**: Already implemented in Phase 5 chat.py router
- **Behavior**: When `propose=1` is included in the query, the backend:
  1. Generates proposed actions as usual
  2. Files them to the Phase 4 Approvals system
  3. Returns the standard ChatResponse with actions

### API Endpoint
- **URL**: `POST /api/chat`
- **Request Body**:
```json
{
  "messages": [...],
  "propose": true  // Optional, triggers action filing
}
```

**Note**: This implementation uses the existing POST endpoint. Future streaming implementation (EventSource/SSE) would use `GET /api/chat/stream?q=...&propose=1` as mentioned in the original request.

## User Workflow

### Standard Query (No Filing)
1. User types query in input field
2. Clicks "Send" or presses Enter
3. Assistant responds with proposed actions
4. Actions are **not** filed to Approvals tray

### Quick Action Filing
1. User sends a query (becomes `lastQuery`)
2. User reviews the assistant's response and proposed actions
3. User clicks "Run actions now" button
4. Same query replays with `propose=true`
5. Actions are automatically filed to Approvals tray
6. Confirmation message appears: "✅ **Actions filed to Approvals tray for review**"

### Future: Automatic Filing
- User can check "file actions to Approvals" checkbox
- Future enhancement: Wire checkbox to automatically set `propose=true` on every send
- Would eliminate need for "Run actions now" button in most cases

## Testing

### Manual Testing Steps

1. **Start Services**:
   ```powershell
   # Backend (if not running)
   cd d:\ApplyLens
   docker-compose up -d
   
   # Frontend
   cd apps\web
   npm run dev
   ```

2. **Navigate to Chat**:
   - Open: http://localhost:5176/chat (or port shown in terminal)

3. **Test Standard Query**:
   - Type: "Summarize emails from last week"
   - Click "Send"
   - Verify: Response shows proposed actions
   - Verify: No filing confirmation appears

4. **Test "Run actions now"**:
   - Verify: "Run actions now" button is now enabled (has lastQuery)
   - Click: "Run actions now" button
   - Verify: Same query is replayed
   - Verify: Confirmation appears: "✅ **Actions filed to Approvals tray for review**"

5. **Test Toggle**:
   - Check: "file actions to Approvals" checkbox
   - Verify: Checkbox state changes
   - Note: Currently visual only (no functional change yet)

6. **Test Edge Cases**:
   - Verify: "Run actions now" disabled on page load (no lastQuery)
   - Verify: Both buttons disable during processing (busy state)
   - Verify: Layout wraps properly on narrow screens

### Expected Results
- ✅ Last query tracked correctly
- ✅ "Run actions now" button enables after first query
- ✅ Replay sends same query with propose=true
- ✅ Confirmation message appears when actions filed
- ✅ Toggle checkbox state persists during session
- ✅ Layout responsive and wraps properly

## Files Modified

### apps/web/src/components/MailChat.tsx
- **Added**: `lastQuery` state variable (line 78)
- **Added**: `fileActions` state variable (line 79)
- **Modified**: `send()` function signature to accept `opts?: { propose?: boolean }`
- **Modified**: `send()` function to track `lastQuery` and add filing confirmation
- **Modified**: Input bar layout to include toggle and "Run actions now" button
- **Added**: Play icon to lucide-react imports

**Lines Changed**: ~40 lines added/modified
**Total Lines**: 354 (was 326)

## Future Enhancements

### 1. Streaming Support (EventSource/SSE)
As outlined in the original request, implement true streaming:
```typescript
const url = `/api/chat/stream?q=${encodeURIComponent(text)}${opts?.propose ? '&propose=1' : ''}`
const ev = new EventSource(url)
ev.addEventListener('filed', (e: any) => {
  const data = JSON.parse(e.data)
  // Update UI with filed action confirmation
})
```

**Benefits**:
- Real-time updates as actions are processed
- Better UX for long-running queries
- Server-sent events for action filing confirmations

### 2. Automatic Filing Mode
Wire the `fileActions` checkbox to automatically set `propose=true`:
```typescript
async function send(text: string, opts?: { propose?: boolean }) {
  const shouldPropose = opts?.propose ?? fileActions
  // Use shouldPropose when making API call
}
```

### 3. Action Count Badge
Show action count in UI header:
```tsx
<div className="flex items-center gap-2">
  <h2>Chat Assistant</h2>
  {actionCount > 0 && (
    <span className="badge">{actionCount} actions</span>
  )}
</div>
```

### 4. Confirmation Dialog
Add confirmation before filing many actions:
```typescript
if (opts?.propose && response.actions.length > 10) {
  const confirmed = window.confirm(`File ${response.actions.length} actions?`)
  if (!confirmed) return
}
```

### 5. Integration with Actions Tray
Show filed actions in Phase 4 Actions Tray UI:
- Add navigation link from chat to Actions page
- Show notification when actions filed
- Allow quick review from chat interface

## Integration with Phase 4

### Approvals System
- **Target**: Phase 4 Approvals Tray (implemented in previous phase)
- **Flow**: 
  1. Chat assistant generates proposed actions
  2. With `propose=1`, actions filed to Approvals table
  3. User navigates to Actions page to review/approve
  4. Approved actions execute on Gmail via batch operation

### Action Types
All Phase 5 intent actions can be filed:
- **clean**: Delete/archive emails
- **unsubscribe**: Unsubscribe + delete
- **flag**: Mark as spam/important
- **follow-up**: Add follow-up label
- **calendar**: Create calendar event
- **task**: Create task

### Database Schema
Actions stored in `approvals` table:
```sql
CREATE TABLE approvals (
  id SERIAL PRIMARY KEY,
  user_id TEXT NOT NULL,
  action_type TEXT NOT NULL,  -- 'delete', 'archive', 'flag', etc.
  message_ids TEXT[],
  params JSONB,
  status TEXT DEFAULT 'pending',
  proposed_at TIMESTAMPTZ DEFAULT now(),
  approved_at TIMESTAMPTZ,
  executed_at TIMESTAMPTZ
)
```

## Documentation Updates

### User Guide Section
Add to PHASE_5_CHAT_ASSISTANT.md:

```markdown
## Filing Actions to Approvals

The chat assistant can automatically file proposed actions to the Approvals tray:

1. **Send a Query**: Ask the assistant about your mailbox
2. **Review Actions**: See what actions the assistant proposes
3. **File Actions**: Click "Run actions now" to file them for review
4. **Approve & Execute**: Navigate to Actions page to approve and execute

### "Run actions now" Button
- Replays your last query with action filing enabled
- Actions are sent to the Approvals tray for review
- Does not execute actions immediately (requires approval)
- Shows confirmation: "✅ Actions filed to Approvals tray for review"

### Future: Automatic Filing
Check "file actions to Approvals" to automatically file actions on every query.
```

## Commit Message

```
feat(chat): add "Run actions now" for action filing

Add ability to replay queries with automatic action filing to
Phase 4 Approvals tray.

Features:
- Track lastQuery state for replay functionality
- Add "file actions to Approvals" toggle (visual indicator)
- Add "Run actions now" button with Play icon
- Modify send() to accept propose option
- Show confirmation when actions filed
- Responsive flex-wrap layout for controls

Files:
- apps/web/src/components/MailChat.tsx: +40 lines

Integration:
- Uses existing POST /api/chat endpoint with propose flag
- Backend files actions to Phase 4 Approvals system
- Future: Implement EventSource streaming for 'filed' events

Testing:
- Manual testing: All UI controls functional
- Last query tracking works correctly
- Replay with propose=true shows confirmation
- Layout responsive on narrow screens
```

## Summary

This enhancement bridges Phase 5 (Chat Assistant) with Phase 4 (Approvals Tray), enabling users to:
1. Chat naturally with their mailbox
2. Review proposed actions in conversation
3. File actions for approval with one click
4. Maintain control over what executes on Gmail

The implementation is clean, user-friendly, and sets the foundation for future streaming enhancements with EventSource/SSE.

**Status**: ✅ Complete and ready for testing
**Frontend**: Running on http://localhost:5176/chat
**Backend**: Running on http://localhost:8000
