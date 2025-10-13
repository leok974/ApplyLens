import { test, expect } from "@playwright/test";
import { API } from "./utils/env";

test.describe("Profile page", () => {
  test("profile page shows summary", async ({ page, context }) => {
    // If API not live, mock
    let apiLive = false;
    try {
      const r = await page.request.get(`${API}/profile/summary?user_email=leoklemet.pa@gmail.com`);
      apiLive = r.ok();
    } catch {
      apiLive = false;
    }

    if (!apiLive) {
      await context.route(`${API}/profile/summary**`, route => {
        route.fulfill({
          json: {
            top_senders: [
              { domain: "news.example.com", total: 12 },
              { domain: "jobs.linkedin.com", total: 8 }
            ],
            top_categories: [
              { category: "promotions", total: 20 },
              { category: "ats", total: 15 }
            ],
            interests: [
              { interest: "ai conference", score: 3 },
              { interest: "react developer", score: 2 }
            ],
            email_count: 50,
            replied_count: 10,
            avg_response_time_hours: 12.5
          }
        });
      });
    }

    await page.goto("/");
    const link = page.getByTestId("nav-profile").or(page.getByRole("link", { name: /profile/i }));
    await link.click();

    // Wait for profile page to load
    await expect(page).toHaveURL(/\/profile/);

    // Check that profile summary components are visible
    await expect(page.getByText(/Top senders/i).or(page.getByText(/Senders/i))).toBeVisible({ timeout: 10000 });
    await expect(page.getByText(/Top categories/i).or(page.getByText(/Categories/i))).toBeVisible({ timeout: 10000 });
    await expect(page.getByText(/Interests/i).or(page.getByText(/Keywords/i))).toBeVisible({ timeout: 10000 });
  });

  test("profile link is in header navigation", async ({ page }) => {
    await page.goto("/");
    
    const profileLink = page.getByTestId("nav-profile").or(page.getByRole("link", { name: /^profile$/i }));
    await expect(profileLink).toBeVisible();
  });

  test("profile page displays data when API is live", async ({ page }) => {
    // Try to hit live API
    try {
      const r = await page.request.get(`${API}/profile/summary?user_email=leoklemet.pa@gmail.com`);
      if (!r.ok()) {
        test.skip(true, "API not reachable—skipping live profile test");
      }
    } catch {
      test.skip(true, "API not reachable—skipping live profile test");
    }

    await page.goto("/profile");

    // Should display actual data from API
    await expect(page.getByText(/Top senders/i).or(page.getByText(/Senders/i))).toBeVisible({ timeout: 10000 });
    
    // Check for at least one sender domain or category
    const hasData = await page.locator("text=/\\.com|promotions|ats|bills|events/i").count();
    expect(hasData).toBeGreaterThan(0);
  });

  test("profile page handles empty state gracefully", async ({ page, context }) => {
    await context.route(`${API}/profile/summary**`, route => {
      route.fulfill({
        json: {
          top_senders: [],
          top_categories: [],
          interests: [],
          email_count: 0,
          replied_count: 0,
          avg_response_time_hours: null
        }
      });
    });

    await page.goto("/profile");

    // Should still render without errors
    await expect(page.getByText(/Top senders|Senders|Categories|Interests/i).first()).toBeVisible({ timeout: 10000 });
  });
});
