# E2E Testing Guide

## Quick Start

### Running Core Tests

```bash
cd apps/web

# Set environment variables
export E2E_BASE_URL="http://127.0.0.1:8888"
export E2E_API="$E2E_BASE_URL/api"
export USE_SMOKE_SETUP="true"
export SEED_COUNT="20"

# Run core authentication and search flows
npx playwright test tests/e2e/auth.demo.spec.ts \
  tests/e2e/auth.logout.spec.ts \
  tests/e2e/search-populates.spec.ts \
  --workers=2
```

### Windows (PowerShell)

```powershell
cd apps\web

$env:E2E_BASE_URL='http://127.0.0.1:8888'
$env:E2E_API='http://127.0.0.1:8888/api'
$env:USE_SMOKE_SETUP='true'
$env:SEED_COUNT='20'

npx playwright test tests/e2e/auth.demo.spec.ts tests/e2e/auth.logout.spec.ts tests/e2e/search-populates.spec.ts --workers=2
```

## Environment Variables

### Required

- **E2E_BASE_URL**: Base URL of the web application (default: `http://127.0.0.1:8000`)
- **E2E_API**: API endpoint URL (default: `http://127.0.0.1:8000/api`)

### Optional

- **USE_SMOKE_SETUP**: Enable inbox seeding in global setup (default: `false`, set to `"true"` for smoke tests)
- **SEED_COUNT**: Number of email threads to seed (default: `40`, recommend `20` for faster tests)
- **ALLOW_DEV_ROUTES**: Enable dev-only routes in API (must be `"1"` for E2E tests)
- **CI**: Set to any value to enable CI mode (2 workers, 1 retry)

## Architecture

### Test Setup Flow

1. **Global Setup** (`tests/global.setup.ts`)
   - Gets CSRF token from `/auth/csrf`
   - Authenticates with `/auth/demo/start`
   - Seeds inbox with test data (if `USE_SMOKE_SETUP=true`)
   - Saves storage state with cookies for subsequent tests

2. **Test Execution**
   - Each test loads the saved storage state (authenticated session)
   - Tests run in parallel (default 4 workers locally, 2 in CI)
   - Console logs captured via `console-listeners` fixture

3. **Cleanup**
   - Database state persists between tests (use unique test data)
   - Storage state regenerated on each test run

## Common Failures & Solutions

### 1. CSRF Token Issues

**Symptom**: 403 Forbidden on POST requests

**Cause**: CSRF token not included or expired

**Solution**:
```typescript
// Use apiFetch wrapper (auto-includes CSRF)
import { apiFetch } from '@/lib/apiBase';
await apiFetch('/api/auth/logout', { method: 'POST' });
```

**Check**: Global setup should log "CSRF token extracted"

### 2. Rate Limiting

**Symptom**: 429 Too Many Requests

**Cause**: Too many requests in short time (default: 60 req/60s)

**Solution**: Increase rate limit for dev/test:
```bash
# In API .env
APPLYLENS_RATE_LIMIT_MAX_REQ=300
```

**Check**: API logs should show rate limit configuration on startup

### 3. Dev Routes Not Available

**Symptom**: 404 on `/api/dev/*` or `/api/security/*` endpoints

**Cause**: `ALLOW_DEV_ROUTES` not set to `"1"`

**Solution**:
```bash
# In API .env or environment
export ALLOW_DEV_ROUTES="1"
```

**Check**: API logs should show "Dev routes enabled" on startup

### 4. Session/Cookie Issues

**Symptom**: LoginGuard shows "retrying" or redirects to /welcome unexpectedly

**Cause**: Session cookie not saved/restored properly

**Solution**:
- Check that global setup completes successfully
- Verify `tests/.auth/storageState.json` exists and has cookies
- Clear storage state and re-run: `rm tests/.auth/storageState.json`

**Check**: Global setup should log "Storage state saved"

### 5. Nginx Proxy Issues

**Symptom**: CORS errors, 502 Bad Gateway, or "Network error"

**Cause**: Nginx not running or misconfigured

**Solution**:
```bash
# Restart Nginx
cd infra
docker compose restart web

# Check Nginx is running on port 8888
curl -I http://127.0.0.1:8888/
```

**Check**: Should return 200 OK with HTML

### 6. Database Connection Errors

**Symptom**: "Connection refused" or "Database not found"

**Cause**: PostgreSQL not running or wrong credentials

**Solution**:
```bash
# Check database is running
docker compose ps db

# Check connection
docker compose exec db psql -U applylens -d applylens -c "SELECT 1;"
```

**Check**: Should return `(1 row)`

## Test Categories

### Authentication Tests (`tests/e2e/auth.*.spec.ts`)

- **auth.demo.spec.ts**: Demo login flow (landing → demo → inbox)
- **auth.logout.spec.ts**: Logout clears session and redirects
- **auth.logout.regression.spec.ts**: Regression tests for logout bugs

**Tags**: `@devOnly` (uses demo auth, not safe for production)

### Search Tests (`tests/e2e/search-*.spec.ts`)

- **search-populates.spec.ts**: Search returns results after backfill
- **search-form.spec.ts**: Search form interactions
- **search-renders.spec.ts**: Search UI rendering

**Tags**: `@prodSafe` (safe to run against production data)

### UI Tests (`tests/e2e/ux-*.spec.ts`)

- **ux-heartbeat.spec.ts**: Core UI elements render and are interactive

**Tags**: `@prodSafe`

## Debugging Tips

### Run Tests Headed (See Browser)

```bash
npx playwright test tests/e2e/auth.logout.spec.ts --headed
```

### Run with Trace

```bash
npx playwright test tests/e2e/auth.logout.spec.ts --trace=on
```

### View Trace File

```bash
npx playwright show-trace test-results/[test-name]/trace.zip
```

### Open Last HTML Report

```bash
npx playwright show-report
```

### Run Single Test

```bash
npx playwright test tests/e2e/auth.logout.spec.ts
```

### Run with Specific Worker Count

```bash
npx playwright test --workers=1  # Sequential
npx playwright test --workers=4  # Parallel (faster)
```

### Enable Verbose Logging

```bash
DEBUG=pw:api npx playwright test
```

## Writing New Tests

### Template

```typescript
import { test, expect } from '../setup/console-listeners';

test.describe('My Feature', () => {
  test('should do something', async ({ page }) => {
    // Navigate
    await page.goto('/my-page');

    // Wait for element
    await page.waitForSelector('[data-testid="my-button"]');

    // Interact
    await page.getByTestId('my-button').click();

    // Assert
    await expect(page).toHaveURL(/\/expected-path/);
    await expect(page.getByText('Success')).toBeVisible();
  });
});
```

### Best Practices

1. **Use data-testid for selectors**: More stable than text or CSS classes
2. **Wait for navigation**: Use `page.waitForURL()` after actions that navigate
3. **Use console-listeners fixture**: Captures console errors/warnings
4. **Tag appropriately**: `@devOnly` or `@prodSafe`
5. **Clean up test data**: Use unique IDs or delete after test
6. **Avoid hard waits**: Use `waitForSelector`, `waitForURL`, etc.

## CI Integration

### GitHub Actions Example

```yaml
- name: E2E Tests (Core Flows)
  run: |
    cd apps/web
    export E2E_BASE_URL="http://127.0.0.1:8888"
    export E2E_API="$E2E_BASE_URL/api"
    export USE_SMOKE_SETUP="true"
    export SEED_COUNT="20"
    npx playwright install --with-deps chromium
    npx playwright test tests/e2e/auth.demo.spec.ts \
      tests/e2e/auth.logout.spec.ts \
      tests/e2e/search-populates.spec.ts \
      --workers=2
```

### Troubleshooting CI Failures

1. **Check environment variables**: CI may not inherit .env files
2. **Check service health**: Database, Elasticsearch, API all running?
3. **Check rate limits**: CI may hit limits faster (increase limits)
4. **Check timing**: CI may be slower (increase timeouts)
5. **Check artifacts**: Download test-results from CI for debugging

## Performance Tips

### Faster Test Runs

1. **Reduce SEED_COUNT**: Use `20` instead of `40`
2. **Run subset of tests**: Only run changed tests
3. **Increase workers**: Use `--workers=4` (or more if CPU allows)
4. **Use fullyParallel**: Set to `true` in config if tests are independent

### Slower, More Stable Runs

1. **Sequential execution**: Use `--workers=1`
2. **Increase timeouts**: Set `timeout: 60000` in config
3. **Disable parallel**: Set `fullyParallel: false`

## Maintenance

### Update Baseline Data

```bash
# Regenerate storage state
rm tests/.auth/storageState.json
npm run test:e2e
```

### Update Snapshots

```bash
npx playwright test --update-snapshots
```

### Clean Test Results

```bash
rm -rf test-results/
rm -rf playwright-report/
```

## Resources

- [Playwright Documentation](https://playwright.dev)
- [Playwright Best Practices](https://playwright.dev/docs/best-practices)
- [Debugging Tests](https://playwright.dev/docs/debug)
