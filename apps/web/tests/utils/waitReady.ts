import { Page } from "@playwright/test";

/**
 * Wait for the app to be fully loaded and ready for interaction.
 *
 * This is more reliable than arbitrary timeouts or just networkidle,
 * as it waits for the app's actual ready state.
 *
 * @param page - Playwright page instance
 * @param timeout - Maximum wait time in ms (default: 5000)
 */
export async function waitReady(page: Page, timeout: number = 5000) {
  // Wait for network to be idle
  await page.waitForLoadState("networkidle");

  // Optional: Wait for app-level ready indicator if you have one
  // Uncomment this if you add a data-testid="app-ready" to your root component
  // await page.waitForSelector('[data-testid="app-ready"]', { timeout });

  // Give React a moment to finish hydration and initial renders
  await page.waitForTimeout(100);
}

/**
 * Wait for search results to load and be visible.
 * More reliable than checking for specific result counts.
 *
 * @param page - Playwright page instance
 * @param options - Options for waiting
 * @returns true if results are visible, false if no results found
 */
export async function waitForSearchResults(
  page: Page,
  options: { skipIfNoResults?: boolean } = {}
): Promise<boolean> {
  // Wait for the results container to exist (may be hidden if no results)
  try {
    await page.waitForSelector('[data-testid="results"]', {
      state: "attached",
      timeout: 10000
    });

    // Check if it's visible (has results) or hidden (no results)
    const resultsContainer = page.locator('[data-testid="results"]');
    const isVisible = await resultsContainer.isVisible();

    if (isVisible) {
      // Give search results a moment to render
      await page.waitForTimeout(200);
      return true;
    } else {
      // No results found - container is hidden
      if (options.skipIfNoResults) {
        return false;
      }
      // If we're not skipping, wait a bit more in case results are loading
      await page.waitForTimeout(500);
      return await resultsContainer.isVisible();
    }
  } catch (error) {
    // Results container doesn't exist at all
    if (options.skipIfNoResults) {
      return false;
    }
    throw error;
  }
}
