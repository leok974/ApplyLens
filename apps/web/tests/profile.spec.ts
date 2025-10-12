import { test, expect } from "@playwright/test";
import { waitForApp } from "./utils/waitApp";

test.describe("Profile page", () => {
  test("profile page renders summary", async ({ page, context }) => {
    // Mock profile endpoint
    await context.route('**/profile/db-summary**', route => route.fulfill({
      json: {
        user_email: "leoklemet.pa@gmail.com",
        top_senders: [{ domain: "news.example.com", total: 12, categories: {}, open_rate: 0 }],
        categories: [{ category: "promotions", total: 20 }],
        interests: [{ keyword: "ai conference", score: 3 }],
      }
    }));    await page.goto("/", { waitUntil: "domcontentloaded" });
    await waitForApp(page);
    
    const link = page.getByTestId("nav-profile").or(page.getByRole("link", { name: /profile/i }));
    await link.click();

    await expect(page).toHaveURL(/\/profile/);
    await expect(page.getByText(/Top Senders/i)).toBeVisible({ timeout: 10000 });
  });

  test("profile link is in header navigation", async ({ page }) => {
    await page.goto("/", { waitUntil: "domcontentloaded" });
    await waitForApp(page);
    
    const profileLink = page.getByTestId("nav-profile").or(page.getByRole("link", { name: /^profile$/i }));
    await expect(profileLink).toBeVisible();
  });

  test("profile page displays data when API is live", async ({ page }) => {
    // This test requires the real API
    test.skip(true, "Skipped - requires live API");

    await page.goto("/profile", { waitUntil: "domcontentloaded" });
    await waitForApp(page);
    
    // Should show summary sections
    await expect(page.getByText(/Top senders/i)).toBeVisible({ timeout: 10000 });
    await expect(page.getByText(/Categories|Interests/i)).toBeVisible();
  });

  test("profile page handles empty state gracefully", async ({ page, context }) => {
    // Mock empty profile
    await context.route('**/profile/db-summary**', route => route.fulfill({
      json: {
        user_email: "leoklemet.pa@gmail.com",
        top_senders: [],
        categories: [],
        interests: [],
      }
    }));

    await page.goto("/profile", { waitUntil: "domcontentloaded" });
    await waitForApp(page);

    // Should still render without errors
    await expect(page.getByText(/Top Senders|Top Categories|Top Interests/i).first()).toBeVisible({ timeout: 10000 });
  });
});