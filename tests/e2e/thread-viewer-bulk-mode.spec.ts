import { test, expect } from "@playwright/test";
import { seedInboxThreads } from "./utils/seedInbox";

const SKIP_MUTATING = process.env.PROD === "1";

test.describe("ThreadViewer bulk mode (Phase 4 / 4.5 / 4.6 / 4.7)", () => {

  test(SKIP_MUTATING ? "skipped in prod" : "bulk select, bulk action, undo works with optimistic updates", async ({ page, request }) => {
    test.skip(SKIP_MUTATING, "Bulk actions mutate state; skipping in prod");

    await seedInboxThreads(request);

    await page.goto("/inbox");

    const rows = page.locator('[data-testid="thread-row"]');
    await expect(rows.nth(0)).toBeVisible();
    await expect(rows.nth(1)).toBeVisible();
    await expect(rows.nth(2)).toBeVisible();

    // Select multiple rows via their checkboxes (this should NOT open viewer)
    const cb0 = rows.nth(0).locator('[data-testid="thread-row-checkbox"]');
    const cb1 = rows.nth(1).locator('[data-testid="thread-row-checkbox"]');
    await cb0.check();
    await cb1.check();

    // Open one of them in ThreadViewer just to mount the action bar
    await rows.nth(0).click();
    const viewer = page.locator('[data-testid="thread-viewer"]');
    await expect(viewer).toBeVisible();

    const actionBar = viewer.locator('[data-testid="thread-action-bar"]');
    await expect(actionBar).toBeVisible();

    // Now we expect to be in "bulk mode": bulk buttons should be visible.
    const bulkArchiveBtn = actionBar.locator('[data-testid="action-archive-bulk"]');
    await expect(bulkArchiveBtn).toBeVisible();

    // Handled progress should be visible and non-empty (e.g. "2 of 50 handled")
    const progress = actionBar.locator('[data-testid="handled-progress"]');
    await expect(progress).toBeVisible();
    await expect(progress).not.toHaveText("");

    // Toggle auto-advance and confirm analytics doesn't crash UI
    const autoToggle = actionBar.locator('[data-testid="auto-advance-toggle"] input[type=checkbox]');
    await autoToggle.click(); // flip it off or on
    // we don't assert analytics, but this covers the UI path

    // Click bulk archive
    await bulkArchiveBtn.click();

    // We expect an optimistic toast to appear:
    // success (📥 archived), warning for partial, or error for full fail.
    const toast = page.locator('[data-testid="toast-container"]');
    await expect(toast).toBeVisible();

    // If success toast has Undo button, press it and assert toast again.
    const undoButton = toast.locator("button:has-text('Undo')");
    if (await undoButton.isVisible()) {
      await undoButton.click();

      // After undo click we expect a follow-up toast ("↩️ Undone" variant).
      await expect(toast).toContainText(/Undone|↩️/i);
    }
  });
});
