import { test, expect } from "@playwright/test";
import { seedInboxThreads } from "./utils/seedInbox";

test.describe("Thread summary feedback flow (Phase 5.2)", () => {
  test.beforeEach(async ({ request }) => {
    await seedInboxThreads(request);
  });

  test("user can mark summary as helpful and see optimistic thank-you", async ({ page }) => {
    // 1. Go to Inbox page (or Actions/Search if that's more reliable in prod-safe env)
    // Assumption: /inbox is routed and shows email/thread rows.
    await page.goto("/inbox");

    // 2. Wait for at least one row to render so we can open ThreadViewer.
    // Prefer a data-testid if you have one like data-testid="thread-row"
    const row = page.locator('[data-testid="thread-row"]').first();
    await expect(row, "Expected at least one inbox row to render").toBeVisible();

    // 3. Click that row to open the drawer (ThreadViewer).
    await row.click();

    // 4. ThreadViewer should now be open. We assert the Summary section is present BEFORE feedback.
    // Prefer: data-testid="thread-summary-section"
    const summarySection = page.locator('[data-testid="thread-summary-section"]');
    await expect(summarySection, "ThreadSummarySection should render").toBeVisible();

    // 5. Inside summary section, we should see the rating prompt "Helpful? Yes / No"
    // Prefer: data-testid="summary-feedback-controls"
    const feedbackControls = summarySection.locator('[data-testid="summary-feedback-controls"]');
    await expect(
      feedbackControls,
      "Expected the Yes/No controls to be visible before feedback is submitted"
    ).toBeVisible();

    // 6. Click "Yes" to indicate the summary was helpful.
    // Prefer button testid data-testid="summary-feedback-yes"
    const yesButton = summarySection.locator('[data-testid="summary-feedback-yes"]');
    await yesButton.click();

    // 7. Immediately after clicking, the UI should flip to acknowledgement text.
    // Prefer: data-testid="summary-feedback-ack"
    const ack = summarySection.locator('[data-testid="summary-feedback-ack"]');
    await expect(
      ack,
      "After clicking Yes, component should optimistically replace controls with a thank-you message"
    ).toBeVisible();

    // The ack text should be either "Thanks!" or "Got it — we'll improve this."
    await expect(
      ack,
      "Acknowledgement copy should match one of the expected variants"
    ).toHaveText(/Thanks|we'll improve/i);

    // 8. Toast should appear confirming that feedback was recorded.
    // We don't assert exact wording because your toast can differ ("Thanks for the feedback." / "Couldn't record feedback"),
    // but we *do* assert that some toast container appeared.
    //
    // If you have data-testid on your toast container, use it. Otherwise, we look for text.
    const toast = page.locator('[data-testid="toast-container"], text=feedback');
    await expect(
      toast,
      "Expected some toast related to feedback to appear"
    ).toBeVisible({ timeout: 5000 });

    // 9. Ensure no crash: RiskAnalysisSection + ActionBar should still be visible after feedback.
    const riskSection = page.locator('[data-testid="risk-analysis-section"]');
    const actionBar = page.locator('[data-testid="thread-action-bar"]');
    await expect(riskSection, "Risk panel should still be mounted").toBeVisible();
    await expect(actionBar, "Action bar should still be mounted").toBeVisible();

    // 10. Sanity check: the Yes/No controls should now be gone (we don't want flicker or duplicate submission).
    await expect(
      feedbackControls,
      "Feedback controls should be hidden or removed after submission"
    ).toHaveCount(0);
  });

  test("user can mark summary as not helpful and see acknowledgment", async ({ page }) => {
    // Similar flow but click "No" button
    await page.goto("/inbox");

    const row = page.locator('[data-testid="thread-row"]').first();
    await expect(row).toBeVisible();
    await row.click();

    const summarySection = page.locator('[data-testid="thread-summary-section"]');
    await expect(summarySection).toBeVisible();

    const feedbackControls = summarySection.locator('[data-testid="summary-feedback-controls"]');
    await expect(feedbackControls).toBeVisible();

    // Click "No"
    const noButton = summarySection.locator('[data-testid="summary-feedback-no"]');
    await noButton.click();

    // Expect acknowledgment
    const ack = summarySection.locator('[data-testid="summary-feedback-ack"]');
    await expect(ack).toBeVisible();
    await expect(ack).toHaveText(/we'll improve/i);

    // Toast should appear
    const toast = page.locator('[data-testid="toast-container"]');
    await expect(toast).toBeVisible({ timeout: 5000 });

    // Controls should be gone
    await expect(feedbackControls).toHaveCount(0);
  });

  test("feedback works without network (optimistic UI)", async ({ page }) => {
    // Simulate offline mode to test optimistic UI behavior
    await page.goto("/inbox");

    const row = page.locator('[data-testid="thread-row"]').first();
    await expect(row).toBeVisible();
    await row.click();

    const summarySection = page.locator('[data-testid="thread-summary-section"]');
    await expect(summarySection).toBeVisible();

    // Go offline
    await page.context().setOffline(true);

    const yesButton = summarySection.locator('[data-testid="summary-feedback-yes"]');
    await yesButton.click();

    // Even offline, UI should update optimistically
    const ack = summarySection.locator('[data-testid="summary-feedback-ack"]');
    await expect(ack).toBeVisible();
    await expect(ack).toHaveText(/Thanks/i);

    // Toast might show error, but UI state should remain
    // (We don't undo the UI state on network failure)
  });
});
