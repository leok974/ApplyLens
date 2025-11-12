import { test, expect } from "@playwright/test";
import { seedInboxThreads } from "./utils/seedInbox";

test.describe("ThreadViewer keyboard triage mode (Phase 3)", () => {
  test.beforeEach(async ({ request }) => {
    await seedInboxThreads(request);
  });

  test("ArrowUp/ArrowDown cycle selection, D triggers archive+advance locally, Escape closes", async ({ page }) => {
    await page.goto("/inbox");

    const rows = page.locator('[data-testid="thread-row"]');
    await expect(rows.nth(0)).toBeVisible();
    await expect(rows.nth(1)).toBeVisible();

    // Click first row to open ThreadViewer
    await rows.nth(0).click();

    const viewer = page.locator('[data-testid="thread-viewer"]');
    await expect(viewer).toBeVisible();

    // First row should be selected
    await expect(rows.nth(0)).toHaveAttribute("data-selected", "true");

    // Press ArrowDown → selection moves to second row (no close)
    await page.keyboard.press("ArrowDown");

    await expect(rows.nth(1)).toHaveAttribute("data-selected", "true");
    await expect(rows.nth(0)).not.toHaveAttribute("data-selected", "true");

    // Press ArrowUp → selection moves back to first row
    await page.keyboard.press("ArrowUp");
    await expect(rows.nth(0)).toHaveAttribute("data-selected", "true");

    // Press "D" (archive+advance shortcut)
    // NOTE: this is potentially stateful. We assert local behavior but won't assert side effects in prod.
    await page.keyboard.press("KeyD");

    // After D with auto-advance ON, we expect to have advanced to next thread.
    // That means row[1] should now be selected.
    await expect(
      rows.nth(1),
      "Pressing D should advance to the next thread when auto-advance is enabled"
    ).toHaveAttribute("data-selected", "true");

    // Press Escape → ThreadViewer should close/unmount
    await page.keyboard.press("Escape");
    await expect(viewer).toHaveCount(0);
  });
});
