# Playwright Authentication States

This directory contains Playwright storage state files for authenticated E2E tests.

## Files (gitignored)

- `prod.json` - Production session cookies for https://applylens.app
- `*.json` - All JSON files in this directory are gitignored to protect credentials

## Generating prod.json

To run authenticated E2E tests against production, you need to generate a session file:

```powershell
# From apps/web directory
cd d:\ApplyLens\apps\web

# Open browser, log in, and save session
npx playwright codegen https://applylens.app --save-storage=tests/auth/prod.json
```

**Flow:**
1. Browser opens to https://applylens.app
2. Click "Sign in with Google" and authenticate
3. Once logged in and you can see the app (e.g., /chat page), close the browser
4. Playwright saves cookies/session to `tests/auth/prod.json`

**Verify file created:**
```powershell
Get-Item tests/auth/prod.json
```

## Running authenticated tests

```powershell
# Set environment variables
$env:E2E_BASE_URL = "https://applylens.app"
$env:E2E_AUTH_STATE = "tests/auth/prod.json"

# Run Agent V2 UI tests with authentication
npx playwright test tests/e2e/chat-agent-v2.spec.ts
```

## Without authentication

If `E2E_AUTH_STATE` is not set, tests tagged with `@authRequired` will be skipped (not failed):

```powershell
# Tests will skip gracefully
$env:E2E_BASE_URL = "https://applylens.app"
npx playwright test tests/e2e/chat-agent-v2.spec.ts
```

Output: `E2E_AUTH_STATE not configured; skipping Agent V2 UI tests that require authenticated session.`

## Session expiration

If cookies expire, tests will fail with auth errors. Regenerate `prod.json` using the codegen command above.

## Security

**Never commit authentication files to git!** The `.gitignore` pattern `/tests/.auth/` prevents accidental commits.
