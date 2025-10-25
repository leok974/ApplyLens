/**
 * @prodSafe: Search filter interactions and regression tests
 *
 * These tests verify that:
 * 1. Strict filters can lead to empty results (not stuck in loading)
 * 2. "Clear all filters" button resets to defaults and re-runs search
 * 3. Filter state is deterministic (not accidentally enabled)
 */

import { test, expect } from '@playwright/test';

test.describe('@prodSafe search filters', () => {
  test('strict filters can lead to empty, clearing brings results/empty deterministically', async ({ page }) => {
    // Navigate to search with VERY strict filters (likely to be empty)
    await page.goto('/search?q=Interview&scale=30d&hideExpired=true&risk_min=80&quarantined=true');

    // Should show empty state (not stuck in loading)
    await expect(page.getByTestId('empty-state')).toBeVisible({ timeout: 10000 });

    // Should show active filters in empty state
    await expect(page.getByText(/Scale: 30d/i)).toBeVisible();
    await expect(page.getByText(/Hide expired/i)).toBeVisible();
    await expect(page.getByText(/Risk ≥ 80/i)).toBeVisible();
    await expect(page.getByText(/Quarantined only/i)).toBeVisible();

    // Clear all filters button should be visible
    const clearButton = page.getByTestId('clear-filters-button');
    await expect(clearButton).toBeVisible();

    // Click clear filters
    await clearButton.click();

    // Now either see items or explicit empty (but filters should be cleared)
    // Poll to handle async search
    await expect.poll(async () => {
      const hasResults = await page.getByTestId('result-item').count();
      const hasEmpty = await page.getByTestId('empty-state').isVisible().catch(() => false);
      return hasResults > 0 || hasEmpty;
    }, { timeout: 10000 }).toBeTruthy();

    // Verify filters are cleared (check URL)
    const url = new URL(page.url());
    expect(url.searchParams.get('hideExpired')).toBeNull();
    expect(url.searchParams.get('quarantined')).toBeNull();
    expect(url.searchParams.get('risk_min')).toBeNull();
    // Scale should be default (60d) or omitted
    const scale = url.searchParams.get('scale');
    expect(scale === null || scale === '60d').toBeTruthy();
  });

  test('URL params are parsed strictly (no accidental filter enabling)', async ({ page }) => {
    // Navigate with NO filter params (should use defaults)
    await page.goto('/search?q=Interview');

    // Wait for search to complete
    await page.waitForTimeout(2000);

    // Check that filters are NOT enabled by default
    const url = new URL(page.url());
    expect(url.searchParams.get('hideExpired')).toBeNull();
    expect(url.searchParams.get('quarantined')).toBeNull();
    expect(url.searchParams.get('risk_min')).toBeNull();

    // Verify filter buttons show default state
    const hideExpiredButton = page.getByTestId('filter-hide-expired');
    await expect(hideExpiredButton).toContainText(/Hide expired/i); // Should say "Hide" not "Show"
  });

  test('clear filters resets to defaults and runs search', async ({ page }) => {
    // Start with some filters enabled
    await page.goto('/search?q=Interview&hideExpired=true&risk_min=70');

    // Wait for initial search
    await expect(page.getByTestId('empty-state').or(page.getByTestId('result-item').first())).toBeVisible({ timeout: 10000 });

    // Verify filters are active in URL
    let url = new URL(page.url());
    expect(url.searchParams.get('hideExpired')).toBe('true');
    expect(url.searchParams.get('risk_min')).toBe('70');

    // Find and click clear filters button (in empty state or add to filter controls)
    const clearButton = page.getByTestId('clear-filters-button');
    if (await clearButton.isVisible()) {
      await clearButton.click();

      // Wait for search to complete
      await page.waitForTimeout(2000);

      // Verify filters are cleared in URL
      url = new URL(page.url());
      expect(url.searchParams.get('hideExpired')).toBeNull();
      expect(url.searchParams.get('risk_min')).toBeNull();
    }
  });

  test('empty state shows active filters for debugging', async ({ page }) => {
    // Navigate with multiple active filters
    await page.goto('/search?q=NonexistentCompanyXYZ123&scale=7d&hideExpired=true&risk_min=90&quarantined=true');

    // Should show empty state
    await expect(page.getByTestId('empty-state')).toBeVisible({ timeout: 10000 });

    // Should show query
    await expect(page.getByText(/Query:.*NonexistentCompanyXYZ123/i)).toBeVisible();

    // Should show all active filters
    await expect(page.getByText(/Scale: 7d/i)).toBeVisible();
    await expect(page.getByText(/Hide expired/i)).toBeVisible();
    await expect(page.getByText(/Risk ≥ 90/i)).toBeVisible();
    await expect(page.getByText(/Quarantined only/i)).toBeVisible();

    // Should have clear button
    await expect(page.getByTestId('clear-filters-button')).toBeVisible();
  });

  test('omit default values from URL to avoid stale params', async ({ page }) => {
    // Navigate with explicit defaults
    await page.goto('/search?q=Interview&scale=60d&hideExpired=false&quarantined=false');

    // Wait for search
    await page.waitForTimeout(2000);

    // After search, URL should omit default values
    const url = new URL(page.url());

    // Scale=60d should be omitted (it's the default)
    expect(url.searchParams.get('scale')).toBeNull();

    // hideExpired=false should be omitted (default is false)
    expect(url.searchParams.get('hideExpired')).toBeNull();

    // quarantined=false should be omitted (default is false)
    expect(url.searchParams.get('quarantined')).toBeNull();
  });
});
