/**
 * E2E tests for Agent V2 Chat UI
 *
 * Tests the structured LLM answering flow with enhanced card rendering.
 * Uses mocked API responses to ensure consistent test behavior.
 */

import { test, expect } from '@playwright/test';

const AUTH_STATE = process.env.E2E_AUTH_STATE ?? '';

// Skip all tests in this file if we don't have an auth storage state configured.
// This keeps prod runs clean until we explicitly set up login.
test.skip(
  !AUTH_STATE,
  'E2E_AUTH_STATE not configured; skipping Agent V2 UI tests that require authenticated session.'
);

test.describe('@frontend @agent-v2 @prodSafe @authRequired Chat Agent V2 UI', () => {
  test('renders answer and suspicious_summary card with data-driven content', async ({ page }) => {
    // Mock Agent V2 API response
    await page.route('**/api/v2/agent/run', async (route) => {
      const req = route.request();
      const bodyRaw = req.postData() || '{}';
      const body = JSON.parse(bodyRaw);

      // Verify request payload
      expect(body.query).toContain('suspicious');
      expect(body.mode).toBe('preview_only');

      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          run_id: 'test-run-123',
          user_id: 'test@example.com',
          query: body.query,
          mode: 'preview_only',
          context: body.context,
          status: 'done',
          intent: 'suspicious',
          answer:
            'I scanned 1393 emails from the last 14 days and found 3 suspicious messages linked to risky domains.',
          cards: [
            {
              kind: 'suspicious_summary',
              title: 'Suspicious Emails Found',
              body: 'I found 3 potentially risky emails from new or suspicious domains. These emails exhibit warning signs like urgent payment requests, mismatched URLs, or lack of company verification.',
              email_ids: ['email-1', 'email-2', 'email-3'],
              meta: {
                count: 3,
                risky_domains: ['phishy-pay.com', 'login-secure-now.net', 'urgent-verify.xyz'],
                time_window_days: 14,
              },
            },
          ],
          tools_used: ['email_search', 'security_scan'],
          metrics: {
            emails_scanned: 1393,
            tool_calls: 2,
            rag_sources: 0,
            duration_ms: 2340,
          },
          created_at: new Date().toISOString(),
          completed_at: new Date().toISOString(),
        }),
      });
    });

    // Navigate to chat page
    await page.goto(`/chat`);

    // Wait for chat interface to load
    await expect(page.getByTestId('agent-mail-chat')).toBeVisible();

    // Type query and send
    const input = page.getByTestId('chat-input');
    await input.fill('Show suspicious emails from the last 2 weeks');

    const sendButton = page.getByTestId('chat-send');
    await sendButton.click();

    // Verify user message appears
    const userMessage = page.getByTestId('chat-message-user').last();
    await expect(userMessage).toBeVisible();
    await expect(userMessage).toContainText('Show suspicious emails');

    // Verify assistant message with data-driven summary
    const assistantMessage = page.getByTestId('chat-message-assistant').last();
    await expect(assistantMessage).toBeVisible();
    await expect(assistantMessage).toContainText('scanned 1393 emails');
    await expect(assistantMessage).toContainText('found 3 suspicious messages');

    // Verify suspicious_summary card is rendered
    const suspiciousCard = page.getByTestId('agent-card-suspicious_summary');
    await expect(suspiciousCard).toBeVisible();

    // Check card title
    await expect(suspiciousCard).toContainText('Suspicious Emails Found');

    // Check card body
    await expect(suspiciousCard).toContainText('I found 3 potentially risky emails');

    // Check card metadata - count metric
    await expect(suspiciousCard).toContainText('Suspicious emails');
    await expect(suspiciousCard).toContainText('3');

    // Check risky domains list
    await expect(suspiciousCard).toContainText('Risky domains:');
    await expect(suspiciousCard).toContainText('phishy-pay.com');
    await expect(suspiciousCard).toContainText('login-secure-now.net');

    // Check email citation footer
    await expect(suspiciousCard).toContainText('Based on 3 emails');
  });

  test('renders bills_summary card with due soon/overdue pills', async ({ page }) => {
    await page.route('**/api/v2/agent/run', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          run_id: 'test-run-456',
          user_id: 'test@example.com',
          query: 'Show my bills',
          mode: 'preview_only',
          context: { time_window_days: 30, filters: {} },
          status: 'done',
          intent: 'bills',
          answer: 'I found 5 bills and invoices from the last 30 days.',
          cards: [
            {
              kind: 'bills_summary',
              title: 'Bills & Invoices',
              body: 'You have 2 bills due soon, 1 overdue payment, and 2 other invoices.',
              email_ids: ['bill-1', 'bill-2', 'bill-3', 'bill-4', 'bill-5'],
              meta: {
                count: 5,
                due_soon: [
                  { sender: 'Electric Company', amount: '$145.00', due_date: '2025-11-25' },
                  { sender: 'Internet Provider', amount: '$79.99', due_date: '2025-11-27' },
                ],
                overdue: [
                  { sender: 'Credit Card', amount: '$523.45', due_date: '2025-11-15' },
                ],
                other: [
                  { sender: 'Phone Bill', amount: '$45.00' },
                  { sender: 'Subscription', amount: '$9.99' },
                ],
                time_window_days: 30,
              },
            },
          ],
          tools_used: ['email_search', 'applications_lookup'],
          metrics: {
            emails_scanned: 1540,
            tool_calls: 2,
            rag_sources: 0,
            duration_ms: 1890,
          },
          created_at: new Date().toISOString(),
          completed_at: new Date().toISOString(),
        }),
      });
    });

    await page.goto(`/chat`);
    await expect(page.getByTestId('agent-mail-chat')).toBeVisible();

    await page.getByTestId('chat-input').fill('Show my bills and invoices');
    await page.getByTestId('chat-send').click();

    // Verify bills card appears
    const billsCard = page.getByTestId('agent-card-bills_summary');
    await expect(billsCard).toBeVisible();
    await expect(billsCard).toContainText('Bills & Invoices');

    // Check metric pills
    await expect(billsCard).toContainText('Due soon');
    await expect(billsCard).toContainText('2');
    await expect(billsCard).toContainText('Overdue');
    await expect(billsCard).toContainText('1');
    await expect(billsCard).toContainText('Other');

    // Check due soon details
    await expect(billsCard).toContainText('Electric Company');
    await expect(billsCard).toContainText('$145.00');
  });

  test('renders interviews_summary card with upcoming/waiting/closed pills', async ({ page }) => {
    await page.route('**/api/v2/agent/run', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          run_id: 'test-run-789',
          user_id: 'test@example.com',
          query: 'Show interviews',
          mode: 'preview_only',
          context: { time_window_days: 30, filters: {} },
          status: 'done',
          intent: 'interviews',
          answer: 'I found 4 interview-related threads from the last 30 days.',
          cards: [
            {
              kind: 'interviews_summary',
              title: 'Interview Schedule',
              body: 'You have 2 upcoming interviews, 1 recruiter waiting for response, and 1 closed thread.',
              email_ids: ['int-1', 'int-2', 'int-3', 'int-4'],
              meta: {
                count: 4,
                upcoming: [
                  { company: 'TechCorp', role: 'Senior Engineer', date: 'Nov 22, 2pm' },
                  { company: 'StartupXYZ', role: 'Lead Developer', date: 'Nov 25, 10am' },
                ],
                waiting: [
                  { company: 'BigCompany', role: 'Staff Engineer', last_contact: '5 days ago' },
                ],
                closed: [
                  { company: 'SmallCo', role: 'Developer' },
                ],
                time_window_days: 30,
              },
            },
          ],
          tools_used: ['email_search', 'applications_lookup', 'thread_detail'],
          metrics: {
            emails_scanned: 1540,
            tool_calls: 3,
            rag_sources: 0,
            duration_ms: 3120,
          },
          created_at: new Date().toISOString(),
          completed_at: new Date().toISOString(),
        }),
      });
    });

    await page.goto(`/chat`);
    await expect(page.getByTestId('agent-mail-chat')).toBeVisible();

    await page.getByTestId('chat-input').fill('Show my interviews');
    await page.getByTestId('chat-send').click();

    // Verify interviews card
    const interviewsCard = page.getByTestId('agent-card-interviews_summary');
    await expect(interviewsCard).toBeVisible();
    await expect(interviewsCard).toContainText('Interview Schedule');

    // Check pills
    await expect(interviewsCard).toContainText('Upcoming');
    await expect(interviewsCard).toContainText('2');
    await expect(interviewsCard).toContainText('Waiting');
    await expect(interviewsCard).toContainText('1');
    await expect(interviewsCard).toContainText('Closed');

    // Check upcoming interview details
    await expect(interviewsCard).toContainText('TechCorp');
    await expect(interviewsCard).toContainText('Senior Engineer');
    await expect(interviewsCard).toContainText('Nov 22, 2pm');
  });

  test('renders generic_summary card with email statistics', async ({ page }) => {
    await page.route('**/api/v2/agent/run', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          run_id: 'test-run-profile',
          user_id: 'test@example.com',
          query: 'profile',
          mode: 'preview_only',
          context: { time_window_days: 60, filters: {} },
          status: 'done',
          intent: 'profile',
          answer: 'Your inbox has high activity with 1557 emails analyzed in the last 60 days.',
          cards: [
            {
              kind: 'generic_summary',
              title: 'Mailbox Profile',
              body: 'Your job search inbox shows strong engagement with recruiters and companies.',
              email_ids: [],
              meta: {
                total_emails: 3229,
                emails_scanned: 1557,
                time_window_days: 60,
              },
            },
          ],
          tools_used: ['profile_stats', 'email_search'],
          metrics: {
            emails_scanned: 1557,
            tool_calls: 2,
            rag_sources: 3,
            duration_ms: 1650,
          },
          created_at: new Date().toISOString(),
          completed_at: new Date().toISOString(),
        }),
      });
    });

    await page.goto(`/chat`);
    await expect(page.getByTestId('agent-mail-chat')).toBeVisible();

    await page.getByTestId('chat-input').fill('Give me a profile');
    await page.getByTestId('chat-send').click();

    // Verify generic_summary card
    const profileCard = page.getByTestId('agent-card-generic_summary');
    await expect(profileCard).toBeVisible();
    await expect(profileCard).toContainText('Mailbox Profile');

    // Check metric pills
    await expect(profileCard).toContainText('Emails scanned');
    await expect(profileCard).toContainText('1557');
    await expect(profileCard).toContainText('Total found');
    await expect(profileCard).toContainText('3229');
    await expect(profileCard).toContainText('Time window');
    await expect(profileCard).toContainText('60d');
  });

  test('shows error banner when API request fails', async ({ page }) => {
    await page.route('**/api/v2/agent/run', async (route) => {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Internal server error during test' }),
      });
    });

    await page.goto(`/chat`);
    await expect(page.getByTestId('agent-mail-chat')).toBeVisible();

    await page.getByTestId('chat-input').fill('Show my followups');
    await page.getByTestId('chat-send').click();

    // Verify error banner appears
    const errorBanner = page.getByTestId('chat-error-banner');
    await expect(errorBanner).toBeVisible();
    await expect(errorBanner).toContainText('Connection hiccup');
  });

  test('shows thinking indicator while processing', async ({ page }) => {
    // Mock with a delay to capture thinking state
    await page.route('**/api/v2/agent/run', async (route) => {
      await new Promise(resolve => setTimeout(resolve, 500));
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          run_id: 'test-run-thinking',
          user_id: 'test@example.com',
          query: 'test',
          mode: 'preview_only',
          context: { time_window_days: 30, filters: {} },
          status: 'done',
          intent: 'generic',
          answer: 'Test response',
          cards: [],
          tools_used: [],
          metrics: { emails_scanned: 0, tool_calls: 0, rag_sources: 0, duration_ms: 500 },
          created_at: new Date().toISOString(),
          completed_at: new Date().toISOString(),
        }),
      });
    });

    await page.goto(`/chat`);
    await expect(page.getByTestId('agent-mail-chat')).toBeVisible();

    await page.getByTestId('chat-input').fill('test query');
    await page.getByTestId('chat-send').click();

    // Verify thinking indicator appears
    const thinkingIndicator = page.getByTestId('chat-thinking');
    await expect(thinkingIndicator).toBeVisible({ timeout: 1000 });
    await expect(thinkingIndicator).toContainText('Mailbox Assistant is thinking');

    // Wait for response
    await expect(page.getByTestId('chat-message-assistant').last()).toBeVisible({ timeout: 3000 });
  });
});
