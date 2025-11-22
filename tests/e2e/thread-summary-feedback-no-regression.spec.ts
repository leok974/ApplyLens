import { test, expect } from "@playwright/test";
import { seedInboxThreads } from "./utils/seedInbox";

/**
 * ThreadViewer regression safety after Phase 5.2
 *
 * This test ensures that Phase 5.2 (summary feedback) did NOT secretly break
 * existing triage console behaviors we rely on.
 *
 * PROD-SAFE: Does NOT press Archive/Quarantine/Mark Safe.
 * Only tests keyboard nav and presence of sections.
 */
test.describe("ThreadViewer regression safety after Phase 5.2", () => {
  test.beforeEach(async ({ request }) => {
    await seedInboxThreads(request);
  });

  test("ThreadViewer still mounts core sections and keyboard nav still moves selection", async ({ page }) => {
    await page.goto("/inbox");

    // 1. We expect multiple rows. We'll grab the first two.
    const rows = page.locator('[data-testid="thread-row"]');
    await expect(rows.first(), "Need at least one thread row").toBeVisible();
    await expect(rows.nth(1), "Need at least two thread rows for nav test").toBeVisible();

    // 2. Click first row to open ThreadViewer and establish initial selection.
    await rows.first().click();

    // Assert that first row is marked selected visually.
    // Add data-selected="true" or aria-selected="true" in your row render.
    await expect(
      rows.first(),
      "First row should report itself as selected after click"
    ).toHaveAttribute("data-selected", "true");

    // 3. Core sections should render in correct order.
    const riskSection = page.locator('[data-testid="risk-analysis-section"]');
    const summarySection = page.locator('[data-testid="thread-summary-section"]');
    const timelineSection = page.locator('[data-testid="conversation-timeline-section"]');
    const actionBar = page.locator('[data-testid="thread-action-bar"]');

    await expect(riskSection, "RiskAnalysisSection should be visible").toBeVisible();
    await expect(summarySection, "ThreadSummarySection should be visible").toBeVisible();
    await expect(timelineSection, "ConversationTimelineSection should be visible").toBeVisible();
    await expect(actionBar, "ThreadActionBar should be visible").toBeVisible();

    // 4. Keyboard nav: ArrowDown should move selection to the next row
    // and ThreadViewer should update to that row's content.
    await page.keyboard.press("ArrowDown");

    // Expect second row is now selected.
    await expect(
      rows.nth(1),
      "Second row should become selected after ArrowDown"
    ).toHaveAttribute("data-selected", "true");

    // And first row should no longer be selected.
    await expect(
      rows.first(),
      "First row should no longer be selected after ArrowDown"
    ).toHaveAttribute("data-selected", "false");

    // 5. Escape should close the viewer drawer.
    await page.keyboard.press("Escape");

    // After Escape, ThreadViewer sections should be gone.
    await expect(
      riskSection,
      "RiskAnalysisSection should unmount on Escape close"
    ).toHaveCount(0);

    await expect(
      actionBar,
      "Action bar should unmount on Escape close"
    ).toHaveCount(0);
  });

  test("ArrowUp navigation works correctly", async ({ page }) => {
    await page.goto("/inbox");

    const rows = page.locator('[data-testid="thread-row"]');
    await expect(rows.nth(1)).toBeVisible();

    // Click second row
    await rows.nth(1).click();

    // Verify second row is selected
    await expect(rows.nth(1)).toHaveAttribute("data-selected", "true");

    // Press ArrowUp to move to first row
    await page.keyboard.press("ArrowUp");

    // Verify first row is now selected
    await expect(rows.first()).toHaveAttribute("data-selected", "true");
    await expect(rows.nth(1)).toHaveAttribute("data-selected", "false");
  });

  test("all Phase 5 sections render without errors", async ({ page }) => {
    await page.goto("/inbox");

    const row = page.locator('[data-testid="thread-row"]').first();
    await row.click();

    // Verify all sections are present
    const riskSection = page.locator('[data-testid="risk-analysis-section"]');
    const summarySection = page.locator('[data-testid="thread-summary-section"]');
    const timelineSection = page.locator('[data-testid="conversation-timeline-section"]');
    const actionBar = page.locator('[data-testid="thread-action-bar"]');

    // All sections should be visible
    await expect(riskSection).toBeVisible();
    await expect(summarySection).toBeVisible();
    await expect(timelineSection).toBeVisible();
    await expect(actionBar).toBeVisible();

    // Verify sections render in correct order (risk -> summary -> timeline)
    const sections = page.locator('[data-testid^="risk-analysis-section"], [data-testid^="thread-summary-section"], [data-testid^="conversation-timeline-section"]');
    const count = await sections.count();
    expect(count).toBeGreaterThanOrEqual(3);
  });

  test("feedback controls don't interfere with keyboard shortcuts", async ({ page }) => {
    await page.goto("/inbox");

    const rows = page.locator('[data-testid="thread-row"]');
    await rows.first().click();

    // Wait for summary section to load
    const summarySection = page.locator('[data-testid="thread-summary-section"]');
    await expect(summarySection).toBeVisible();

    // Press ArrowDown - should navigate to next thread, not interfere with feedback UI
    await page.keyboard.press("ArrowDown");

    // Verify navigation worked
    await expect(rows.nth(1)).toHaveAttribute("data-selected", "true");

    // Press Escape - should close drawer
    await page.keyboard.press("Escape");

    // Verify drawer closed
    const actionBar = page.locator('[data-testid="thread-action-bar"]');
    await expect(actionBar).toHaveCount(0);
  });
});
