/**
 * Agent V2 Production Smoke Tests
 *
 * Validates Agent V2 works end-to-end in production without mocking.
 * Tests assert API shape and rendering, not exact text/data.
 *
 * @prodSafe - Safe to run against production with real data
 *
 * Usage:
 * E2E_BASE_URL=https://applylens.app \
 * E2E_API=https://applylens.app/api \
 * E2E_AUTH_STATE=tests/auth/prod.json \
 * USE_SMOKE_SETUP=false \
 * npx playwright test tests/e2e/chat-agent-v2.prod-smoke.spec.ts
 */

import { test, expect } from '@playwright/test';

const AUTH_STATE = process.env.E2E_AUTH_STATE ?? '';

// Skip all tests in this file if we don't have an auth storage state configured.
test.skip(
  !AUTH_STATE,
  'E2E_AUTH_STATE not configured; skipping Agent V2 prod smoke tests that require authenticated session.'
);

// Use existing auth state, don't run global setup for prod
test.use({
  storageState: AUTH_STATE,
});

test.describe('@prodSafe @agent-v2 @authRequired Agent V2 Production Smoke', () => {
  test('suspicious emails flow - API called and response rendered', async ({ page }) => {
    await page.goto('/chat');

    // Wait for chat shell ready
    await page.getByTestId('agent-mail-chat').waitFor();

    // Ask a suspicious question
    const input = page.getByRole('textbox', { name: /ask.*inbox/i });
    await input.fill('show suspicious emails');

    const sendButton = page.getByRole('button', { name: /send/i });

    // Start waiting for API call before clicking
    const requestPromise = page.waitForRequest(
      req => req.url().includes('/api/v2/agent/run') && req.method() === 'POST',
      { timeout: 5000 }
    );
    const responsePromise = page.waitForResponse(
      res => res.url().includes('/api/v2/agent/run') && res.status() === 200,
      { timeout: 15000 }
    );

    await sendButton.click();

    // 1) Ensure we called the right endpoint
    const [request, response] = await Promise.all([requestPromise, responsePromise]);

    expect(request.url()).toContain('/api/v2/agent/run');
    expect(request.method()).toBe('POST');
    expect(response.status()).toBe(200);

    // 2) Ensure we rendered at least one assistant message
    const assistantMessage = page.getByTestId('chat-message-assistant').last();
    await expect(assistantMessage).toBeVisible({ timeout: 5000 });

    // 3) Make sure we didn't hit the generic error banner
    await expect(
      page.getByText(/I hit an error while running the Mailbox Assistant/i)
    ).not.toBeVisible({ timeout: 2000 });

    // 4) Check that some reasonable text pattern appears (without hardcoding exact numbers)
    // Could be "0 emails found", "found 3 emails", "no suspicious emails", etc.
    await expect(
      assistantMessage.locator('text=/emails? found|no suspicious|suspicious (?:email|message)/i')
    ).toBeVisible();

    // 5) Verify at least one card is rendered (Agent V2 always returns cards)
    const agentCard = page.locator('[data-agent-card]').first();
    await expect(agentCard).toBeVisible();
  });

  test('bills flow - API called and response rendered', async ({ page }) => {
    await page.goto('/chat');
    await page.getByTestId('agent-mail-chat').waitFor();

    const input = page.getByRole('textbox', { name: /ask.*inbox/i });
    await input.fill('show my bills');

    const sendButton = page.getByRole('button', { name: /send/i });

    const requestPromise = page.waitForRequest(
      req => req.url().includes('/api/v2/agent/run') && req.method() === 'POST',
      { timeout: 5000 }
    );
    const responsePromise = page.waitForResponse(
      res => res.url().includes('/api/v2/agent/run') && res.status() === 200,
      { timeout: 15000 }
    );

    await sendButton.click();
    await Promise.all([requestPromise, responsePromise]);

    // Assert assistant message rendered
    const assistantMessage = page.getByTestId('chat-message-assistant').last();
    await expect(assistantMessage).toBeVisible({ timeout: 5000 });

    // No error banner
    await expect(
      page.getByText(/I hit an error while running the Mailbox Assistant/i)
    ).not.toBeVisible({ timeout: 2000 });

    // Check for bill-related text (flexible patterns)
    await expect(
      assistantMessage.locator('text=/bills?|payments?|invoices?|due|overdue|upcoming/i')
    ).toBeVisible();
  });

  test('interviews flow - API called and response rendered', async ({ page }) => {
    await page.goto('/chat');
    await page.getByTestId('agent-mail-chat').waitFor();

    const input = page.getByRole('textbox', { name: /ask.*inbox/i });
    await input.fill('show interview emails');

    const sendButton = page.getByRole('button', { name: /send/i });

    const responsePromise = page.waitForResponse(
      res => res.url().includes('/api/v2/agent/run') && res.status() === 200,
      { timeout: 15000 }
    );

    await sendButton.click();
    const response = await responsePromise;
    expect(response.status()).toBe(200);

    // Assert assistant message rendered
    const assistantMessage = page.getByTestId('chat-message-assistant').last();
    await expect(assistantMessage).toBeVisible({ timeout: 5000 });

    // No error banner
    await expect(
      page.getByText(/I hit an error while running the Mailbox Assistant/i)
    ).not.toBeVisible({ timeout: 2000 });

    // Check for interview-related text
    await expect(
      assistantMessage.locator('text=/interviews?|upcoming|waiting|schedul/i')
    ).toBeVisible();
  });

  test('error handling - shows error banner when API fails', async ({ page }) => {
    await page.goto('/chat');
    await page.getByTestId('agent-mail-chat').waitFor();

    // Mock a 500 error for this test
    await page.route('**/api/v2/agent/run', route => {
      route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Internal server error' }),
      });
    });

    const input = page.getByRole('textbox', { name: /ask.*inbox/i });
    await input.fill('test error handling');

    const sendButton = page.getByRole('button', { name: /send/i });
    await sendButton.click();

    // Should show error message
    const errorMessage = page.getByTestId('chat-message-assistant').last();
    await expect(errorMessage).toContainText(/I hit an error while running the Mailbox Assistant/i);
  });
});
