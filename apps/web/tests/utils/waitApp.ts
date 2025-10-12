import { Page, expect } from "@playwright/test";

export async function waitForApp(page: Page) {
  // Wait until body is visible and our root anchor is mounted
  await page.waitForFunction(() => {
    const b = document.body;
    if (!b) return false;
    const vis = getComputedStyle(b).visibility !== "hidden" && getComputedStyle(b).display !== "none";
    const root = document.querySelector('[data-testid="app-root"]');
    return vis && !!root;
  }, null, { timeout: 10_000 });
  await expect(page.getByTestId("app-root")).toBeVisible();
}
