/**
 * Companion Settings Page Tests
 *
 * Verifies the Browser Companion settings page displays correctly
 * and shows extension activity when the API is available.
 *
 * To run locally:
 * 1. Start API: docker ps (ensure applylens-api-prod is running)
 * 2. Start frontend: npm run dev (in apps/web)
 * 3. Run tests: npx playwright test tests/settings-companion.spec.ts --reporter=line
 */

import { test, expect } from "@playwright/test";

test.describe("Companion Settings page", () => {
  test("shows install instructions and API connectivity status", async ({ page }) => {
    // Mock runtime config endpoint
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

    // Mock profile ping endpoint (API OK)
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

    // Mock extension applications endpoint
    await page.route("**/api/extension/applications**", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([
          {
            id: 1,
            company: "Acme Corp",
            role: "Senior Engineer",
            job_url: "https://example.com/jobs/123",
            source: "lever",
            applied_at: new Date().toISOString(),
            created_at: new Date().toISOString()
          }
        ])
      });
    });

    // Mock extension outreach endpoint
    await page.route("**/api/extension/outreach**", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([
          {
            id: 1,
            company: "TechCo",
            role: "Staff Engineer",
            recruiter_name: "Jane Smith",
            recruiter_profile_url: "https://linkedin.com/in/jsmith",
            message_preview: "I'd love to chat...",
            sent_at: new Date().toISOString(),
            source: "linkedin",
            created_at: new Date().toISOString()
          }
        ])
      });
    });

    // Navigate to Companion Settings page
    await page.goto("http://localhost:5176/settings/companion", { waitUntil: "domcontentloaded" });
    await page.waitForLoadState("networkidle");

    // Verify page title
    await expect(page.getByRole("heading", { name: /Browser Companion/i })).toBeVisible({ timeout: 10000 });

    // Verify install instructions
    await expect(page.getByRole("heading", { name: /Install/i })).toBeVisible();
    await expect(page.getByText(/chrome:\/\/extensions/)).toBeVisible();
    await expect(page.getByText(/Developer mode/)).toBeVisible();

    // Verify API connectivity shows OK
    await expect(page.getByText(/API connectivity/)).toBeVisible();
    const apiStatus = page.locator('text=API connectivity').locator('..').getByText('OK');
    await expect(apiStatus).toBeVisible();

    // Verify Recent Applications section
    await expect(page.getByRole("heading", { name: /Recent Applications/i })).toBeVisible();
    await expect(page.getByText("Acme Corp")).toBeVisible();
    await expect(page.getByText("Senior Engineer")).toBeVisible();

    // Verify Recent Outreach section
    await expect(page.getByRole("heading", { name: /Recent Outreach/i })).toBeVisible();
    await expect(page.getByText("TechCo")).toBeVisible();
    await expect(page.getByText("Jane Smith")).toBeVisible();
  });

  test("shows offline status when API is unreachable", async ({ page }) => {
    // Mock config and auth as before
    await page.route("**/api/config", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ readOnly: false, version: "0.5.0" })
      });
    });

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

    // Mock profile ping to fail
    await page.route("**/api/profile/me", async route => {
      await route.abort("failed");
    });

    // Navigate to Companion Settings page
    await page.goto("http://localhost:5176/settings/companion", { waitUntil: "domcontentloaded" });
    await page.waitForLoadState("networkidle");

    // Wait a moment for API calls to complete
    await page.waitForTimeout(1000);

    // Verify offline status
    await expect(page.getByText(/API connectivity/)).toBeVisible({ timeout: 10000 });
    await expect(page.getByText(/offline/)).toBeVisible();
  });

  test("shows empty state when no extension activity exists", async ({ page }) => {
    // Mock endpoints
    await page.route("**/api/config", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ readOnly: false, version: "0.5.0" })
      });
    });

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

    await page.route("**/api/profile/me", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ id: "user123", email: "test@example.com" })
      });
    });

    // Mock empty responses
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

    await page.goto("http://localhost:5176/settings/companion", { waitUntil: "domcontentloaded" });
    await page.waitForLoadState("networkidle");

    // Verify empty state messages
    await expect(page.getByText(/No applications yet/i)).toBeVisible({ timeout: 10000 });
    await expect(page.getByText(/No outreach yet/i)).toBeVisible();
  });

  test("shows tips section with helpful guidance", async ({ page }) => {
    // Mock endpoints
    await page.route("**/api/config", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ readOnly: false, version: "0.5.0" })
      });
    });

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

    await page.route("**/api/profile/me", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ id: "user123" })
      });
    });

    await page.route("**/api/extension/applications**", async route => {
      await route.fulfill({ status: 200, contentType: "application/json", body: "[]" });
    });

    await page.route("**/api/extension/outreach**", async route => {
      await route.fulfill({ status: 200, contentType: "application/json", body: "[]" });
    });

    await page.goto("http://localhost:5176/settings/companion", { waitUntil: "domcontentloaded" });
    await page.waitForLoadState("networkidle");

    // Verify tips section
    await expect(page.getByRole("heading", { name: /Tips/i })).toBeVisible({ timeout: 10000 });
    await expect(page.getByText(/Reload the page after reloading the extension/i)).toBeVisible();
    await expect(page.getByText(/LinkedIn.*Draft recruiter DM/i)).toBeVisible();
  });
});
