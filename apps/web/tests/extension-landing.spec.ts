/**
 * Extension Landing Page Tests
 *
 * Verifies the public extension pages render correctly and links work.
 */

import { test, expect } from "@playwright/test";

test.describe("Extension landing pages", () => {
  test("Extension landing renders and links exist", async ({ page }) => {
    await page.goto("/extension");

    // Verify page title
    await expect(page.getByRole("heading", { name: "ApplyLens Companion" })).toBeVisible();

    // Verify install button (at least one visible)
    await expect(page.getByRole("link", { name: /Install from Chrome Web Store/i }).first()).toBeVisible();

    // Verify support link
    await expect(page.getByRole("link", { name: /Need help/i })).toBeVisible();

    // Verify privacy policy link
    const privacyLink = page.getByRole("link", { name: /Privacy Policy/i });
    await expect(privacyLink).toBeVisible();
  });

  test("Support page renders with troubleshooting info", async ({ page }) => {
    await page.goto("/extension/support");

    // Verify page title
    await expect(page.getByRole("heading", { name: /ApplyLens Companion — Support/i })).toBeVisible();

    // Verify troubleshooting sections
    await expect(page.getByText(/Quick checks/i)).toBeVisible();
    await expect(page.getByText(/Common issues/i)).toBeVisible();

    // Verify contact email
    await expect(page.getByRole("link", { name: /leoklemet.pa@gmail.com/i })).toBeVisible();

    // Verify privacy policy link
    await expect(page.getByRole("link", { name: /Privacy Policy/i })).toBeVisible();
  });

  test("Privacy page renders iframe", async ({ page }) => {
    await page.goto("/extension/privacy");

    // Verify iframe exists
    const iframe = page.frameLocator('iframe[title="Privacy Policy"]');

    // Wait for iframe to load and verify content
    await expect(iframe.getByRole("heading", { name: /ApplyLens Companion — Privacy Policy/i })).toBeVisible({ timeout: 10000 });
  });

  test("Navigation between extension pages works", async ({ page }) => {
    // Start at landing
    await page.goto("/extension");

    // Click support link
    await page.getByRole("link", { name: /Need help/i }).click();
    await expect(page).toHaveURL(/\/extension\/support/);

    // Click privacy link
    await page.getByRole("link", { name: /Privacy Policy/i }).click();
    await expect(page).toHaveURL(/\/extension\/privacy/);
  });
});
