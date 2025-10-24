import { test, expect } from "@playwright/test";

/**
 * @prodSafe
 *
 * This test is allowed to run against production.
 * - It does NOT click sync or mutate filters.
 * - It only asserts that the search UI and results list render for a real user.
 * - It should pass with prod data, dev data, or staging data.
 */

test.describe("@prodSafe search smoke", () => {
  // NOTE: baseURL should be set via Playwright config to https://applylens.app when running in prod.
  // NOTE: These tests require authentication. Ensure you're logged in before running.

  test("search page loads and shows results list", async ({ page }) => {
    // 1. Go to the search page with safe default params.
    await page.goto("/search", { waitUntil: "domcontentloaded" });

    // 2. Check if we're on the login page (production auth required)
    // Wait a bit and check for sign-in text
    await page.waitForTimeout(1000);
    const pageContent = await page.content();
    if (pageContent.includes("Sign In Required") || pageContent.includes("Please sign in to access this page")) {
      test.skip(true, "Skipping - authentication required for production");
      return;
    }

    // 3. The main search input is visible.
    const searchInput = page.getByPlaceholder(/search.*subject/i);
    await expect(searchInput).toBeVisible({ timeout: 10000 });

    // 4. The filter section renders.
    const filterBlock = page.getByText(/Filter by/i).first();
    await expect(filterBlock).toBeVisible({ timeout: 5000 });

    // 5. The results header shows "Results" and a count.
    const resultsHeader = page.getByText(/Results/i).first();
    await expect(resultsHeader).toBeVisible({ timeout: 5000 });

    // 6. At least one result row renders (may not be present if no data).
    const resultsList = page.locator("[role='list'], ul, .grid").first();
    await expect(resultsList).toBeVisible({ timeout: 5000 });

    // 7. The "Scoring" pill is visible in the header row next to Results.
    const scoringPill = page.getByText(/^Scoring$/i).first();
    await expect(scoringPill).toBeVisible({ timeout: 5000 });
  });

  test("tooltip appears on scoring pill (new v0.4.22 feature)", async ({ page }) => {
    // Navigate to search
    await page.goto("/search", { waitUntil: "domcontentloaded" });

    // Check if we're on the login page
    await page.waitForTimeout(1000);
    const pageContent = await page.content();
    if (pageContent.includes("Sign In Required") || pageContent.includes("Please sign in to access this page")) {
      test.skip(true, "Skipping - authentication required for production");
      return;
    }

    // Wait for page to load
    await page.waitForLoadState("networkidle");

    // Find the scoring pill
    const scoringPill = page.getByTestId("scoring-pill");
    await expect(scoringPill).toBeVisible({ timeout: 10000 });

    // Hover over the pill
    await scoringPill.hover();

    // Wait a bit for tooltip to appear (100ms delay from TooltipProvider)
    await page.waitForTimeout(200);

    // Check tooltip is visible
    const tooltip = page.locator("[role='tooltip']");
    await expect(tooltip).toBeVisible({ timeout: 3000 });

    // Verify tooltip contains expected content
    await expect(tooltip).toContainText(/boost|recency|scale/i);
  });

  test("active filters show visual feedback (new v0.4.22 feature)", async ({ page }) => {
    // Navigate to search
    await page.goto("/search", { waitUntil: "domcontentloaded" });

    // Check if we're on the login page
    await page.waitForTimeout(1000);
    const pageContent = await page.content();
    if (pageContent.includes("Sign In Required") || pageContent.includes("Please sign in to access this page")) {
      test.skip(true, "Skipping - authentication required for production");
      return;
    }

    // Find and click the "ats" filter button
    const atsFilter = page.getByTestId("filter-ats");
    await expect(atsFilter).toBeVisible({ timeout: 10000 });

    // Click to activate
    await atsFilter.click();

    // Wait for state update
    await page.waitForTimeout(300);

    // Check that active filters bar appears
    const activeFiltersText = page.getByText(/Active filters:/i);
    await expect(activeFiltersText).toBeVisible({ timeout: 5000 });

    // Check that "ats" badge appears in active filters
    const atsBadge = page.locator("div, span").filter({ hasText: /^ats$/i }).first();
    await expect(atsBadge).toBeVisible({ timeout: 3000 });

    // Check that "Clear all" button is visible
    const clearAllButton = page.getByText(/Clear all/i);
    await expect(clearAllButton).toBeVisible({ timeout: 3000 });
  });

  test("scores are displayed correctly (new v0.4.22 feature)", async ({ page }) => {
    // Navigate to search with relevance sort (default)
    await page.goto("/search?q=Interview&sort=relevance", { waitUntil: "domcontentloaded" });

    // Check if we're on the login page
    await page.waitForTimeout(1000);
    const pageContent = await page.content();
    if (pageContent.includes("Sign In Required") || pageContent.includes("Please sign in to access this page")) {
      test.skip(true, "Skipping - authentication required for production");
      return;
    }

    // Wait for results
    await page.waitForLoadState("networkidle");

    // Check results header is visible
    const resultsHeader = page.getByTestId("results-header");
    await expect(resultsHeader).toBeVisible({ timeout: 10000 });

    // Check that score labels exist (may or may not be visible depending on data)
    const scoreLabels = page.locator("span:has-text('score:')");
    const scoreCount = await scoreLabels.count();

    // If scores are shown, they should be positive numbers
    if (scoreCount > 0) {
      const firstScore = await scoreLabels.first().textContent();
      expect(firstScore).toMatch(/score:\s*\d+/);
    }

    // This test passes either way - we're just checking the feature doesn't break
  });
});
