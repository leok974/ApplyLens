# Smoke Tests with Inbox Seeding

These tests verify basic API functionality after seeding the inbox with test data.

## Quick Start

### Using npm/pnpm scripts (Recommended)
```powershell
# Run smoke tests only
pnpm test:smoke

# Run full E2E suite with limited workers
pnpm test:e2e

# Open Playwright UI for debugging
pnpm test:e2e:ui

# Run with trace recording
pnpm test:e2e:trace
```

## Running Tests

### Option 1: Using the Launcher Script
```powershell
# From repository root - starts everything and runs tests
.\launch-applylens-workday.ps1

# With custom seed count
.\launch-applylens-workday.ps1 -SeedCount 100

# For production environment
.\launch-applylens-workday.ps1 -Env prod
```

### Option 2: Using VS Code Tasks
1. Open Command Palette: `Ctrl+Shift+P`
2. Type: `Tasks: Run Task`
3. Select one of:
   - **Run Smoke Tests** (default test task)
   - **Run Full E2E Suite**
   - **Run E2E with UI Mode**
   - **Run E2E with Trace**
   - **Run Smoke Tests (Production)**

Or press `Ctrl+Shift+B` to see build/test tasks.

### Option 3: Direct Commands

**Local Environment:**
```powershell
# Set environment variables
$env:ALLOW_DEV_ROUTES = "1"                     # Enable dev routes in API
$env:E2E_BASE_URL = "http://127.0.0.1:8000"     # API on port 8000
$env:E2E_API      = "http://127.0.0.1:8000/api" # API base
$env:SEED_COUNT   = "40"                        # number of threads to seed
$env:USE_SMOKE_SETUP = "true"                   # use global.setup.ts for seeding

# Run smoke tests only
npx playwright test tests/smoke/inbox-has-data.spec.ts --config=playwright.config.ts --workers=2

# Run full suite (limit workers so ES/API don't get hammered)
npx playwright test --config=playwright.config.ts --workers=2
```

**Production Environment:**
```powershell
$env:E2E_BASE_URL = "https://applylens.app"
$env:E2E_API      = "https://applylens.app/api"
$env:SEED_COUNT   = "40"   # only if your prod seed route is allowed; otherwise omit
$env:USE_SMOKE_SETUP = "false"  # skip seeding in production

# Only run smoke tests
npx playwright test tests/smoke/inbox-has-data.spec.ts --config=playwright.config.ts --workers=2
```

## Debugging

### Open Playwright UI Runner
```powershell
# Interactive UI mode
npx playwright test --ui --workers=1

# Or use npm script
pnpm test:e2e:ui
```

### Save Traces for Failures
```powershell
# Record traces
npx playwright test --trace=on --workers=1

# Or use npm script
pnpm test:e2e:trace
```

## Ramping Safely

To safely increase load on your ES/API, gradually ramp up workers:

```powershell
# 1. Start with smoke tests (2 workers)
pnpm test:smoke

# 2. Run with 4 workers
npx playwright test --workers=4

# 3. Then 6 workers
npx playwright test --workers=6

# 4. Then 8 workers (or your system max)
npx playwright test --workers=8
```

**Why ramp gradually?**
- Prevents overwhelming Elasticsearch/API
- Identifies bottlenecks at different load levels
- Allows monitoring of system behavior under increasing load
- Helps tune worker count for optimal performance

**Recommended approach:**
1. Run smoke tests first to verify basic functionality
2. Monitor system resources (CPU, memory, ES performance)
3. Increase workers incrementally
4. Stop at the sweet spot where tests run fast without errors

## What the Tests Do

1. **Global Setup** (`global.setup.ts`):
   - Fetches CSRF token from `/auth2/google/csrf`
   - Seeds inbox with test threads via `/dev/seed-threads`
   - Runs once before all tests

2. **Smoke Tests** (`inbox-has-data.spec.ts`):
   - Verifies `/ready` endpoint returns healthy status
   - Checks that `/actions/tray` returns seeded data

## Configuration

The smoke tests use:
- `workers: 2` - Limited parallelization to avoid hammering ES/API
- `fullyParallel: false` - Sequential execution to avoid race conditions
- `globalSetup: './tests/global.setup.ts'` - Data seeding before tests (when `USE_SMOKE_SETUP=true`)

## Available npm Scripts

```json
{
  "test:smoke": "Run smoke tests with 2 workers",
  "test:e2e": "Run full E2E suite with 2 workers",
  "test:e2e:ui": "Open Playwright UI runner (1 worker)",
  "test:e2e:trace": "Run with trace recording (1 worker)"
}
```

## Environment Variables

- `E2E_BASE_URL` - API URL (e.g., `http://127.0.0.1:8000`)
- `E2E_API` - Full API URL with `/api` (e.g., `http://127.0.0.1:8000/api`)
- `SEED_COUNT` - Number of threads to seed (default: 40)
- `USE_SMOKE_SETUP` - Set to `"true"` to use inbox seeding setup, `"false"` to skip
- `ALLOW_DEV_ROUTES` - Set to `"1"` in API server environment to enable seed endpoint

**API Requirements:**
- API must have `ALLOW_DEV_ROUTES=1` environment variable set to enable seed endpoint
- API should run on port 8000 for local development
- User authentication handled automatically via Playwright request context
