import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  testMatch: ["pipeline.spec.ts", "search.spec.ts", "highlight.spec.ts", "profile.spec.ts", "e2e/auth.*.spec.ts", "e2e/email-risk-banner.spec.ts"],
  testIgnore: ["**/e2e-new/**"],
  timeout: 30_000,
  expect: { timeout: 5_000 },
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: process.env.E2E_BASE_URL || "http://localhost:5175",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: process.env.E2E_NO_SERVER
    ? undefined
    : {
        command: "pnpm dev",
        port: 5175,
        reuseExistingServer: true,
        timeout: 120_000,
      },
});
