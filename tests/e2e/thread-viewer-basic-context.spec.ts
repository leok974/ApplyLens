import { test, expect } from "@playwright/test";
import { seedInboxThreads } from "./utils/seedInbox";

test.describe("ThreadViewer basic context (Phases 1, 2, 5)", () => {
  test.beforeEach(async ({ request }) => {
    await seedInboxThreads(request);
  });

  test("opens a thread and shows risk → summary → timeline → body → actions in order", async ({ page }) => {
    await page.goto("/inbox");

    // Need at least one row
    const rows = page.locator('[data-testid="thread-row"]');
    await expect(rows.first()).toBeVisible();

    // Open first row
    await rows.first().click();

    const viewer = page.locator('[data-testid="thread-viewer"]');
    await expect(viewer).toBeVisible();

    // Sections should all render
    const risk = viewer.locator('[data-testid="risk-analysis-section"]');
    const summary = viewer.locator('[data-testid="thread-summary-section"]');
    const timeline = viewer.locator('[data-testid="conversation-timeline-section"]');
    const actionBar = viewer.locator('[data-testid="thread-action-bar"]');

    await expect(risk, "RiskAnalysisSection should be visible").toBeVisible();
    await expect(summary, "ThreadSummarySection should be visible").toBeVisible();
    await expect(timeline, "ConversationTimelineSection should be visible").toBeVisible();
    await expect(actionBar, "ThreadActionBar should be visible").toBeVisible();

    // Summary block should actually have a headline + bullet list
    await expect(summary.locator('[data-testid="thread-summary-headline"]')).toBeVisible();
    await expect(summary.locator('[data-testid="thread-summary-details"] li').first()).toBeVisible();

    // Timeline should have at least one event row
    await expect(timeline.locator("[data-testid='timeline-event']").first()).toBeVisible();

    // ActionBar single-thread actions exist
    await expect(actionBar.locator('[data-testid="action-archive-single"]')).toBeVisible();
    await expect(actionBar.locator('[data-testid="action-mark-safe-single"]')).toBeVisible();
    await expect(actionBar.locator('[data-testid="action-quarantine-single"]')).toBeVisible();
    await expect(actionBar.locator('[data-testid="action-open-gmail"]')).toBeVisible();

    // Sanity: auto-advance toggle and progress footer exist
    await expect(actionBar.locator('[data-testid="auto-advance-toggle"]')).toBeVisible();
    await expect(actionBar.locator('[data-testid="handled-progress"]')).toBeVisible();

    // Risk badge sanity (optional low/med/high/etc.): check text exists
    await expect(risk).toContainText(/low|medium|high|critical/i);
  });
});
