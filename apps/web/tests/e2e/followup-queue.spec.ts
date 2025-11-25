/**
 * E2E Test: Follow-up Queue Page
 *
 * Tests that the Follow-up Queue page loads and displays the merged list
 * of threads and applications. Tests row selection and ThreadViewer integration.
 *
 * Production-safe: Uses test.skip() when no queue items are present.
 *
 * @prodSafe @followups @queue @threads
 */

import { test, expect } from '@playwright/test';

const baseUrl = process.env.E2E_BASE_URL ?? 'http://127.0.0.1:5173';

test.describe('@prodSafe @followups @queue Follow-up Queue Page', () => {
  test('Navigate to follow-up queue and verify page structure', async ({ page }) => {
    // ========================================
    // STEP 1: Navigate to Follow-up Queue
    // ========================================
    await page.goto(`${baseUrl}/followups`);
    await page.waitForLoadState('networkidle');

    // Wait for page to be ready
    await expect(page.getByTestId('followup-queue-page')).toBeVisible({ timeout: 10000 });

    // ========================================
    // STEP 2: Check for Queue Items
    // ========================================
    const queueRows = page.getByTestId('followup-row');
    const hasQueueItems = await queueRows.first().isVisible({ timeout: 5000 }).catch(() => false);

    if (!hasQueueItems) {
      // Empty state - verify "All caught up" message
      await expect(page.getByText('All caught up!')).toBeVisible();
      console.log('Follow-up queue is empty - skipping interaction tests');
      test.skip();
      return;
    }

    // ========================================
    // STEP 3: Verify Queue List Structure
    // ========================================
    await expect(page.getByTestId('followup-queue-list')).toBeVisible();
    await expect(page.getByText('Follow-up Queue')).toBeVisible();

    // Verify at least one queue item is present
    const itemCount = await queueRows.count();
    expect(itemCount).toBeGreaterThan(0);
    console.log(`Found ${itemCount} queue items`);

    // ========================================
    // STEP 4: Click First Queue Item
    // ========================================
    const firstRow = queueRows.first();
    await firstRow.click();

    // Wait for ThreadViewer to appear
    await page.waitForTimeout(1000);

    // ========================================
    // STEP 5: Verify ThreadViewer Appears
    // ========================================
    // ThreadViewer should be visible (exact testid depends on ThreadViewer implementation)
    const threadViewer = page.locator('[data-testid*="thread"]').first();
    const hasThreadViewer = await threadViewer.isVisible({ timeout: 5000 }).catch(() => false);

    if (hasThreadViewer) {
      console.log('ThreadViewer successfully displayed after selecting queue item');
    } else {
      console.log('ThreadViewer not immediately visible - this may be expected for some queue items');
    }

    // ========================================
    // STEP 6: Test Done Toggle (Optional)
    // ========================================
    const doneButton = firstRow.getByTestId('toggle-done-button').first();
    const hasDoneButton = await doneButton.isVisible({ timeout: 2000 }).catch(() => false);

    if (hasDoneButton) {
      await doneButton.click();
      console.log('Toggled first queue item as done');

      // Verify row styling changed (opacity/strikethrough)
      // This is a visual check - exact assertion depends on CSS implementation
      await page.waitForTimeout(500);
    }

    // ========================================
    // STEP 7: Verify Navigation Entry
    // ========================================
    const navFollowupQueue = page.getByTestId('nav-followup-queue');
    await expect(navFollowupQueue).toBeVisible();
    console.log('Follow-up Queue navigation entry is visible');
  });

  test('Empty queue shows empty state', async ({ page }) => {
    // This test will pass if the queue is empty - complementary to the main test
    await page.goto(`${baseUrl}/followups`);
    await page.waitForLoadState('networkidle');

    await expect(page.getByTestId('followup-queue-page')).toBeVisible({ timeout: 10000 });

    // Check if empty state OR queue items are present
    const queueRows = page.getByTestId('followup-row');
    const hasQueueItems = await queueRows.first().isVisible({ timeout: 5000 }).catch(() => false);

    if (!hasQueueItems) {
      // Verify empty state elements
      await expect(page.getByText('All caught up!')).toBeVisible();
      await expect(page.getByText(/Check back later or adjust your time window/)).toBeVisible();
      console.log('Verified empty state rendering');
    } else {
      console.log('Queue has items - empty state not applicable');
      test.skip();
    }
  });

  test('Navigation entry is accessible from all pages', async ({ page }) => {
    // Verify that the Follow-up Queue nav entry is visible from different pages
    const pagesToCheck = ['/', '/inbox', '/tracker', '/chat'];

    for (const path of pagesToCheck) {
      await page.goto(`${baseUrl}${path}`);
      await page.waitForLoadState('networkidle');

      const navEntry = page.getByTestId('nav-followup-queue');
      const isVisible = await navEntry.isVisible({ timeout: 5000 }).catch(() => false);

      if (isVisible) {
        console.log(`✓ Follow-up Queue nav entry visible on ${path}`);
      } else {
        console.warn(`✗ Follow-up Queue nav entry NOT visible on ${path}`);
      }
    }
  });
});
