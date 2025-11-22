# Card ↔ Thread Viewer UI Polish - Implementation Summary

## Overview
Enhanced the ApplyLens chat UI to display metadata from scan intent cards (followups, unsubscribe, clean_promos, bills, interviews, suspicious) with improved visual clarity and user guidance.

## Changes Implemented

### 1. AgentCard Component (`src/components/AgentCard.tsx`)

#### Added Intent-Specific Subtitles
- **Function**: `getScanSubtitle(card: AgentCard)`
- Maps scan intents to descriptive subtitles:
  - `followups` → "Conversations waiting on your reply"
  - `unsubscribe` → "Newsletters you haven't opened recently"
  - `clean_promos` → "Promotions you may want to archive"
  - `bills` → "Bills and payment reminders from your inbox"
  - `interviews` → "Interview and recruiter threads"
  - `suspicious` → "Emails that might be risky"

#### Added Metadata Pill
- Displays combined count + time window when both are present
- Format: `{count} {item|items} · last {days} days`
- Example: "10 items · last 90 days"
- Styled with low-contrast dark theme (`text-slate-300/80`)
- `data-testid="agent-card-meta-pill"` for testing

#### Visual Layout
```
┌─────────────────────────────────────────────┐
│ [KIND BADGE]    [10 items · last 90 days]   │
│ Card Title                                  │
│ Intent-specific subtitle (if scan intent)   │
│ Card body text...                           │
└─────────────────────────────────────────────┘
```

### 2. ThreadListCard Component (`src/components/mail/ThreadListCard.tsx`)

#### Added Metadata Pill to Header
- Same format as AgentCard: `{count} items · last {days} days`
- Positioned next to card title
- Only renders when both `count` and `time_window_days` exist in `card.meta`

#### Added UX Hint
- Appears below the thread list for scan intents
- Text: "Click a conversation to see details here, or open it in Gmail to reply."
- Styled with `text-slate-400/80` for subtle guidance
- Only renders when `card.kind === 'thread_list'` AND `card.intent` is present

### 3. Comprehensive Test Coverage (`src/tests/AgentCard.test.tsx`)

#### Test Suites
1. **Metadata Pill Tests** (5 tests)
   - ✅ Renders pill with count and time_window_days
   - ✅ Shows "1 item" for singular count
   - ✅ Hides pill when meta is missing
   - ✅ Hides pill when count is missing
   - ✅ Hides pill when time_window_days is missing

2. **Intent Subtitle Tests** (9 tests)
   - ✅ Correct subtitle for each scan intent (followups, unsubscribe, clean_promos, bills, interviews, suspicious)
   - ✅ No subtitle for generic intent
   - ✅ No subtitle when intent is unspecified
   - ✅ Infers intent from kind when intent field is missing

3. **Combined Features Tests** (3 tests)
   - ✅ Renders both pill and subtitle together
   - ✅ Renders card title and body correctly
   - ✅ Renders kind label badge

#### Total: 17 tests, all passing

### 4. ThreadListCard Test Enhancements (`src/tests/ThreadListCard.test.tsx`)

#### New Tests Added (7 tests)
- ✅ Renders metadata pill when count and time_window_days are present
- ✅ Shows "1 item" for singular count
- ✅ Hides pill when count is missing
- ✅ Hides pill when time_window_days is missing
- ✅ Renders UX hint for thread_list cards with intent
- ✅ Hides UX hint when intent is missing

#### Total: 15 tests, all passing

## Verification Checklist

### UI Components
- ✅ Metadata pills render on summary cards
- ✅ Metadata pills render on thread_list cards
- ✅ Intent-specific subtitles display correctly
- ✅ UX hint appears on thread_list cards
- ✅ Dark-first Banana theme preserved (no bright backgrounds)

### Data-TestId Attributes
- ✅ `agent-card-meta-pill` - Metadata pill
- ✅ `agent-card-subtitle` - Intent subtitle
- ✅ `thread-card` - Thread list card wrapper
- ✅ `thread-list` - Thread list container
- ✅ `thread-row` - Individual thread row
- ✅ `thread-viewer` - Thread viewer component
- ✅ `message-card` - Message cards in thread viewer

### Thread Selection
- ✅ `data-thread-id` attribute on each row
- ✅ `data-selected="true"/"false"` on rows
- ✅ `aria-selected` for accessibility
- ✅ Clicking thread updates selection (no agent re-run)

### Backend Contract
- ✅ No backend changes required
- ✅ Uses existing `card.meta.count` field
- ✅ Uses existing `card.meta.time_window_days` field
- ✅ Uses existing `card.intent` field
- ✅ Compatible with all scan intents

## Test Results

```bash
pnpm -C apps/web vitest run src/tests/AgentCard.test.tsx
# ✓ 17 tests passed

pnpm -C apps/web vitest run src/tests/ThreadListCard.test.tsx
# ✓ 15 tests passed

# Total: 32 tests passed
```

## Dark Theme Compliance

All new UI elements follow the Banana theme's dark-first design:
- Pill text: `text-slate-300/80` (low contrast)
- Subtitle text: `text-slate-300/80` (low contrast)
- UX hint text: `text-slate-400/80` (very subtle)
- No bright backgrounds or legacy blue buttons

## Files Modified

1. `apps/web/src/components/AgentCard.tsx` - Added subtitles and metadata pill
2. `apps/web/src/components/mail/ThreadListCard.tsx` - Added metadata pill and UX hint
3. `apps/web/src/tests/AgentCard.test.tsx` - New test file (17 tests)
4. `apps/web/src/tests/ThreadListCard.test.tsx` - Enhanced with 7 new tests

## Future Work (Optional E2E Testing)

Note for future enhancement:
```typescript
// apps/web/tests/e2e/chat-card-metadata.spec.ts
test('scan card shows same count in answer and pill', async ({ page }) => {
  // 1. Log into /chat
  // 2. Click Follow-ups toolbar button (data-testid="mailtool-followups")
  // 3. Extract count from LLM answer text
  // 4. Extract count from pill (data-testid="agent-card-meta-pill")
  // 5. Assert they match
});
```

## Summary

All requirements implemented and tested:
- ✅ Count + time window pill on scan cards
- ✅ Intent-specific subtitles for scan cards
- ✅ ThreadViewer ↔ ThreadList wiring verified
- ✅ UX hint on thread_list cards
- ✅ 32 Vitest unit tests (all passing)
- ✅ Dark-first theme preserved
- ✅ No backend changes
