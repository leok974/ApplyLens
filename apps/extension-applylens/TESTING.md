# ApplyLens Extension - Test Suite

Complete test infrastructure for browser extension and API endpoints.

## 📁 Structure

```
apps/extension-applylens/
├── vitest.config.ts          # Vitest configuration
├── vitest.setup.ts           # Chrome API mocks
├── playwright.config.ts      # Playwright E2E config
├── package.json              # Test scripts
├── tests/
│   ├── popup.test.ts        # Popup UI unit tests
│   └── content.test.ts      # Content script unit tests
└── e2e/
    └── fill-form.spec.ts    # E2E form autofill test

services/api/
└── tests/
    └── test_extension_endpoints.py  # API integration tests
```

## 🚀 Quick Start

### 1. Install Dependencies (Extension)

```powershell
cd D:\ApplyLens\apps\extension-applylens
pnpm install
pnpm dlx playwright install
```

### 2. Run Unit Tests (Vitest)

```powershell
# Run all unit tests
pnpm test

# Watch mode
pnpm test:ui

# Specific test file
pnpm vitest tests/popup.test.ts
```

### 3. Run E2E Tests (Playwright)

```powershell
# Run E2E tests (auto-starts http-server)
pnpm e2e

# Debug mode
pnpm dlx playwright test --debug

# UI mode
pnpm dlx playwright test --ui
```

### 4. Run API Tests (Python)

```powershell
cd D:\ApplyLens\services\api
pytest tests/test_extension_endpoints.py -v
```

## 🧪 Test Coverage

### Extension Unit Tests

**tests/popup.test.ts**
- ✅ Profile connection status display
- ✅ Scan button triggers content script message
- ✅ DM button clipboard functionality

**tests/content.test.ts**
- ✅ Form field scanning
- ✅ Answer generation via API
- ✅ Auto-fill field population
- ✅ Event dispatching (input/change)

### Extension E2E Tests

**e2e/fill-form.spec.ts**
- ✅ End-to-end form autofill flow
- ✅ API request interception
- ✅ Content script injection
- ✅ Test hook trigger mechanism
- ✅ Field value assertions

### API Integration Tests

**tests/test_extension_endpoints.py**
- ✅ GET /api/profile/me
- ✅ POST /api/extension/generate-form-answers
- ✅ Response structure validation
- ✅ Field answer generation

## 🔧 Test Features

### Chrome API Mocking (vitest.setup.ts)

```typescript
globalThis.chrome = {
  runtime: {
    sendMessage: vi.fn(async () => ({ ok: true, data: { name: "Leo Klemet" } })),
    onMessage: { addListener, removeListener, hasListener, dispatch }
  },
  tabs: { query, sendMessage },
  scripting: { executeScript }
}
```

### Test Hook (content.js)

```javascript
// Enable with: window.__APPLYLENS_TEST = 1
window.addEventListener("message", (ev) => {
  if (ev.data.type === "APPLYLENS_TEST_SCAN") {
    // Triggers SCAN_AND_SUGGEST flow
  }
});
```

### API Mocking (Playwright)

```typescript
await page.route("**/api/extension/generate-form-answers", async route => {
  await route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({ ok: true, data: { answers: [...] } })
  });
});
```

## 📊 CI Integration

### GitHub Actions (Extension)

```yaml
- name: Install dependencies
  run: pnpm install

- name: Run unit tests
  run: pnpm test

- name: Install Playwright
  run: pnpm dlx playwright install --with-deps

- name: Run E2E tests
  run: pnpm e2e
```

### GitHub Actions (API)

```yaml
- name: Install dependencies
  run: pip install -e ".[dev]"

- name: Run API tests
  run: pytest tests/test_extension_endpoints.py -v
```

## 🐛 Debugging

### Vitest Debug

```powershell
# Run with verbose output
pnpm vitest --reporter=verbose

# Run single test
pnpm vitest -t "shows Connected in popup"

# Update snapshots
pnpm vitest -u
```

### Playwright Debug

```powershell
# Headed mode (see browser)
pnpm dlx playwright test --headed

# Slow motion
pnpm dlx playwright test --slow-mo=1000

# Trace viewer
pnpm dlx playwright test --trace on
pnpm dlx playwright show-trace trace.zip
```

### API Debug

```powershell
# Verbose pytest output
pytest -vv tests/test_extension_endpoints.py

# Stop on first failure
pytest -x tests/test_extension_endpoints.py

# Print output
pytest -s tests/test_extension_endpoints.py
```

## 📝 Writing New Tests

### Add Vitest Unit Test

```typescript
// tests/new-feature.test.ts
import { describe, it, expect } from "vitest";

describe("New Feature", () => {
  it("does something", () => {
    expect(true).toBe(true);
  });
});
```

### Add Playwright E2E Test

```typescript
// e2e/new-flow.spec.ts
import { test, expect } from "@playwright/test";

test("new user flow", async ({ page }) => {
  await page.goto("/demo-form.html");
  // Your test logic
});
```

### Add API Test

```python
# tests/test_new_endpoint.py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_new_endpoint():
    r = client.get("/api/new")
    assert r.status_code == 200
```

## 🎯 Test Checklist

Before committing:

- [ ] `pnpm test` passes (extension unit tests)
- [ ] `pnpm e2e` passes (extension E2E)
- [ ] `pytest` passes (API tests)
- [ ] No console errors in Playwright traces
- [ ] Coverage meets minimum threshold
- [ ] Test names are descriptive

## 🔍 Troubleshooting

### "Cannot find module 'vitest'"

```powershell
cd D:\ApplyLens\apps\extension-applylens
pnpm install
```

### "Playwright not found"

```powershell
pnpm dlx playwright install --with-deps
```

### "Port 5177 already in use"

```powershell
# Kill existing http-server
Get-Process -Name node | Where-Object { $_.MainWindowTitle -match '5177' } | Stop-Process
```

### API tests fail with "Module not found"

```powershell
cd D:\ApplyLens\services\api
pip install -e ".[dev]"
```

## 📈 Coverage Reports

### Vitest Coverage

```powershell
pnpm add -D @vitest/coverage-v8
pnpm vitest --coverage
```

### Playwright Coverage

```powershell
pnpm dlx playwright test --reporter=html
# Open playwright-report/index.html
```

### Python Coverage

```powershell
pip install pytest-cov
pytest --cov=app tests/test_extension_endpoints.py
```

---

**Ready to test!** Run `pnpm install && pnpm test` to get started. 🎉
