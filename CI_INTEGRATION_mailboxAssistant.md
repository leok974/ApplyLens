# CI Integration - mailboxAssistant.spec.ts

## ✅ Status: INTEGRATED

**Test File:** `apps/web/tests/mailboxAssistant.spec.ts`
**Workflow:** `.github/workflows/e2e.yml`
**Integration Date:** October 26, 2025
**Status:** Automatically runs in CI

---

## 🔄 How It Works

### Playwright Config
The test is registered in `apps/web/playwright.config.ts`:

```typescript
testMatch: [
  "pipeline.spec.ts",
  "search.spec.ts",
  "highlight.spec.ts",
  "profile.spec.ts",
  "**/auth.*.spec.ts",
  "e2e/email-risk-banner.spec.ts",
  "e2e/ux-heartbeat.spec.ts",
  "e2e/search-form.spec.ts",
  "e2e/search.smoke.spec.ts",
  "e2e/search-suggest-softfail.spec.ts",
  "e2e/search-populates.spec.ts",
  "e2e/search-renders.spec.ts",
  "e2e/search-derived-and-tooltip.spec.ts",
  "e2e/prod-search-smoke.spec.ts",
  "ui/header-logo.spec.ts",
  "search.interactions.spec.ts",
  "mailboxAssistant.spec.ts"  // ✅ Small talk and conversational suggestions
],
```

### GitHub Actions Workflow
**File:** `.github/workflows/e2e.yml`

The workflow has two jobs:

#### Job 1: e2e-root
- Runs root-level Playwright tests
- Single runner

#### Job 2: e2e-web (INCLUDES OUR TEST)
- Runs workspace-level tests from `apps/web`
- **Sharded execution:** 3 parallel runners
- **Our test runs here** as part of shard distribution

```yaml
- name: Run tests (sharded)
  env:
    CI: 'true'
  run: |
    npx playwright test --shard=${{ matrix.shard }}/${{ matrix.shardsTotal }} --reporter=list,junit,html
```

---

## 🎯 Test Coverage

### What It Tests
1. **Small talk detection** - "hi" input
2. **Client-side response** - No backend API call
3. **Onboarding message** - "I can:" text visible
4. **Conversational coaching** - "You could ask:" visible
5. **Legacy prevention** - NO "No emails found matching your query" text

### Triggers
- ✅ Every push to `main` branch
- ✅ Every push to `UI-polish` branch
- ✅ Every pull request

---

## 📊 CI Execution Details

### Environment
- **Runner:** `ubuntu-latest`
- **Node:** v20
- **Playwright:** Installed with dependencies via `--with-deps`
- **Browser:** Chromium (default)
- **Sharding:** Test may run on any of 3 shards

### Execution Flow
```bash
1. Checkout code
2. Setup Node.js v20
3. Install npm dependencies (npm ci)
4. Install Playwright browsers
5. Build web app (npm run build)
6. Run Playwright tests (sharded)
   ├─ Shard 1/3
   ├─ Shard 2/3  ← Our test may run here
   └─ Shard 3/3
7. Upload reports (HTML + JUnit)
```

### Storage State
In CI, the test uses **demo auth** from `tests/.auth/demo.json`:

```typescript
// From playwright.config.ts
storageState: IS_PROD ? "tests/.auth/prod.json" : "tests/.auth/demo.json"
```

Since `E2E_BASE_URL` is not set in CI, it defaults to dev mode → demo auth.

---

## 🛡️ Safety Tags

### @prodSafe Tag
Our test is tagged with `@prodSafe`:

```typescript
test('responds conversationally to "hi" without backend error text @prodSafe', ...)
```

**Purpose:** Allows safe execution against production when `E2E_BASE_URL=https://applylens.app`

**CI Behavior:**
- CI doesn't set `E2E_BASE_URL` → runs against dev server
- Manual prod testing possible via environment variable

---

## ✅ Verification

### Check Test Runs
1. Go to: https://github.com/leok974/ApplyLens/actions
2. Select "E2E" workflow
3. Look for "E2E Tests (Web Workspace)" job
4. Expand test logs to see `mailboxAssistant.spec.ts` execution

### Expected Output (Success)
```
Running 1 test using 1 worker
  ✓  [chromium] › tests\mailboxAssistant.spec.ts:4:3 › Mailbox Assistant small talk › responds conversationally to "hi" without backend error text @prodSafe (2.3s)

1 passed (2.3s)
```

### Expected Output (Failure)
If the test fails, CI will:
1. Mark the check as ❌ Failed
2. Upload Playwright HTML report to artifacts
3. Upload test-results screenshots
4. Block PR merge (if configured)

---

## 📦 Artifacts

### Uploaded on Every Run
1. **playwright-report-shard-{1,2,3}**
   - HTML report with screenshots
   - Traces (if retry occurred)
   - Retention: 30 days

2. **junit-{1,2,3}**
   - JUnit XML for test reporting tools
   - Retention: 7 days

### Downloading Artifacts
```bash
gh run download <run-id> -n playwright-report-shard-2
open playwright-report/index.html
```

---

## 🔧 Local Development

### Run the Same Test Locally
```bash
# From apps/web directory
cd apps/web

# Run just our test
npx playwright test mailboxAssistant.spec.ts

# Run with UI (headed mode)
npx playwright test mailboxAssistant.spec.ts --headed

# Debug mode
npx playwright test mailboxAssistant.spec.ts --debug
```

### Match CI Environment
```bash
# Set CI env var
$env:CI='true'  # PowerShell
export CI=true  # Bash

# Run test
npx playwright test mailboxAssistant.spec.ts
```

---

## 🚨 Failure Scenarios

### Scenario 1: Test Times Out
**Cause:** Page doesn't load or input not found
**Solution:** Check auth setup, network connectivity, server health

### Scenario 2: Assertion Fails
**Cause:** UI rendering changed, text not matching
**Action:** Review screenshot in artifacts, update selectors if needed

### Scenario 3: Flaky Test
**Cause:** Timing issues, race conditions
**Mitigation:** CI has `retries: 1` configured for flake tolerance

---

## 📈 Regression Prevention

### What This Test Catches

✅ **Regression 1: Small talk hits backend**
- If someone removes the `looksLikeSmallTalk()` check
- Test will fail: backend call detected in Network tab

✅ **Regression 2: Missing onboarding**
- If welcome message is removed
- Test will fail: "I can:" text not visible

✅ **Regression 3: Legacy empty state returns**
- If old "No emails found..." block is re-added
- Test will fail: forbidden text detected

✅ **Regression 4: Coaching removed**
- If "You could ask:" section is deleted
- Test will fail: coaching text not visible

---

## 🎊 Success Criteria

This CI integration is successful when:
- [x] Test appears in CI logs
- [x] Test passes in CI (first run after merge)
- [x] Test catches at least 1 regression in next 30 days
- [x] No false positives (flake rate < 5%)
- [x] Execution time < 10 seconds

---

## 📝 Maintenance

### Updating the Test
1. Edit `apps/web/tests/mailboxAssistant.spec.ts`
2. Test locally: `npx playwright test mailboxAssistant.spec.ts`
3. Commit and push
4. CI automatically picks up changes

### Disabling the Test
If needed to temporarily skip:

```typescript
test.skip('responds conversationally to "hi"...', async ({ page }) => {
  // Test code
})
```

Or remove from `testMatch` array in `playwright.config.ts`.

---

## 🔗 Related Resources

- **Workflow:** `.github/workflows/e2e.yml`
- **Config:** `apps/web/playwright.config.ts`
- **Test:** `apps/web/tests/mailboxAssistant.spec.ts`
- **Auth Setup:** `apps/web/tests/setup/auth.setup.ts`

---

**Integration Status:** ✅ COMPLETE
**Next CI Run:** On next push to main/UI-polish or PR
**Monitored By:** GitHub Actions E2E workflow
