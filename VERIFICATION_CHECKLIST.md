# Thread Viewer Integration - Verification Checklist

## ✅ Implementation Complete

All scan-style intents now use the unified `_build_thread_cards()` helper in `orchestrator.py`.

## Backend Implementation Status

### Helper Function
- ✅ `_build_thread_cards()` - Lines 1091-1158 in orchestrator.py
- ✅ `_build_thread_summary()` - Lines 1046-1071
- ✅ `_group_emails_by_thread()` - Lines 1073-1083

### Intents Using Helper
- ✅ **followups** (lines 1215-1246)
- ✅ **suspicious** (lines 1179-1213)
- ✅ **interviews** (lines 1248-1280)
- ✅ **unsubscribe** (lines 1282-1333)
- ✅ **clean_promos** (lines 1282-1333, shared with unsubscribe)
- ✅ **bills** (lines 1335-1367)

## Manual Testing Steps

### 1. Start Backend Server

```bash
cd D:\ApplyLens\services\api
python -m uvicorn app.main:app --reload --port 8000
```

### 2. Test Each Intent on /chat

For each button, verify the following:

#### Follow-ups Button

**Zero Results:**
- [ ] Click "Follow-ups"
- [ ] Verify ONE card appears (summary only)
- [ ] Card title: "No Conversations Need Follow-up"
- [ ] Card body: "You're all caught up – I couldn't find anything..."
- [ ] No thread viewer below

**Non-Zero Results:**
- [ ] Click "Follow-ups" (with actual follow-ups)
- [ ] Verify TWO cards appear:
  1. Summary card with count
  2. Thread viewer card with list/detail layout
- [ ] Verify thread viewer shows actual threads
- [ ] Click a thread → detail panel updates

#### Suspicious Emails Button

**Zero Results:**
- [ ] Click "Suspicious"
- [ ] Verify ONE card (summary only)
- [ ] Card body: "You're all caught up..."

**Non-Zero Results:**
- [ ] Click "Suspicious" (with risky emails)
- [ ] Verify TWO cards appear
- [ ] Thread viewer shows suspicious emails
- [ ] Risk scores visible in thread list

#### Unsubscribe Button

**Zero Results:**
- [ ] Click "Unsubscribe"
- [ ] Verify ONE card (summary only)

**Non-Zero Results:**
- [ ] Click "Unsubscribe" (with unopened newsletters)
- [ ] Verify TWO cards appear
- [ ] Summary body: "X newsletters found that haven't been opened in Y days."
- [ ] Thread viewer shows newsletter threads
- [ ] Intent badge shows "unsubscribe"

#### Bills Due Button

**Zero Results:**
- [ ] Click "Bills Due"
- [ ] Verify ONE card (summary only)

**Non-Zero Results:**
- [ ] Click "Bills Due" (with bills)
- [ ] Verify TWO cards appear
- [ ] Summary body: "X bill(s) found..."
- [ ] Thread viewer shows bill threads

#### Clean Promos Button

**Zero Results:**
- [ ] Click "Clean Promos"
- [ ] Verify ONE card (summary only)

**Non-Zero Results:**
- [ ] Click "Clean Promos" (with promos)
- [ ] Verify TWO cards appear
- [ ] Summary body: "X promotional email(s) found..."
- [ ] Thread viewer shows promo threads

#### Find Interviews Button

**Zero Results:**
- [ ] Click "Find Interviews"
- [ ] Verify ONE card (summary only)

**Non-Zero Results:**
- [ ] Click "Find Interviews" (with interviews)
- [ ] Verify TWO cards appear
- [ ] Summary body: "X interview-related email(s) found..."
- [ ] Thread viewer shows interview threads

### 3. Network Tab Verification

For any intent with results:

- [ ] Open DevTools → Network tab
- [ ] Click intent button
- [ ] Find the `/api/agent/run` request
- [ ] Verify response JSON contains:

```json
{
  "cards": [
    {
      "kind": "followups_summary" | "generic_summary",
      "title": "...",
      "body": "...",
      "count": N,
      "time_window_days": X,
      "mode": "preview_only",
      "threads": [],
      "email_ids": []
    },
    {
      "kind": "thread_list",
      "intent": "followups" | "suspicious" | "unsubscribe" | "bills" | "clean_promos" | "interviews",
      "title": "...",
      "time_window_days": X,
      "mode": "normal",
      "threads": [
        {
          "threadId": "...",
          "subject": "...",
          "from": "...",
          "lastMessageAt": "...",
          "snippet": "...",
          ...
        }
      ],
      "meta": {
        "count": N,
        "time_window_days": X
      }
    }
  ]
}
```

### 4. UI Component Verification

- [ ] Thread viewer shows correct intent badge color:
  - suspicious → red
  - followups → yellow
  - bills → blue
  - interviews → purple
  - unsubscribe → orange (if styled)
  - clean_promos → green (if styled)

- [ ] Thread list (left pane):
  - [ ] Shows all threads
  - [ ] First thread auto-selected
  - [ ] Click changes selection
  - [ ] Selected thread highlighted

- [ ] Thread detail (right pane):
  - [ ] Shows selected thread details
  - [ ] Gmail URL link works
  - [ ] Subject, sender, snippet visible

### 5. Edge Cases

- [ ] Test with exactly 1 result (singular "email" not "emails" in body)
- [ ] Test with 11+ results (verify only 10 threads in thread_list card)
- [ ] Test rapid clicking (no race conditions)
- [ ] Test different time windows (7, 30, 60, 90 days)

## Expected Behavior Summary

| Intent | Zero Count | Non-Zero Count |
|--------|-----------|----------------|
| **followups** | 1 card (followups_summary) | 2 cards (summary + thread_list) |
| **suspicious** | 1 card (generic_summary) | 2 cards (summary + thread_list) |
| **unsubscribe** | 1 card (generic_summary) | 2 cards (summary + thread_list) |
| **bills** | 1 card (generic_summary) | 2 cards (summary + thread_list) |
| **clean_promos** | 1 card (generic_summary) | 2 cards (summary + thread_list) |
| **interviews** | 1 card (generic_summary) | 2 cards (summary + thread_list) |

## Automated Tests

Frontend tests (already passing):
```bash
cd D:\ApplyLens\apps\web
npm test -- agentUi.test.ts
```

Result: ✅ 9/9 tests passing

## Known Issues / Future Work

- [ ] E2E tests against production still failing (unrelated to this change)
- [ ] Dynamic DNS resolution in nginx (prevent cache issues)
- [ ] Add intent-specific colors for unsubscribe/clean_promos badges

## Files Modified

### Backend
- `services/api/app/agent/orchestrator.py`
  - Added `_build_thread_cards()` helper
  - Added `_build_thread_summary()` helper
  - Added `_group_emails_by_thread()` helper
  - Updated `_build_cards_from_spec()` for all intents
  - Added `unsubscribe` IntentSpec

- `services/api/app/schemas_agent.py`
  - Added `ThreadSummary` model
  - Added `ThreadListCard` model
  - Updated `AgentCard` to include `intent` field

### Frontend
- `apps/web/src/types/agent.ts`
  - Added `intent?: string` to `AgentCard` interface

- `apps/web/src/components/mail/ThreadListCard.tsx`
  - Updated to read `card.intent` with fallback to `meta.intent`

- `apps/web/src/lib/agentUi.test.ts`
  - Added 3 new tests for thread_list behavior

### Documentation
- `docs/THREAD_LIST_CARD_CONTRACT.md` - Complete contract specification
- `VERIFICATION_CHECKLIST.md` - This file

## Sign-off

- [ ] All intents tested manually
- [ ] Network responses verified
- [ ] Thread viewer UI working correctly
- [ ] Zero-count states verified
- [ ] Automated tests passing
- [ ] Ready for commit/deploy
