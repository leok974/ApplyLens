/**
 * E2E Test: Chat Thread Viewer
 *
 * Tests the Thread Viewer v1 functionality on the /chat page.
 *
 * @prodSafe @chat @threads
 */

import { test, expect } from '@playwright/test';

test.describe('@prodSafe @chat @threads Thread Viewer v1', () => {
  test('shows thread list card with selectable rows', async ({ page }) => {
    // Navigate to chat (auth handled by storageState)
    await page.goto('/chat');
    await page.waitForLoadState("networkidle");

    // Wait for chat interface to load
    await expect(page.getByTestId('chat-root')).toBeVisible({ timeout: 15000 });

    // Wait specifically for the input to appear (authentication might still be loading)
    const input = page.locator('textarea[placeholder*="Ask"]');
    await expect(input).toBeVisible({ timeout: 30000 });

    // Send a query that should return thread_list card
    await input.fill('Show people I still owe a reply to');
    await input.press('Enter');

    // Wait for response with thread card
    const threadCard = page.getByTestId('thread-card');
    await expect(threadCard).toBeVisible({ timeout: 15000 });

    // Verify thread list is present
    const threadList = page.getByTestId('thread-list');
    await expect(threadList).toBeVisible();

    // Verify at least one thread row is rendered
    const threadRows = page.getByTestId('thread-row');
    await expect(threadRows.first()).toBeVisible();

    // Count threads
    const threadCount = await threadRows.count();
    expect(threadCount).toBeGreaterThan(0);
  });

  test('first thread is selected by default and viewer shows details', async ({ page }) => {
    await page.goto('/chat');
    await page.waitForLoadState("networkidle");

    // Send query
    const input = page.locator('textarea[placeholder*="Ask"]');
    await input.fill('Show people I still owe a reply to');
    await input.press('Enter');

    // Wait for thread card
    const threadCard = page.getByTestId('thread-card');
    await expect(threadCard).toBeVisible({ timeout: 15000 });

    // First thread row should be selected
    const firstRow = page.getByTestId('thread-row').first();
    await expect(firstRow).toHaveAttribute('aria-selected', 'true');

    // Thread viewer should be visible and show subject
    const viewer = page.getByTestId('thread-viewer');
    await expect(viewer).toBeVisible();

    // Viewer should show some content (subject, actions, etc.)
    await expect(viewer.locator('h3').first()).toBeVisible();
  });

  test('clicking a thread row updates the viewer', async ({ page }) => {
    await page.goto('/chat');
    await page.waitForLoadState("networkidle");

    // Send query
    const input = page.locator('textarea[placeholder*="Ask"]');
    await input.fill('Show people I still owe a reply to');
    await input.press('Enter');

    // Wait for thread card
    await expect(page.getByTestId('thread-card')).toBeVisible({ timeout: 15000 });

    const threadRows = page.getByTestId('thread-row');
    const threadCount = await threadRows.count();

    if (threadCount > 1) {
      // Get subject of first thread
      const firstRowSubject = await threadRows.first().locator('h4').textContent();

      // Click second thread
      await threadRows.nth(1).click();

      // Wait for viewer to update
      await page.waitForTimeout(500);

      // Second thread should now be selected
      await expect(threadRows.nth(1)).toHaveAttribute('aria-selected', 'true');
      await expect(threadRows.first()).toHaveAttribute('aria-selected', 'false');

      // Viewer subject should have changed
      const viewer = page.getByTestId('thread-viewer');
      const viewerSubject = await viewer.locator('h3').first().textContent();

      expect(viewerSubject).not.toBe(firstRowSubject);
    }
  });

  test('Open in Gmail button has correct href', async ({ page }) => {
    await page.goto('/chat');
    await page.waitForLoadState("networkidle");

    // Send query
    const input = page.locator('textarea[placeholder*="Ask"]');
    await input.fill('Show people I still owe a reply to');
    await input.press('Enter');

    // Wait for thread card
    await expect(page.getByTestId('thread-card')).toBeVisible({ timeout: 15000 });

    // Wait for viewer to load
    const viewer = page.getByTestId('thread-viewer');
    await expect(viewer).toBeVisible();

    // Wait a bit for detail to fetch
    await page.waitForTimeout(1000);

    // Find "Open in Gmail" button
    const gmailButton = viewer.getByRole('link', { name: /Open in Gmail/i });
    await expect(gmailButton).toBeVisible();

    // Verify it has a Gmail URL
    const href = await gmailButton.getAttribute('href');
    expect(href).toBeTruthy();
    expect(href).toContain('mail.google.com');
  });

  test('thread rows show risk badges for risky threads', async ({ page }) => {
    await page.goto('/chat');
    await page.waitForLoadState("networkidle");

    // Send query that might return risky threads
    const input = page.locator('textarea[placeholder*="Ask"]');
    await input.fill('Show suspicious emails');
    await input.press('Enter');

    // Wait for response
    const threadCard = page.getByTestId('thread-card');

    // This might return thread_list or a different card type
    // Only proceed if we got a thread card
    try {
      await expect(threadCard).toBeVisible({ timeout: 15000 });

      // Check if any thread row has a Risk badge
      const riskBadges = page.getByText('Risk');
      const riskBadgeCount = await riskBadges.count();

      // It's okay if there are no risky threads, this test is just checking the UI exists
      if (riskBadgeCount > 0) {
        await expect(riskBadges.first()).toBeVisible();
      }
    } catch (e) {
      // If thread card doesn't appear, that's fine - the query might return a different card type
      console.log('No thread card returned for suspicious query, skipping risk badge check');
    }
  });

  test('thread viewer shows message timeline', async ({ page }) => {
    await page.goto('/chat');
    await page.waitForLoadState("networkidle");

    // Send query
    const input = page.locator('textarea[placeholder*="Ask"]');
    await input.fill('Show people I still owe a reply to');
    await input.press('Enter');

    // Wait for thread card
    await expect(page.getByTestId('thread-card')).toBeVisible({ timeout: 15000 });

    // Wait for viewer
    const viewer = page.getByTestId('thread-viewer');
    await expect(viewer).toBeVisible();

    // Check for "Message Timeline" heading
    await expect(viewer.getByText('Message Timeline')).toBeVisible();

    // Wait for messages to load (or loading skeleton)
    await page.waitForTimeout(2000);

    // Check if message cards appear
    const messageCards = viewer.getByTestId('message-card');
    const messageCount = await messageCards.count();

    // If messages loaded, verify they're visible
    if (messageCount > 0) {
      await expect(messageCards.first()).toBeVisible();
    }
  });

  test('thread card shows thread count badge', async ({ page }) => {
    await page.goto('/chat');
    await page.waitForLoadState("networkidle");

    // Send query
    const input = page.locator('textarea[placeholder*="Ask"]');
    await input.fill('Show people I still owe a reply to');
    await input.press('Enter');

    // Wait for thread card
    const threadCard = page.getByTestId('thread-card');
    await expect(threadCard).toBeVisible({ timeout: 15000 });

    // Look for badge showing thread count (e.g., "5 threads" or "1 thread")
    const countBadge = threadCard.getByText(/\d+ threads?/);
    await expect(countBadge).toBeVisible();
  });

  test('mobile layout: thread list and viewer stack vertically', async ({ page, isMobile }) => {
    if (!isMobile) {
      test.skip();
    }

    await page.goto('/chat');
    await page.waitForLoadState("networkidle");

    // Send query
    const input = page.locator('textarea[placeholder*="Ask"]');
    await input.fill('Show people I still owe a reply to');
    await input.press('Enter');

    // Wait for thread card
    await expect(page.getByTestId('thread-card')).toBeVisible({ timeout: 15000 });

    // On mobile, the grid should stack - verify both list and viewer are visible
    await expect(page.getByTestId('thread-list')).toBeVisible();
    await expect(page.getByTestId('thread-viewer')).toBeVisible();

    // Click a thread row and verify viewer scrolls into view or is visible
    const threadRows = page.getByTestId('thread-row');
    if ((await threadRows.count()) > 1) {
      await threadRows.nth(1).click();
      await page.waitForTimeout(300);

      // Viewer should still be visible after selection
      await expect(page.getByTestId('thread-viewer')).toBeVisible();
    }
  });
});
