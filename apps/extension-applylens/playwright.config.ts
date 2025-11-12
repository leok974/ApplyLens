import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  use: {
    headless: true,
    baseURL: "http://127.0.0.1:5177",
  },
  webServer: {
    command: "npx http-server ./test -p 5177 -c-1",
    port: 5177,
    reuseExistingServer: !process.env.CI,
  },
});
