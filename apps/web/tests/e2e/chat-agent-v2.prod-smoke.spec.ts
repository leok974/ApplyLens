/**
 * PROD SMOKE TEST
 *
 * - Assumes you're already logged in via storageState (tests/auth/prod.json)
 * - Does NOT mock anything (except error handling test)
 * - Only checks:
 *    • /api/v2/agent/run is called
 *    • it returns 200
 *    • the chat shell renders (no hard text assertions)
 *
 * Safe to run against real production (@prodSafe).
 *
 * Usage:
 * $env:E2E_BASE_URL="https://applylens.app"
 * $env:E2E_API="https://applylens.app/api"
 * $env:E2E_AUTH_STATE="tests/auth/prod.json"
 * npx playwright test tests/e2e/chat-agent-v2.prod-smoke.spec.ts --project=chromium
 */

import { test, expect } from '@playwright/test';

const BASE_URL = process.env.E2E_BASE_URL ?? 'https://applylens.app';
const AUTH_STATE = process.env.E2E_AUTH_STATE ?? 'tests/auth/prod.json';

test.describe('@prodSafe Agent V2 – prod smoke', () => {
  test.use({
    // Reuse your saved prod cookies
    storageState: AUTH_STATE,
    baseURL: BASE_URL,
  });

  test('suspicious query calls /api/v2/agent/run and returns 200', async ({ page }) => {
    // Skip entirely if someone forgot to point at prod
    test.skip(
      !BASE_URL.includes('applylens.app'),
      'Prod smoke only runs against applylens.app',
    );

    await page.goto('/chat');

    // Wait for the Mailbox Assistant shell to appear
    await page.getByTestId('agent-mail-chat').waitFor({ state: 'visible' });

    // Fill and send using testids instead of role/name
    const input = page.getByTestId('chat-input');
    await expect(input).toBeVisible();
    await expect(input).toBeEnabled();
    await input.fill('show suspicious emails');

    const sendButton = page.getByTestId('chat-send');
    await expect(sendButton).toBeVisible();
    await expect(sendButton).toBeEnabled();

    await Promise.all([
      // Wait for the agent run request + response
      page.waitForResponse((res) => {
        const url = res.url();
        return (
          url.includes('/api/v2/agent/run') &&
          res.request().method() === 'POST'
        );
      }),
      sendButton.click(),
    ]).then(async ([response]) => {
      // Make sure backend actually succeeded
      expect(response.ok(), `Agent V2 response status = ${response.status()}`).toBe(
        true,
      );
    });

    // Sanity check: make sure we did NOT hit the generic red error banner
    await expect(
      page.getByText(/I hit an error while running the Mailbox Assistant/i),
    ).not.toBeVisible({ timeout: 1500 });

    // Optional: very soft assertion that some reply text showed up,
    // without depending on exact wording or counts.
    // This keeps the test from passing if nothing rendered.
    await expect(
      page
        .getByTestId('agent-mail-chat')
        // any non-empty assistant bubble inside the chat shell
        .locator('text=/emails?|inbox|no suspicious emails/i')
        .first(),
    ).toBeVisible({ timeout: 10_000 });
  });

  test('bills query calls /api/v2/agent/run and returns 200', async ({ page }) => {
    test.skip(
      !BASE_URL.includes('applylens.app'),
      'Prod smoke only runs against applylens.app',
    );

    await page.goto('/chat');
    await page.getByTestId('agent-mail-chat').waitFor();

    const input = page.getByTestId('chat-input');
    await input.fill('show my bills');

    const sendButton = page.getByTestId('chat-send');
    await Promise.all([
      page.waitForResponse((res) => {
        const url = res.url();
        return (
          url.includes('/api/v2/agent/run') &&
          res.request().method() === 'POST'
        );
      }),
      sendButton.click(),
    ]).then(async ([response]) => {
      expect(response.ok(), `Agent V2 response status = ${response.status()}`).toBe(
        true,
      );
    });

    // No error banner
    await expect(
      page.getByText(/I hit an error while running the Mailbox Assistant/i),
    ).not.toBeVisible({ timeout: 1500 });

    // Soft assertion: some bill/payment related text appeared
    await expect(
      page
        .getByTestId('agent-mail-chat')
        .locator('text=/bills?|payments?|invoices?|due|overdue/i')
        .first(),
    ).toBeVisible({ timeout: 10_000 });
  });

  test('error handling - shows error banner when API fails', async ({ page }) => {
    await page.goto('/chat');
    await page.getByTestId('agent-mail-chat').waitFor();

    // Mock a 500 error for this test only
    await page.route('**/api/v2/agent/run', route => {
      route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Internal server error' }),
      });
    });

    const input = page.getByTestId('chat-input');
    await input.fill('test error handling');

    const sendButton = page.getByTestId('chat-send');
    await sendButton.click();

    // Should show error message
    await expect(
      page.getByText(/I hit an error while running the Mailbox Assistant/i),
    ).toBeVisible({ timeout: 5000 });
  });
});
