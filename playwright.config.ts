/// <reference types="node" />
import { defineConfig, devices } from "@playwright/test";

// Use external servers when running via playwright.test-run.ps1 script
// Set this to false if you want Playwright to manage the server itself
const useExternalServers = process.env.USE_EXTERNAL_SERVERS !== "0";

// Detect production environment
const BASE = process.env.E2E_BASE_URL ?? "http://localhost:5175";
const IS_PROD = /^https:\/\/applylens\.app/.test(BASE);

export default defineConfig({
  testDir: "tests/e2e",
  fullyParallel: true,
  retries: process.env.CI ? 2 : 0,
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: BASE,
    // Use demo storage state for authentication
    storageState: "apps/web/tests/.auth/demo.json",
    trace: process.env.CI ? "on-first-retry" : "retain-on-failure",
    video: process.env.CI ? "on-first-retry" : "retain-on-failure",
    screenshot: "only-on-failure",
    viewport: { width: 1360, height: 900 },
  },
  // Run auth setup before tests
  globalSetup: IS_PROD ? undefined : "./tests/setup/auth.setup.ts",
  // Only start web server if not using external servers
  // When running via playwright.test-run.ps1, servers are already running
  ...(useExternalServers
    ? {}
    : {
        webServer: {
          // Start the web preview server from the web app workspace
          command: "npm run -w apps/web preview -- --port 5175",
          url: "http://localhost:5175",
          reuseExistingServer: !process.env.CI,
          timeout: 90_000,
        },
      }),
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
