/**
 * Agent V2 Contract Tests
 *
 * Tests exact API request/response contracts with mocked data.
 * Asserts precise JSON structure and UI rendering.
 *
 * For production smoke tests (no mocking), see chat-agent-v2.prod-smoke.spec.ts
 */

import { test, expect } from '@playwright/test';

const AUTH_STATE = process.env.E2E_AUTH_STATE ?? '';

// Skip all tests in this file if we don't have an auth storage state configured.
test.skip(
  !AUTH_STATE,
  'E2E_AUTH_STATE not configured; skipping Agent V2 contract tests that require authenticated session.'
);

test.describe('@frontend @agent-v2 @contract @authRequired @prodSafe Agent V2 API Contracts', () => {
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
      // Soft error: HTTP 200 with status="error" in payload (v0.5.14+)
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          status: 'error',
          message: 'Connection hiccup',
          error: 'Simulated error for testing',
        }),
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

  test('suspicious intent - zero results shows "No Suspicious Emails Found"', async ({ page }) => {
    // Mock Agent V2 response with zero suspicious emails
    await page.route('**/api/v2/agent/run', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          run_id: 'test-suspicious-zero',
          user_id: 'test@example.com',
          query: 'show suspicious emails',
          mode: 'preview_only',
          context: { time_window_days: 30, filters: {} },
          status: 'done',
          intent: 'suspicious',
          answer: 'No suspicious emails were identified in your inbox over the last 30 days. Stay vigilant and report any emails that seem suspicious.',
          cards: [
            {
              kind: 'suspicious_summary',
              title: 'No Suspicious Emails Found',
              body: '',
              email_ids: [],
              meta: {
                count: 0,
                time_window_days: 30,
              },
            },
          ],
          tools_used: ['email_search', 'security_scan'],
          metrics: {
            emails_scanned: 50,
            matches: 0,
            high_risk: 0,
            tool_calls: 2,
            rag_sources: 0,
            duration_ms: 1200,
            time_window_days: 30,
          },
          created_at: new Date().toISOString(),
          completed_at: new Date().toISOString(),
        }),
      });
    });

    await page.goto(`/chat`);
    await expect(page.getByTestId('agent-mail-chat')).toBeVisible();

    await page.getByTestId('chat-input').fill('show suspicious emails');
    await page.getByTestId('chat-send').click();

    // Verify zero-result message
    const assistantMessage = page.getByTestId('chat-message-assistant').last();
    await expect(assistantMessage).toBeVisible();
    await expect(assistantMessage).toContainText('No suspicious emails were identified');
    await expect(assistantMessage).toContainText('30 days');

    // Verify zero-result card
    const suspiciousCard = page.getByTestId('agent-card-suspicious_summary');
    await expect(suspiciousCard).toBeVisible();
    await expect(suspiciousCard).toContainText('No Suspicious Emails Found');
  });

  test('suspicious intent - non-zero results shows "Suspicious Emails Found" with items', async ({ page }) => {
    // Mock Agent V2 response with 3 suspicious emails
    await page.route('**/api/v2/agent/run', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          run_id: 'test-suspicious-nonzero',
          user_id: 'test@example.com',
          query: 'show suspicious emails',
          mode: 'preview_only',
          context: { time_window_days: 30, filters: {} },
          status: 'done',
          intent: 'suspicious',
          answer: 'I found 3 emails that look suspicious out of 50 scanned. These include fake invoices and urgent payment requests.',
          cards: [
            {
              kind: 'suspicious_summary',
              title: 'Suspicious Emails Found',
              body: '',
              email_ids: ['msg1', 'msg2', 'msg3'],
              meta: {
                count: 3,
                time_window_days: 30,
                items: [
                  {
                    id: 'msg1',
                    subject: 'Urgent: Verify your account',
                    sender: 'phish@example.com',
                    risk_level: 'high',
                    reasons: ['Suspicious link', 'Urgent language'],
                    received_at: '2025-11-20T10:00:00Z',
                  },
                  {
                    id: 'msg2',
                    subject: 'You won the lottery!',
                    sender: 'scam@bad.com',
                    risk_level: 'high',
                    reasons: ['Too good to be true', 'Unknown sender'],
                    received_at: '2025-11-19T15:30:00Z',
                  },
                  {
                    id: 'msg3',
                    subject: 'Invoice payment required',
                    sender: 'fake@invoice.net',
                    risk_level: 'medium',
                    reasons: ['Fake invoice pattern'],
                    received_at: '2025-11-18T09:15:00Z',
                  },
                ],
              },
            },
          ],
          tools_used: ['email_search', 'security_scan'],
          metrics: {
            emails_scanned: 50,
            matches: 3,
            high_risk: 2,
            tool_calls: 2,
            rag_sources: 0,
            duration_ms: 1500,
            time_window_days: 30,
          },
          created_at: new Date().toISOString(),
          completed_at: new Date().toISOString(),
        }),
      });
    });

    await page.goto(`/chat`);
    await expect(page.getByTestId('agent-mail-chat')).toBeVisible();

    await page.getByTestId('chat-input').fill('show suspicious emails');
    await page.getByTestId('chat-send').click();

    // Verify non-zero message
    const assistantMessage = page.getByTestId('chat-message-assistant').last();
    await expect(assistantMessage).toBeVisible();
    await expect(assistantMessage).toContainText('3 emails that look suspicious');
    await expect(assistantMessage).toContainText('50 scanned');

    // Verify card with matches
    const suspiciousCard = page.getByTestId('agent-card-suspicious_summary');
    await expect(suspiciousCard).toBeVisible();
    await expect(suspiciousCard).toContainText('Suspicious Emails Found');

    // Verify count in card metadata
    await expect(suspiciousCard).toContainText('3');
  });

  test('followups intent shows conversations waiting for reply', async ({ page }) => {
    // Mock Agent V2 response for followups
    await page.route('**/api/v2/agent/run', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          run_id: 'test-followups',
          user_id: 'test@example.com',
          query: 'show me followups',
          mode: 'preview_only',
          context: { time_window_days: 30, filters: {} },
          status: 'done',
          intent: 'followups',
          answer: 'You have 2 conversations waiting for your reply in the last 30 days.',
          cards: [
            {
              kind: 'followups_summary',
              title: 'Conversations Waiting on Your Reply',
              body: '',
              email_ids: [],
              meta: {
                count: 2,
                time_window_days: 30,
                items: [
                  {
                    id: 't1',
                    company: 'TechCorp',
                    subject: 'Interview invitation',
                    last_from: 'recruiter',
                    last_received_at: '2025-11-18T14:00:00Z',
                    suggested_angle: 'Confirm interest and availability',
                  },
                  {
                    id: 't2',
                    company: 'StartupXYZ',
                    subject: 'Technical assessment',
                    last_from: 'hiring_manager',
                    last_received_at: '2025-11-17T10:00:00Z',
                    suggested_angle: 'Ask for timeline clarification',
                  },
                ],
              },
            },
          ],
          tools_used: ['email_search'],
          metrics: {
            conversations_scanned: 3,
            needs_reply: 2,
            tool_calls: 1,
            rag_sources: 0,
            duration_ms: 800,
            time_window_days: 30,
          },
          created_at: new Date().toISOString(),
          completed_at: new Date().toISOString(),
        }),
      });
    });

    await page.goto(`/chat`);
    await expect(page.getByTestId('agent-mail-chat')).toBeVisible();

    await page.getByTestId('chat-input').fill('show me followups');
    await page.getByTestId('chat-send').click();

    // Verify message
    const assistantMessage = page.getByTestId('chat-message-assistant').last();
    await expect(assistantMessage).toBeVisible();
    await expect(assistantMessage).toContainText('2 conversations waiting');

    // Verify card
    const followupsCard = page.getByTestId('agent-card-followups_summary');
    await expect(followupsCard).toBeVisible();
    await expect(followupsCard).toContainText('Conversations Waiting');
    await expect(followupsCard).toContainText('Suggested follow-ups');
  });

  test('bills intent shows due soon and overdue sections', async ({ page }) => {
    // Mock Agent V2 response for bills
    await page.route('**/api/v2/agent/run', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          run_id: 'test-bills',
          user_id: 'test@example.com',
          query: 'show my bills',
          mode: 'preview_only',
          context: { time_window_days: 60, filters: {} },
          status: 'done',
          intent: 'bills',
          answer: 'I found 4 bills in the last 60 days: 2 due soon, 1 overdue, and 1 upcoming or paid.',
          cards: [
            {
              kind: 'bills_summary',
              title: 'Bills Overview',
              body: '',
              email_ids: [],
              meta: {
                total: 4,
                due_soon: 2,
                overdue: 1,
                other: 1,
                time_window_days: 60,
                sections: [
                  {
                    id: 'due_soon',
                    title: 'Due soon (next 7 days)',
                    items: [
                      { id: 'b1', merchant: 'Electric Co', amount: 150, due_date: '2025-11-22', status: 'due_soon' },
                      { id: 'b2', merchant: 'Internet ISP', amount: 80, due_date: '2025-11-23', status: 'due_soon' },
                    ],
                  },
                  {
                    id: 'overdue',
                    title: 'Overdue',
                    items: [
                      { id: 'b3', merchant: 'Credit Card', amount: 500, due_date: '2025-11-15', status: 'overdue' },
                    ],
                  },
                  {
                    id: 'other',
                    title: 'Other bills',
                    items: [
                      { id: 'b4', merchant: 'Phone Bill', amount: 60, due_date: '2025-12-01', status: 'other' },
                    ],
                  },
                ],
              },
            },
          ],
          tools_used: ['email_search', 'bill_parser'],
          metrics: {
            total_bills: 4,
            due_soon: 2,
            overdue: 1,
            other: 1,
            tool_calls: 2,
            rag_sources: 0,
            duration_ms: 1100,
            time_window_days: 60,
          },
          created_at: new Date().toISOString(),
          completed_at: new Date().toISOString(),
        }),
      });
    });

    await page.goto(`/chat`);
    await expect(page.getByTestId('agent-mail-chat')).toBeVisible();

    await page.getByTestId('chat-input').fill('show my bills');
    await page.getByTestId('chat-send').click();

    // Verify message
    const assistantMessage = page.getByTestId('chat-message-assistant').last();
    await expect(assistantMessage).toBeVisible();
    await expect(assistantMessage).toContainText('4 bills');
    await expect(assistantMessage).toContainText('2 due soon');
    await expect(assistantMessage).toContainText('1 overdue');

    // Verify card
    const billsCard = page.getByTestId('agent-card-bills_summary');
    await expect(billsCard).toBeVisible();
    await expect(billsCard).toContainText('Bills Overview');
    await expect(billsCard).toContainText('Overdue');
    await expect(billsCard).toContainText('Due soon');
  });

  test('feedback buttons send correct API calls with intent and card_id', async ({ page }) => {
    // Track feedback API calls
    const feedbackCalls: any[] = [];

    await page.route('**/api/v2/agent/feedback', async (route) => {
      const req = route.request();
      const bodyRaw = req.postData() || '{}';
      const body = JSON.parse(bodyRaw);

      // Store for assertion
      feedbackCalls.push(body);

      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          ok: true,
          message: 'Feedback saved successfully',
        }),
      });
    });

    // Mock Agent V2 run with suspicious card
    await page.route('**/api/v2/agent/run', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          run_id: 'feedback-test-run',
          user_id: 'test@example.com',
          query: 'show suspicious emails',
          mode: 'preview_only',
          context: { time_window_days: 7 },
          status: 'done',
          intent: 'suspicious',
          answer: 'I found 2 suspicious emails from risky domains.',
          cards: [
            {
              kind: 'suspicious_summary',
              title: 'Suspicious Emails',
              body: 'Found 2 risky emails',
              email_ids: ['email-1', 'email-2'],
              meta: { count: 2 },
            },
          ],
          tools_used: ['email_search'],
          metrics: { emails_scanned: 100, tool_calls: 1, duration_ms: 1000 },
          created_at: new Date().toISOString(),
          completed_at: new Date().toISOString(),
        }),
      });
    });

    await page.goto(`/chat`);
    await expect(page.getByTestId('agent-mail-chat')).toBeVisible();

    // Send agent query
    await page.getByTestId('chat-input').fill('show suspicious emails');
    await page.getByTestId('chat-send').click();

    // Wait for card to render
    const suspiciousCard = page.getByTestId('agent-card-suspicious_summary');
    await expect(suspiciousCard).toBeVisible();

    // Click helpful button (👍)
    const helpfulButton = page.getByTestId('agent-feedback-suspicious_summary-helpful');
    await expect(helpfulButton).toBeVisible();
    await helpfulButton.click();

    // Wait for API call
    await page.waitForTimeout(200);

    // Verify feedback API was called with correct payload
    expect(feedbackCalls.length).toBeGreaterThan(0);
    const helpfulCall = feedbackCalls[0];
    expect(helpfulCall.intent).toBe('suspicious');
    expect(helpfulCall.card_id).toBe('suspicious_summary');
    expect(helpfulCall.label).toBe('helpful');
    expect(helpfulCall.run_id).toBe('feedback-test-run');

    // Click not helpful button (👎)
    const notHelpfulButton = page.getByTestId('agent-feedback-suspicious_summary-not-helpful');
    await notHelpfulButton.click();
    await page.waitForTimeout(200);

    expect(feedbackCalls.length).toBe(2);
    const notHelpfulCall = feedbackCalls[1];
    expect(notHelpfulCall.label).toBe('not_helpful');

    // Click hide button - should trigger optimistic UI
    const hideButton = page.getByTestId('agent-feedback-suspicious_summary-hide');
    await hideButton.click();

    // Verify card is removed from DOM (optimistic update)
    await expect(suspiciousCard).not.toBeVisible({ timeout: 1000 });

    // Verify hide feedback was sent
    await page.waitForTimeout(200);
    expect(feedbackCalls.length).toBe(3);
    const hideCall = feedbackCalls[2];
    expect(hideCall.label).toBe('hide');
  });

  test('feedback on card with items includes item_id', async ({ page }) => {
    const feedbackCalls: any[] = [];

    await page.route('**/api/v2/agent/feedback', async (route) => {
      const req = route.request();
      const body = JSON.parse(req.postData() || '{}');
      feedbackCalls.push(body);

      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ ok: true, message: 'Feedback saved' }),
      });
    });

    // Mock followups card with items
    await page.route('**/api/v2/agent/run', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          run_id: 'followup-run',
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
              title: 'Follow-ups',
              body: 'Found 2 threads needing replies',
              email_ids: ['email-1', 'email-2'],
              meta: {
                count: 2,
                items: [
                  { id: 'thread-1', company: 'ACME Corp', last_email_date: '2025-11-10' },
                  { id: 'thread-2', company: 'Widget Inc', last_email_date: '2025-11-15' },
                ],
              },
            },
          ],
          tools_used: ['email_search'],
          metrics: { emails_scanned: 500, tool_calls: 1, duration_ms: 800 },
          created_at: new Date().toISOString(),
          completed_at: new Date().toISOString(),
        }),
      });
    });

    await page.goto(`/chat`);
    await expect(page.getByTestId('agent-mail-chat')).toBeVisible();

    await page.getByTestId('chat-input').fill('show followups');
    await page.getByTestId('chat-send').click();

    // Wait for card
    const followupsCard = page.getByTestId('agent-card-followups_summary');
    await expect(followupsCard).toBeVisible();

    // Click hide on the card (not individual item)
    const hideButton = page.getByTestId('agent-feedback-followups_summary-hide');
    await hideButton.click();

    await page.waitForTimeout(200);

    // Verify feedback call includes card_id but no item_id (whole card hidden)
    expect(feedbackCalls.length).toBe(1);
    const call = feedbackCalls[0];
    expect(call.intent).toBe('followups');
    expect(call.card_id).toBe('followups_summary');
    expect(call.label).toBe('hide');
    // item_id should be undefined or null when hiding entire card
    expect(call.item_id).toBeUndefined();
  });
});
