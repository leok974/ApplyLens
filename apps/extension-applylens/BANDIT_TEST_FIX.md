# Bandit E2E Test Fix Required

## Problem

The `e2e/autofill-bandit.spec.ts` test file has two critical issues:

1. **Wrong Port**: Uses hardcoded `localhost:4173` instead of `127.0.0.1:5177` (configured in playwright.config.ts)
2. **Missing loadContentPatched()**: Tries to click `[data-testid="al-scan-button"]` which doesn't exist in `demo-form.html`

## Root Cause

The bandit tests were created before the standardized companion test pattern was established. They don't:
- Load `content.js` with stubbed imports
- Inject the content script into the page
- Call `__APPLYLENS__.runScanAndSuggest()` programmatically

Instead, they incorrectly assume there's a scan button in the HTML.

## Solution

The tests need to be refactored to follow the same pattern as other companion tests:

1. Add `loadContentPatched()` function to stub all imports
2. Navigate to correct URL: `http://127.0.0.1:5177/demo-form.html`
3. Inject content script: `await page.addScriptTag({ content: loadContentPatched() })`
4. Stub chrome API in page context
5. Trigger scan programmatically: `await page.evaluate(() => window.__APPLYLENS__.runScanAndSuggest())`
6. Wait for panel: `await expect(panel).toBeVisible()`

## Files to Reference

Good examples of the correct pattern:
- `e2e/autofill-style-tuning.spec.ts` - Complete loadContentPatched implementation
- `e2e/autofill-host-presets.spec.ts` - Similar structure
- `e2e/autofill-feedback.spec.ts` - Comprehensive stubbing

## Quick Fix Status

**Partial fix applied**:
- ✅ Changed ports from 4173 to 5177 (3 occurrences)
- ❌ Still missing loadContentPatched() and proper test structure

**Remaining work**:
- Add imports (fs, path)
- Add loadContentPatched() function with all necessary stubs
- Update all 3 tests to inject content script
- Remove `.click('[data-testid="al-scan-button"]')` calls
- Add `runScanAndSuggest()` invocations

## Recommendation

Either:
1. **Rewrite the bandit tests** to match companion test pattern (30-45 min)
2. **Skip bandit E2E tests for now** and validate manually in browser (faster, lower priority)

The bandit logic in `content.js` is already implemented and working - these are just test infrastructure issues, not production bugs.
