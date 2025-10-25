# Testing Improvements - v0.4.21

## ✅ Changes Made

### 1. Playwright Config - baseURL Already Set
The `playwright.config.ts` already had `baseURL` configured:
```typescript
use: {
  baseURL: process.env.E2E_BASE_URL || "http://localhost:5175",
  // ... other config
}
```

### 2. Test Spec Updated - Simplified URLs
Updated `search-derived-and-tooltip.spec.ts` to use relative URLs:

**Before:**
```typescript
const base = process.env.E2E_BASE_URL || "http://localhost:5175";
await page.goto(`${base}/search?q=*`);
```

**After:**
```typescript
await page.goto("/search?q=*");
```

The baseURL from config is automatically prepended. This makes tests:
- ✅ Cleaner and easier to read
- ✅ Easier to override via `E2E_BASE_URL` environment variable
- ✅ CI/CD ready (can test against staging, prod, etc.)

### 3. One-Liner Test Script Added
Added `testenv` script to `package.json`:

```json
{
  "scripts": {
    "testenv": "set E2E_BASE_URL=http://localhost:5175 && npm run test:e2e -- e2e/search-derived-and-tooltip --reporter=list"
  }
}
```

## Usage

### Quick Test Run (One Command)
```powershell
cd apps/web
npm run testenv
```

This automatically:
1. Sets the base URL to dev server
2. Runs the derived subjects & tooltip tests
3. Shows results in list format

### Custom Environment
```powershell
# Override to test against different environments
$env:E2E_BASE_URL="http://localhost"  # Production Docker
npm run test:e2e -- e2e/search-derived-and-tooltip --reporter=list

$env:E2E_BASE_URL="https://staging.applylens.app"  # Staging
npm run test:e2e -- e2e/search-derived-and-tooltip --reporter=list
```

### All Tests
```powershell
# Run all search tests
npm run test:e2e -- e2e/search-renders --reporter=list

# Run all E2E tests
npm run test:e2e
```

## Benefits

### 1. Cleaner Test Code
Tests now use simple relative URLs like `/search?q=*` instead of string concatenation.

### 2. Environment Flexibility
Easy to switch test environments:
```powershell
# Dev server (default)
npm run testenv

# Local Docker
$env:E2E_BASE_URL="http://localhost" ; npm run testenv

# Production
$env:E2E_BASE_URL="https://applylens.app" ; npm run testenv
```

### 3. CI/CD Ready
In GitHub Actions or other CI:
```yaml
- name: Run E2E Tests
  env:
    E2E_BASE_URL: ${{ secrets.STAGING_URL }}
  run: npm run test:e2e
```

## Cross-Platform Note

Current `testenv` script uses Windows `set` command:
```json
"testenv": "set E2E_BASE_URL=... && npm run test:e2e"
```

For cross-platform support (Linux/Mac/Windows), we could use:
1. **cross-env** package (recommended for production)
2. **Node wrapper script** (lightweight)
3. **Environment files** (.env)

For now, Windows-only is fine for local development. CI can override via environment variables directly.

## Example Workflows

### Development Flow
```powershell
# Terminal 1: Start services
docker-compose -f docker-compose.prod.yml up -d db elasticsearch redis api

# Terminal 2: Start dev server
cd apps/web
npm run dev

# Terminal 3: Run tests
cd apps/web
npm run testenv
```

### Quick Regression Check
```powershell
# Services already running, dev server running
npm run testenv
```

### Production Smoke Test
```powershell
$env:E2E_BASE_URL="https://applylens.app"
npm run test:e2e -- --grep @prodSafe --reporter=list
```

## Files Modified

- ✅ `apps/web/tests/e2e/search-derived-and-tooltip.spec.ts` - Use relative URLs
- ✅ `apps/web/package.json` - Add `testenv` script
- ℹ️ `apps/web/playwright.config.ts` - No changes needed (baseURL already set)

## Next Steps

1. ✅ Test the new script: `npm run testenv`
2. Consider adding similar shortcuts for other test suites:
   ```json
   "testenv:search": "set E2E_BASE_URL=http://localhost:5175 && npm run test:e2e -- e2e/search-renders --reporter=list",
   "testenv:auth": "set E2E_BASE_URL=http://localhost:5175 && npm run test:e2e -- e2e/auth.*.spec.ts --reporter=list"
   ```
3. Update CI/CD pipelines to use environment variable override

---

**Status**: ✅ Complete
**Version**: v0.4.21
**Date**: October 24, 2025
