import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "e2e",
  testMatch: "review-panel.spec.ts",
  timeout: 30_000,
  fullyParallel: false,
  use: {
    headless: true,
    viewport: { width: 1200, height: 900 },
  },
  // Serve the /test directory so we can load demo-form.html at a stable port
  webServer: {
    command: "npx http-server ./test -p 5177 -a 127.0.0.1 --silent",
    port: 5177,
    reuseExistingServer: true,
    timeout: 10_000,
  },
});
