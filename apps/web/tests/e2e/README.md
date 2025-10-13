# E2E Test Suite Guide

## Overview

This directory contains end-to-end tests for the ApplyLens web application using Playwright.

## Quick Start

```bash
# Run all tests
npm run test:e2e

# Run with visible browser
npm run test:e2e:headed

# Run smoke tests only
npm run test:e2e:smoke

# Run with Playwright UI (interactive)
npm run test:e2e:ui
```

## Network Control

### Deny-by-Default Network Policy

To prevent accidental external network requests during tests:

```bash
# Unix/Linux/macOS
PW_LOCK_NET=1 npm run test:e2e

# Windows PowerShell
$env:PW_LOCK_NET='1'; npm run test:e2e; Remove-Item Env:\PW_LOCK_NET

# Smoke tests with locked network
npm run test:e2e:smoke:locked  # Unix/macOS/Linux only
```

**Note:** On Windows, the `test:e2e:smoke:locked` script won't work directly. Use the PowerShell syntax above or set the environment variable in your CI/CD pipeline.

### How It Works

When `PW_LOCK_NET=1` is set, a global `beforeEach` hook enforces a deny-by-default network policy that:

- Blocks all external network requests (returns HTTP 418)
- Allows localhost requests (your dev server)
- Allows WebSocket connections (for HMR)
- Allows data:, about:, and blob: URLs

Tests can still mock APIs using `withMockedNet([...])` - those mocks take precedence over the lock.

## Test Utilities

### assertToast Helper

Clean, reusable helper for toast assertions:

```typescript
import { assertToast } from './utils'

// Check title and variant
await assertToast(page, { 
  title: /Note saved/i, 
  variant: 'success' 
})

// Check title and description
await assertToast(page, { 
  title: /Status: Interview/i, 
  desc: /Acme AI/i,
  variant: 'success'
})

// Custom timeout
await assertToast(page, { 
  title: /Saved/i, 
  timeout: 10000 
})
```

**Benefits:**

- Type-safe assertions
- Consistent error messages
- Automatic visibility checks
- Flexible matching (string or regex)

### Test Factories

DRY up mock data creation with factories:

```typescript
import { appRow, listResponse, patchResponse } from './factories'

const row = appRow({ 
  id: 404, 
  company: 'Anthropic', 
  role: 'Research Engineer',
  notes: '',
})

await withMockedNet([
  {
    url: '/api/applications',
    method: 'GET',
    body: listResponse([row]),
  },
  {
    url: '/api/applications/404',
    method: 'PATCH',
    body: patchResponse(row, { notes: 'Updated' }),
  },
])
```

**Factory Functions:**

- `appRow(overrides)` - Creates an application row with sensible defaults
- `listResponse(rows)` - Wraps rows in a list response
- `patchResponse(prev, patch)` - Creates an updated row with new `updated_at`

**Benefits:**

- Less boilerplate in tests
- Consistent test data structure
- Easy to update defaults globally
- Type-safe with TypeScript

## Authentication Tests

```bash
# Bootstrap authentication state
npm run test:e2e:login

# Run tests with authentication
npm run test:e2e:auth

# Refresh authentication state
npm run test:e2e:auth:refresh
```

Set these environment variables to configure login:

- `RUN_LOGIN=1` - Enable login bootstrap test
- `LOGIN_USER` - Username selector
- `LOGIN_PASS` - Password selector
- `LOGIN_SUCCESS_URL` - Expected URL after login
- `STORAGE_STATE` - Path to save authentication state

## Fixtures

### mockApi

Mock API endpoints declaratively:

```typescript
await mockApi([
  { url: '/api/applications', method: 'GET', body: [...] },
  { url: '/api/applications/123', method: 'PATCH', body: {...} },
])
```

### enforceNetworkPolicy

Deny-by-default network policy (blocks external requests):

```typescript
await enforceNetworkPolicy()
```

### withMockedNet

Convenience fixture that installs mocks then enforces network policy:

```typescript
await withMockedNet([
  { url: '/api/applications', method: 'GET', body: [...] },
])
```

## CI/CD Integration

### GitHub Actions Example

```yaml
- name: Run E2E Tests (Locked Network)
  env:
    CI: 'true'
    PW_LOCK_NET: '1'
  run: |
    npm run test:e2e -- --reporter=list,junit,html
```

### Sharding (Parallel Execution)

```yaml
strategy:
  matrix:
    shard: [1, 2, 3, 4]
steps:
  - name: Run Tests (Shard ${{ matrix.shard }}/4)
    env:
      PW_LOCK_NET: '1'
    run: |
      npx playwright test --shard=${{ matrix.shard }}/4
```

## Project Structure

```
tests/e2e/
├── fixtures.ts          # Custom Playwright fixtures
├── utils.ts             # Test helper functions (assertToast)
├── factories.ts         # Test data factories
├── *.spec.ts            # Test files
└── .auth/               # Authentication state storage
```

## Best Practices

1. **Use assertToast** instead of manual toast checks
2. **Use factories** for creating test data
3. **Use withMockedNet** to mock APIs and enforce network policy
4. **Enable PW_LOCK_NET** in CI to catch accidental external requests
5. **Use data-testid** for stable element selection
6. **Tag smoke tests** with `@smoke` for quick validation

## Troubleshooting

### Tests failing with network errors

If you see "Blocked outbound network request" errors:

- Add the URL to your mocks with `withMockedNet([...])`
- Or temporarily allow network with `PW_ALLOW_NET=1`

### TypeScript errors with process.env

Install `@types/node`:

```bash
npm install --save-dev @types/node
```

### Tests timing out

- Check that your dev server is running on the expected port
- Verify API mocks are matching the correct URLs
- Increase timeout in test or assertion: `{ timeout: 10000 }`
