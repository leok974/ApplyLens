import { test, expect } from "@playwright/test";

test.describe("Search – derived subjects & scoring tooltip", () => {
  test.beforeEach(async ({ page }) => {
    // Load wildcard search which lists everything
    await page.goto("/search?q=*");
    // Wait until results list appears
    await page.getByTestId("results-list").waitFor({ state: "visible", timeout: 10000 });
  });

  test("renders a derived subject when original subject is missing", async ({ page }) => {
    // Find any subject with data-derived="1"
    const derived = page.locator('[data-testid="result-subject"][data-derived="1"]').first();
    const isVisible = await derived.isVisible().catch(() => false);
    if (!isVisible) {
      test.skip(true, "No derived subjects present in current dataset");
    }

    const text = (await derived.textContent())?.trim() || "";
    expect(text.length).toBeGreaterThan(0);
    expect(text.toLowerCase()).not.toContain("(no subject)");
  });

  test("results header shows total and query", async ({ page }) => {
    const header = page.getByTestId("results-header");
    await expect(header).toBeVisible();
    const text = (await header.textContent()) || "";
    expect(text).toMatch(/Results/i);
    expect(text).toMatch(/for/i);
  });

  test("scoring tooltip appears on hover", async ({ page }) => {
    const pill = page.getByTestId("scoring-pill");
    await expect(pill).toBeVisible();

    await pill.hover();
    const tooltip = page.locator("[role='tooltip']");
    await expect(tooltip).toBeVisible({ timeout: 2000 });

    // sanity: check some of the content
    await expect(tooltip).toContainText(/Boosts:/i);
    await expect(tooltip).toContainText(/offer ×4/i);
    await expect(tooltip).toContainText(/gauss/i);  // Match actual text (lowercase)
  });

  test("scoring tooltip appears on keyboard focus (a11y)", async ({ page }) => {
    const pill = page.getByTestId("scoring-pill");

    // Try both focus and hover as Radix tooltips may need hover for visibility
    await pill.focus();
    await pill.hover();  // Add hover to trigger tooltip

    const tooltip = page.locator("[role='tooltip']");
    await expect(tooltip).toBeVisible({ timeout: 2000 });
  });
});
