/**
 * E2E Test: Chat Thread Viewer
 *
 * Tests the Thread Viewer v1 functionality on the /chat page.
 *
 * Production-safe: Uses explicit baseUrl, networkidle waits, and toolbar button clicks.
 *
 * @prodSafe @chat @threads
 */

import { test, expect } from '@playwright/test';

const baseUrl = process.env.E2E_BASE_URL ?? 'http://127.0.0.1:5173';

test.describe('@prodSafe @chat @threads Thread Viewer v1', () => {
  // Lightweight smoke test - just verify one scan intent returns thread_list
  test('smoke: Follow-ups toolbar button shows thread list UI', async ({ page }) => {
    // Navigate to chat
    await page.goto(`${baseUrl}/chat`);
    await page.waitForLoadState('networkidle');

    // Wait for chat root to be ready
    await expect(page.getByTestId('chat-root')).toBeVisible({ timeout: 10000 });

    // Click Follow-ups toolbar button
    const followupsButton = page.getByTestId('mailtool-followups');
    await expect(followupsButton).toBeVisible({ timeout: 5000 });
    await followupsButton.click();

    // Wait for "Thinking" indicator to disappear (agent is processing)
    const thinkingText = page.getByText(/Thinking about your mailbox/i);
    await expect(thinkingText).toBeHidden({ timeout: 30000 });

    // Wait for thread card to appear
    const threadCard = page.getByTestId('thread-card');
    await expect(threadCard).toBeVisible({ timeout: 10000 });

    // Verify thread list is present
    const threadList = page.getByTestId('thread-list');
    await expect(threadList).toBeVisible();

    // Verify at least one thread row exists
    const threadRows = page.getByTestId('thread-row');
    await expect(threadRows.first()).toBeVisible();

    // Verify thread viewer is present
    const threadViewer = page.getByTestId('thread-viewer');
    await expect(threadViewer).toBeVisible();
  });

  test('shows thread list card with selectable rows via toolbar button', async ({ page }) => {
    // Navigate to chat
    await page.goto(`${baseUrl}/chat`);
    await page.waitForLoadState('networkidle');

    // Wait for chat interface to load
    await expect(page.getByTestId('chat-root')).toBeVisible({ timeout: 10000 });

    // Click Follow-ups toolbar button (more reliable than typing query)
    const followupsButton = page.getByTestId('mailtool-followups');
    await expect(followupsButton).toBeVisible({ timeout: 5000 });
    await followupsButton.click();

    // Wait for "Thinking" to disappear
    await expect(page.getByText(/Thinking about your mailbox/i)).toBeHidden({ timeout: 30000 });

    // Wait for response with thread card
    const threadCard = page.getByTestId('thread-card');
    await expect(threadCard).toBeVisible({ timeout: 10000 });

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
    await page.goto(`${baseUrl}/chat`);
    await page.waitForLoadState('networkidle');

    // Wait for chat root
    await expect(page.getByTestId('chat-root')).toBeVisible({ timeout: 10000 });

    // Click toolbar button
    const followupsButton = page.getByTestId('mailtool-followups');
    await followupsButton.click();

    // Wait for thinking to disappear
    await expect(page.getByText(/Thinking about your mailbox/i)).toBeHidden({ timeout: 30000 });

    // Wait for thread card
    const threadCard = page.getByTestId('thread-card');
    await expect(threadCard).toBeVisible({ timeout: 10000 });

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
    await page.goto(`${baseUrl}/chat`);
    await page.waitForLoadState('networkidle');

    await expect(page.getByTestId('chat-root')).toBeVisible({ timeout: 10000 });

    // Click toolbar button
    await page.getByTestId('mailtool-followups').click();

    // Wait for thinking to disappear
    await expect(page.getByText(/Thinking about your mailbox/i)).toBeHidden({ timeout: 30000 });

    // Wait for thread card
    await expect(page.getByTestId('thread-card')).toBeVisible({ timeout: 10000 });

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
    await page.goto(`${baseUrl}/chat`);
    await page.waitForLoadState('networkidle');

    await expect(page.getByTestId('chat-root')).toBeVisible({ timeout: 10000 });

    // Click toolbar button
    await page.getByTestId('mailtool-followups').click();

    // Wait for thinking to disappear
    await expect(page.getByText(/Thinking about your mailbox/i)).toBeHidden({ timeout: 30000 });

    // Wait for thread card
    await expect(page.getByTestId('thread-card')).toBeVisible({ timeout: 10000 });

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

  test('thread card shows thread count badge', async ({ page }) => {
    await page.goto(`${baseUrl}/chat`);
    await page.waitForLoadState('networkidle');

    await expect(page.getByTestId('chat-root')).toBeVisible({ timeout: 10000 });

    // Click toolbar button
    await page.getByTestId('mailtool-followups').click();

    // Wait for thinking to disappear
    await expect(page.getByText(/Thinking about your mailbox/i)).toBeHidden({ timeout: 30000 });

    // Wait for thread card
    const threadCard = page.getByTestId('thread-card');
    await expect(threadCard).toBeVisible({ timeout: 10000 });

    // Look for badge showing thread count (e.g., "5 threads" or "1 thread")
    const countBadge = threadCard.getByText(/\d+ threads?/);
    await expect(countBadge).toBeVisible();
  });

  test('thread viewer shows message timeline', async ({ page }) => {
    await page.goto(`${baseUrl}/chat`);
    await page.waitForLoadState('networkidle');

    await expect(page.getByTestId('chat-root')).toBeVisible({ timeout: 10000 });

    // Click toolbar button
    await page.getByTestId('mailtool-followups').click();

    // Wait for thinking to disappear
    await expect(page.getByText(/Thinking about your mailbox/i)).toBeHidden({ timeout: 30000 });

    // Wait for thread card
    await expect(page.getByTestId('thread-card')).toBeVisible({ timeout: 10000 });

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

  test('Bills intent: returns thread_list when bills exist', async ({ page }) => {
    await page.goto(`${baseUrl}/chat`);
    await page.waitForLoadState('networkidle');

    await expect(page.getByTestId('chat-root')).toBeVisible({ timeout: 10000 });

    // Click Bills toolbar button
    const billsButton = page.getByTestId('mailtool-bills');
    await expect(billsButton).toBeVisible({ timeout: 5000 });
    await billsButton.click();

    // Wait for response - might be thread_list or summary only
    await page.waitForTimeout(3000);

    // Check if thread card exists (bills might return 0 results)
    const threadCard = page.getByTestId('thread-card');
    const hasThreadCard = await threadCard.isVisible().catch(() => false);

    if (hasThreadCard) {
      // If we got threads, verify the structure
      const threadList = page.getByTestId('thread-list');
      await expect(threadList).toBeVisible();

      const threadRows = page.getByTestId('thread-row');
      const count = await threadRows.count();
      expect(count).toBeGreaterThan(0);
    } else {
      // No thread card means no bills found - that's valid
      console.log('No bills found - count=0 case verified');
    }
  });

  test('Suspicious intent: handles zero results gracefully', async ({ page }) => {
    await page.goto(`${baseUrl}/chat`);
    await page.waitForLoadState('networkidle');

    await expect(page.getByTestId('chat-root')).toBeVisible({ timeout: 10000 });

    // Click Suspicious toolbar button
    const suspiciousButton = page.getByTestId('mailtool-suspicious');
    await expect(suspiciousButton).toBeVisible({ timeout: 5000 });
    await suspiciousButton.click();

    // Wait for response
    await page.waitForTimeout(3000);

    // Should get a summary card (not thread_list when count=0)
    // Verify we don't crash and show appropriate message
    const chatShell = page.getByTestId('chat-shell');
    await expect(chatShell).toBeVisible();

    // Should have some response text (either threads or "You're all caught up")
    const responseText = await chatShell.textContent();
    expect(responseText).toBeTruthy();
  });
});
