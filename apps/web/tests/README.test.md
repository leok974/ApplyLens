# Running Playwright Tests

This document explains how to run different types of tests in the ApplyLens project.

## Test Categories

### 1. Mock-Based Tests (No Backend Required) - **prodSafe**

These tests use `page.route()` mocks and do NOT require:
- Backend API server (uvicorn)
- PostgreSQL database
- Elasticsearch
- BigQuery

**Tests in this category:**
- `profile-warehouse.spec.ts` - Warehouse-backed profile page with mocked BigQuery data
- `mailboxAssistant.spec.ts` - Mailbox assistant with mocked responses

#### How to Run Mock-Based Tests

```powershell
# 1. Navigate to the web app directory
cd d:\ApplyLens\apps\web

# 2. Start the frontend dev server (if not already running)
npm run dev
# This will start Vite on http://localhost:5175

# 3. In a SEPARATE terminal, run the tests with SKIP_AUTH
cd d:\ApplyLens\apps\web
$env:SKIP_AUTH='1'
npx playwright test tests/profile-warehouse.spec.ts --reporter=line

# Or run all mock-based tests
$env:SKIP_AUTH='1'
npx playwright test tests/profile-warehouse.spec.ts tests/mailboxAssistant.spec.ts --reporter=line
```

**Why `SKIP_AUTH=1`?**
- The `auth.setup.ts` normally tries to authenticate against a live backend
- Setting `SKIP_AUTH=1` bypasses this and creates a minimal auth state file
- The tests then use `mockProfileSession()` or similar helpers to fake authentication

### 2. Full-Stack Tests (Backend Required)

These tests require the complete infrastructure:
- Frontend dev server
- Backend API server
- PostgreSQL database
- Elasticsearch (optional for some tests)

**Tests in this category:**
- `pipeline.spec.ts`
- `search.spec.ts`
- `profile.spec.ts` (the original, not warehouse version)
- Most `e2e/*.spec.ts` tests

#### How to Run Full-Stack Tests

```powershell
# 1. Start Docker Desktop (if not running)

# 2. Start infrastructure services
cd d:\ApplyLens\infra
docker-compose up -d

# 3. Start backend API (in a new terminal)
cd d:\ApplyLens\services\api
python -m uvicorn app.main:app --reload --port 8000

# 4. Start frontend dev server (in another terminal)
cd d:\ApplyLens\apps\web
npm run dev

# 5. Run tests (in another terminal)
cd d:\ApplyLens\apps\web
npx playwright test tests/pipeline.spec.ts --reporter=line
```

## Test Helper: `mockProfileSession`

For creating new mock-based tests, use the `mockProfileSession` helper:

```typescript
import { test, expect } from "@playwright/test";
import { mockProfileSession } from "./utils/mockProfileSession";

test("my new profile test", async ({ page }) => {
  // Mock all backend endpoints
  await mockProfileSession(page);

  // Navigate to the page
  await page.goto("http://localhost:5175/profile");

  // Make assertions
  await expect(page.getByText("Email Activity")).toBeVisible();
});
```

### What `mockProfileSession` mocks:

1. **`/api/config`** - Runtime configuration (version, read-only mode)
2. **`/api/auth/me`** - User session (makes app think you're logged in)
3. **`/api/metrics/profile/summary`** - Warehouse analytics data (BigQuery results)

You can customize the mocked data by modifying `tests/utils/mockProfileSession.ts` or creating inline mocks in your test.

## Warehouse Sync Debug

The Profile page now includes observability fields to help debug data freshness issues:

### New API Fields

- **`last_sync_at`**: ISO8601 timestamp of the most recent successful warehouse sync (from BigQuery data)
- **`dataset`**: Dataset or dataset+table prefix being queried (e.g., `"applylens.gmail_raw"`)

These fields are included in the `/api/metrics/profile/summary` response and cached for 60 seconds.

### UI Indicators

**Email Activity Card:**
- Shows "Last sync: {time}" (e.g., "Last sync: 12m ago", "Last sync: 2h ago")
- Helps determine if data is fresh or stale

**Bottom Badge:**
- Shows "Dataset: {dataset}" for debugging which BigQuery tables are being queried

### Empty State Messages

The Profile page uses defensive rendering to distinguish between "no data yet" vs "no data available":

- **"No data yet"**: Displayed when `last_sync_at` is null OR sync is recent (< 30 minutes)
  - Indicates data sync might still be in progress

- **"No data in the last 30 days."**: Displayed when sync is stale (> 30 minutes) AND arrays are empty
  - Indicates the sync completed but there truly was no data in the time window

### Test Assertions

Tests in `profile-warehouse.spec.ts` assert these strings to detect regressions:

```typescript
// Verify sync info is displayed
await expect(page.getByText(/Last sync:/i)).toBeVisible();

// Verify dataset debug info
await expect(page.getByText(/Dataset:/i)).toBeVisible();

// Verify appropriate empty state message
await expect(page.getByText(/No data in the last 30 days\./i)).toBeVisible();
```

## Debugging Tests

### Run in Headed Mode (See Browser)

```powershell
npx playwright test tests/profile-warehouse.spec.ts --headed
```

### Run with Debug Inspector

```powershell
npx playwright test tests/profile-warehouse.spec.ts --debug
```

### Check Test Output

Test results and screenshots are saved to:
- `test-results/` - Screenshots and error contexts
- `playwright-report/` - HTML report

```powershell
# Open HTML report
npx playwright show-report
```

## CI/CD Integration

### Production-Safe Tests

Tests marked with `[prodSafe]` in their description can run in production without:
- Writing to databases
- Modifying real data
- Requiring test infrastructure

Example:
```typescript
test.describe("Profile page (warehouse analytics) [prodSafe]", () => {
  // Tests here use mocks only
});
```

### Playwright Config Filtering

The `playwright.config.ts` automatically filters tests based on environment:

```typescript
const IS_PROD = /^https:\/\/applylens\.app/.test(BASE);

// Only run @prodSafe tests in production
grep: IS_PROD ? /@prodSafe/ : undefined,
```

## Common Issues

### 1. "Service Temporarily Unavailable" Error

**Problem:** App shows auth error page
**Solution:** Make sure `SKIP_AUTH=1` is set when running mock-based tests

### 2. "Cannot find module './utils/waitApp'"

**Problem:** Old import path for helper utilities
**Solution:** Update to use `./utils/mockProfileSession` for new tests

### 3. Port 5175 Already in Use

**Problem:** Vite dev server can't start
**Solution:**
```powershell
# Find and kill the process
netstat -ano | findstr :5175
Stop-Process -Id <PID> -Force

# Or let Vite use another port
npm run dev
# It will auto-select port 5176, 5177, etc.
```

### 4. Tests Timeout Waiting for Elements

**Problem:** Test fails with "Test timeout of 30000ms exceeded"
**Solution:**
- Ensure dev server is running on port 5175
- Check that mocks are set up BEFORE `page.goto()`
- Verify the component actually renders the expected text
