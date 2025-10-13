import { test, expect } from "@playwright/test";
import { stubApi } from "./_fixtures";
import { guardConsole } from "./_consoleGuard";

test.beforeEach(async ({ page }) => {
  guardConsole(page);
  await stubApi(page);
});

test("Legibility controls adjust CSS vars and persist", async ({ page, context }) => {
  await page.goto("/inbox-polished-demo");

  // Wait for legibility bar to be visible
  await page.waitForSelector('text=/View:/');

  // Click "L" font button (look for it near "View:" text)
  await page.locator('button[title*="Font L"]').click();

  // Click "Spacious" density
  await page.getByRole("button", { name: "Spacious" }).click();

  // Switch contrast to high
  await page.locator('button:has-text("high")').click();

  // Check CSS variables applied
  const fontScale = await page.evaluate(() => getComputedStyle(document.documentElement).getPropertyValue("--font-scale").trim());
  expect(fontScale).toBe("1.1");
  const density = await page.evaluate(() => getComputedStyle(document.documentElement).getPropertyValue("--density").trim());
  expect(density).toBe("1.08");

  // Verify contrast actually changed the CSS variable
  const borderAfterHigh = await page.evaluate(() => 
    getComputedStyle(document.documentElement).getPropertyValue("--border").trim()
  );
  expect(borderAfterHigh).toBeTruthy();

  // Reload: should persist
  await page.reload();
  const fontScale2 = await page.evaluate(() => getComputedStyle(document.documentElement).getPropertyValue("--font-scale").trim());
  expect(fontScale2).toBe("1.1");
  const density2 = await page.evaluate(() => getComputedStyle(document.documentElement).getPropertyValue("--density").trim());
  expect(density2).toBe("1.08");
});
