/**
 * Settings Page - Logout Flow Tests [prodSafe]
 *
 * These tests verify the logout button works on the Settings page with mocked backend calls.
 * They do NOT require a live backend, BigQuery, Postgres, or Elasticsearch.
 *
 * To run locally:
 * 1. Start frontend dev server: npm run dev (in apps/web)
 * 2. Set environment variable: $env:SKIP_AUTH='1'
 * 3. Run tests: npx playwright test tests/settings-logout.spec.ts --reporter=line
 *
 * All API calls are intercepted with page.route() mocks.
 */

import { test, expect } from "@playwright/test";

test.describe("Settings page logout flow [prodSafe]", () => {
  test("shows account email and logout button", async ({ page }) => {
    // Mock runtime config endpoint
    await page.route("**/api/config", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          readOnly: false,
          version: "0.4.51"
        })
      });
    });

    // Mock authentication endpoint - user is logged in
    await page.route("**/api/auth/me", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          id: "user123",
          email: "leoklemet.pa@gmail.com",
          name: "Leo",
          is_demo: false
        })
      });
    });

    // Mock logout endpoint
    await page.route("**/api/auth/logout", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ ok: true })
      });
    });

    // Navigate to Settings page
    await page.goto("http://localhost:5175/settings", { waitUntil: "domcontentloaded" });
    await page.waitForLoadState("networkidle");

    // Verify Account card is present
    await expect(page.getByText("Account")).toBeVisible({ timeout: 10000 });

    // Verify signed-in email is shown
    await expect(page.getByText(/Signed in as/i)).toBeVisible();
    await expect(page.getByText("leoklemet.pa@gmail.com")).toBeVisible();

    // Verify logout button exists
    const logoutButton = page.getByTestId("logout-button");
    await expect(logoutButton).toBeVisible();
    await expect(logoutButton).toHaveText("Log out");
  });

  test("clicking logout button redirects to home page", async ({ page }) => {
    // Mock runtime config endpoint
    await page.route("**/api/config", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          readOnly: false,
          version: "0.4.51"
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
          email: "leoklemet.pa@gmail.com",
          name: "Leo",
          is_demo: false
        })
      });
    });

    // Mock logout endpoint
    await page.route("**/api/auth/logout", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ ok: true })
      });
    });

    // Navigate to Settings page
    await page.goto("http://localhost:5175/settings", { waitUntil: "domcontentloaded" });
    await page.waitForLoadState("networkidle");

    // Click logout button
    const logoutButton = page.getByTestId("logout-button");
    await expect(logoutButton).toBeVisible({ timeout: 10000 });
    await logoutButton.click();

    // Wait for navigation to complete
    await page.waitForURL("**/*", { timeout: 5000 });

    // Verify we redirected to home page
    const currentUrl = page.url();
    expect(currentUrl).toMatch(/http:\/\/localhost:5175\/?$/);
  });

  test("logout works even if backend endpoint fails", async ({ page }) => {
    // Mock runtime config endpoint
    await page.route("**/api/config", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          readOnly: false,
          version: "0.4.51"
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
          email: "leoklemet.pa@gmail.com",
          name: "Leo",
          is_demo: false
        })
      });
    });

    // Mock logout endpoint to FAIL
    await page.route("**/api/auth/logout", async route => {
      await route.fulfill({
        status: 500,
        contentType: "application/json",
        body: JSON.stringify({ error: "Internal server error" })
      });
    });

    // Navigate to Settings page
    await page.goto("http://localhost:5175/settings", { waitUntil: "domcontentloaded" });
    await page.waitForLoadState("networkidle");

    // Click logout button
    const logoutButton = page.getByTestId("logout-button");
    await expect(logoutButton).toBeVisible({ timeout: 10000 });
    await logoutButton.click();

    // Wait for navigation to complete
    await page.waitForURL("**/*", { timeout: 5000 });

    // Verify we STILL redirected to home page (resilient logout)
    const currentUrl = page.url();
    expect(currentUrl).toMatch(/http:\/\/localhost:5175\/?$/);
  });

  test("shows Experimental badge on Search Scoring card", async ({ page }) => {
    // Mock endpoints
    await page.route("**/api/config", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ readOnly: false, version: "0.4.51" })
      });
    });

    await page.route("**/api/auth/me", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          id: "user123",
          email: "leoklemet.pa@gmail.com",
          is_demo: false
        })
      });
    });

    await page.goto("http://localhost:5175/settings", { waitUntil: "domcontentloaded" });
    await page.waitForLoadState("networkidle");

    // Verify Search Scoring section has Experimental badge
    await expect(page.getByText("Search Scoring")).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("Experimental")).toBeVisible();

    // Verify footer text mentions upcoming features
    await expect(page.getByText(/muted senders.*safe senders.*data sync controls/i)).toBeVisible();
  });
});
