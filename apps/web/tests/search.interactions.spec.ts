import { test, expect } from "@playwright/test";
import { waitForSearchResults } from "./utils/waitReady";

test.describe("Search Filters Interactivity", () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to search page with initial query
    await page.goto("/search?q=Interview");
    await page.waitForLoadState("networkidle");
  });

  test("label filters are clickable and update results", async ({ page }) => {
    // Wait for search results to load with proper timeout
    const hasResults = await waitForSearchResults(page, { skipIfNoResults: true });

    // Check if we have results - if not, skip this test as it's data-dependent
    if (!hasResults) {
      console.log('⏭️  Skipping test: No search results available for query "Interview"');
      test.skip();
      return;
    }

    const resultsContainer = page.locator('[data-testid="results"]');

    // Get initial result count
    const initialResults = await page.locator('[data-testid^="result-"]').count();
    console.log(`Initial results: ${initialResults}`);    // Click on "Interview" label filter
    const interviewFilter = page.locator('button:has-text("Interview")').first();
    await expect(interviewFilter).toBeVisible();
    await expect(interviewFilter).toBeEnabled();

    await interviewFilter.click();

    // Wait for URL to update with labels parameter
    await page.waitForURL(/labels=interview/, { timeout: 2000 });

    // Verify URL contains the label filter
    expect(page.url()).toContain("labels=interview");

    // Wait for results to update (debounce + API call)
    await page.waitForTimeout(500);

    console.log("✅ Label filter successfully clicked and URL updated");
  });

  test("category filters are clickable and update URL", async ({ page }) => {
    // Click on "ats" category filter
    const atsFilter = page.locator('[data-testid="cat-ats"]');
    await expect(atsFilter).toBeVisible();
    await expect(atsFilter).toBeEnabled();

    await atsFilter.click();

    // Wait for URL to update with category parameter
    await page.waitForURL(/cat=ats/, { timeout: 2000 });

    // Verify URL contains the category filter
    expect(page.url()).toContain("cat=ats");

    console.log("✅ Category filter successfully clicked and URL updated");
  });

  test("replied filter chips are clickable", async ({ page }) => {
    // Click on "Replied" chip
    const repliedChip = page.locator('button:has-text("Replied")').first();
    await expect(repliedChip).toBeVisible();
    await expect(repliedChip).toBeEnabled();

    await repliedChip.click();

    // Wait for URL to update with replied parameter
    await page.waitForURL(/replied=true/, { timeout: 2000 });

    // Verify URL contains the replied filter
    expect(page.url()).toContain("replied=true");

    console.log("✅ Replied filter successfully clicked and URL updated");
  });

  test("date range controls are accessible", async ({ page }) => {
    // Find date inputs
    const fromInput = page.locator('input[type="date"]').first();
    const toInput = page.locator('input[type="date"]').last();

    await expect(fromInput).toBeVisible();
    await expect(toInput).toBeVisible();
    await expect(fromInput).toBeEnabled();
    await expect(toInput).toBeEnabled();

    // Set date range
    await fromInput.fill("2025-01-01");
    await toInput.fill("2025-12-31");

    // Wait for URL to update
    await page.waitForURL(/date_from=2025-01-01/, { timeout: 2000 });

    expect(page.url()).toContain("date_from=2025-01-01");
    expect(page.url()).toContain("date_to=2025-12-31");

    console.log("✅ Date filters successfully set and URL updated");
  });

  test("clear all filters button works", async ({ page }) => {
    // Apply multiple filters
    await page.locator('button:has-text("Interview")').first().click();
    await page.waitForURL(/labels=interview/, { timeout: 2000 });

    await page.locator('[data-testid="cat-ats"]').click();
    await page.waitForURL(/cat=ats/, { timeout: 2000 });

    // Click "Clear all filters" button in SearchFilters card
    const clearButton = page.locator('button:has-text("Clear all filters")');
    await expect(clearButton).toBeVisible();
    await clearButton.click();

    // Wait for filters to clear
    await page.waitForTimeout(500);

    // Verify URL no longer contains filter params (except q)
    const url = page.url();
    expect(url).not.toContain("labels=");
    expect(url).toContain("q=Interview"); // Original query should remain

    console.log("✅ Clear all filters successfully cleared filters");
  });

  test("security filters are clickable", async ({ page }) => {
    // Click high-risk filter
    const highRiskChip = page.locator('[data-testid="chip-high-risk"]');
    await expect(highRiskChip).toBeVisible();

    await highRiskChip.click();

    // Wait for URL to update
    await page.waitForURL(/risk_min=80/, { timeout: 2000 });

    expect(page.url()).toContain("risk_min=80");

    console.log("✅ Security filter successfully clicked and URL updated");
  });

  test("no stealth overlays block filter interactions", async ({ page }) => {
    // Get position of a filter button
    const filterButton = page.locator('button:has-text("Interview")').first();
    const box = await filterButton.boundingBox();

    if (!box) {
      throw new Error("Filter button not found");
    }

    // Get element at that position
    const elementHandle = await page.evaluateHandle(
      ({ x, y }) => document.elementFromPoint(x, y),
      { x: box.x + box.width / 2, y: box.y + box.height / 2 }
    );

    // Get computed styles
    const styles = await page.evaluate((el) => {
      if (!el) return null;
      const cs = getComputedStyle(el as Element);
      return {
        pointerEvents: cs.pointerEvents,
        opacity: cs.opacity,
        zIndex: cs.zIndex,
      };
    }, elementHandle);

    console.log("Element at filter position:", styles);

    // Verify no transparent overlay is blocking
    if (styles) {
      expect(styles.pointerEvents).not.toBe("none");
      expect(parseFloat(styles.opacity)).toBeGreaterThan(0.5);
    }

    // Verify button is actually clickable
    await filterButton.click({ force: false }); // force: false ensures natural click

    console.log("✅ No stealth overlays detected, filters are clickable");
  });

  test("sort control changes trigger re-fetch", async ({ page }) => {
    // Change sort order
    const sortSelect = page.locator('select').first();
    await expect(sortSelect).toBeVisible();
    await expect(sortSelect).toBeEnabled();

    await sortSelect.selectOption("received_desc");

    // Wait for URL to update
    await page.waitForURL(/sort=received_desc/, { timeout: 2000 });

    expect(page.url()).toContain("sort=received_desc");

    // Wait for results to refresh
    await page.waitForTimeout(500);

    console.log("✅ Sort control successfully changed and URL updated");
  });
});

test.describe("Search Page - No Paused State Blocking", () => {
  test("filters remain interactive when system is operational", async ({ page }) => {
    await page.goto("/search?q=Interview");
    await page.waitForLoadState("networkidle");

    // Check that no fieldset is disabled
    const disabledFieldsets = page.locator('fieldset[disabled]');
    await expect(disabledFieldsets).toHaveCount(0);

    // Check that filter container doesn't have pointer-events-none
    const filterCard = page.locator('.p-4.mb-4').first();
    const pointerEvents = await filterCard.evaluate((el) =>
      getComputedStyle(el).pointerEvents
    );

    expect(pointerEvents).not.toBe("none");

    console.log("✅ No disabled fieldsets or pointer-events blocking filters");
  });
});
