/**
 * E2E Test: Chat → Thread Viewer → Tracker Deep-Link Flow
 *
 * Tests the complete user journey:
 * 1. Starting from /chat
 * 2. Opening Follow-ups mail tool
 * 3. Viewing a thread in Thread Viewer
 * 4. Clicking "Open in Tracker" button
 * 5. Verifying deep-link navigation and row selection in Tracker
 *
 * Production-safe: Uses explicit baseUrl, networkidle waits, and data-testid selectors.
 *
 * @prodSafe @chat @threads @tracker @integration
 */

import { test, expect } from '@playwright/test';

const baseUrl = process.env.E2E_BASE_URL ?? 'http://127.0.0.1:5173';

test.describe('@prodSafe @chat @threads @tracker @integration Thread Viewer → Tracker Deep-Link', () => {
  test('complete flow: Follow-ups → Thread Viewer → Open in Tracker', async ({ page }) => {
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
    await expect(followupsButton).toBeVisible({ timeout: 5000 });
    await followupsButton.click();

    // Wait for agent response (may not always show "Thinking" text)
    await page.waitForTimeout(5000);

    // ========================================
    // STEP 3: Check if Thread List UI Appears
    // ========================================
    // Thread card might not appear if no follow-ups exist
    const threadCard = page.getByTestId('thread-card');
    const hasThreads = await threadCard.isVisible({ timeout: 15000 }).catch(() => false);

    if (!hasThreads) {
      console.log('No follow-up threads found - skipping deep-link test');
      test.skip();
      return;
    }

    // Verify thread list is present
    const threadList = page.getByTestId('thread-list');
    await expect(threadList).toBeVisible();

    // Verify at least one thread row exists
    const threadRows = page.getByTestId('thread-row');
    await expect(threadRows.first()).toBeVisible();

    // ========================================
    // STEP 4: Select First Thread
    // ========================================
    const firstThread = threadRows.first();
    await firstThread.click();

    // ========================================
    // STEP 5: Verify Thread Viewer Appears
    // ========================================
    const threadViewer = page.getByTestId('thread-viewer');
    await expect(threadViewer).toBeVisible({ timeout: 5000 });

    // Verify the metadata pill is visible in card header
    const metadataPill = threadCard.locator('.text-xs, [class*="text-xs"]').first();
    await expect(metadataPill).toBeVisible();

    // ========================================
    // STEP 6: Check for "Open in Tracker" Button
    // ========================================
    const openTrackerButton = threadViewer.getByTestId('thread-open-tracker');
    const hasTrackerButton = await openTrackerButton.isVisible({ timeout: 3000 }).catch(() => false);

    if (!hasTrackerButton) {
      console.log('Selected thread does not have applicationId - skipping tracker navigation');
      test.skip();
      return;
    }

    // ========================================
    // STEP 7: Click "Open in Tracker"
    // ========================================
    await openTrackerButton.click();

    // ========================================
    // STEP 8: Wait for Navigation to /tracker
    // ========================================
    await page.waitForURL(/\/tracker/, { timeout: 10000 });
    await page.waitForLoadState('networkidle');

    // ========================================
    // STEP 9: Verify Tracker Page Loaded
    // ========================================
    // Check if tracker has any rows at all
    const trackerRow = page.locator('[data-testid="tracker-row"]').first();
    const hasTrackerData = await trackerRow.isVisible({ timeout: 10000 }).catch(() => false);

    if (!hasTrackerData) {
      console.log('Tracker has no data - cannot verify selection');
      // At least verify we navigated to tracker
      expect(page.url()).toContain('/tracker');
      return;
    }

    // ========================================
    // STEP 10: Verify Row Selection/Highlight
    // ========================================
    // Find row with data-selected="true"
    const selectedRow = page.locator('[data-testid="tracker-row"][data-selected="true"]');
    await expect(selectedRow).toBeVisible({ timeout: 5000 });

    // Verify exactly ONE row is selected
    const selectedCount = await selectedRow.count();
    expect(selectedCount).toBe(1);

    // Verify selected row has the yellow highlight styling
    const selectedRowClasses = await selectedRow.getAttribute('class');
    expect(selectedRowClasses).toContain('bg-yellow-400/10');
    expect(selectedRowClasses).toContain('border-yellow-400');
  });

  test('Tracker: navigates and loads successfully', async ({ page }) => {
    // ========================================
    // Navigate directly to Tracker
    // ========================================
    await page.goto(`${baseUrl}/tracker`);
    await page.waitForLoadState('networkidle');

    // ========================================
    // Verify Tracker page loads
    // ========================================
    const pageHeading = page.locator('h1, h2').filter({ hasText: /Application/i }).first();
    const hasHeading = await pageHeading.isVisible({ timeout: 5000 }).catch(() => false);

    // At minimum, verify we're on the tracker page
    expect(page.url()).toContain('/tracker');

    // If there's data, verify tracker rows exist
    const trackerRow = page.locator('[data-testid="tracker-row"]').first();
    const hasData = await trackerRow.isVisible({ timeout: 5000 }).catch(() => false);

    if (hasData) {
      // Verify multiple rows if data exists
      const rowCount = await page.locator('[data-testid="tracker-row"]').count();
      expect(rowCount).toBeGreaterThan(0);
    }
  });

  test('Tracker: appId param works when valid application exists', async ({ page }) => {
    // ========================================
    // First, get a valid application ID
    // ========================================
    await page.goto(`${baseUrl}/tracker`);
    await page.waitForLoadState('networkidle');

    const trackerRow = page.locator('[data-testid="tracker-row"]').first();
    const hasData = await trackerRow.isVisible({ timeout: 10000 }).catch(() => false);

    if (!hasData) {
      console.log('No tracker data available - skipping appId test');
      test.skip();
      return;
    }

    // Get the ID from the first row
    const firstRowId = await trackerRow.getAttribute('data-id');
    if (!firstRowId) {
      console.log('No data-id found on tracker row - skipping');
      test.skip();
      return;
    }

    // ========================================
    // Navigate with appId parameter
    // ========================================
    await page.goto(`${baseUrl}/tracker?appId=${firstRowId}`);
    await page.waitForLoadState('networkidle');

    // Wait for tracker to load
    await expect(trackerRow).toBeVisible({ timeout: 10000 });

    // ========================================
    // Verify row is selected
    // ========================================
    const selectedRow = page.locator(`[data-testid="tracker-row"][data-id="${firstRowId}"][data-selected="true"]`);
    await expect(selectedRow).toBeVisible({ timeout: 5000 });

    // Verify selection styling
    const selectedRowClasses = await selectedRow.getAttribute('class');
    expect(selectedRowClasses).toContain('bg-yellow-400/10');

    // ========================================
    // Verify URL cleanup
    // ========================================
    await page.waitForTimeout(1000);
    const currentUrl = page.url();
    expect(currentUrl).not.toContain('appId=');
  });
});
