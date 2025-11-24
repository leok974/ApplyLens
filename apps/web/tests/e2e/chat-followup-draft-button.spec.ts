/**
 * E2E Test: Chat Thread Viewer - Follow-up Draft Button
 *
 * Tests that the "Draft follow-up" button appears in Thread Viewer
 * when viewing a thread that has an associated application.
 *
 * This is a sanity check - we do NOT click the button to avoid
 * triggering LLM API calls in production.
 *
 * Production-safe: Uses explicit baseUrl, networkidle waits, and data-testid selectors.
 *
 * @prodSafe @chat @threads @followup-draft
 */

import { test, expect } from '@playwright/test';

const baseUrl = process.env.E2E_BASE_URL ?? 'http://127.0.0.1:5173';

test.describe('@prodSafe @chat @threads @followup-draft Thread Viewer Follow-up Draft Button', () => {
  test('Draft follow-up button is visible for threads with application context', async ({ page }) => {
    // ========================================
    // STEP 1: Navigate to Chat
    // ========================================
    await page.goto(`${baseUrl}/chat`);
    await page.waitForLoadState('networkidle');

    // Wait for chat root to be ready
    await expect(page.getByTestId('chat-root')).toBeVisible({ timeout: 10000 });

    // ========================================
    // STEP 2: Click Follow-ups Mail Tool
    // ========================================
    const followupsButton = page.getByTestId('mailtool-followups');

    // If Follow-ups button doesn't exist, skip test
    const hasFollowupsButton = await followupsButton.isVisible({ timeout: 5000 }).catch(() => false);
    if (!hasFollowupsButton) {
      console.log('Follow-ups mail tool button not found - skipping test');
      test.skip();
      return;
    }

    await followupsButton.click();

    // Wait for agent response
    await page.waitForTimeout(5000);

    // ========================================
    // STEP 3: Check if Thread List UI Appears
    // ========================================
    const threadCard = page.getByTestId('thread-card');
    const hasThreads = await threadCard.isVisible({ timeout: 15000 }).catch(() => false);

    if (!hasThreads) {
      console.log('No follow-up threads found - skipping test');
      test.skip();
      return;
    }

    // Verify thread list is present
    const threadList = page.getByTestId('thread-list');
    await expect(threadList).toBeVisible();

    // ========================================
    // STEP 4: Find Thread with Application ID
    // ========================================
    // Look for thread rows that have data-application-id attribute
    const threadRows = page.getByTestId('thread-row');
    const rowCount = await threadRows.count();

    let foundThreadWithApp = false;
    let rowIndex = -1;

    for (let i = 0; i < rowCount; i++) {
      const row = threadRows.nth(i);
      const appId = await row.getAttribute('data-application-id');

      if (appId && appId !== 'null' && appId !== '') {
        foundThreadWithApp = true;
        rowIndex = i;
        break;
      }
    }

    if (!foundThreadWithApp) {
      console.log('No threads with application_id found - skipping test');
      test.skip();
      return;
    }

    // ========================================
    // STEP 5: Click Thread Row to Open Viewer
    // ========================================
    const targetRow = threadRows.nth(rowIndex);
    await targetRow.click();

    // Wait for Thread Viewer to appear
    const threadViewer = page.getByTestId('thread-viewer');
    await expect(threadViewer).toBeVisible({ timeout: 10000 });

    // ========================================
    // STEP 6: Verify Draft Follow-up Button
    // ========================================
    const draftButton = page.getByTestId('thread-viewer-draft-followup');
    await expect(draftButton).toBeVisible({ timeout: 5000 });

    // Verify button has expected text
    await expect(draftButton).toContainText(/Draft follow-up/i);

    // Verify button is enabled (not disabled)
    await expect(draftButton).toBeEnabled();

    // ========================================
    // IMPORTANT: Do NOT click the button
    // ========================================
    // We don't want to trigger LLM API calls in production E2E tests.
    // This test only verifies UI presence and state.

    console.log('✅ Draft follow-up button is visible and enabled');
  });
});
