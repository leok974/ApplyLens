#!/usr/bin/env tsx
/**
 * Production Storage State Setup Script
 *
 * This script helps you manually create a production storage state file
 * for running E2E tests against https://applylens.app in read-only mode.
 *
 * Usage:
 *   1. Run: pnpm --filter applylens-web exec tsx tests/setup/save-prod-state.ts
 *   2. Browser will open to https://applylens.app
 *   3. Log in manually with a non-privileged test account
 *   4. Press Enter in the terminal
 *   5. Storage state saved to tests/.auth/prod.json
 *
 * Security Notes:
 * - Use a dedicated test account (not your personal account)
 * - Test account should have minimal privileges
 * - Do NOT commit prod.json to git (add to .gitignore)
 * - Rotate credentials periodically
 */

import { chromium } from "@playwright/test";
import * as path from "path";
import * as fs from "fs";
import * as readline from "readline";

const BASE = "https://applylens.app";
const OUTPUT_PATH = path.join(__dirname, "../.auth/prod.json");

async function main() {
  console.log("🔐 Production Storage State Setup");
  console.log("================================\n");
  console.log(`Target: ${BASE}`);
  console.log(`Output: ${OUTPUT_PATH}\n`);

  // Ensure .auth directory exists
  const authDir = path.dirname(OUTPUT_PATH);
  if (!fs.existsSync(authDir)) {
    fs.mkdirSync(authDir, { recursive: true });
    console.log(`✓ Created directory: ${authDir}`);
  }

  // Launch browser
  console.log("🌐 Launching browser...");
  const browser = await chromium.launch({ headless: false });
  const context = await browser.newContext();
  const page = await context.newPage();

  // Navigate to production
  console.log(`📡 Navigating to ${BASE}...`);
  await page.goto(BASE);

  // Wait for user to log in
  console.log("\n⏳ Please log in manually in the browser window.");
  console.log("   Use a dedicated test account (not your personal account).");
  console.log("   Press Enter here when you've successfully logged in...\n");

  // Wait for Enter key
  await new Promise<void>((resolve) => {
    const rl = readline.createInterface({
      input: process.stdin,
      output: process.stdout
    });

    rl.question("", () => {
      rl.close();
      resolve();
    });
  });

  // Save storage state
  console.log("\n💾 Saving storage state...");
  await context.storageState({ path: OUTPUT_PATH });

  // Display summary
  const state = JSON.parse(fs.readFileSync(OUTPUT_PATH, 'utf-8'));
  const cookieCount = state.cookies?.length ?? 0;
  const originCount = state.origins?.length ?? 0;

  console.log("\n✅ Storage state saved successfully!");
  console.log(`   File: ${OUTPUT_PATH}`);
  console.log(`   Cookies: ${cookieCount}`);
  console.log(`   Origins: ${originCount}`);

  if (cookieCount === 0) {
    console.warn("\n⚠️  Warning: No cookies found. Make sure you're logged in!");
  }

  // Cleanup
  await browser.close();

  console.log("\n🎯 Next steps:");
  console.log("   1. Add prod.json to .gitignore");
  console.log("   2. Run: E2E_BASE_URL=https://applylens.app pnpm test:e2e");
  console.log("   3. Only @prodSafe tests will run (read-only mode)\n");
}

main().catch((error) => {
  console.error("❌ Error:", error.message);
  process.exit(1);
});
