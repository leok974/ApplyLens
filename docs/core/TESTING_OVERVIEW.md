# Testing & E2E Overview

## Testing Philosophy

ApplyLens uses a multi-layered testing approach:

1. **Unit Tests** - Fast, isolated tests for business logic (Vitest)
2. **E2E Tests** - Browser-based tests for user flows (Playwright)
3. **Smoke Tests** - Critical path validation (local & production)
4. **Contract Tests** - API endpoint validation

## Test Stacks

### Backend (API)
- **Framework**: pytest
- **Location**: `services/api/tests/`
- **Run**: `pytest tests/ -v`

### Frontend (Web App)
- **Unit Tests**: Vitest
- **E2E Tests**: Playwright
- **Location**: `apps/web/tests/`
- **Config**: `apps/web/playwright.config.ts`

### Extension
- **Unit Tests**: Vitest
- **E2E Tests**: Playwright with extension loading
- **Location**: `apps/extension-applylens/tests/`, `apps/extension-applylens/e2e/`
- **Configs**:
  - `playwright.config.ts` - Content script tests
  - `playwright.with-extension.config.ts` - Full extension tests
  - `playwright.panel.config.ts` - Panel UI tests

## Key E2E Test Suites

### 1. Companion Settings Tests

**File**: `apps/web/tests/e2e/companion-settings.spec.ts`

**Purpose**: Verify Companion settings page functionality

**What it tests**:
- Settings page loads at `/settings/companion`
- Experimental styles toggle works
- Application history displays correctly
- Outreach history displays correctly
- Learning preferences toggle

**Run locally**:
```powershell
cd apps/web
npx playwright test tests/e2e/companion-settings.spec.ts
```

**Key assertions**:
```typescript
// Experimental styles toggle
await expect(page.locator('[data-testid="experimental-styles-toggle"]')).toBeVisible();
await page.click('[data-testid="experimental-styles-toggle"]');
await expect(page.locator('[data-testid="experimental-styles-enabled"]')).toBeVisible();

// Application history
await expect(page.locator('[data-testid="application-history"]')).toBeVisible();
await expect(page.locator('[data-testid="application-row"]')).toHaveCount(5);
```

### 2. Production Smoke Tests

**File**: `apps/web/tests/prod/prod-smoke.spec.ts`

**Purpose**: Validate critical paths work in production

**What it tests**:
- ✅ Homepage loads without errors
- ✅ `/api/auth/me` returns 200 or 401 (not 502)
- ✅ Profile loads for authenticated users
- ✅ Search returns results
- ✅ No console errors on critical pages

**Run against production**:
```powershell
cd apps/web
$env:PROD_BASE_URL="https://applylens.app"
npx playwright test tests/prod/prod-smoke.spec.ts --workers=2 --reporter=list
```

**Run against local**:
```powershell
cd apps/web
npx playwright test tests/prod/prod-smoke.spec.ts --workers=2 --reporter=list
# Uses BASE_URL from playwright.config.ts (http://localhost:5176)
```

**Critical checks**:
```typescript
test('auth endpoint returns valid status', async ({ page }) => {
  const response = await page.request.get('/api/auth/me');

  // Should be 200 (authenticated) or 401 (not authenticated)
  // NOT 502 (bad gateway - indicates backend issue)
  expect([200, 401]).toContain(response.status());
});

test('profile loads without 502 errors', async ({ page }) => {
  await page.goto('/');

  // Wait for network idle
  await page.waitForLoadState('networkidle');

  // Check for 502 errors in console
  const errors = [];
  page.on('console', msg => {
    if (msg.type() === 'error' && msg.text().includes('502')) {
      errors.push(msg.text());
    }
  });

  expect(errors).toHaveLength(0);
});
```

### 3. Companion Extension Tests

**File**: `apps/extension-applylens/e2e/with-extension.spec.ts`

**Purpose**: Test full extension integration with real Chrome

**What it tests**:
- Extension loads in Chrome
- Popup shows connection status
- Content script scans forms
- Autofill generates answers
- Learning events sync

**Run locally**:
```powershell
cd apps/extension-applylens
npx playwright test -c ./playwright.with-extension.config.ts
```

**Special notes**:
- Runs Chrome in **headed mode** (extension requires real browser)
- Loads extension from `apps/extension-applylens/` directory
- Uses demo form at `test/demo-form.html`

**Key setup**:
```typescript
// playwright.with-extension.config.ts
export default defineConfig({
  use: {
    headless: false, // Extension needs visible browser
    baseURL: "http://127.0.0.1:5178",
  },
  projects: [
    {
      name: "chromium-with-extension",
      use: {
        launchOptions: {
          args: [
            `--disable-extensions-except=${EXT_DIR}`,
            `--load-extension=${EXT_DIR}`,
          ],
        },
      },
    },
  ],
});
```

### 4. Learning Profile Tests

**File**: `apps/extension-applylens/e2e/learning-profile.spec.ts`

**Purpose**: Verify learning profile fetch and sync

**What it tests**:
- Profile fetch with host + schema_hash
- Canonical field mappings applied
- Learning events sent after autofill
- Fallback when profile not found

**Run locally**:
```powershell
cd apps/extension-applylens
npx playwright test e2e/learning-profile.spec.ts
```

**API expectations**:
```typescript
// Expect GET /api/extension/learning/profile?host=...&schema_hash=...
await page.waitForRequest(req =>
  req.url().includes('/api/extension/learning/profile')
);

// Expect POST /api/extension/learning/sync after autofill
await page.waitForRequest(req =>
  req.url().includes('/api/extension/learning/sync') &&
  req.method() === 'POST'
);
```

### 5. Auth Contract Tests

**File**: `apps/web/tests/e2e/auth.contract.spec.ts`

**Purpose**: Validate OAuth flow and session handling

**What it tests**:
- Login redirects to Google OAuth
- Callback handles OAuth code
- Session persists across refreshes
- Logout clears session
- `/api/auth/me` contract

**Run locally** (requires OAuth setup):
```powershell
cd apps/web
npx playwright test tests/e2e/auth.contract.spec.ts --project=chromium-auth
```

**Contract validation**:
```typescript
test('/api/auth/me returns valid user schema', async ({ page }) => {
  const response = await page.request.get('/api/auth/me');

  expect(response.status()).toBe(200);

  const user = await response.json();
  expect(user).toMatchObject({
    id: expect.any(String),
    email: expect.stringContaining('@'),
    name: expect.any(String),
  });
});
```

## Running Tests Locally

### Web App Tests

```powershell
cd apps/web

# All tests
npx playwright test

# Specific file
npx playwright test tests/e2e/companion-settings.spec.ts

# Headed mode (see browser)
npx playwright test --headed

# Debug mode (pause on each step)
npx playwright test --debug

# UI mode (interactive)
npx playwright test --ui

# Specific project
npx playwright test --project=chromium-auth
```

### Extension Tests

```powershell
cd apps/extension-applylens

# Content script tests (no extension)
npx playwright test -c ./playwright.config.ts

# Full extension tests (Chrome with extension)
npx playwright test -c ./playwright.with-extension.config.ts

# Panel tests
npx playwright test -c ./playwright.panel.config.ts

# Specific test with tag
npx playwright test -g "@companion"
```

### Unit Tests

```powershell
# Web app
cd apps/web
npm test              # Run once
npm run test:watch    # Watch mode
npm run test:coverage # With coverage

# Extension
cd apps/extension-applylens
npm test              # Run once
npm run test:ui       # Interactive UI
```

## Running Tests Against Production

### Production Smoke Tests

```powershell
cd apps/web

# Set production URL
$env:PROD_BASE_URL="https://applylens.app"

# Run prod-safe tests
npx playwright test tests/prod/prod-smoke.spec.ts --workers=2 --reporter=list

# Run with grep for specific tests
npx playwright test --grep @prodSafe --reporter=line
```

**Safe for production**:
- ✅ Read-only operations (GET requests)
- ✅ Health checks (`/api/ops/diag/health`)
- ✅ Auth endpoint validation
- ✅ Public page loads

**NOT safe for production**:
- ❌ Creating test data (POST/PUT/DELETE)
- ❌ Modifying user profiles
- ❌ Triggering emails or external services

### Production Validation Checklist

Before deploying to production, run:

```powershell
# 1. Web smoke tests
cd apps/web
npx playwright test tests/smoke/inbox-has-data.spec.ts --config=playwright.config.ts --workers=2

# 2. Backend API tests
cd services/api
pytest tests/test_extension_endpoints.py -v

# 3. Extension unit tests
cd apps/extension-applylens
npm test

# 4. Production smoke (after deployment)
cd apps/web
$env:PROD_BASE_URL="https://applylens.app"
npx playwright test tests/prod/prod-smoke.spec.ts --workers=2 --reporter=list
```

## Test Organization

### Web App (`apps/web/tests/`)

```
tests/
├── e2e/                          # End-to-end user flows
│   ├── auth.contract.spec.ts     # OAuth flow, session
│   ├── companion-settings.spec.ts # Companion settings page
│   ├── search.interactions.spec.ts # Search functionality
│   └── ux-heartbeat.spec.ts      # Critical UX paths
├── prod/                         # Production-safe tests
│   └── prod-smoke.spec.ts        # Read-only validation
├── smoke/                        # Quick smoke tests
│   └── inbox-has-data.spec.ts    # Inbox loads with data
└── ui/                           # UI component tests
    └── header-logo.spec.ts       # Header navigation
```

### Extension (`apps/extension-applylens/`)

```
tests/                            # Unit tests (Vitest)
├── content.test.ts               # Content script logic
├── mergeMaps.test.ts             # Field mapping merge
└── profileClient.test.ts         # Profile client API

e2e/                              # E2E tests (Playwright)
├── with-extension.spec.ts        # Full extension flow
├── learning-profile.spec.ts      # Learning profile fetch/sync
└── autofill-bandit.spec.ts       # Bandit policy selection
```

### Backend (`services/api/tests/`)

```
tests/
├── test_extension_endpoints.py   # Extension API endpoints
├── test_auth.py                  # Authentication flows
├── test_search.py                # Search functionality
└── test_learning.py              # Learning profile endpoints
```

## Common Test Patterns

### 1. Waiting for API Requests

```typescript
// Wait for specific endpoint
await page.waitForRequest(req =>
  req.url().includes('/api/extension/generate-form-answers')
);

// Wait for response with validation
const response = await page.waitForResponse(resp =>
  resp.url().includes('/api/profile/me') && resp.status() === 200
);
const user = await response.json();
```

### 2. Handling Authentication

```typescript
// Use stored auth state
test.use({ storageState: 'tests/.auth/state.json' });

// Or authenticate in test
await page.goto('/');
await page.click('[data-testid="login-button"]');
// ... OAuth flow ...
await page.waitForURL('/');
await page.context().storageState({ path: 'tests/.auth/state.json' });
```

### 3. Testing Forms

```typescript
// Fill and submit
await page.fill('[name="company"]', 'AcmeCo');
await page.fill('[name="role"]', 'Engineer');
await page.click('button[type="submit"]');

// Wait for success
await expect(page.locator('[data-testid="success-message"]')).toBeVisible();
```

### 4. Network Mocking

```typescript
// Mock API response
await page.route('/api/extension/generate-form-answers', route => {
  route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({
      answers: [{ field_id: 'cover_letter', answer: 'Mock answer' }]
    })
  });
});
```

## Environment Variables

### Web App Tests

```bash
# Base URL for tests
BASE_URL=http://localhost:5176

# Production URL for prod tests
PROD_BASE_URL=https://applylens.app

# Run login flow (creates auth state)
RUN_LOGIN=1

# Use existing auth state
STORAGE_STATE=tests/.auth/state.json

# Allow network requests (for debugging)
PW_ALLOW_NET=1

# Lock network (prevent external calls)
PW_LOCK_NET=1

# Skip WebSocket connections
PW_SKIP_WS=1
```

### Extension Tests

```bash
# API base URL
APPLYLENS_API_BASE=http://localhost:8003

# Enable learning features
LEARNING_ENABLED=true

# Demo form URL
DEMO_FORM_URL=http://localhost:5178/test/demo-form.html
```

## Debugging Tests

### Playwright Inspector

```powershell
# Run with debug flag
npx playwright test --debug

# Pause on specific test
test.only('my test', async ({ page }) => {
  await page.pause(); // Opens inspector
  // ... rest of test
});
```

### Console Logs

```typescript
// Capture browser console
page.on('console', msg => console.log('BROWSER:', msg.text()));

// Capture network requests
page.on('request', req => console.log('→', req.method(), req.url()));
page.on('response', resp => console.log('←', resp.status(), resp.url()));
```

### Screenshots & Videos

```typescript
// playwright.config.ts
export default defineConfig({
  use: {
    screenshot: 'on',           // Take screenshot on failure
    video: 'retain-on-failure', // Save video on failure
    trace: 'on-first-retry',    // Save trace on retry
  },
});

// Manual screenshot in test
await page.screenshot({ path: 'screenshot.png' });
```

### HTML Report

```powershell
# Generate HTML report
npx playwright test --reporter=html

# Show report
npx playwright show-report
```

## CI/CD Integration

### GitHub Actions

```yaml
# .github/workflows/e2e.yml
name: E2E Tests

on: [push, pull_request]

jobs:
  test:
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

      - name: Run tests
        run: npx playwright test --reporter=list,junit,html
        env:
          BASE_URL: http://localhost:5173

      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: playwright-report
          path: playwright-report/
```

## Test Markers & Tags

### Playwright

```typescript
// Tag with @smoke
test('@smoke - Homepage loads', async ({ page }) => {
  await page.goto('/');
  await expect(page).toHaveTitle(/ApplyLens/);
});

// Tag with @prodSafe
test('@prodSafe - Auth endpoint valid', async ({ page }) => {
  const response = await page.request.get('/api/auth/me');
  expect([200, 401]).toContain(response.status());
});

// Run only smoke tests
// npx playwright test --grep @smoke

// Skip slow tests
// npx playwright test --grep-invert @slow
```

### Pytest

```python
# Mark with pytest.mark
@pytest.mark.smoke
def test_health_endpoint():
    response = client.get("/api/ops/diag/health")
    assert response.status_code == 200

@pytest.mark.integration
def test_extension_autofill():
    # ... test code ...

# Run only smoke tests
# pytest -m smoke

# Run everything except slow
# pytest -m "not slow"
```

## Best Practices

### 1. Independent Tests
- Each test should be able to run in isolation
- Don't rely on test execution order
- Clean up test data after each test

### 2. Stable Selectors
- Prefer `data-testid` over classes or text
- Use semantic selectors when possible
- Avoid brittle CSS selectors

### 3. Explicit Waits
- Use `waitForSelector`, `waitForResponse` instead of `sleep`
- Wait for network idle on page loads
- Use `waitForLoadState` for dynamic content

### 4. Meaningful Assertions
- Test user-visible behavior, not implementation
- Use descriptive error messages
- Group related assertions

### 5. Test Data
- Use factories or fixtures for test data
- Keep test data minimal and focused
- Clean up after tests

## Troubleshooting

### Tests Flaking
- Add explicit waits for async operations
- Check for race conditions
- Increase timeout for slow operations
- Use retry logic for network requests

### Auth Issues
- Verify `STORAGE_STATE` points to valid auth file
- Re-run login flow if session expired
- Check OAuth redirect URLs match environment

### Network Errors
- Verify API server is running
- Check CORS configuration
- Ensure backend is accessible from test environment

### Extension Not Loading
- Confirm extension directory has `manifest.json`
- Check Chrome args in playwright config
- Run in headed mode to see browser errors

## Resources

- [Playwright Documentation](https://playwright.dev/)
- [Vitest Documentation](https://vitest.dev/)
- [Pytest Documentation](https://docs.pytest.org/)
- [Testing Best Practices](https://playwright.dev/docs/best-practices)
