# Playwright E2E Test Runner

## Quick Start

Run all thread viewer E2E tests with one command:

```powershell
.\playwright.test-run.ps1
```

This script will:
1. ✅ Start backend API with dev routes enabled (`ALLOW_DEV_ROUTES=1`)
2. ✅ Start web preview server on port 5175
3. ✅ Run all thread viewer Playwright tests
4. ✅ Clean up background jobs when done

## What It Does

### Environment Setup
- Sets `ALLOW_DEV_ROUTES=1` → enables `/api/dev/seed-threads` endpoint
- Sets `PROD=0` → allows destructive tests (bulk mode) to run
- Sets `E2E_BASE_URL=http://127.0.0.1:5175` → tells Playwright to use external servers
- Sets `USE_EXTERNAL_SERVERS=1` → prevents Playwright from starting its own servers

### Server Management
- **Backend API**: `uvicorn app.main:app --host 127.0.0.1 --port 8003`
- **Web Preview**: `npm run preview -- --port 5175`
- Health checks both servers before running tests
- Automatically stops all background jobs when done

### Test Execution
Runs all thread viewer tests:
- `thread-viewer-basic-context.spec.ts` (Phases 1, 2, 5)
- `thread-viewer-triage-navigation.spec.ts` (Phase 3)
- `thread-viewer-bulk-mode.spec.ts` (Phases 4, 4.5, 4.6, 4.7)
- `thread-summary-feedback.spec.ts` (Phase 5.2)
- `thread-summary-feedback-no-regression.spec.ts` (Phase 5.2)

## Prerequisites

1. **Python + uvicorn** (for backend API)
   ```bash
   python --version  # Should be 3.8+
   pip install uvicorn
   ```

2. **Node.js + npm** (for web preview)
   ```bash
   node --version    # Should be 18+
   npm --version
   ```

3. **Playwright installed**
   ```bash
   cd apps/web
   npx playwright install
   ```

4. **Backend seeding implemented** (see `FINAL_IMPLEMENTATION_CHECKLIST.md`)
   - Edit `services/api/app/routers/dev_seed.py`
   - Replace TODO with actual ES/DB insert logic

## Expected Output

```
=== ApplyLens E2E Runner (Thread Viewer Phases 1–5.1) ===

[1/4] Starting backend API with dev routes enabled...
Waiting for API to start...
[OK] Backend responded: {"status":"ok"}

[2/4] Starting web preview server...
Waiting for web server to start...
[OK] Web server responding (status: 200)

[3/4] Running Playwright tests (thread viewer focus)...

Test Environment:
  PROD = 0
  ALLOW_DEV_ROUTES = 1
  E2E_BASE_URL = http://127.0.0.1:5175
  API: http://127.0.0.1:8003
  Web: http://127.0.0.1:5175

Running 5 tests using 5 workers
  ✓ [chromium] › thread-viewer-basic-context.spec.ts:9:7 (3.2s)
  ✓ [chromium] › thread-viewer-triage-navigation.spec.ts:9:7 (2.8s)
  ✓ [chromium] › thread-viewer-bulk-mode.spec.ts:8:7 (4.1s)
  ✓ [chromium] › thread-summary-feedback.spec.ts:9:7 (2.5s)
  ✓ [chromium] › thread-summary-feedback.spec.ts:78:7 (2.3s)

5 passed (15.0s)

[4/4] Stopping background jobs...

Done.
✅ All tests passed!
```

## Troubleshooting

### Port Already in Use
```
Error: listen EADDRINUSE: address already in use :::8003
```

**Solution**: Kill existing processes on ports 8003 or 5175
```powershell
# Find process on port 8003
netstat -ano | findstr "8003"
# Kill process (replace PID)
taskkill /PID <PID> /F

# Or restart your computer to clear all ports
```

### Backend Health Check Fails
```
[WARN] Backend health check failed.
```

**Possible causes**:
1. Python/uvicorn not installed
2. `/ready` endpoint not implemented (script continues anyway)
3. Backend takes longer than 3 seconds to start

**Solution**: Check backend logs in Job output

### Web Server Check Fails
```
[WARN] Web server check failed.
```

**Possible causes**:
1. Web app not built (`npm run build` in `apps/web`)
2. Preview server takes longer than 5 seconds to start
3. Port 5175 already in use

**Solution**: Build the web app first
```bash
cd apps/web
npm run build
```

### Tests Fail with Empty Inbox
```
Error: expect(locator).toBeVisible() failed
Locator: locator('[data-testid="thread-row"]').first()
```

**Cause**: Backend seeding not implemented or not working

**Solution**:
1. Check backend logs for `[DEV SEED] inbox seeding 3 threads`
2. Implement seeding logic in `services/api/app/routers/dev_seed.py`
3. See `FINAL_IMPLEMENTATION_CHECKLIST.md` for implementation guide

### Seed Endpoint Returns 403
```
[SEED] Dev routes disabled (ALLOW_DEV_ROUTES != 1)
```

**Cause**: Environment variable not passed to backend process

**Solution**: Verify script sets `$env:ALLOW_DEV_ROUTES = "1"` in the Job ScriptBlock

## Running Specific Tests

To run individual test files, use the standard Playwright commands after starting servers manually:

```powershell
# Terminal 1: Start backend
cd services/api
$env:ALLOW_DEV_ROUTES = "1"
uvicorn app.main:app --reload --port 8003

# Terminal 2: Start web
cd apps/web
npm run preview -- --port 5175

# Terminal 3: Run specific test
cd apps/web
$env:PROD = "0"
$env:E2E_BASE_URL = "http://localhost:5175"
npx playwright test tests/e2e/thread-viewer-basic-context.spec.ts
```

Or use the script and manually stop after one test run.

## CI/CD Integration

For CI pipelines, replicate the script's logic:

```yaml
- name: Run E2E Tests
  run: |
    # Start backend
    cd services/api
    export ALLOW_DEV_ROUTES=1
    uvicorn app.main:app --host 0.0.0.0 --port 8003 &
    sleep 5

    # Start web
    cd ../../apps/web
    npm run preview -- --port 5175 &
    sleep 5

    # Run tests
    export PROD=0
    export E2E_BASE_URL=http://localhost:5175
    npx playwright test tests/e2e/thread-viewer-*.spec.ts
```

## Production Mode

To skip destructive tests (bulk mode), set `PROD=1`:

```powershell
# Edit the script line:
$env:PROD = "1"  # Instead of "0"

# Or run manually:
$env:PROD = "1"
.\playwright.test-run.ps1
```

This will skip the bulk-mode test but still run all other tests.

## More Information

- **Complete Setup**: See `FINAL_IMPLEMENTATION_CHECKLIST.md`
- **Test Documentation**: See `THREAD_VIEWER_E2E_TESTS.md`
- **Seeding System**: See `E2E_TEST_SEEDING_SYSTEM.md`
- **All Docs**: See markdown files in repo root

## Support

If tests fail after following this guide:
1. Check `test-results/` folder for screenshots and traces
2. Run `npx playwright show-report` to view HTML report
3. See `FINAL_IMPLEMENTATION_CHECKLIST.md` for debugging steps
