import { test, expect } from "@playwright/test";
import { waitForApp } from "./utils/waitApp";

// helper
function params(url: string) {
  const u = new URL(url);
  const cats = u.searchParams.getAll("cat");
  const q = u.searchParams.get("q") ?? "";
  const hide = u.searchParams.get("hideExpired");
  const hideExpired = hide !== null ? !["0", "false"].includes(hide) : undefined;
  return { cats, q, hideExpired };
}

test.describe("Search controls", () => {
  test.beforeEach(async ({ page, context }) => {
    // Mock handler for SEARCH endpoint
    const handler = async (route: any) => {
      const u = new URL(route.request().url());
      const hide = u.searchParams.get("hide_expired");
      const hideExpired = hide !== null ? !["0","false"].includes(hide) : true;

      if (hideExpired === false) {
        // show an expired result (has expires_at)
        return route.fulfill({
          json: {
            total: 1,
            hits: [{
              id: "exp1",
              subject: "Promo – 50% OFF",
              category: "promotions",
              expires_at: "2024-01-01T00:00:00Z"
            }]
          }
        });
      }
      // fresh (no expires_at badge)
      return route.fulfill({
        json: {
          total: 1,
          hits: [{
            id: "fresh1",
            subject: "Promo – New arrival",
            category: "promotions"
          }]
        }
      });
    };

    // Intercept both possible endpoint patterns
    await context.route('**/api/search/**', handler);
    await context.route('**/search/emails**', handler);

    await page.goto("/search", { waitUntil: "domcontentloaded" });
    await waitForApp(page);
  });

  test("category buttons mutate URL and drive query", async ({ page }) => {
    const ats = page.getByTestId("cat-ats").or(page.getByRole("button", { name: /^ats$/i }));
    const pro = page.getByTestId("cat-promotions").or(page.getByRole("button", { name: /^promotions$/i }));

    await ats.click();
    await expect(page).toHaveURL(/cat=ats/);
    await page.waitForTimeout(500);

    await pro.click();
    await expect(page).toHaveURL(/cat.*ats.*promotions|cat.*promotions.*ats/);
    await page.waitForTimeout(500);

    await ats.click();
    await expect(page).toHaveURL(/cat=promotions/);
  });

  test("hide expired switch toggles results", async ({ page }) => {
    const sw = page.getByTestId("switch-hide-expired").or(page.getByRole("switch", { name: /hide expired/i }));

    // Turn OFF -> expect an expired badge to appear
    await Promise.all([
      page.waitForResponse(r => r.url().includes('/search') && r.ok()),
      sw.click(),
    ]);
    await expect(page).toHaveURL(/hideExpired=0/);
    await expect(page.getByTestId("badge-expires")).toBeVisible();

    // Turn ON -> expect badge to disappear (fresh item)
    await Promise.all([
      page.waitForResponse(r => r.url().includes('/search') && r.ok()),
      sw.click(),
    ]);
    await expect(page.getByTestId("badge-expires")).toHaveCount(0);
  });

  test("expired chip toggles same state as switch", async ({ page }) => {
    const chip = page.getByTestId("chip-expired-toggle").or(page.getByRole("button", { name: /show expired|hide expired/i }));

    // Click chip to show expired -> expect badge
    await Promise.all([
      page.waitForResponse(r => r.url().includes('/search') && r.ok()),
      chip.click()
    ]);
    await expect(page).toHaveURL(/hideExpired=0/);
    await expect(page.getByTestId("badge-expires")).toBeVisible();

    // Click again to hide -> badge disappears
    await Promise.all([
      page.waitForResponse(r => r.url().includes('/search') && r.ok()),
      chip.click()
    ]);
    await expect(page.getByTestId("badge-expires")).toHaveCount(0);
  });

  test("multiple category filters work together", async ({ page }) => {
    const ats = page.getByTestId("cat-ats").or(page.getByRole("button", { name: /^ats$/i }));
    const bills = page.getByTestId("cat-bills").or(page.getByRole("button", { name: /^bills$/i }));
    const events = page.getByTestId("cat-events").or(page.getByRole("button", { name: /^events$/i }));

    // Select multiple categories
    await ats.click();
    await bills.click();
    await events.click();

    await expect(page).toHaveURL(/cat.*ats/);
    await expect(page).toHaveURL(/cat.*bills/);
    await expect(page).toHaveURL(/cat.*events/);
  });
});
