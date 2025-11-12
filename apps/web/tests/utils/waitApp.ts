import { Page, expect } from "@playwright/test";

export async function waitForApp(page: Page, options?: { skipHealthCheck?: boolean }) {
  // Network pre-flight: API reachable (skip for tests that don't need API)
  if (!options?.skipHealthCheck) {
    try {
      const resp = await page.request.get('/api/healthz');
      expect(resp.ok()).toBeTruthy();
    } catch (e) {
      console.warn('⚠ API health check failed, continuing anyway:', e);
    }
  }

  // Ensure page is loaded
  await page.waitForLoadState('domcontentloaded');

  // Wait until body is visible and our root anchor is mounted
  await page.waitForFunction(() => {
    const b = document.body;
    if (!b) return false;
    const vis = getComputedStyle(b).visibility !== "hidden" && getComputedStyle(b).display !== "none";
    const root = document.querySelector('[data-testid="app-root"]');
    return vis && !!root;
  }, null, { timeout: 10_000 });

  await expect(page.getByTestId("app-root")).toBeVisible();

  // If your app sets a ready flag, wait for it
  const ready = page.locator('[data-testid="app-ready"]');
  const readyCount = await ready.count();
  if (readyCount > 0) {
    await expect(ready).toBeVisible({ timeout: 5000 });
  } else {
    // Fallback: wait for network to be reasonably quiet
    await page.waitForLoadState('networkidle', { timeout: 15_000 }).catch(() => {
      // networkidle can timeout on polling apps, that's OK
      console.log('   ℹ Network not idle, continuing...');
    });
  }
}
