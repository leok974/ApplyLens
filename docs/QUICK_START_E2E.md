# Quick Start: Running E2E Tests

## Prerequisites ✅

1. ✅ Infrastructure running (API on 8003, Web on 5175)
2. ✅ Playwright installed
3. ✅ Test files created
4. ✅ Test IDs added to components

---

## Run Tests Now

### Option 1: UI Mode (Recommended)

```bash
cd d:\ApplyLens\apps\web
pnpm test:e2e:ui
```text

**What you'll see:**

- Interactive test runner
- Click to run individual tests
- Watch tests execute in real-time
- Inspect failures with time-travel debugging

---

### Option 2: Headless Mode (Fast)

```bash
cd d:\ApplyLens\apps\web
pnpm test:e2e
```text

**Output:**

```text
✓ [chromium] › pipeline.spec.ts:5:3 › runs Gmail→Label→Profile with toasts (25s)
✓ [chromium] › search.spec.ts:50:3 › category buttons mutate URL (1s)
✓ [chromium] › highlight.spec.ts:7:3 › subject/snippet render <mark> (500ms)
✓ [chromium] › profile.spec.ts:8:3 › profile page shows summary (2s)

4 passed (28s)
```text

---

### Option 3: Headed Mode (See Browser)

```bash
cd d:\ApplyLens\apps\web
pnpm test:e2e:headed
```text

**What you'll see:**

- Browser window opens
- Tests run visibly
- Good for debugging

---

## Test Descriptions

### 1. Pipeline Tests (`pipeline.spec.ts`)

**Duration:** ~30-60s (live API calls)

**Tests:**

- 7-day sync button → 4 toasts appear
- 60-day sync button → sync completes

**Note:** These tests hit the real API, so they take longer.

---

### 2. Search Tests (`search.spec.ts`)

**Duration:** ~3-5s (mocked API)

**Tests:**

- Category button clicks update URL
- Multiple categories can be selected
- Hide expired switch works
- Expired chip toggles same state

**Note:** Fast because API is mocked.

---

### 3. Highlight Tests (`highlight.spec.ts`)

**Duration:** ~2-3s (mocked API)

**Tests:**

- `<mark>` tags render in subjects
- `<mark>` tags render in body snippets
- XSS protection (scripts blocked)
- Multiple highlights work

**Note:** Fast and safe (mocked data).

---

### 4. Profile Tests (`profile.spec.ts`)

**Duration:** ~5-10s (real or mocked API)

**Tests:**

- Profile link in navigation
- Profile page loads
- Summary data displays
- Empty state handled gracefully

**Note:** Automatically mocks if API is down.

---

## Expected Results

### All Tests Passing ✅

```text
✓ pipeline.spec.ts (2 tests, 30s)
✓ search.spec.ts (4 tests, 5s)
✓ highlight.spec.ts (4 tests, 3s)
✓ profile.spec.ts (4 tests, 10s)

14 tests passed in 48s
```text

### Some Tests Skipped (API Down) ⏭️

```text
✓ search.spec.ts (4 tests, 5s)
✓ highlight.spec.ts (4 tests, 3s)
✓ profile.spec.ts (4 tests, 10s)
⊘ pipeline.spec.ts (2 tests skipped - API not reachable)

12 tests passed, 2 skipped in 18s
```text

---

## Troubleshooting

### Tests Fail: "Cannot connect to <http://localhost:5175>"

**Solution:**

```bash
# Check if web container is running
docker ps | Select-String "infra-web"

# If not running, start it
cd d:\ApplyLens\infra
docker compose up -d web

# Wait 10 seconds, then retry tests
```text

---

### Tests Fail: "API not reachable"

**This is expected!** Pipeline tests will skip gracefully.

**To fix (optional):**

```bash
# Check if API container is running
docker ps | Select-String "infra-api"

# If not running, start it
cd d:\ApplyLens\infra
docker compose up -d api

# Wait for API to be ready
curl http://localhost:8003/docs

# Retry tests
```text

---

### Tests Fail: "Element not found"

**Possible causes:**

1. Test IDs not deployed yet
2. Component changed
3. Timing issue

**Solution:**

```bash
# Rebuild web container
cd d:\ApplyLens\infra
docker compose up -d --build web

# Wait 10 seconds
Start-Sleep -Seconds 10

# Retry tests
cd d:\ApplyLens\apps\web
pnpm test:e2e
```text

---

### Playwright Not Installed

**Error:** `command not found: playwright`

**Solution:**

```bash
cd d:\ApplyLens\apps\web
pnpm add -D @playwright/test
pnpm exec playwright install --with-deps
```text

---

## View Test Report

After tests run, view HTML report:

```bash
pnpm test:e2e:report
```text

**Opens browser with:**

- Test results
- Screenshots (on failure)
- Videos (on failure)
- Execution traces

---

## Debug a Single Test

```bash
# Run one test file
pnpm exec playwright test tests/search.spec.ts

# Run one specific test
pnpm exec playwright test tests/search.spec.ts -g "category buttons"

# Debug mode (interactive)
PWDEBUG=1 pnpm exec playwright test tests/search.spec.ts
```text

---

## Next Steps

### 1. Run Tests Now

```bash
cd d:\ApplyLens\apps\web
pnpm test:e2e:ui
```text

### 2. Watch Tests Execute

- Click "pipeline.spec.ts" to run sync tests
- Click "search.spec.ts" to run filter tests
- Click "highlight.spec.ts" to run highlight tests
- Click "profile.spec.ts" to run profile tests

### 3. Verify All Features

- ✅ Sync buttons work
- ✅ Category filters work
- ✅ Highlights render
- ✅ Profile page loads

---

## Common Commands

```bash
# Run all tests
pnpm test:e2e

# Run with UI
pnpm test:e2e:ui

# Run in headed mode
pnpm test:e2e:headed

# Run specific file
pnpm exec playwright test tests/pipeline.spec.ts

# Debug mode
PWDEBUG=1 pnpm test:e2e

# View report
pnpm test:e2e:report
```text

---

**Ready to test! Run `pnpm test:e2e:ui` to get started. 🎉**
