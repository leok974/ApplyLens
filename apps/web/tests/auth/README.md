# Playwright Authentication for E2E Tests

Automated authentication setup for E2E tests using test-only backend endpoint.

## How It Works

1. **Backend**: `/api/auth/e2e/login` endpoint (only enabled with `E2E_PROD=1`)
2. **Frontend**: Playwright global setup calls endpoint before tests run
3. **Tests**: All tests automatically use the saved session

## Setup (One-time)

### 1. Generate shared secret

```powershell
# Generate a random secret
$secret = [Convert]::ToBase64String([System.Security.Cryptography.RandomNumberGenerator]::GetBytes(32))
Write-Host "E2E_SHARED_SECRET=$secret"
```

### 2. Configure environment variables

Add to your production environment (or `.env` for local testing):

```bash
# Enable E2E test endpoint
E2E_PROD=1

# Shared secret for E2E authentication (keep this private!)
E2E_SHARED_SECRET=your-generated-secret-here
```

### 3. Run E2E tests

```powershell
cd d:\ApplyLens\apps\web

# Set environment variables
$env:E2E_BASE_URL = "https://applylens.app"
$env:E2E_SHARED_SECRET = "your-generated-secret-here"

# Run tests - auth happens automatically
npx playwright test e2e/chat-agent-v2.spec.ts
```

## How Global Setup Works

When you run Playwright tests:

1. **Global setup** runs first (`tests/setup/global-setup-auth.ts`)
2. Calls `POST /api/auth/e2e/login` with `X-E2E-Secret` header
3. Backend creates session for `leoklemet.pa@gmail.com`
4. Session cookies saved to `tests/auth/prod.json`
5. **All tests** automatically load this auth state
6. Tests run as authenticated user

## Files

- `tests/auth/prod.json` - Auto-generated session file (gitignored)
- `tests/setup/global-setup-auth.ts` - Playwright global setup
- `services/api/app/routes_e2e_auth.py` - Backend test endpoint

## Without Authentication

If `E2E_SHARED_SECRET` is not set:

- Global setup skips auth (logs warning)
- Tests tagged with `@authRequired` skip gracefully
- No failures, just skipped tests

## Security

**Important:**
- Never commit `E2E_SHARED_SECRET` to git
- Only enable `E2E_PROD=1` on test infrastructure
- Endpoint validates secret on every request
- Session expires after 1 hour

## Troubleshooting

### Tests still skip

```powershell
# Verify secret is set
Write-Host $env:E2E_SHARED_SECRET

# Check if endpoint is enabled
curl https://applylens.app/api/auth/e2e/login -X POST -H "X-E2E-Secret: test"
# Should return 403 (not 404) if enabled
```

### Auth file not created

Check Playwright output for errors:

```powershell
npx playwright test e2e/chat-agent-v2.spec.ts --debug
```

Look for "🔧 E2E Global Setup" logs.

### Manual cookie extraction (fallback)

If automated auth fails, you can still manually extract cookies from Chrome:

1. Use the script in `scripts/save-chrome-cookies.js`
2. Follow instructions in the script
3. Save output to `tests/auth/prod.json`
