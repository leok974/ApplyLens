/**
 * Companion Navigation Tests
 *
 * Verifies the Companion navigation link appears when feature flag is enabled
 * and routes to the extension landing page correctly.
 */

import { test, expect } from "@playwright/test";

test.describe("Companion navigation", () => {
  test("nav shows Companion when feature flag on", async ({ page }) => {
    // Mock runtime config
    await page.route("**/api/config", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          readOnly: false,
          version: "0.5.0"
        })
      });
    });

    // Mock authentication
    await page.route("**/api/auth/me", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          id: "user123",
          email: "test@example.com",
          is_demo: false
        })
      });
    });

    // Mock health check for extension page
    await page.route("**/api/ops/diag/health", async route => {
      await route.fulfill({
        status: 200,
        contentType: "text/plain",
        body: "OK"
      });
    });

    // Navigate to home
    await page.goto("/", { waitUntil: "domcontentloaded" });
    await page.waitForLoadState("networkidle");

    // Verify Companion link exists in nav
    const companionLink = page.getByTestId("nav-companion");
    await expect(companionLink).toBeVisible({ timeout: 10000 });

    // Click Companion link
    await companionLink.click();

    // Verify navigation to extension page
    await expect(page).toHaveURL(/\/extension$/);
    await expect(page.getByRole("heading", { name: /ApplyLens Companion/i })).toBeVisible({ timeout: 10000 });
  });
});
