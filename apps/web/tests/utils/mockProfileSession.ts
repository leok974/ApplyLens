import { Page } from "@playwright/test";

/**
 * Mock all backend API calls needed for the Profile page to render.
 * This allows tests to run without a live backend, BigQuery, or Postgres.
 *
 * Usage:
 *   await mockProfileSession(page);
 *   await page.goto("http://localhost:5175/profile");
 */
export async function mockProfileSession(page: Page) {
  // 1. Mock runtime config endpoint
  await page.route("**/api/config", async route => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        readOnly: false,
        version: "0.4.48"
      })
    });
  });

  // 2. Mock authentication/session endpoint
  // This makes the app think we're logged in, so the Profile nav tab appears
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

  // 3. Mock the warehouse profile summary endpoint
  await page.route("**/api/metrics/profile/summary", async route => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        account: "leoklemet.pa@gmail.com",
        totals: {
          all_time_emails: 1234,
          last_30d_emails: 87
        },
        top_senders_30d: [
          { sender: "Acme Robotics", email: "jane@acme.io", count: 12 },
          { sender: "LinkedIn Jobs", email: "jobs@linkedin.com", count: 9 }
        ],
        top_categories_30d: [
          { category: "Interview", count: 4 },
          { category: "Offer", count: 1 }
        ],
        top_interests: [
          { keyword: "LLM engineer", count: 6 },
          { keyword: "Applied AI", count: 4 }
        ]
      })
    });
  });
}
