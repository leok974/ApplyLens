/**
 * Companion Experimental Styles Toggle Tests
 *
 * Phase 5.4/5.5: Verifies the bandit toggle UI works correctly and
 * properly syncs with localStorage and window.__APPLYLENS_BANDIT_ENABLED.
 *
 * To run locally:
 * 1. Start API: docker ps (ensure applylens-api-prod is running)
 * 2. Start frontend: npm run dev (in apps/web)
 * 3. Run test: npx playwright test tests/settings-companion-experimental-styles.spec.ts --reporter=line
 */

import { test, expect } from "@playwright/test";

test.describe("Companion Experimental Styles Toggle", () => {
  test.beforeEach(async ({ page }) => {
    // Mock runtime config endpoint
    await page.route("**/api/config", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          readOnly: false,
          version: "0.6.0"
        })
      });
    });

    // Mock authentication endpoint
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

    // Mock profile ping endpoint
    await page.route("**/api/profile/me", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          id: "user123",
          email: "test@example.com"
        })
      });
    });

    // Mock extension endpoints
    await page.route("**/api/extension/applications**", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([])
      });
    });

    await page.route("**/api/extension/outreach**", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([])
      });
    });

    // Clear localStorage before each test
    await page.goto("http://localhost:5176/settings/companion");
    await page.evaluate(() => {
      window.localStorage.removeItem("applylens:banditEnabled");
      delete (window as any).__APPLYLENS_BANDIT_ENABLED;
    });
  });

  test("shows autofill learning card with toggle", async ({ page }) => {
    await page.goto("http://localhost:5176/settings/companion", { waitUntil: "domcontentloaded" });

    // Wait for card presence using stable testid
    const card = page.getByTestId("companion-autofill-learning-card");
    await expect(card).toBeVisible({ timeout: 10000 });

    // Assert title inside the card
    await expect(card.getByText("Autofill learning")).toBeVisible();

    // Verify toggle exists
    const toggle = page.getByTestId("companion-experimental-styles-toggle");
    await expect(toggle).toBeVisible();

    // Verify info tooltip trigger exists
    const infoButton = page.getByTestId("companion-experimental-styles-tooltip-trigger");
    await expect(infoButton).toBeVisible();
  });

  test("toggle defaults to enabled (true)", async ({ page }) => {
    await page.goto("http://localhost:5176/settings/companion", { waitUntil: "domcontentloaded" });


    const toggle = page.getByTestId("companion-experimental-styles-toggle");
    await expect(toggle).toBeVisible({ timeout: 10000 });

    // Check that toggle is enabled by default
    await expect(toggle).toBeChecked();

    // Verify window.__APPLYLENS_BANDIT_ENABLED is true
    const banditEnabled = await page.evaluate(() => {
      return (window as any).__APPLYLENS_BANDIT_ENABLED;
    });
    expect(banditEnabled).toBe(true);

    // Verify localStorage
    const storageValue = await page.evaluate(() => {
      return window.localStorage.getItem("applylens:banditEnabled");
    });
    expect(storageValue).toBe("true");
  });

  test("can toggle off experimental styles", async ({ page }) => {
    await page.goto("http://localhost:5176/settings/companion", { waitUntil: "domcontentloaded" });


    const toggle = page.getByTestId("companion-experimental-styles-toggle");
    await expect(toggle).toBeVisible({ timeout: 10000 });
    await expect(toggle).toBeChecked();

    // Click to turn off
    await toggle.click();
    await page.waitForTimeout(100); // Wait for state update

    // Verify toggle is now unchecked
    await expect(toggle).not.toBeChecked();

    // Verify window.__APPLYLENS_BANDIT_ENABLED is false
    const banditEnabled = await page.evaluate(() => {
      return (window as any).__APPLYLENS_BANDIT_ENABLED;
    });
    expect(banditEnabled).toBe(false);

    // Verify localStorage
    const storageValue = await page.evaluate(() => {
      return window.localStorage.getItem("applylens:banditEnabled");
    });
    expect(storageValue).toBe("false");
  });

  test("can toggle on experimental styles after turning off", async ({ page }) => {
    await page.goto("http://localhost:5176/settings/companion", { waitUntil: "domcontentloaded" });


    const toggle = page.getByTestId("companion-experimental-styles-toggle");
    await expect(toggle).toBeVisible({ timeout: 10000 });

    // Turn off
    await toggle.click();
    await page.waitForTimeout(100);
    await expect(toggle).not.toBeChecked();

    // Turn back on
    await toggle.click();
    await page.waitForTimeout(100);
    await expect(toggle).toBeChecked();

    // Verify window flag is back to true
    const banditEnabled = await page.evaluate(() => {
      return (window as any).__APPLYLENS_BANDIT_ENABLED;
    });
    expect(banditEnabled).toBe(true);

    // Verify localStorage
    const storageValue = await page.evaluate(() => {
      return window.localStorage.getItem("applylens:banditEnabled");
    });
    expect(storageValue).toBe("true");
  });

  test("persists setting across page reloads", async ({ page }) => {
    await page.goto("http://localhost:5176/settings/companion", { waitUntil: "domcontentloaded" });


    const toggle = page.getByTestId("companion-experimental-styles-toggle");
    await expect(toggle).toBeVisible({ timeout: 10000 });

    // Turn off
    await toggle.click();
    await page.waitForTimeout(100);
    await expect(toggle).not.toBeChecked();

    // Reload page
    await page.reload({ waitUntil: "domcontentloaded" });


    // Verify toggle is still off after reload
    const toggleAfterReload = page.getByTestId("companion-experimental-styles-toggle");
    await expect(toggleAfterReload).toBeVisible({ timeout: 10000 });
    await expect(toggleAfterReload).not.toBeChecked();

    // Verify window flag persisted
    const banditEnabled = await page.evaluate(() => {
      return (window as any).__APPLYLENS_BANDIT_ENABLED;
    });
    expect(banditEnabled).toBe(false);
  });

  test("shows tooltip with explanation when hovering info icon", async ({ page }) => {
    await page.goto("http://localhost:5176/settings/companion", { waitUntil: "domcontentloaded" });

    // Use stable testid for tooltip trigger
    const trigger = page.getByTestId("companion-experimental-styles-tooltip-trigger").first();
    await expect(trigger).toBeVisible({ timeout: 10000 });

    // Hover to show tooltip (don't click for tooltips that show on hover)
    await trigger.hover();
    await page.waitForTimeout(500); // Wait for tooltip animation

    // Verify tooltip content using stable testid
    const tooltip = page.getByTestId("companion-experimental-styles-tooltip-content");
    await expect(tooltip).toBeVisible({ timeout: 3000 });
    await expect(tooltip).toContainText("What this means");
    await expect(tooltip).toContainText("Sometimes tries alternate phrasing");
  });
});
