import { defineConfig, devices } from "@playwright/test";

// Detect production environment
const BASE = process.env.E2E_BASE_URL ?? "http://127.0.0.1:8000";
const IS_PROD = /^https:\/\/applylens\.app/.test(BASE);

export default defineConfig({
  testDir: "./tests",
  testMatch: [
    "preflight/**/*.spec.ts",  // Run preflight checks first
    "pipeline.spec.ts",
    "search.spec.ts",
    "highlight.spec.ts",
    "profile.spec.ts",
    "profile-warehouse.spec.ts",  // Warehouse-backed profile page
    "**/auth.*.spec.ts",  // Must include glob pattern
    "settings-logout.spec.ts",  // Settings page logout flow [prodSafe]
    "settings-companion-experimental-styles.spec.ts",  // Bandit toggle UI tests
    "e2e/email-risk-banner.spec.ts",
    "e2e/ux-heartbeat.spec.ts",
    "e2e/search-form.spec.ts",
    "e2e/search.smoke.spec.ts",
    "e2e/search-suggest-softfail.spec.ts",
    "e2e/search-populates.spec.ts",
    "e2e/search-renders.spec.ts",
    "e2e/search-derived-and-tooltip.spec.ts",
    "e2e/prod-search-smoke.spec.ts",  // Production-safe smoke tests
    "ui/header-logo.spec.ts",
    "search.interactions.spec.ts",
    "mailboxAssistant.spec.ts",  // Small talk and conversational suggestions
    "smoke/**/*.spec.ts"  // Smoke tests with inbox seeding
  ],
  testIgnore: ["**/e2e-new/**"],
  timeout: 45_000,  // Increased from 30s to 45s for stability
  expect: { timeout: 10_000 },  // Increased from 5s to 10s
  retries: 2,  // Always retry twice for flake tolerance
  workers: process.env.CI ? 2 : 4,  // 4 workers locally, 2 in CI
  fullyParallel: false,  // Run tests sequentially when seeding data
  reporter: [
    ["list"],
    ["html", { open: "never" }],
    ["json", { outputFile: "playwright-report.json" }]  // For failure analysis
  ],

  // Production safety: only run tests tagged with @prodSafe
  grep: IS_PROD ? /@prodSafe/ : undefined,
  grepInvert: IS_PROD ? /@devOnly/ : undefined,

  use: {
    baseURL: BASE,
    // Use prod storage state on production, demo state on dev
    storageState: IS_PROD ? "tests/.auth/prod.json" : "tests/.auth/storageState.json",
    trace: "on-first-retry",  // Capture trace on first retry for efficiency
    video: "retain-on-failure",  // Keep videos of failed tests
    screenshot: "only-on-failure",  // Screenshots on failure
  },

  // Use new global setup that handles CSRF + session + seeding
  globalSetup: IS_PROD
    ? undefined
    : "./tests/setup/global-setup.ts",

  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],

  // Auto-start dev server if E2E_BASE_URL not set (local dev runs)
  webServer: process.env.E2E_BASE_URL
    ? undefined
    : {
        command: "pnpm dev",
        url: "http://localhost:5175",
        reuseExistingServer: true,
        timeout: 120_000,
      },
});
