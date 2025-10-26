import { defineConfig, devices } from "@playwright/test";

// Detect production environment
const BASE = process.env.E2E_BASE_URL ?? "http://localhost:5175";
const IS_PROD = /^https:\/\/applylens\.app/.test(BASE);

export default defineConfig({
  testDir: "./tests",
  testMatch: [
    "pipeline.spec.ts",
    "search.spec.ts",
    "highlight.spec.ts",
    "profile.spec.ts",
    "profile-warehouse.spec.ts",  // Warehouse-backed profile page
    "**/auth.*.spec.ts",  // Must include glob pattern
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
    "mailboxAssistant.spec.ts"  // Small talk and conversational suggestions
  ],
  testIgnore: ["**/e2e-new/**"],
  timeout: 30_000,
  expect: { timeout: 5_000 },
  retries: process.env.CI ? 1 : 0, // Retry once in CI
  reporter: [["list"], ["html", { open: "never" }]],

  // Production safety: only run tests tagged with @prodSafe
  grep: IS_PROD ? /@prodSafe/ : undefined,
  grepInvert: IS_PROD ? /@devOnly/ : undefined,

  use: {
    baseURL: process.env.E2E_BASE_URL || "http://localhost:5175",
    // Use prod storage state on production, demo state on dev
    storageState: IS_PROD ? "tests/.auth/prod.json" : "tests/.auth/demo.json",
    trace: "on-first-retry",
    video: process.env.CI ? "retain-on-failure" : "off",
    screenshot: "only-on-failure",
  },

  // Only run auth setup on dev (prod uses manual prod.json)
  globalSetup: IS_PROD ? undefined : "./tests/setup/auth.setup.ts",

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
