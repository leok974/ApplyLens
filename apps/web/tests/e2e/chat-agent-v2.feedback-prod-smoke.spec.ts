/**
 * @prod @chat @agentv2 @feedback
 *
 * Prod smoke test for Agent V2 feedback endpoint.
 *
 * Verifies:
 * - /api/v2/agent/feedback endpoint is accessible in production
 * - Clicking feedback buttons successfully sends requests
 * - Backend returns 200 OK (doesn't validate full response structure)
 *
 * Usage:
 *   $env:E2E_BASE_URL="https://applylens.app"
 *   $env:E2E_API="https://applylens.app/api"
 *   $env:E2E_AUTH_STATE="tests/auth/prod.json"
 *   npx playwright test tests/e2e/chat-agent-v2.feedback-prod-smoke.spec.ts
 */

import { test, expect } from '@playwright/test';

test.describe('@prod @chat @agentv2 @feedback', () => {
  test('feedback hide sends /agent/feedback and gets 200', async ({ page }) => {
    const baseUrl = process.env.E2E_BASE_URL || 'http://localhost:5173';
    const apiBase = process.env.E2E_API || `${baseUrl}/api`;

    // 1) Mock Agent V2 run so we always have a card to click
    await page.route('**/api/v2/agent/run', async (route) => {
      const json = {
        run_id: '00000000-0000-0000-0000-000000000001',
        user_id: 'test@example.com',
        query: 'test feedback flow',
        mode: 'preview_only',
        context: { time_window_days: 30 },
        status: 'done',
        intent: 'suspicious',
        answer: 'I found 1 suspicious email from a risky domain.',
        cards: [
          {
            kind: 'suspicious_summary',
            title: 'Suspicious Emails Found',
            body: 'Found 1 email that may be a phishing attempt.',
            email_ids: ['email-test-1'],
            meta: {
              count: 1,
              items: [
                {
                  id: 'test-thread-1',
                  thread_id: 'test-thread-1',
                  subject: 'Password reset required',
                  sender: 'security@example.com',
                  risk_level: 90,
                },
              ],
            },
          },
        ],
        tools_used: ['email_search', 'security_scan'],
        metrics: {
          emails_scanned: 10,
          tool_calls: 2,
          rag_sources: 0,
          duration_ms: 1200,
        },
        created_at: new Date().toISOString(),
        completed_at: new Date().toISOString(),
      };

      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(json),
      });
    });

    // 2) Watch for real /feedback responses (let it hit production backend)
    const feedbackResponses: { status: number; url: string }[] = [];
    page.on('response', async (response) => {
      const url = response.url();
      if (url.includes('/v2/agent/feedback')) {
        feedbackResponses.push({ status: response.status(), url });
      }
    });

    // 3) Go to /chat and trigger Agent V2
    await page.goto(`${baseUrl}/chat`);

    // Wait for chat to be ready
    await expect(page.getByTestId('agent-mail-chat')).toBeVisible({ timeout: 10000 });

    // Send agent query
    const input = page.getByTestId('chat-input');
    await input.fill('show me suspicious emails');

    const sendButton = page.getByTestId('chat-send');
    await sendButton.click();

    // 4) Wait for Agent V2 card to appear
    const card = page.getByTestId('agent-card-suspicious_summary');
    await expect(card).toBeVisible({ timeout: 10000 });

    // 5) Click Hide on that card
    const hideButton = page.getByTestId('agent-feedback-suspicious_summary-hide');
    await expect(hideButton).toBeVisible();
    await hideButton.click();

    // 6) Assert we saw at least one /feedback response and it was 200
    await expect
      .poll(() => feedbackResponses.length, {
        message: 'Expected at least one /agent/feedback response',
        timeout: 5000,
      })
      .toBeGreaterThan(0);

    const first = feedbackResponses[0];
    expect(first.status).toBe(200);

    console.log(`✅ Feedback endpoint returned ${first.status} for URL: ${first.url}`);
  });

  test('feedback helpful sends correct request', async ({ page }) => {
    const baseUrl = process.env.E2E_BASE_URL || 'http://localhost:5173';

    // Mock Agent V2 run
    await page.route('**/api/v2/agent/run', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          run_id: '00000000-0000-0000-0000-000000000002',
          user_id: 'test@example.com',
          query: 'show followups',
          mode: 'preview_only',
          context: { time_window_days: 30 },
          status: 'done',
          intent: 'followups',
          answer: 'You have 2 emails waiting for replies.',
          cards: [
            {
              kind: 'followups_summary',
              title: 'Follow-ups Needed',
              body: 'Found 2 threads needing your attention.',
              email_ids: ['email-1', 'email-2'],
              meta: { count: 2 },
            },
          ],
          tools_used: ['email_search'],
          metrics: {
            emails_scanned: 50,
            tool_calls: 1,
            duration_ms: 800,
          },
          created_at: new Date().toISOString(),
          completed_at: new Date().toISOString(),
        }),
      });
    });

    // Track feedback responses
    const feedbackResponses: { status: number }[] = [];
    page.on('response', async (response) => {
      if (response.url().includes('/v2/agent/feedback')) {
        feedbackResponses.push({ status: response.status() });
      }
    });

    await page.goto(`${baseUrl}/chat`);
    await expect(page.getByTestId('agent-mail-chat')).toBeVisible({ timeout: 10000 });

    // Send query
    await page.getByTestId('chat-input').fill('show followups');
    await page.getByTestId('chat-send').click();

    // Wait for card
    const card = page.getByTestId('agent-card-followups_summary');
    await expect(card).toBeVisible({ timeout: 10000 });

    // Click helpful button (👍)
    const helpfulButton = page.getByTestId('agent-feedback-followups_summary-helpful');
    await expect(helpfulButton).toBeVisible();
    await helpfulButton.click();

    // Verify feedback sent successfully
    await expect
      .poll(() => feedbackResponses.length, { timeout: 5000 })
      .toBeGreaterThan(0);

    expect(feedbackResponses[0].status).toBe(200);
    console.log('✅ Helpful feedback sent successfully');
  });

  test('feedback hint text is displayed', async ({ page }) => {
    const baseUrl = process.env.E2E_BASE_URL || 'http://localhost:5173';

    // Mock Agent V2 run
    await page.route('**/api/v2/agent/run', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          run_id: 'hint-test',
          user_id: 'test@example.com',
          query: 'test',
          mode: 'preview_only',
          context: { time_window_days: 30 },
          status: 'done',
          intent: 'generic',
          answer: 'Test answer',
          cards: [
            {
              kind: 'generic_summary',
              title: 'Test Card',
              body: 'Test body',
              email_ids: [],
              meta: {},
            },
          ],
          tools_used: [],
          metrics: { emails_scanned: 0, tool_calls: 0, duration_ms: 100 },
          created_at: new Date().toISOString(),
          completed_at: new Date().toISOString(),
        }),
      });
    });

    await page.goto(`${baseUrl}/chat`);
    await expect(page.getByTestId('agent-mail-chat')).toBeVisible({ timeout: 10000 });

    // Send query to trigger agent response
    await page.getByTestId('chat-input').fill('test query');
    await page.getByTestId('chat-send').click();

    // Wait for card
    await expect(page.getByTestId('agent-card-generic_summary')).toBeVisible({ timeout: 10000 });

    // Verify feedback hint is displayed
    const hint = page.getByTestId('agent-feedback-hint');
    await expect(hint).toBeVisible();
    await expect(hint).toContainText('teach ApplyLens what\'s useful');
    await expect(hint).toContainText('fewer irrelevant cards');

    console.log('✅ Feedback hint text is displayed correctly');
  });
});
