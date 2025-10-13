import { test, expect } from "@playwright/test";
import { stubApi } from "./_fixtures";
import { guardConsole } from "./_consoleGuard";

test.beforeEach(async ({ page }) => {
  guardConsole(page);
  await stubApi(page);
});

test("Theme toggle switches .dark on html and persists", async ({ page }) => {
  await page.goto("/inbox-polished-demo");

  const html = page.locator("html");
  
  // Start in light mode (or get current state)
  const initialClass = await html.getAttribute("class");
  const isDarkInitially = initialClass?.includes("dark") ?? false;

  // Open the dropdown menu and click on "Dark" or "Light"
  const toggle = page.getByRole("button", { name: /toggle theme/i });
  await toggle.click();
  
  // Wait for dropdown to open
  await page.waitForTimeout(100);
  
  // Click the opposite theme
  if (isDarkInitially) {
    await page.getByRole("menuitem", { name: "Light" }).click();
  } else {
    await page.getByRole("menuitem", { name: "Dark" }).click();
  }

  // Wait for theme to apply
  await page.waitForTimeout(200);

  // Verify it toggled
  const afterToggleClass = await html.getAttribute("class");
  const isDarkAfterToggle = afterToggleClass?.includes("dark") ?? false;
  expect(isDarkAfterToggle).toBe(!isDarkInitially);

  // Reload and verify persistence
  await page.reload();
  await page.waitForTimeout(200);
  const afterReloadClass = await html.getAttribute("class");
  const isDarkAfterReload = afterReloadClass?.includes("dark") ?? false;
  expect(isDarkAfterReload).toBe(isDarkAfterToggle);
});
