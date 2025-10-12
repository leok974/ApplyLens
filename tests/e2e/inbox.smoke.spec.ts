import { test, expect } from "@playwright/test";
import { stubApi } from "./_fixtures";
import { guardConsole } from "./_consoleGuard";

test.beforeEach(async ({ page }) => {
  guardConsole(page);
  await stubApi(page);
});

test("Inbox renders cards with readable surface", async ({ page }) => {
  await page.goto("/inbox-polished-demo");
  
  // Wait for page to load - check for legibility bar
  await page.waitForLoadState("networkidle");
  await page.waitForSelector('text=/View:/', { timeout: 10000 });

  // Cards exist and look like our theme (surface-card class)
  const cards = page.locator(".surface-card");
  await expect(cards.first()).toBeVisible();

  // Check text legibility with actual demo data
  await expect(page.getByText(/Your application to Software Engineer/i).first()).toBeVisible();
  await expect(page.getByText(/Thank you for applying/i).first()).toBeVisible();
});
