import { test, expect } from "@playwright/test";
import { API } from "./utils/env";

// Helper to parse query params from intercepted GET
function getParams(url: string) {
  const u = new URL(url);
  const cats = u.searchParams.getAll("categories"); // supports multiple
  const q = u.searchParams.get("q") || "";
  const hide = u.searchParams.get("hide_expired");
  return { q, cats, hideExpired: hide !== null ? hide !== "false" && hide !== "0" : undefined };
}

test.describe("Search controls", () => {
  test.beforeEach(async ({ page, context }) => {
    // Mock live ES only for search so tests are deterministic
    await context.route(`${API}/search/**`, async route => {
      const req = route.request();
      const { q, cats, hideExpired } = getParams(req.url());

      // craft deterministic results based on params
      if (hideExpired === false) {
        return route.fulfill({
          json: {
            total: 1,
            hits: [{
              id: "exp1",
              subject: `Expired ${q}`,
              category: cats[0] || "promotions",
              expires_at: "2024-01-01T00:00:00Z",
              sender: "test@example.com",
              received_at: "2024-01-01T00:00:00Z",
              score: 1.0
            }]
          }
        });
      }
      return route.fulfill({
        json: {
          total: 1,
          hits: [{
            id: "fresh1",
            subject: `Fresh ${q}`,
            category: cats[0] || "promotions",
            sender: "test@example.com",
            received_at: "2025-01-01T00:00:00Z",
            score: 1.0
          }]
        }
      });
    });

    await page.goto("/search");
  });

  test("category buttons mutate URL and drive query", async ({ page }) => {
    const ats = page.getByTestId("cat-ats").or(page.getByRole("button", { name: /^ats$/i }));
    const pro = page.getByTestId("cat-promotions").or(page.getByRole("button", { name: /^promotions$/i }));

    await ats.click();
    await expect(page).toHaveURL(/cat=ats/);

    await pro.click();
    await expect(page).toHaveURL(/cat=ats,promotions/);

    await ats.click();
    await expect(page).toHaveURL(/cat=promotions/);
  });

  test("hide expired switch toggles payload & results", async ({ page }) => {
    const sw = page.getByTestId("switch-hide-expired").or(page.getByRole("switch", { name: /hide expired/i }));

    // Default should be on (expired hidden)
    await expect(page.getByText(/Fresh/)).toBeVisible({ timeout: 5000 });

    // Turn OFF → expired appears
    await sw.click();
    await expect(page).toHaveURL(/hideExpired=0/);
    await expect(page.getByText(/Expired/)).toBeVisible();

    // Turn ON → fresh appears
    await sw.click();
    await expect(page.getByText(/Fresh/)).toBeVisible();
  });

  test("expired chip toggles same state as switch", async ({ page }) => {
    const chip = page.getByTestId("chip-expired-toggle").or(page.getByRole("button", { name: /show expired|hide expired/i }));

    // Default: expired hidden, chip says "Show expired"
    await expect(chip).toHaveText(/show expired/i);
    await expect(page.getByText(/Fresh/)).toBeVisible({ timeout: 5000 });

    // Click chip to show expired
    await chip.click();
    await expect(page).toHaveURL(/hideExpired=0/);
    await expect(chip).toHaveText(/hide expired/i);
    await expect(page.getByText(/Expired/)).toBeVisible();

    // Click chip to hide expired
    await chip.click();
    await expect(chip).toHaveText(/show expired/i);
    await expect(page.getByText(/Fresh/)).toBeVisible();
  });

  test("multiple category filters work together", async ({ page }) => {
    const ats = page.getByTestId("cat-ats").or(page.getByRole("button", { name: /^ats$/i }));
    const bills = page.getByTestId("cat-bills").or(page.getByRole("button", { name: /^bills$/i }));
    const events = page.getByTestId("cat-events").or(page.getByRole("button", { name: /^events$/i }));

    // Select multiple categories
    await ats.click();
    await bills.click();
    await events.click();

    await expect(page).toHaveURL(/cat=ats,bills,events/);

    // Deselect one
    await bills.click();
    await expect(page).toHaveURL(/cat=ats,events/);
    await expect(page).not.toHaveURL(/bills/);
  });
});
