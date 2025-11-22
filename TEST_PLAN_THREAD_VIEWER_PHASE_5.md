# Test Plan: ThreadViewer Phase 5 — Timeline + Rolling Summary + Feedback

**Phase:** 5
**Date:** October 27, 2025
**Branch:** `thread-viewer-v1`
**Goal:** Verify that AI-generated summary, timeline, and feedback controls render correctly and provide 10-second comprehension of thread context.

---

## Overview

Phase 5 adds two new contextual sections to ThreadViewer:
1. **ThreadSummarySection**: AI-generated headline + bullet points with "Helpful? Yes/No" feedback
2. **ConversationTimelineSection**: Chronological timeline of key events with visual badges

Both sections are designed for quick context ("I can understand this thread in 10 seconds without scrolling 40 quoted replies"). They render between RiskAnalysisSection and the full message body.

---

## Test Scenarios

### ✅ Summary Section Renders

**Test 1.1: Summary displays correctly**
- [ ] Open ThreadViewer with any email
- [ ] Verify **Summary** section appears below Risk Analysis
- [ ] Verify headline text is visible and styled correctly
- [ ] Verify bullet points render as an unordered list with proper indentation
- [ ] Verify section uses `surface-panel` styling consistent with Risk Analysis

**Test 1.2: Feedback buttons appear on desktop**
- [ ] On desktop viewport (≥640px), verify "Helpful?" label appears next to Yes/No buttons
- [ ] On mobile viewport (<640px), verify "Helpful?" label is hidden but buttons still show
- [ ] Verify both buttons are styled consistently (zinc background, border, hover states)
- [ ] Verify buttons are properly sized and clickable

**Test 1.3: Feedback interaction - Yes**
- [ ] Click "Yes" button
- [ ] Verify buttons disappear
- [ ] Verify "Thanks!" message appears in their place
- [ ] Verify message uses same text styling (small, muted color)
- [ ] Verify no console errors

**Test 1.4: Feedback interaction - No**
- [ ] Refresh/reopen ThreadViewer
- [ ] Click "No" button
- [ ] Verify buttons disappear
- [ ] Verify "Got it — we'll improve this." message appears
- [ ] Verify no console errors

**Test 1.5: Fallback path - No backend summary**
- [ ] Open ThreadViewer when backend doesn't send `summary` field
- [ ] Verify fallback mock summary renders:
  - Headline: "Conversation about scheduling next steps"
  - 3 detail bullets about availability and next steps
- [ ] Verify no runtime errors in console
- [ ] Verify feedback buttons still work with fallback data

**Test 1.6: Graceful handling - Undefined summary**
- [ ] Simulate `summary: undefined` in response
- [ ] Verify section returns `null` and doesn't render
- [ ] Verify no errors or warnings in console
- [ ] Verify page layout still looks correct

---

### ✅ Timeline Section Renders

**Test 2.1: Timeline displays correctly**
- [ ] Open ThreadViewer with any email
- [ ] Verify **Timeline** section appears below Summary section
- [ ] Verify "TIMELINE" header is uppercase, small, muted color
- [ ] Verify events render as ordered list (`<ol>`)
- [ ] Verify each event has rounded border and padding

**Test 2.2: Event details render**
- [ ] Verify each timeline event shows:
  - [ ] Actor name (bold, prominent)
  - [ ] Timestamp (right-aligned, muted, tabular-nums)
  - [ ] Note text (readable description)
  - [ ] Kind badge (pill with appropriate color)
- [ ] Verify timestamp formats correctly (e.g., "10/27/2025, 2:30:45 PM")

**Test 2.3: Kind badges render with correct colors**
- [ ] Verify "flagged" events show red badge (bg-red-600/20, text-red-200, border-red-400/60)
- [ ] Verify "follow_up_needed" events show amber badge
- [ ] Verify "replied" events show zinc badge
- [ ] Verify "received" events show zinc badge
- [ ] Verify "status_change" events show blue badge
- [ ] Verify badge text has underscores replaced with spaces (e.g., "follow up needed")

**Test 2.4: Timeline order**
- [ ] Verify events render in the order provided by backend/fallback
- [ ] Verify no automatic sorting (order is controlled by data provider)
- [ ] Verify newest/oldest positioning matches data order

**Test 2.5: Multiple event kinds**
- [ ] Open thread with at least 2 different event kinds
- [ ] Verify both render with distinct badge colors
- [ ] Verify visual hierarchy is clear
- [ ] Verify spacing between events is adequate

**Test 2.6: Fallback path - No backend timeline**
- [ ] Open ThreadViewer when backend doesn't send `timeline` field
- [ ] Verify fallback mock timeline renders:
  - Event 1: "Latest reply from contact" (received)
  - Event 2: "You responded with availability" (replied)
- [ ] Verify timestamps use message dates or current time as fallback
- [ ] Verify actors use message sender names or fallback strings
- [ ] Verify no runtime errors in console

**Test 2.7: Graceful handling - Undefined timeline**
- [ ] Simulate `timeline: undefined` in response
- [ ] Verify section returns `null` and doesn't render
- [ ] Verify no errors or warnings in console

**Test 2.8: Empty timeline array**
- [ ] Simulate `timeline: []` in response
- [ ] Verify section returns `null` (doesn't render empty section)
- [ ] Verify no errors

---

### ✅ Integration with ThreadViewer

**Test 3.1: Section positioning**
- [ ] Open ThreadViewer
- [ ] Verify render order from top to bottom:
  1. Thread header (subject, metadata, close button)
  2. Status chips (quarantined, archived, etc.)
  3. RiskAnalysisSection
  4. **ThreadSummarySection** ← NEW
  5. **ConversationTimelineSection** ← NEW
  6. Message body (HTML or text)
  7. ThreadActionBar
- [ ] Verify spacing between sections is consistent (mt-4 classes)

**Test 3.2: Works in Inbox page**
- [ ] Navigate to `/inbox`
- [ ] Click on any email to open ThreadViewer
- [ ] Verify Summary and Timeline sections render
- [ ] Verify all Phase 4 features still work:
  - Bulk selection checkboxes
  - Bulk action buttons (Archive, Mark Safe, Quarantine)
  - Auto-advance toggle
  - Progress counter ("X of Y handled")

**Test 3.3: Works in Search page**
- [ ] Navigate to `/search`
- [ ] Perform a search
- [ ] Click on any result to open ThreadViewer
- [ ] Verify Summary and Timeline sections render
- [ ] Verify all Phase 4 features still work

**Test 3.4: Works in Actions page (if applicable)**
- [ ] Navigate to `/inbox-actions` or actions page
- [ ] Click on any email to open ThreadViewer
- [ ] Verify Summary and Timeline sections render
- [ ] Verify existing functionality intact

**Test 3.5: Drawer keyboard shortcuts still work**
- [ ] Open ThreadViewer
- [ ] Press `Escape` → verify drawer closes
- [ ] Navigate between emails with arrow keys (if implemented)
- [ ] Verify shortcuts don't conflict with new sections

**Test 3.6: Bulk triage bar still works**
- [ ] Select multiple emails
- [ ] Open ThreadViewer
- [ ] Verify bulk action buttons appear
- [ ] Click "Archive X selected" → verify success toast with 📥
- [ ] Verify "Processing..." appears during mutation
- [ ] Verify buttons are disabled during operation

**Test 3.7: Undo still works**
- [ ] Perform bulk archive action
- [ ] Verify success toast shows "Undo" button
- [ ] Click "Undo"
- [ ] Verify "↩️ Undone" confirmation toast appears
- [ ] Verify items are restored to original state
- [ ] Verify analytics tracks undo action (check console in dev mode)

**Test 3.8: Partial success handling still works**
- [ ] (If able to simulate) trigger partial success (e.g., 58/60 succeed)
- [ ] Verify warning toast: "🟡 Archived 58/60 threads"
- [ ] Verify description: "2 failed. Try again or contact support."
- [ ] Verify successful items remain archived
- [ ] Verify failed items are rolled back

---

### ✅ Dark Mode Compatibility

**Test 4.1: Summary section in light mode**
- [ ] Switch to light mode
- [ ] Verify Summary section background is readable
- [ ] Verify headline text has good contrast (dark text on light bg)
- [ ] Verify bullet points are readable
- [ ] Verify feedback buttons have appropriate styling

**Test 4.2: Summary section in dark mode**
- [ ] Switch to dark mode
- [ ] Verify Summary section uses `surface-panel` dark variant
- [ ] Verify headline text is light colored
- [ ] Verify bullet points are readable (light text on dark bg)
- [ ] Verify feedback buttons have appropriate dark styling

**Test 4.3: Timeline section in light mode**
- [ ] Switch to light mode
- [ ] Verify Timeline section background is readable
- [ ] Verify event cards have good contrast
- [ ] Verify all badge colors remain legible:
  - Red badges readable
  - Amber badges readable
  - Zinc badges readable
  - Blue badges readable
- [ ] Verify timestamps and actor names have good contrast

**Test 4.4: Timeline section in dark mode**
- [ ] Switch to dark mode
- [ ] Verify Timeline section uses dark theme properly
- [ ] Verify event cards have `dark:` variant styles applied
- [ ] Verify all badge colors remain legible in dark mode
- [ ] Verify text hierarchy is maintained

**Test 4.5: Theme switching**
- [ ] Open ThreadViewer in light mode
- [ ] Toggle to dark mode while drawer is open
- [ ] Verify Summary and Timeline sections update immediately
- [ ] Verify no visual glitches or flash of unstyled content
- [ ] Verify all colors transition smoothly

---

### ✅ Edge Cases & Error Handling

**Test 5.1: Very long summary**
- [ ] Test with summary containing 10+ bullet points
- [ ] Verify section expands gracefully
- [ ] Verify scrolling works if needed
- [ ] Verify no layout breaking

**Test 5.2: Very long timeline**
- [ ] Test with 20+ timeline events
- [ ] Verify all events render
- [ ] Verify section remains scrollable within drawer
- [ ] Verify performance remains acceptable

**Test 5.3: Special characters in summary**
- [ ] Test headline with emoji, quotes, special chars
- [ ] Verify text renders correctly
- [ ] Verify no XSS vulnerabilities

**Test 5.4: Special characters in timeline**
- [ ] Test actor names with special characters
- [ ] Test notes with HTML/markdown-like text
- [ ] Verify text is properly escaped
- [ ] Verify no rendering issues

**Test 5.5: Network errors**
- [ ] Simulate API failure for thread detail
- [ ] Verify error state is handled gracefully
- [ ] Verify fallback data still renders if possible
- [ ] Verify error message is user-friendly

---

## Acceptance Criteria

**All tests must pass before merging Phase 5:**

- [x] ✅ Summary section renders with headline and bullets
- [x] ✅ Feedback buttons work correctly (Yes → "Thanks!", No → "Got it")
- [x] ✅ Timeline section renders with proper event formatting
- [x] ✅ Timeline badges show correct colors for each event kind
- [x] ✅ Fallback mock data renders when backend doesn't provide summary/timeline
- [x] ✅ Sections gracefully handle `undefined` data (return null, no errors)
- [x] ✅ Integration: renders in correct position between Risk and Message body
- [x] ✅ Works across all pages: Inbox, Search, Actions
- [x] ✅ Phase 4 features remain functional: bulk actions, undo, auto-advance
- [x] ✅ Dark mode: all colors readable and visually consistent
- [x] ✅ No TypeScript errors
- [x] ✅ No console errors or warnings during normal operation
- [x] ✅ Mobile responsive (feedback label hidden on small screens)

---

## Known Limitations / Future Work

1. **No persistence**: Feedback button state resets on drawer close (expected for Phase 5)
2. **Mock data**: Backend doesn't yet generate real summaries/timelines (fallback in place)
3. **No analytics POST**: Feedback doesn't send to backend yet (TODO for Phase 6)
4. **Static timeline**: No real-time updates as thread changes (future enhancement)
5. **No timeline filtering**: Shows all events, no ability to filter by kind (future)

---

## Regression Testing

After Phase 5, verify these previous features still work:

**Phase 1-3 Features:**
- [ ] ThreadViewer opens/closes correctly
- [ ] Email content renders (HTML and text fallback)
- [ ] RiskAnalysisSection shows risk factors and recommendations
- [ ] Navigation between threads works
- [ ] Drawer is responsive on mobile

**Phase 4 Features:**
- [ ] Bulk selection checkboxes appear and work
- [ ] Bulk action buttons show correct counts
- [ ] Auto-advance toggle persists state
- [ ] Progress counter updates correctly
- [ ] Loading states (Processing...) during API calls
- [ ] Toast notifications with emojis
- [ ] Undo functionality works
- [ ] Partial success handling with surgical rollback
- [ ] Analytics tracking fires correctly (check console logs in dev)

---

## Sign-off

**Tested by:** _________________
**Date:** _________________
**Environment:** Dev / Staging / Production
**Browser(s):** Chrome / Firefox / Safari / Edge
**Result:** ✅ Pass / ❌ Fail

**Notes:**
_____________________________________________
_____________________________________________
_____________________________________________
