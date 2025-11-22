# TEST PLAN: ThreadViewer Phase 4

**Scope:** Auto-Advance, Batch Selection, Bulk Actions, Progress Footer
**Status:** Ready for manual validation pre-merge

## 1. Components Under Test

**useThreadViewer hook**
- `autoAdvance` state
- `selectedBulkIds` state
- `advanceAfterAction()`
- `toggleBulkSelect()`, `clearBulkSelect()`
- `bulkArchive()`, `bulkMarkSafe()`, `bulkQuarantine()` (stubs)

**ThreadActionBar**
- Bulk mode vs single-thread mode
- Progress counter
- Auto-advance toggle

**Parent pages:**
- Inbox
- Search
- InboxWithActions (Actions page)

**ThreadViewer**
- Prop wiring from page → viewer → action bar

## 2. Test Matrix

### A. Auto-Advance Behavior

**Setup:**
1. Open Inbox.
2. Click the first email to open the ThreadViewer.
3. Confirm ThreadViewer is open and a row is visually "selected".

#### Test A1: Auto-advance ON

1. In the drawer footer, confirm Auto-advance toggle is "on" (green indicator).
2. Press `D` or click "Archive" in the action bar.

**Expected:**
- The currently viewed thread is marked archived in local ThreadViewer state.
- The drawer immediately jumps to the next thread (selected row visually moves).
- The drawer stays open (no flicker).
- Auto-advance toggle stays ON after navigation.

#### Test A2: Auto-advance OFF

1. Click the Auto-advance toggle to turn it off.
   - **Expected:** visually goes from "active" style (green indicator) to "inactive" style (gray/hollow).
2. Press `D` or click "Archive".

**Expected:**
- The current thread is archived locally.
- The drawer does NOT jump to the next thread.
- The same row remains selected.
- **Reactivity:** Confirm you can still manually `ArrowDown`/`ArrowUp` to move.

#### Edge cases:
- **At the last item in the list:**
  - With auto-advance ON, archiving should NOT crash / go out of bounds.
  - It should just remain on the same last thread.

**Pass criteria:**
- No console errors.
- No React state warning loops.
- Toggling auto-advance does not require a reload.

---

### B. Bulk Selection & Bulk Mode

**Setup:**
1. In Inbox (or Actions table), look at each row.
2. There should now be a checkbox on the left of each row.
3. The rest of the row is still clickable to open ThreadViewer.
4. Clicking the checkbox should NOT open the ThreadViewer.

#### Test B1: Selecting multiple

1. Click checkbox on Email A.
   - **Expected:** checkbox becomes checked.
   - **Expected:** no drawer auto-opens.
2. Click checkbox on Email B.
   - **Expected:** now 2 items are selected.
3. Open (or keep open) ThreadViewer for ANY email.
4. Look at the footer (ThreadActionBar).

**Expected:**
- Footer switches to "bulk mode":
  - You should see:
    - `Archive 2 selected`
    - `Mark Safe (2)`
    - `Quarantine 2`
  - The individual per-thread buttons (`Archive` / `Mark Safe` / etc) should be hidden.

#### Test B2: Going back below 2

1. Uncheck one of those boxes (so only 1 is selected).

**Expected:**
- Footer switches back to single-thread mode.
- Shows the normal per-thread buttons:
  - `Mark Safe`
  - `Quarantine` / `Quarantined`
  - `Archive`
  - `Open in Gmail →`

**Pass criteria:**
- Bulk mode and single-thread mode correctly toggle at `bulkCount > 1`.
- No visual overlap between modes.

---

### C. Bulk Action Buttons (stub behavior)

**Setup:**
1. Select 2+ checkboxes again (B1).
2. View footer so it shows bulk actions.

#### Test C1: Bulk Archive

1. Click `Archive X selected`.

**Expected:**
- All checkboxes immediately clear (selection reset).
- Footer drops back to single-thread mode (since now `bulkCount = 0`).
- No crash / no error noise in console.

#### Test C2: Bulk Mark Safe / Bulk Quarantine

1. Re-select 2+ rows.
2. Click `Mark Safe (X)` or `Quarantine X`.

**Expected:**
- Same as above: selection clears, bulk mode exits, no console errors.

**Pass criteria:**
- After any bulk action, `thread.selectedBulkIds.size` goes back to 0.
- No infinite re-render loops.

---

### D. Progress Counter

In the ThreadViewer footer, you should see:
```
0 of N handled
```

Where:
- `N` = total number of rows in the current page (`thread.items.length`)
- `"0 handled"` is currently stubbed

#### Test D1: Visibility

1. Confirm that `"0 of [some number] handled"` renders in:
   - Inbox
   - Search (results view)
   - Actions / InboxWithActions table
2. Confirm it appears in both bulk mode and non-bulk mode.

**Note / TODO:**
Handled count is not wired yet and will always be 0 in this phase. That's expected.

**Pass criteria:**
- Counter renders in all three pages.
- No `NaN`, `undefined`, etc.

---

### E. Keyboard Triage Didn't Regress

Because Phase 4 modified ThreadViewer's props (and ThreadViewer sits in the middle of keyboard triage from Phase 3), we should re-check navigation keys:

1. Open a thread in ThreadViewer.
2. Press `ArrowDown`.
   - **Expected:** moves to next row.
3. Press `ArrowUp`.
   - **Expected:** moves to previous row.
4. Press `Escape`.
   - **Expected:** drawer closes.

**Pass criteria:**
- Still works after Phase 4 changes.
- No duplicate "keydown" listeners firing twice.

---

## 3. Regression Areas to Watch

**Clicking row checkbox should NOT:**
- open ThreadViewer,
- scroll the list unexpectedly,
- or steal focus and break ArrowUp/ArrowDown nav.

**Auto-advance toggle should NOT:**
- reset when you navigate between rows,
- reset when you reopen ThreadViewer in the same session.

**Bulk mode footer should NOT:**
- flicker between modes every render,
- show both sets of actions at once.

---

## 4. Known Limitations (Intentional for Phase 4)

1. **Bulk actions don't call backend yet.** They just clear selection.
2. **handledCount is hardcoded to 0.** We haven't wired `archived`/`quarantined` state into list rows yet.
3. **There's no "Select all" checkbox** in table headers yet.
4. **autoAdvance is not persisted** to localStorage or user prefs yet; it's in-memory per page load.

---

## 5. Acceptance Criteria (Phase 4 is "done" if…)

✅ You can sit in Inbox, open the drawer, select multiple emails, archive them in bulk, and continue working without a full reload.

✅ You can turn auto-advance off if you want to inspect a sensitive thread instead of blazing through.

✅ The action footer reflects your "mode": single-thread or batch.

✅ Keyboard nav Up/Down/Escape/D still works.

✅ No console errors.

---

**That's the test plan. Drop it into the repo and you look very prepared in review.**
