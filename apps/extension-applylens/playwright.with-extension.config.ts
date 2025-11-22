import { defineConfig, devices } from "@playwright/test";
import * as path from "node:path";
import * as fs from "node:fs";

const EXT_DIR = path.resolve(__dirname); // the extension root (has manifest.json)
const DEMO_DIR = path.resolve(__dirname, "test"); // serves demo-form.html

export default defineConfig({
  testDir: "./e2e",
  testMatch: "**/with-extension.spec.ts", // Only run the MV3 extension test
  timeout: 30_000,
  use: {
    headless: false, // run Chrome visible for easier debugging; switch to true in CI if you like
    baseURL: "http://127.0.0.1:5178",
  },
  projects: [
    {
      name: "chromium-with-extension",
      use: {
        ...devices["Desktop Chrome"],
        launchOptions: {
          args: [
            `--disable-extensions-except=${EXT_DIR}`,
            `--load-extension=${EXT_DIR}`,
            "--no-first-run",
            "--no-default-browser-check",
          ],
        },
      },
    },
  ],
  webServer: {
    // serve only the demo page (no bundler needed)
    command: "npx http-server ./test -p 5178 -c-1",
    port: 5178,
    reuseExistingServer: !process.env.CI,
  },
});
