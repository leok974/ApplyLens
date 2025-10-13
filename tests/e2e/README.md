# End-to-End Testing with Playwright

This project uses [Playwright](https://playwright.dev/) for end-to-end testing of the ApplyLens UI.

## 📦 Installation

Playwright is already installed. If you need to reinstall:

```bash
pnpm add -D @playwright/test
pnpm exec playwright install --with-deps
```text

## 🧪 Running Tests

From the repo root:

```bash
# Run all tests (headless)
pnpm test:e2e

# Run tests with UI mode (great for debugging)
pnpm test:e2e:ui

# Update snapshots
pnpm test:e2e:update
```text

## 📁 Test Structure

```text
tests/e2e/
├── _fixtures.ts              # API mocking utilities (search, applications, inbox, emails, threads)
├── _consoleGuard.ts          # Console error/warning guard (fails tests on unexpected console errors)
├── inbox.smoke.spec.ts       # Basic inbox rendering
├── legibility.spec.ts        # Font/Density/Contrast controls
├── theme.spec.ts             # Dark mode toggle
├── details-panel.spec.ts     # Email details panel
├── search.spec.ts            # Search page with BM25 results
└── tracker.spec.ts           # Applications tracker page
```text

## 🎯 Test Coverage

### ✅ Inbox Smoke Test

- Verifies cards render with `.surface-card` class
- Checks text legibility with demo data
- Ensures calmer theme tokens are applied

### ✅ Legibility Controls

- **Font Scale**: Tests S/M/L buttons (0.9/1.0/1.1)
- **Density**: Tests Compact/Cozy/Spacious (0.92/1/1.08)
- **Contrast**: Tests Soft/High contrast modes
- **Persistence**: Verifies localStorage saves settings across page reloads

### ✅ Theme Toggle

- Tests dark mode toggle via dropdown menu
- Verifies `.dark` class applied to `<html>`
- Checks persistence across page reloads

### ✅ Details Panel

- Tests panel opening on card double-click
- Verifies panel visibility
- Tests ESC key to close panel

### ✅ Search Page

- Tests search functionality with query input
- Verifies BM25 results render
- Guards against duplicate React keys

### ✅ Tracker Page

- Tests application tracker list rendering
- Verifies stubbed application data (Acme, Example Inc)
- Validates table structure

## 🛡️ Console Error Guard

The `_consoleGuard.ts` utility automatically fails tests when unexpected console errors or warnings appear. This helps catch:

- Uncaught exceptions
- React errors
- Network failures (except expected 404s from API stubs)
- Performance warnings

To use in your tests:

```typescript
import { guardConsole } from "./_consoleGuard";

test.beforeEach(async ({ page }) => {
  guardConsole(page);
  await stubApi(page);
});
```text

## 🔧 Configuration

The tests use:

- **Base URL**: `http://localhost:5175`
- **Viewport**: 1360x900 (Desktop Chrome)
- **Retries**: 2 in CI, 0 locally
- **Artifacts**: Screenshots, videos, traces on failure

See `playwright.config.ts` for full configuration.

## 🎨 Testability Hooks

Components have been enhanced with `data-testid` attributes:

- `data-testid="email-details-panel"` - Main panel container
- `data-testid="details-resizer"` - Drag handle for resizing

## 📊 Viewing Reports

After running tests:

```bash
pnpm exec playwright show-report
```text

This opens an HTML report with:

- Test results
- Screenshots on failure
- Video recordings
- Trace files for debugging

## 🐛 Debugging

For step-by-step debugging:

```bash
# Run with Playwright Inspector
pnpm exec playwright test --debug

# Or use UI mode (recommended)
pnpm test:e2e:ui
```text

## 📝 Writing New Tests

1. Create a new `.spec.ts` file in `tests/e2e/`
2. Import fixtures if needed: `import { stubApi } from "./_fixtures";`
3. Use `test.beforeEach()` to set up API mocks
4. Write test assertions using `expect()`

Example:

```typescript
import { test, expect } from "@playwright/test";
import { stubApi } from "./_fixtures";

test.beforeEach(async ({ page }) => {
  await stubApi(page);
});

test("My new feature works", async ({ page }) => {
  await page.goto("/inbox-polished-demo");
  await expect(page.locator(".my-element")).toBeVisible();
});
```text

## 🚀 CI Integration

Tests are configured for CI with:

- 2 retries on failure
- List and HTML reporters
- Automatic artifact uploads

Add to your CI pipeline:

```yaml
- name: Run e2e tests
  run: pnpm test:e2e
```text

## 📚 Resources

- [Playwright Documentation](https://playwright.dev/)
- [Playwright Best Practices](https://playwright.dev/docs/best-practices)
- [Test Selectors](https://playwright.dev/docs/selectors)
