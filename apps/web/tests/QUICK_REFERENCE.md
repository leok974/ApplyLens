# 🚀 ApplyLens E2E Testing Quick Reference

## 📦 NPM Scripts (Quick Commands)

```powershell
pnpm test:smoke          # Run smoke tests (2 workers)
pnpm test:e2e            # Run full E2E suite (2 workers)
pnpm test:e2e:ui         # Open Playwright UI (1 worker)
pnpm test:e2e:trace      # Run with trace recording (1 worker)
```

## 🎯 VS Code Tasks

**Press `Ctrl+Shift+B`** or **`Ctrl+Shift+P` → `Tasks: Run Task`**

- **Launch ApplyLens Workday (Local)** - Full workflow starter
- **Launch ApplyLens Workday (Production)** - Production workflow
- **Launch ApplyLens Workday (Custom Seed)** - Custom seed count
- **Run Smoke Tests** ⭐ - Default test task
- **Run Full E2E Suite** - All tests
- **Run E2E with UI Mode** - Debug mode
- **Run E2E with Trace** - Record traces
- **Run Smoke Tests (Production)** - Prod smoke tests

## 🔧 Manual Commands

### Local Development
```powershell
# Setup environment
$env:ALLOW_DEV_ROUTES = "1"
$env:E2E_BASE_URL = "http://127.0.0.1:8000"
$env:E2E_API = "http://127.0.0.1:8000/api"
$env:USE_SMOKE_SETUP = "true"

# Run tests
npx playwright test tests/smoke/inbox-has-data.spec.ts --config=playwright.config.ts --workers=2
npx playwright test --config=playwright.config.ts --workers=2
```

### Production
```powershell
$env:E2E_BASE_URL = "https://applylens.app"
$env:E2E_API = "https://applylens.app/api"
$env:USE_SMOKE_SETUP = "false"

npx playwright test tests/smoke/inbox-has-data.spec.ts --config=playwright.config.ts --workers=2
```

## 🐛 Debugging

```powershell
# Interactive UI
npx playwright test --ui --workers=1

# With traces
npx playwright test --trace=on --workers=1

# Headed mode (see browser)
npx playwright test --headed

# Debug mode
npx playwright test --debug
```

## 📈 Ramping Safely

Gradually increase workers to avoid overwhelming ES/API:

```powershell
# 1. Start with smoke (2 workers)
pnpm test:smoke

# 2. Ramp to 4 workers
npx playwright test --workers=4

# 3. Ramp to 6 workers
npx playwright test --workers=6

# 4. Ramp to 8 workers
npx playwright test --workers=8
```

💡 Monitor system resources between ramps!

## 📁 File Structure

```
apps/web/
├── tests/
│   ├── smoke/
│   │   ├── inbox-has-data.spec.ts  # Smoke test suite
│   │   └── README.md               # Detailed docs
│   ├── utils/
│   │   └── seedInbox.ts            # Seeding helper
│   └── global.setup.ts             # Pre-test seeding
├── playwright.config.ts            # Main config
└── .vscode/
    └── tasks.json                  # VS Code tasks
```

## 🎬 Workflow Script

```powershell
# Complete workflow launcher
.\launch-applylens-workday.ps1

# Options
.\launch-applylens-workday.ps1 -Env local|prod -SeedCount 40
```

**What it does:**
1. Starts Docker containers
2. Opens VS Code workspaces
3. Seeds inbox with test data
4. Runs smoke tests automatically

---

💡 **Tip:** Use `pnpm test:smoke` for quick smoke tests, `pnpm test:e2e:ui` for debugging!
