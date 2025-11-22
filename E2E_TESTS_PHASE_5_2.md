# E2E Tests for Phase 5.2: Summary Feedback System

**Branch:** `thread-viewer-v1`
**Status:** Tests Ready
**Date:** October 27, 2025

---

## Overview

This document covers the E2E test suite for Phase 5.2 (Summary Feedback System). These tests verify that:

1. ✅ Users can submit feedback on AI-generated summaries (Yes/No)
2. ✅ Optimistic UI works (instant acknowledgment)
3. ✅ Network failures are handled gracefully
4. ✅ Keyboard navigation still works after Phase 5.2 changes
5. ✅ No regression in core ThreadViewer functionality

**PROD-SAFE:** All tests in this suite are safe to run in production. They:
- ✅ Do NOT call destructive endpoints (archive, quarantine, mark_safe)
- ✅ Only submit summary feedback (read-only from server perspective)
- ✅ Only test UI state and keyboard navigation

---

## Test Files

### 1. `tests/e2e/thread-summary-feedback.spec.ts`

**Purpose:** Test the summary feedback happy paths

**Test Cases:**

#### ✅ Test 1: "user can mark summary as helpful and see optimistic thank-you"
- Opens ThreadViewer
- Waits for summary section to render
- Clicks "Yes" button
- Verifies:
  - Feedback controls disappear
  - Acknowledgment text appears ("Thanks!")
  - Toast confirmation shows
  - No crashes in other sections (Risk, ActionBar)

#### ✅ Test 2: "user can mark summary as not helpful and see acknowledgment"
- Similar flow but clicks "No" button
- Verifies acknowledgment text: "Got it — we'll improve this."

#### ✅ Test 3: "feedback works without network (optimistic UI)"
- Goes offline before clicking feedback
- Verifies UI still updates optimistically
- Demonstrates graceful degradation

### 2. `tests/e2e/thread-summary-feedback-no-regression.spec.ts`

**Purpose:** Ensure Phase 5.2 didn't break existing functionality

**Test Cases:**

#### ✅ Test 1: "ThreadViewer still mounts core sections and keyboard nav still moves selection"
- Opens ThreadViewer
- Verifies all sections render:
  - RiskAnalysisSection
  - ThreadSummarySection
  - ConversationTimelineSection
  - ThreadActionBar
- Tests keyboard navigation:
  - ArrowDown moves to next thread
  - ArrowUp moves to previous thread
  - Escape closes drawer
- Verifies data-selected attribute updates correctly

#### ✅ Test 2: "ArrowUp navigation works correctly"
- Tests reverse navigation
- Verifies selection state updates

#### ✅ Test 3: "all Phase 5 sections render without errors"
- Smoke test for section presence
- No assertions about content, just that sections mount

#### ✅ Test 4: "feedback controls don't interfere with keyboard shortcuts"
- Ensures feedback buttons don't capture keyboard events
- Verifies ArrowDown/Escape still work when summary section is visible

---

## Data-TestID Attributes Added

To support deterministic testing, the following `data-testid` attributes were added:

### Components

| Component | data-testid | Location |
|-----------|-------------|----------|
| ThreadSummarySection root | `thread-summary-section` | ThreadSummarySection.tsx |
| Feedback controls wrapper | `summary-feedback-controls` | ThreadSummarySection.tsx |
| Yes button | `summary-feedback-yes` | ThreadSummarySection.tsx |
| No button | `summary-feedback-no` | ThreadSummarySection.tsx |
| Acknowledgment text | `summary-feedback-ack` | ThreadSummarySection.tsx |
| RiskAnalysisSection root | `risk-analysis-section` | RiskAnalysisSection.tsx |
| ConversationTimelineSection root | `conversation-timeline-section` | ConversationTimelineSection.tsx |
| ThreadActionBar root | `thread-action-bar` | ThreadActionBar.tsx |
| Toast container | `toast-container` | sonner.tsx |

### Pages

| Page | Element | data-testid | data-selected | Location |
|------|---------|-------------|---------------|----------|
| Inbox | Email row | `thread-row` | `"true"` or `"false"` | Inbox.tsx |

**Usage Example:**

```tsx
// In Inbox.tsx
<div
  data-testid="thread-row"
  data-selected={thread.selectedId === String(e.id) ? "true" : "false"}
  className="flex items-start gap-2"
>
  ...
</div>
```

**Benefits:**

- ✅ **Deterministic selectors**: No brittle text matching
- ✅ **Prod-safe**: data-testid has no runtime cost
- ✅ **Refactor-proof**: Independent of CSS classes/structure
- ✅ **A11y-neutral**: Doesn't affect accessibility tree

---

## Running the Tests

### Prerequisites

1. **Build the app:**
   ```bash
   npm run build
   ```

2. **Install Playwright browsers (first time only):**
   ```bash
   npx playwright install
   ```

### Run All E2E Tests

```bash
npx playwright test
```

### Run Only Phase 5.2 Tests

```bash
npx playwright test tests/e2e/thread-summary-feedback
```

### Run Specific Test File

```bash
# Feedback tests
npx playwright test tests/e2e/thread-summary-feedback.spec.ts

# Regression tests
npx playwright test tests/e2e/thread-summary-feedback-no-regression.spec.ts
```

### Run in Headed Mode (See Browser)

```bash
npx playwright test --headed
```

### Debug Mode (Step Through Tests)

```bash
npx playwright test --debug
```

### Run Specific Test by Name

```bash
npx playwright test -g "user can mark summary as helpful"
```

---

## CI/CD Integration

### GitHub Actions Example

Add to `.github/workflows/e2e-tests.yml`:

```yaml
name: E2E Tests

on:
  push:
    branches: [main, thread-viewer-v1]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
          cache: 'npm'

      - name: Install dependencies
        run: npm ci

      - name: Build app
        run: npm run build

      - name: Install Playwright browsers
        run: npx playwright install --with-deps chromium

      - name: Run E2E tests
        run: npx playwright test

      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: playwright-report
          path: playwright-report/
```

### Configuration

The tests use `playwright.config.ts`:

```typescript
export default defineConfig({
  testDir: "tests/e2e",
  fullyParallel: true,
  retries: process.env.CI ? 2 : 0,
  use: {
    baseURL: "http://localhost:5175",
    trace: process.env.CI ? "on-first-retry" : "retain-on-failure",
  },
  webServer: {
    command: "npm run -w apps/web preview -- --port 5175",
    url: "http://localhost:5175",
    reuseExistingServer: !process.env.CI,
  },
});
```

**Key settings:**

- ✅ **Retries in CI**: 2 retries on failure (handles flakiness)
- ✅ **Traces on retry**: Automatic debugging artifacts
- ✅ **Auto-start server**: Playwright starts/stops dev server
- ✅ **Parallel execution**: Faster test runs

---

## Test Coverage

### What's Covered ✅

1. **Feedback submission**
   - Happy path (Yes/No buttons)
   - Optimistic UI updates
   - Toast confirmations
   - Network error handling

2. **Keyboard navigation**
   - ArrowDown (next thread)
   - ArrowUp (previous thread)
   - Escape (close drawer)
   - No interference from feedback controls

3. **Component rendering**
   - All Phase 5 sections mount correctly
   - Sections render in correct order
   - No crashes after feedback interaction

4. **State management**
   - data-selected attribute updates
   - Drawer opens/closes properly
   - Selection state persists across navigation

### What's NOT Covered (Intentionally)

1. ❌ **Backend persistence**: We don't verify database writes
   - Why: Out of scope for E2E, covered by backend unit tests

2. ❌ **Analytics tracking**: We don't assert analytics events fire
   - Why: Would require mocking analytics providers

3. ❌ **Destructive actions**: We don't test Archive/Quarantine/Mark Safe
   - Why: Prod-safe constraint (don't mutate server state)

4. ❌ **Multi-user scenarios**: We don't test concurrent users
   - Why: Out of scope for Phase 5.2

---

## Debugging Failed Tests

### 1. Check Screenshot

Playwright auto-captures screenshots on failure:

```bash
open playwright-report/index.html
```

### 2. Watch Video Recording

Videos are saved in `test-results/`:

```bash
open test-results/thread-summary-feedback-chromium/video.webm
```

### 3. Inspect Trace

Traces include full DOM snapshots and network logs:

```bash
npx playwright show-trace test-results/trace.zip
```

### 4. Run with --debug

Step through test interactively:

```bash
npx playwright test --debug -g "user can mark summary as helpful"
```

### 5. Check data-testid Selectors

Common issues:

- ❌ **Selector not found**: Component not mounted yet
  - Fix: Add `await expect(element).toBeVisible()` before interaction

- ❌ **Multiple matches**: data-testid not unique
  - Fix: Use `.first()`, `.nth(0)`, or scope with parent selector

- ❌ **Stale element**: Component unmounted after action
  - Fix: Check that drawer is still open, section didn't re-render

---

## Performance

### Test Execution Time

| Test Suite | Duration | Parallelizable |
|------------|----------|----------------|
| thread-summary-feedback.spec.ts | ~15s | Yes |
| thread-summary-feedback-no-regression.spec.ts | ~10s | Yes |
| **Total** | **~25s** | N/A |

**Notes:**

- Tests run in parallel by default (`fullyParallel: true`)
- Total wall-clock time: ~10-15s (depends on CPU cores)
- CI time: ~20-30s (includes setup overhead)

### Optimization Tips

1. **Reuse browser contexts**: Faster than spawning new browsers
2. **Minimize page navigations**: Each `goto()` is expensive
3. **Use `toBeVisible()` sparingly**: Polls DOM, can be slow
4. **Avoid `waitForTimeout()`**: Use `waitForSelector()` instead

---

## Maintenance

### When to Update Tests

1. **Component refactor**: If data-testid selectors change
2. **New sections added**: Add assertions for new elements
3. **Keyboard shortcuts changed**: Update key press tests
4. **Toast library changed**: Update toast selector

### Adding New Tests

1. **Create test file**: `tests/e2e/your-feature.spec.ts`
2. **Add data-testid**: To any new components
3. **Run test**: `npx playwright test your-feature`
4. **Update this doc**: Add to Test Coverage section

### Regression Testing

After any Phase 5.x change:

1. ✅ Run all E2E tests: `npx playwright test`
2. ✅ Check for new console errors (Playwright captures these)
3. ✅ Verify no visual regressions (screenshots)
4. ✅ Update test assertions if behavior intentionally changed

---

## Known Issues / Limitations

### 1. Toast Timing

**Issue:** Toast assertions can be flaky if toast duration is short

**Workaround:**
```typescript
await expect(toast).toBeVisible({ timeout: 5000 });
```

**Root Cause:** Sonner toasts auto-dismiss after 4 seconds by default

**Fix (if needed):** Increase toast duration in production config

### 2. Offline Mode Test

**Issue:** `page.context().setOffline(true)` doesn't always simulate real network failure

**Workaround:** Test passes if UI updates optimistically (doesn't depend on network mock being perfect)

**Alternative:** Use Playwright's `route()` to block specific requests:
```typescript
await page.route('/api/actions/summary-feedback', route => route.abort());
```

### 3. Multiple Rows Required

**Issue:** Keyboard nav tests need at least 2 rows in inbox

**Workaround:** Seed test data or skip test if `rows.count() < 2`

**Future:** Add test data fixtures in `playwright.config.ts`

---

## Example Test Output

### Successful Run

```
$ npx playwright test

Running 7 tests using 4 workers

  ✓ [chromium] › thread-summary-feedback.spec.ts:5:5 › user can mark summary as helpful (2.1s)
  ✓ [chromium] › thread-summary-feedback.spec.ts:60:5 › user can mark summary as not helpful (1.8s)
  ✓ [chromium] › thread-summary-feedback.spec.ts:82:5 › feedback works without network (1.5s)
  ✓ [chromium] › thread-summary-feedback-no-regression.spec.ts:12:5 › ThreadViewer still mounts (2.3s)
  ✓ [chromium] › thread-summary-feedback-no-regression.spec.ts:70:5 › ArrowUp navigation works (1.6s)
  ✓ [chromium] › thread-summary-feedback-no-regression.spec.ts:89:5 › all Phase 5 sections render (1.4s)
  ✓ [chromium] › thread-summary-feedback-no-regression.spec.ts:110:5 › feedback controls don't interfere (1.9s)

  7 passed (13s)
```

### Failed Test Example

```
$ npx playwright test

  ✗ [chromium] › thread-summary-feedback.spec.ts:5:5 › user can mark summary as helpful (2.3s)

    Error: Expected "Thanks!" but got "Helpful?"

    Call log:
      - page.goto('http://localhost:5175/inbox')
      - locator('[data-testid="thread-row"]').first() click
      - locator('[data-testid="summary-feedback-yes"]').click()
      - expect(locator('[data-testid="summary-feedback-ack"]')).toBeVisible()
        ↪ Timed out 5000ms waiting for expect(locator).toBeVisible()

    Screenshot: test-results/thread-summary-feedback-chromium/test-failed-1.png
    Video: test-results/thread-summary-feedback-chromium/video.webm
```

---

## Best Practices

### 1. Always Use data-testid

❌ **Bad:**
```typescript
const button = page.locator('button:has-text("Yes")');
```

✅ **Good:**
```typescript
const button = page.locator('[data-testid="summary-feedback-yes"]');
```

**Why:** Text content can change (i18n, copy edits), data-testid won't.

### 2. Scope Selectors

❌ **Bad:**
```typescript
const yesButton = page.locator('[data-testid="summary-feedback-yes"]');
```

✅ **Good:**
```typescript
const summarySection = page.locator('[data-testid="thread-summary-section"]');
const yesButton = summarySection.locator('[data-testid="summary-feedback-yes"]');
```

**Why:** Prevents false positives if multiple sections have similar elements.

### 3. Assert Visibility Before Interaction

❌ **Bad:**
```typescript
await yesButton.click();
```

✅ **Good:**
```typescript
await expect(yesButton).toBeVisible();
await yesButton.click();
```

**Why:** Catches timing issues where element isn't ready.

### 4. Use Meaningful Descriptions

❌ **Bad:**
```typescript
await expect(ack).toBeVisible();
```

✅ **Good:**
```typescript
await expect(
  ack,
  "After clicking Yes, component should optimistically replace controls with a thank-you message"
).toBeVisible();
```

**Why:** Failure messages are much clearer.

---

## Changelog

### 2025-10-27: Initial E2E Suite Created
- ✅ Added `thread-summary-feedback.spec.ts` (3 tests)
- ✅ Added `thread-summary-feedback-no-regression.spec.ts` (4 tests)
- ✅ Added data-testid attributes to all Phase 5.2 components
- ✅ Added data-selected attribute to Inbox rows
- ✅ Added data-testid to Sonner toast container
- ✅ Verified all tests pass locally

---

## Next Steps

1. **Run tests in CI**: Add GitHub Actions workflow
2. **Add visual regression tests**: Use Playwright's `toHaveScreenshot()`
3. **Test mobile viewport**: Add iPhone/Android device configs
4. **Test dark mode**: Verify feedback UI in both themes
5. **Add Percy integration**: Automated visual diff reviews

---

## Questions?

Contact the team:
- **Frontend:** Check component test IDs in respective `.tsx` files
- **E2E Tests:** Check `tests/e2e/*.spec.ts` files
- **Playwright Config:** Check `playwright.config.ts`
- **Docs:** This file! (`E2E_TESTS_PHASE_5_2.md`)

---

**End of E2E Test Documentation** 🎉
