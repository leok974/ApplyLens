# Thread Viewer E2E Test Suite - Complete Coverage

## Overview

This document describes the comprehensive E2E test suite for the Thread Viewer feature, covering all phases (1-5) of development. These tests validate the complete user experience from inbox navigation through thread viewing, keyboard triage, bulk operations, and feedback collection.

## Test Files

### 1. `thread-viewer-basic-context.spec.ts`
**Purpose**: Validates core layout and data presence (Phases 1, 2, 5)
**Production Safe**: ✅ Yes (read-only, no mutations)

**What it tests:**
- Thread viewer opens when clicking inbox row
- Risk Analysis section renders with risk level badge
- Thread Summary section renders with headline and bullet points
- Conversation Timeline section renders with event history
- Thread Action Bar renders with all single-thread action buttons
- Auto-advance toggle and progress meter are visible
- Correct rendering order: Risk → Summary → Timeline → Body → Actions

**Test data requirements:**
- At least 1 email in inbox with:
  - Risk analysis data (risk_level field)
  - Summary data (headline + details array)
  - Timeline data (at least 1 event)

---

### 2. `thread-viewer-triage-navigation.spec.ts`
**Purpose**: Validates keyboard navigation shortcuts (Phase 3)
**Production Safe**: ✅ Mostly (D key archives but with optimistic UI)

**What it tests:**
- ArrowUp/ArrowDown cycle through threads without closing viewer
- Selection state updates correctly (data-selected attribute)
- "D" key triggers archive + auto-advance to next thread
- Escape key closes the thread viewer
- Keyboard shortcuts work while viewer is open

**Test data requirements:**
- At least 2 emails in inbox (to test navigation between threads)

**Production considerations:**
- The "D" key test archives an email (state mutation)
- Can be skipped in prod with: `test.skip(process.env.PROD === "1")`
- Or accept that one email will be archived per test run

---

### 3. `thread-viewer-bulk-mode.spec.ts`
**Purpose**: Validates bulk operations and optimistic UI (Phase 4, 4.5, 4.6, 4.7)
**Production Safe**: ❌ No (mutates state by archiving/quarantining)

**What it tests:**
- Multi-select via checkboxes
- Bulk action buttons appear when 2+ emails selected
- Bulk Archive/Mark Safe/Quarantine buttons work
- Progress meter updates correctly
- Auto-advance toggle is interactive
- Optimistic toast notifications appear
- Undo functionality works (if implemented)
- Partial failure handling (some succeed, some fail)

**Test data requirements:**
- At least 3 emails in inbox for bulk selection

**Production considerations:**
- **SKIP THIS TEST IN PRODUCTION** - it will mutate real data
- Use `test.skip(process.env.PROD === "1")` guard
- Or run against staging/dev environment with `ALLOW_ACTION_MUTATIONS=true`

---

### 4. `thread-viewer-summary-feedback.spec.ts`
**Purpose**: Validates feedback loop for AI summaries (Phase 5.1)
**Production Safe**: ✅ Yes (feedback endpoint just logs, doesn't mutate email state)

**What it tests:**
- Feedback controls render (Yes/No buttons)
- Clicking "Yes" shows optimistic acknowledgment ("Thanks!")
- Clicking triggers analytics event
- Toast notification appears
- Feedback controls disappear after submission
- Viewer remains stable (doesn't crash on feedback)
- Network failures handled gracefully

**Test data requirements:**
- At least 1 email with summary data

**API endpoint used:**
- `POST /api/actions/summary-feedback` (Phase 5.2 implementation)

---

## Required Data-testid Attributes

All components have been updated with the following test IDs:

### Inbox/List Components
```tsx
// Inbox row
<div
  data-testid="thread-row"
  data-thread-id={thread.id}
  data-selected="true|false"
>
  <input type="checkbox" data-testid="thread-row-checkbox" />
</div>
```

### Thread Viewer
```tsx
<aside data-testid="thread-viewer">
  {/* Risk section */}
  <section data-testid="risk-analysis-section" />

  {/* Summary section */}
  <section data-testid="thread-summary-section">
    <p data-testid="thread-summary-headline" />
    <ul data-testid="thread-summary-details">
      <li>Bullet points...</li>
    </ul>

    {/* Feedback controls */}
    <div data-testid="summary-feedback-controls">
      <button data-testid="summary-feedback-yes">Yes</button>
      <button data-testid="summary-feedback-no">No</button>
    </div>
    <div data-testid="summary-feedback-ack">Thanks!</div>
  </section>

  {/* Timeline section */}
  <section data-testid="conversation-timeline-section">
    <li data-testid="timeline-event" />
  </section>

  {/* Action bar */}
  <footer data-testid="thread-action-bar">
    {/* Single-thread actions */}
    <button data-testid="action-archive-single">Archive</button>
    <button data-testid="action-mark-safe-single">Mark Safe</button>
    <button data-testid="action-quarantine-single">Quarantine</button>
    <button data-testid="action-open-gmail">Open in Gmail</button>

    {/* Bulk actions (when 2+ selected) */}
    <button data-testid="action-archive-bulk">Archive Selected</button>
    <button data-testid="action-mark-safe-bulk">Mark Safe Selected</button>
    <button data-testid="action-quarantine-bulk">Quarantine Selected</button>

    {/* Status indicators */}
    <div data-testid="handled-progress">X of Y handled</div>
    <label data-testid="auto-advance-toggle">
      <input type="checkbox" />
      Auto-advance
    </label>
  </footer>
</aside>
```

### Toast Notifications
```tsx
<div data-testid="toast-container">
  {/* Sonner toast messages */}
</div>
```

---

## Running the Tests

### All Tests (Development)
```bash
npx playwright test
```

### Only Thread Viewer Tests
```bash
npx playwright test tests/e2e/thread-viewer-*.spec.ts
```

### Production-Safe Tests Only
```bash
# Set environment variable to skip destructive tests
$env:PROD="1"
npx playwright test tests/e2e/thread-viewer-*.spec.ts
```

### Individual Test Files
```bash
npx playwright test tests/e2e/thread-viewer-basic-context.spec.ts
npx playwright test tests/e2e/thread-viewer-triage-navigation.spec.ts
npx playwright test tests/e2e/thread-viewer-bulk-mode.spec.ts --grep-invert "bulk select"  # skip mutating test
npx playwright test tests/e2e/thread-viewer-summary-feedback.spec.ts
```

### With UI Mode (Debug)
```bash
npx playwright test --ui
```

---

## Test Data Setup

### Option 1: Manual Setup (Fastest for Local Dev)
1. Start dev server: `npm run dev`
2. Navigate to `http://localhost:5173`
3. Connect Gmail account
4. Click "Sync Emails" button
5. Wait for emails to sync
6. Run tests: `npx playwright test`

### Option 2: Test Fixtures (Best for CI)
Create mock data in `tests/fixtures/inbox-data.ts`:

```typescript
export const mockEmails = [
  {
    id: "1",
    subject: "Test Interview Request",
    from_email: "recruiter@example.com",
    from_name: "Jane Recruiter",
    to_email: "candidate@example.com",
    received_at: "2025-01-15T10:30:00Z",
    risk_level: "low",
    category: "interview",
    summary: {
      headline: "Interview request for Senior Engineer role",
      details: [
        "Hiring manager wants to schedule 30-min phone screen",
        "Three time slots offered: Jan 20-22",
        "Next step: Reply with availability"
      ]
    },
    timeline: [
      {
        actor: "recruiter@example.com",
        ts: "2025-01-15T10:30:00Z",
        note: "Initial interview request sent",
        kind: "received"
      }
    ]
  },
  // Add 2-3 more emails for navigation/bulk tests
];
```

Then update tests to seed data before each test run.

### Option 3: Skip Data-Dependent Tests
Add to beginning of test files:
```typescript
test.skip(!hasTestData, "Requires test data - run manual setup first");
```

---

## Playwright Configuration

### Current Setup
See `playwright.config.ts`:
- Chromium browser (can extend to Firefox/Safari)
- Retries: 2 on CI, 0 locally
- Timeout: 30 seconds per test
- Screenshots on failure
- Video on first retry
- Trace on first retry

### Production Gating
Add to `playwright.config.ts`:
```typescript
const isProd = process.env.PROD === "1";

export default defineConfig({
  testDir: "tests/e2e",
  grepInvert: isProd ? /bulk-mode/ : undefined, // skip mutating tests
  // ... rest of config
});
```

---

## Test Coverage Matrix

| Phase | Feature | Test File | Prod Safe | Status |
|-------|---------|-----------|-----------|--------|
| 1 | Risk Analysis Display | basic-context | ✅ | ✅ |
| 2 | Inline Action Bar | basic-context | ✅ | ✅ |
| 3 | Keyboard Triage | triage-navigation | ⚠️ | ✅ |
| 4 | Bulk Mode UI | bulk-mode | ❌ | ✅ |
| 4.5 | Optimistic Bulk Actions | bulk-mode | ❌ | ✅ |
| 4.6 | Undo Functionality | bulk-mode | ❌ | ✅ |
| 4.7 | Partial Failure Handling | bulk-mode | ❌ | ✅ |
| 5 | Summary + Timeline | basic-context | ✅ | ✅ |
| 5.1 | Summary Feedback | summary-feedback | ✅ | ✅ |

Legend:
- ✅ Prod Safe: No state mutations
- ⚠️ Partially Safe: Minor mutations (can skip specific assertions)
- ❌ Not Safe: Mutates production data

---

## Debugging Failed Tests

### Common Issues

**1. "Element not found" errors**
- **Cause**: Test data missing (empty inbox)
- **Fix**: Run manual setup (Option 1) or create fixtures (Option 2)

**2. Timeout waiting for toast**
- **Cause**: Network slow or backend down
- **Fix**: Check backend is running, increase timeout in test

**3. "data-selected not updating"**
- **Cause**: React state update race condition
- **Fix**: Add `await page.waitForTimeout(100)` after keyboard events

**4. Bulk buttons not appearing**
- **Cause**: Less than 2 emails selected
- **Fix**: Ensure checkboxes are actually checked before asserting

### Debug Commands
```bash
# Run with headed browser (watch test execute)
npx playwright test --headed

# Run with debug mode (step through)
npx playwright test --debug

# Generate HTML report
npx playwright test --reporter=html
npx playwright show-report

# Run specific test with trace
npx playwright test thread-viewer-basic-context --trace on
```

---

## CI/CD Integration

### GitHub Actions Example
```yaml
name: E2E Tests

on: [push, pull_request]

jobs:
  e2e:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: 18

      - name: Install dependencies
        run: npm ci

      - name: Install Playwright
        run: npx playwright install --with-deps

      - name: Run production-safe tests
        run: |
          export PROD=1
          npx playwright test tests/e2e/thread-viewer-*.spec.ts
        env:
          CI: true

      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: playwright-report
          path: playwright-report/
```

---

## Future Enhancements

1. **Visual Regression Testing**: Add screenshot comparison for UI consistency
2. **API Mocking**: Use MSW to mock backend responses for faster tests
3. **Accessibility Tests**: Add `axe-playwright` for WCAG compliance
4. **Performance Tests**: Add `lighthouse` for page load/interaction metrics
5. **Mobile Tests**: Add webkit/mobile viewport tests
6. **Cross-browser**: Extend to Firefox and Safari

---

## Maintenance

### When to Update Tests

**Add new assertions when:**
- New UI elements added to thread viewer
- New keyboard shortcuts implemented
- New bulk actions added
- Analytics events change

**Update selectors when:**
- data-testid attributes renamed/removed
- Component structure significantly changes
- New sections added to thread viewer

**Add new test files when:**
- New major feature phase (Phase 6+)
- New user flow that doesn't fit existing files
- Integration with external systems (Gmail API, etc.)

### Test Ownership
- **Phase 1-2**: Backend team (API integration)
- **Phase 3**: Frontend team (keyboard UX)
- **Phase 4**: Frontend + Backend (bulk operations)
- **Phase 5**: AI/ML team (summary quality)

---

## Support

**Questions or Issues?**
- Check existing test output: `npx playwright show-report`
- Review Playwright docs: https://playwright.dev
- Check this project's test docs: `docs/testing/`
- File issue: GitHub Issues with label `test:e2e`

**Contributing:**
- Follow existing test patterns (data-testid selectors)
- Add descriptive error messages to assertions
- Mark production-unsafe tests with `test.skip(PROD)`
- Update this documentation when adding new tests
