/**
 * Phase 5.3: Style Choice Explanation E2E Test
 *
 * Verifies the Style Debug Panel on the Companion Settings page
 * exercises the full stack: UI → API → Backend explanation endpoint.
 *
 * @tags @companion @style-debug
 *
 * To run:
 * pnpm exec playwright test --grep "@companion"
 * pnpm exec playwright test --grep "@style-debug"
 */

import { test, expect } from "@playwright/test";

test.describe("@companion @style-debug", () => {
  test("Style Debug Panel fetches and displays explanation", async ({ page }) => {
    // Mock runtime config
    await page.route("**/api/config", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          readOnly: false,
          version: "0.5.0",
        }),
      });
    });

    // Mock authentication
    await page.route("**/api/auth/me", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          id: "user123",
          email: "test@example.com",
          is_demo: false,
        }),
      });
    });

    // Mock profile ping (API OK)
    await page.route("**/api/profile/me", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          id: "user123",
          email: "test@example.com",
        }),
      });
    });

    // Mock extension applications (empty for simplicity)
    await page.route("**/api/extension/applications**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([]),
      });
    });

    // Mock extension outreach (empty)
    await page.route("**/api/extension/outreach**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([]),
      });
    });

    // Mock the style explanation endpoint with realistic payload
    await page.route(
      "**/api/extension/learning/explain-style?host=boards.greenhouse.io&schema_hash=demo-hash-123",
      async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            host: "boards.greenhouse.io",
            schema_hash: "demo-hash-123",
            host_family: "greenhouse",
            segment_key: "junior",
            chosen_style_id: "friendly_bullets_v2",
            source: "segment",
            considered_styles: [
              {
                style_id: "friendly_bullets_v2",
                source: "segment",
                segment_key: "junior",
                total_runs: 14,
                helpful_runs: 12,
                unhelpful_runs: 2,
                helpful_ratio: 0.857,
                avg_edit_chars: 110,
                is_winner: true,
              },
              {
                style_id: "concise_paragraph_v1",
                source: "segment",
                segment_key: "junior",
                total_runs: 9,
                helpful_runs: 6,
                unhelpful_runs: 3,
                helpful_ratio: 0.667,
                avg_edit_chars: 150,
                is_winner: false,
              },
            ],
            explanation:
              "We chose style 'friendly_bullets_v2' at the segment level for host family " +
              "'greenhouse' and segment 'junior' because it has 14 runs, " +
              "12 helpful votes (86%), and an average edit size " +
              "of 110 characters. Other styles had lower helpful ratios or required " +
              "more edits on average.",
          }),
        });
      }
    );

    // Navigate to Companion Settings
    await page.goto("http://localhost:5176/settings/companion", {
      waitUntil: "domcontentloaded",
    });
    await page.waitForLoadState("networkidle");

    // Verify page loaded
    await expect(
      page.getByRole("heading", { name: /Browser Companion/i })
    ).toBeVisible({ timeout: 10000 });

    // Scroll to Style Debug Panel
    const debugPanel = page.getByTestId("style-debug-panel");
    await expect(debugPanel).toBeVisible({ timeout: 10000 });
    await debugPanel.scrollIntoViewIfNeeded();

    // Verify panel title
    await expect(
      debugPanel.getByRole("heading", { name: /Style Choice Explanation/i })
    ).toBeVisible();

    // Fill host input (should already have default value)
    const hostInput = debugPanel.getByTestId("style-debug-host-input");
    await expect(hostInput).toBeVisible();
    await expect(hostInput).toHaveValue("boards.greenhouse.io");

    // Fill schema hash input
    const hashInput = debugPanel.getByTestId("style-debug-hash-input");
    await expect(hashInput).toBeVisible();
    await hashInput.fill("demo-hash-123");

    // Click fetch button
    const fetchButton = debugPanel.getByTestId("style-debug-fetch-btn");
    await expect(fetchButton).toBeEnabled();
    await fetchButton.click();

    // Wait for results to appear
    const resultContainer = debugPanel.getByTestId("style-debug-result");
    await expect(resultContainer).toBeVisible({ timeout: 5000 });

    // Assert: Chosen style ID is rendered
    const styleId = debugPanel.getByTestId("style-debug-style-id");
    await expect(styleId).toBeVisible();
    await expect(styleId).toHaveText("friendly_bullets_v2");

    // Assert: Source label shows 'segment'
    const source = debugPanel.getByTestId("style-debug-source");
    await expect(source).toBeVisible();
    await expect(source).toHaveText("segment");

    // Assert: Explanation text is visible and contains key phrases
    const explanationText = debugPanel.getByTestId("style-debug-text");
    await expect(explanationText).toBeVisible();
    await expect(explanationText).toContainText("friendly_bullets_v2");
    await expect(explanationText).toContainText("segment level");
    await expect(explanationText).toContainText("14 runs");
    await expect(explanationText).toContainText("12 helpful votes");
    await expect(explanationText).toContainText("86%");

    // Assert: Stats table is visible
    const statsTable = debugPanel.getByTestId("style-debug-stats-table");
    await expect(statsTable).toBeVisible();

    // Assert: Winner row shows correct data
    const winnerRow = debugPanel.getByTestId("style-row-friendly_bullets_v2");
    await expect(winnerRow).toBeVisible();
    await expect(winnerRow).toHaveClass(/bg-green-50/); // Winner highlight

    const winnerRuns = debugPanel.getByTestId("style-runs-friendly_bullets_v2");
    await expect(winnerRuns).toHaveText("14");

    const winnerRatio = debugPanel.getByTestId("style-ratio-friendly_bullets_v2");
    await expect(winnerRatio).toHaveText("85.7%");

    // Assert: Competitor row is also present
    const competitorRow = debugPanel.getByTestId("style-row-concise_paragraph_v1");
    await expect(competitorRow).toBeVisible();
    await expect(competitorRow).not.toHaveClass(/bg-green-50/); // Not highlighted

    const competitorRuns = debugPanel.getByTestId("style-runs-concise_paragraph_v1");
    await expect(competitorRuns).toHaveText("9");

    const competitorRatio = debugPanel.getByTestId(
      "style-ratio-concise_paragraph_v1"
    );
    await expect(competitorRatio).toHaveText("66.7%");

    console.log("✅ Phase 5.3 E2E test passed: Style explanation UI works end-to-end");
  });

  test("Style Debug Panel shows error when API fails", async ({ page }) => {
    // Mock endpoints as before
    await page.route("**/api/config", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ readOnly: false, version: "0.5.0" }),
      });
    });

    await page.route("**/api/auth/me", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          id: "user123",
          email: "test@example.com",
          is_demo: false,
        }),
      });
    });

    await page.route("**/api/profile/me", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ id: "user123", email: "test@example.com" }),
      });
    });

    await page.route("**/api/extension/applications**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: "[]",
      });
    });

    await page.route("**/api/extension/outreach**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: "[]",
      });
    });

    // Mock style explanation endpoint to fail
    await page.route(
      "**/api/extension/learning/explain-style**",
      async (route) => {
        await route.fulfill({
          status: 500,
          contentType: "application/json",
          body: JSON.stringify({ detail: "Internal server error" }),
        });
      }
    );

    // Navigate to settings
    await page.goto("http://localhost:5176/settings/companion", {
      waitUntil: "domcontentloaded",
    });
    await page.waitForLoadState("networkidle");

    // Locate debug panel
    const debugPanel = page.getByTestId("style-debug-panel");
    await expect(debugPanel).toBeVisible({ timeout: 10000 });

    // Fill inputs
    const hashInput = debugPanel.getByTestId("style-debug-hash-input");
    await hashInput.fill("error-test");

    // Click fetch
    const fetchButton = debugPanel.getByTestId("style-debug-fetch-btn");
    await fetchButton.click();

    // Assert: Error message appears
    const errorDiv = debugPanel.getByTestId("style-debug-error");
    await expect(errorDiv).toBeVisible({ timeout: 5000 });
    await expect(errorDiv).toContainText("Failed to fetch style explanation");

    // Assert: Results are NOT shown
    const resultContainer = debugPanel.getByTestId("style-debug-result");
    await expect(resultContainer).not.toBeVisible();

    console.log("✅ Error handling test passed");
  });

  test("Style Debug Panel requires both host and schema hash", async ({ page }) => {
    // Mock endpoints
    await page.route("**/api/config", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ readOnly: false, version: "0.5.0" }),
      });
    });

    await page.route("**/api/auth/me", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          id: "user123",
          email: "test@example.com",
          is_demo: false,
        }),
      });
    });

    await page.route("**/api/profile/me", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ id: "user123" }),
      });
    });

    await page.route("**/api/extension/applications**", async (route) => {
      await route.fulfill({ status: 200, contentType: "application/json", body: "[]" });
    });

    await page.route("**/api/extension/outreach**", async (route) => {
      await route.fulfill({ status: 200, contentType: "application/json", body: "[]" });
    });

    // Navigate
    await page.goto("http://localhost:5176/settings/companion", {
      waitUntil: "domcontentloaded",
    });
    await page.waitForLoadState("networkidle");

    const debugPanel = page.getByTestId("style-debug-panel");
    await expect(debugPanel).toBeVisible({ timeout: 10000 });

    // Clear host input
    const hostInput = debugPanel.getByTestId("style-debug-host-input");
    await hostInput.clear();

    // Try to click fetch (should be disabled)
    const fetchButton = debugPanel.getByTestId("style-debug-fetch-btn");
    await expect(fetchButton).toBeDisabled();

    // Fill schema hash only
    const hashInput = debugPanel.getByTestId("style-debug-hash-input");
    await hashInput.fill("some-hash");

    // Button should still be disabled (host is empty)
    await expect(fetchButton).toBeDisabled();

    // Fill host
    await hostInput.fill("example.com");

    // Now button should be enabled
    await expect(fetchButton).toBeEnabled();

    console.log("✅ Validation test passed: requires both inputs");
  });
});
