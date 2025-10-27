/**
 * Profile Page - Warehouse Analytics Tests [prodSafe]
 *
 * These tests verify the warehouse-backed Profile page with mocked backend calls.
 * They do NOT require a live backend, BigQuery, Postgres, or Elasticsearch.
 *
 * To run locally:
 * 1. Start frontend dev server: npm run dev (in apps/web)
 * 2. Set environment variable: $env:SKIP_AUTH='1'
 * 3. Run tests: npx playwright test tests/profile-warehouse.spec.ts --reporter=line
 *
 * All API calls are intercepted with page.route() mocks.
 */

import { test, expect } from "@playwright/test";
import { mockProfileSession } from "./utils/mockProfileSession";

test.describe("Profile page (warehouse analytics) [prodSafe]", () => {
  test("renders analytics cards from warehouse summary", async ({ page }) => {
    // IMPORTANT: Mock all backend calls BEFORE navigation
    await mockProfileSession(page);

    // Navigate directly to /profile
    await page.goto("http://localhost:5175/profile", { waitUntil: "domcontentloaded" });

    // Wait for content to load (the component should render with mocked data)
    await page.waitForLoadState("networkidle");

    // Verify Email Activity card
    await expect(page.getByText("Email Activity")).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("1,234")).toBeVisible(); // all_time_emails with locale formatting
    await expect(page.getByText("87")).toBeVisible(); // last_30d_emails

    // Verify sync info is displayed
    await expect(page.getByText(/Last sync:/i)).toBeVisible();

    // Verify Top Senders card
    await expect(page.getByText(/Top Senders/i)).toBeVisible();
    await expect(page.getByText("Acme Robotics")).toBeVisible();
    await expect(page.getByText("jane@acme.io")).toBeVisible();

    // Verify Top Categories card
    await expect(page.getByText(/Top Categories/i)).toBeVisible();
    await expect(page.getByText("Interview")).toBeVisible();

    // Verify Top Interests card
    await expect(page.getByText(/Top Interests/i)).toBeVisible();
    await expect(page.getByText("LLM engineer")).toBeVisible();

    // Verify warehouse attribution badge
    await expect(page.getByText(/Warehouse analytics/i)).toBeVisible();
    await expect(page.getByText(/Fivetran.*BigQuery/i)).toBeVisible();

    // Verify dataset debug info is displayed
    await expect(page.getByText(/Dataset:/i)).toBeVisible();
  });

  test("handles empty state gracefully", async ({ page }) => {
    // Mock all backend calls with empty data
    await page.route("**/api/config", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ readOnly: false, version: "0.4.48" })
      });
    });

    await page.route("**/api/auth/me", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          email: "leoklemet.pa@gmail.com",
          display_name: "Leo",
          connected: true
        })
      });
    });

    await page.route("**/api/metrics/profile/summary", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          account: "leoklemet.pa@gmail.com",
          last_sync_at: null,
          dataset: "applylens.gmail_raw",
          totals: { all_time_emails: 0, last_30d_emails: 0 },
          top_senders_30d: [],
          top_categories_30d: [],
          top_interests: []
        })
      });
    });

    await page.goto("http://localhost:5175/profile", { waitUntil: "domcontentloaded" });
    await page.waitForLoadState("networkidle");

    // Should still render all 4 cards
    await expect(page.getByText("Email Activity")).toBeVisible({ timeout: 10000 });
    await expect(page.getByText(/Top Senders/i)).toBeVisible();
    await expect(page.getByText(/Top Categories/i)).toBeVisible();
    await expect(page.getByText(/Top Interests/i)).toBeVisible();

    // Should show "No data yet" for empty lists
    const noDataMessages = page.getByText(/No data yet/i);
    await expect(noDataMessages.first()).toBeVisible();
  });

  test("shows 'No data in the last 30 days' when sync is stale", async ({ page }) => {
    // Mock all backend calls with stale sync timestamp (> 30 minutes ago)
    await page.route("**/api/config", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ readOnly: false, version: "0.4.50" })
      });
    });

    await page.route("**/api/auth/me", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          email: "leoklemet.pa@gmail.com",
          display_name: "Leo",
          connected: true
        })
      });
    });

    // Create a timestamp > 30 minutes ago
    const staleTimestamp = new Date(Date.now() - 45 * 60 * 1000).toISOString();

    await page.route("**/api/metrics/profile/summary", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          account: "leoklemet.pa@gmail.com",
          last_sync_at: staleTimestamp,
          dataset: "applylens.gmail_raw",
          totals: { all_time_emails: 0, last_30d_emails: 0 },
          top_senders_30d: [],
          top_categories_30d: [],
          top_interests: []
        })
      });
    });

    await page.goto("http://localhost:5175/profile", { waitUntil: "domcontentloaded" });
    await page.waitForLoadState("networkidle");

    // Should show "No data in the last 30 days." for stale sync with empty data
    await expect(page.getByText(/No data in the last 30 days\./i).first()).toBeVisible({ timeout: 10000 });
  });

  test("handles API failure gracefully with fallback", async ({ page }) => {
    // Mock all backend calls, but make the summary endpoint fail
    await page.route("**/api/config", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ readOnly: false, version: "0.4.48" })
      });
    });

    await page.route("**/api/auth/me", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          email: "leoklemet.pa@gmail.com",
          display_name: "Leo",
          connected: true
        })
      });
    });

    await page.route("**/api/metrics/profile/summary", async route => {
      await route.fulfill({
        status: 500,
        contentType: "application/json",
        body: JSON.stringify({ error: "Internal server error" })
      });
    });

    await page.goto("http://localhost:5175/profile", { waitUntil: "domcontentloaded" });
    await page.waitForLoadState("networkidle");

    // Should still render cards with fallback data
    // The API client returns fallback instead of throwing
    await expect(page.getByText("Email Activity")).toBeVisible({ timeout: 10000 });

    // Verify all cards render with empty/fallback state
    await expect(page.getByText(/Top Senders/i)).toBeVisible();
    await expect(page.getByText(/Top Categories/i)).toBeVisible();
    await expect(page.getByText(/Top Interests/i)).toBeVisible();

    // Should show "No data yet" since API failed and returned fallback (empty arrays)
    const noDataMessages = page.getByText(/No data yet/i);
    await expect(noDataMessages.first()).toBeVisible();
  });
});
