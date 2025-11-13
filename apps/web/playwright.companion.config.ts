import { defineConfig, devices } from "@playwright/test";

/**
 * Minimal config for testing Companion Settings without global setup.
 * Usage: npx playwright test tests/settings-companion.spec.ts --config playwright.companion.config.ts
 */
export default defineConfig({
  testDir: "./tests",
  timeout: 30_000,
  expect: { timeout: 10_000 },
  retries: 0,
  workers: 1,
  reporter: "line",

  use: {
    baseURL: "http://localhost:5176",
    trace: "on-first-retry",
  },

  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
