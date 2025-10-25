# Production-Safe E2E Testing Guide

## Overview

This guide explains how to run E2E tests safely against production (`https://applylens.app`) using a read-only mode that prevents accidental data mutations.

## Architecture

### 1. Tag-Based Test Filtering

Tests are tagged to indicate their safety level:

- **`@prodSafe`**: Safe for production - GET-only operations, rendering checks, metrics
- **`@devOnly`**: Development only - mutations, auth flows, data changes

### 2. Production Read-Only Guard

The `prodGuard.ts` utility blocks all non-GET requests on production except an explicit allowlist:

```typescript
// Allowed on production:
✅ GET, HEAD, OPTIONS (always safe)
✅ POST to /api/ux/heartbeat (metrics)
✅ POST to /api/ux/beacon (analytics)

// Blocked on production:
❌ All other POST/PUT/PATCH/DELETE requests
```

### 3. Environment Detection

Playwright config automatically detects production via `E2E_BASE_URL`:

```typescript
const BASE = process.env.E2E_BASE_URL ?? "http://localhost:5175";
const IS_PROD = /^https:\/\/applylens\.app/.test(BASE);
```

When `IS_PROD` is true:
- Only `@prodSafe` tests run
- `@devOnly` tests are excluded
- Uses `prod.json` storage state
- No dev server started
- No demo auth setup

## Usage

### Running Tests Locally (Development)

```bash
# Runs all tests (including @devOnly)
pnpm test:e2e

# Run specific test suites
pnpm e2e:logo      # Header logo tests
pnpm e2e:heartbeat # Heartbeat tests
pnpm e2e:search    # Search interactions
```

**What runs**: All 41 tests (including auth flows, mutations)
**Auth**: Automatic demo login via `auth.setup.ts`
**Storage State**: `tests/.auth/demo.json`

### Running Tests on Production (Read-Only)

#### Step 1: Create Production Storage State (One-Time Setup)

```bash
# Launch interactive setup
pnpm --filter applylens-web exec tsx tests/setup/save-prod-state.ts
```

This will:
1. Open a browser to `https://applylens.app`
2. Wait for you to log in manually with a **dedicated test account**
3. Save cookies to `tests/.auth/prod.json`

**Security Notes**:
- Use a non-privileged test account (not your personal account)
- Test account should have minimal access
- `prod.json` is gitignored automatically
- Rotate credentials periodically

#### Step 2: Run Production Tests

```bash
# Run only @prodSafe tests on production
E2E_BASE_URL=https://applylens.app pnpm test:e2e
```

**What runs**: Only 11 @prodSafe tests (rendering, heartbeat, metrics)
**Auth**: Uses saved `prod.json` (no demo login)
**Storage State**: `tests/.auth/prod.json`
**Safety**: All mutations blocked by `prodGuard`

### Manual Prod Smoke Tests (CI)

The GitHub Actions workflow `.github/workflows/prod-smoke.yml` enables manual production testing:

1. Go to **Actions** → **Prod Smoke Tests**
2. Click **Run workflow**
3. Workflow will:
   - Check for `prod.json`
   - Run only `@prodSafe` tests
   - Upload reports on failure

**Note**: This workflow requires `prod.json` to be set up in the repository secrets or manually created before the first run.

## Test Authoring Guidelines

### ✅ What Qualifies as @prodSafe

```typescript
test("@prodSafe header renders correctly", async ({ page }) => {
  await installProdReadOnlyGuard(page);
  await page.goto("/inbox");
  await expect(page.getByTestId("header-brand")).toBeVisible();
});
```

**Safe for production**:
- Navigation and routing checks
- Layout and rendering validation
- GET-only API endpoints
- Metrics endpoints (heartbeat, analytics)
- Visual regression tests
- Accessibility checks

### ❌ What Should Be @devOnly

```typescript
test("@devOnly user can create new email", async ({ page }) => {
  // This mutates data - dev only!
  await page.goto("/compose");
  await page.fill("#subject", "Test");
  await page.click("#send");
});
```

**Development only**:
- POST/PUT/PATCH/DELETE operations
- OAuth flows and authentication
- Data backfills or sync jobs
- Rate limit testing
- Feature flags or A/B tests
- Database mutations

### Using the Production Guard

Every `@prodSafe` test MUST call `installProdReadOnlyGuard` at the start:

```typescript
import { installProdReadOnlyGuard } from "../utils/prodGuard";

test("@prodSafe my test", async ({ page }) => {
  // REQUIRED: Install guard first
  await installProdReadOnlyGuard(page);

  // Safe operations only
  await page.goto("/inbox");
  await expect(page.getByRole("heading")).toBeVisible();
});
```

This ensures that even if the test accidentally triggers a mutation (e.g., clicking a delete button), the request will be blocked at the network level.

## File Structure

```
apps/web/
├── playwright.config.ts          # Environment detection + test filtering
├── tests/
│   ├── .auth/
│   │   ├── demo.json            # Dev auth (gitignored)
│   │   └── prod.json            # Prod auth (gitignored, manual setup)
│   ├── setup/
│   │   ├── auth.setup.ts        # Auto demo login (dev only)
│   │   └── save-prod-state.ts   # Manual prod auth capture
│   ├── utils/
│   │   └── prodGuard.ts         # Read-only network guard
│   └── e2e/
│       ├── ux-heartbeat.spec.ts       # @prodSafe
│       └── auth.demo.spec.ts          # @devOnly
└── .github/
    └── workflows/
        └── prod-smoke.yml        # Manual prod testing workflow
```

## Configuration Reference

### Playwright Config (playwright.config.ts)

```typescript
const BASE = process.env.E2E_BASE_URL ?? "http://localhost:5175";
const IS_PROD = /^https:\/\/applylens\.app/.test(BASE);

export default defineConfig({
  // Only @prodSafe tests on prod
  grep: IS_PROD ? /@prodSafe/ : undefined,
  grepInvert: IS_PROD ? /@devOnly/ : undefined,

  use: {
    baseURL: BASE,
    // Switch storage state based on environment
    storageState: IS_PROD ? "tests/.auth/prod.json" : "tests/.auth/demo.json",
  },

  // Only run demo auth setup on dev
  globalSetup: IS_PROD ? undefined : "./tests/setup/auth.setup.ts",

  // Only start dev server locally
  webServer: IS_PROD ? undefined : { /* ... */ },
});
```

### Production Guard (prodGuard.ts)

```typescript
export async function installProdReadOnlyGuard(page: Page) {
  const IS_PROD = /^https:\/\/applylens\.app/.test(process.env.E2E_BASE_URL ?? "");

  if (!IS_PROD) return; // No-op on dev

  await page.route('**/*', (route) => {
    const method = route.request().method();
    const url = route.request().url();

    // Allow safe methods
    if (method === "GET" || method === "HEAD" || method === "OPTIONS") {
      return route.continue();
    }

    // Allow specific metrics endpoints
    if (method === "POST" && /\/api\/ux\/(heartbeat|beacon)$/.test(url)) {
      return route.continue();
    }

    // Block all other mutations
    console.warn(`🚫 Blocked ${method} ${url}`);
    return route.abort('failed');
  });
}
```

## Test Results Summary

### Development (Localhost)
- **Total Tests**: 41
- **Included**: All tests (@prodSafe + @devOnly)
- **Auth**: Automatic demo login
- **Safety**: No restrictions

### Production (applylens.app)
- **Total Tests**: 11
- **Included**: Only @prodSafe tests
- **Auth**: Manual prod.json
- **Safety**: Read-only guard blocks mutations

## Tagged Tests Inventory

### @prodSafe Tests (11 total)

**Heartbeat Tests** (4):
- ✅ Heartbeat endpoint is CSRF-exempt
- ✅ Accepts minimal payload
- ✅ Accepts meta field
- ✅ Validates required fields

**Header Logo Tests** (7):
- ✅ Header logo is large
- ✅ Logo scales on mobile
- ✅ Header height correct
- ✅ Wordmark sized properly
- ✅ Inbox layout single column
- ✅ No gradient halo remnants
- ✅ Logo appears across all pages

### @devOnly Tests (3 total)

**Auth Tests**:
- ❌ Demo login flow
- ❌ Google OAuth mock
- ❌ Logout clears session

## Troubleshooting

### Error: "prod.json not found"

**Solution**: Run the prod setup script:
```bash
pnpm --filter applylens-web exec tsx tests/setup/save-prod-state.ts
```

### Error: "No tests found" on production

**Cause**: No tests are tagged with `@prodSafe`

**Solution**: Add `@prodSafe` tag to test names:
```typescript
test("@prodSafe my test", async ({ page }) => { /* ... */ });
```

### Tests fail with "Network error" on production

**Cause**: Production guard blocked a mutation

**Solution**: Either:
1. Tag test as `@devOnly` if it requires mutations
2. Add endpoint to allowlist in `prodGuard.ts` if it's safe

### Auth cookie expired on production

**Cause**: `prod.json` storage state is outdated

**Solution**: Re-run the setup script:
```bash
pnpm --filter applylens-web exec tsx tests/setup/save-prod-state.ts
```

## Best Practices

1. **Always tag new tests** - Default to `@devOnly` for safety
2. **Install guard in every @prodSafe test** - Use `installProdReadOnlyGuard(page)`
3. **Use dedicated test account** - Never use personal credentials
4. **Rotate prod.json regularly** - Refresh cookies monthly
5. **Review allowlist carefully** - Only add truly safe endpoints
6. **Test locally first** - Verify @prodSafe tests work before prod run
7. **Monitor CI artifacts** - Check for blocked requests in logs

## Security Considerations

### Multi-Layer Safety

1. **Tag Filtering**: Only @prodSafe tests selected
2. **Network Guard**: Blocks mutations at network level
3. **Test Account**: Limited privileges
4. **Manual Trigger**: Prod tests never run automatically

### What Could Still Go Wrong?

- **GET with side effects**: If your API has GET endpoints that mutate data (anti-pattern), the guard won't catch them
- **Allowlisted endpoints**: If you add an unsafe endpoint to the allowlist
- **Test account permissions**: If the test account has elevated privileges

### Mitigation

- **Code review**: Review any changes to `prodGuard.ts` allowlist
- **Audit logs**: Monitor production API logs for test account activity
- **Principle of least privilege**: Give test account minimal access
- **Regular rotation**: Rotate test account credentials

## Migration Checklist

If you're adding this to an existing project:

- [ ] Install production guard utility
- [ ] Update Playwright config with environment detection
- [ ] Tag all existing tests (@prodSafe or @devOnly)
- [ ] Add guard calls to @prodSafe tests
- [ ] Create prod setup script
- [ ] Create prod smoke workflow
- [ ] Add prod.json to .gitignore
- [ ] Document test account creation
- [ ] Set up test account with minimal privileges
- [ ] Run initial prod.json setup
- [ ] Test locally with E2E_BASE_URL
- [ ] Verify tag filtering works
- [ ] Run first prod smoke test
- [ ] Document in team wiki

## Further Reading

- [Playwright Best Practices](https://playwright.dev/docs/best-practices)
- [Test Tags](https://playwright.dev/docs/test-annotations#tag-tests)
- [Storage State](https://playwright.dev/docs/auth#reuse-signed-in-state)
- [Network Interception](https://playwright.dev/docs/network#handle-requests)
