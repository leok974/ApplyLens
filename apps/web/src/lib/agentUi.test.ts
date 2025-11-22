// apps/web/src/lib/agentUi.test.ts
import { describe, it, expect } from 'vitest';
import { mapAgentResultToCards } from './agentUi';

describe('mapAgentResultToCards – Agent V2 intents', () => {
  it('maps suspicious zero-results to a single zero-summary card', () => {
    const agentResult: any = {
      status: 'done',
      intent: 'suspicious',
      metrics: {
        emails_scanned: 50,
        matches: 0,
        time_window_days: 30,
      },
      cards: [
        {
          kind: 'suspicious_summary',
          title: 'No Suspicious Emails Found',
          body: '',
          email_ids: [],
          meta: { count: 0 },
        },
      ],
    };

    const cards = mapAgentResultToCards(agentResult);

    expect(cards).toHaveLength(1);
    const card = cards[0];

    expect(card.kind).toBe('suspicious_summary');
    expect(card.title).toBe('No Suspicious Emails Found');
    expect(card.meta?.count).toBe(0);
    expect(card.email_ids?.length ?? 0).toBe(0);
  });

  it('maps suspicious non-zero results to a match-summary card with items', () => {
    const agentResult: any = {
      status: 'done',
      intent: 'suspicious',
      metrics: {
        emails_scanned: 120,
        matches: 2,
        time_window_days: 30,
      },
      cards: [
        {
          kind: 'suspicious_summary',
          title: 'Suspicious Emails Found',
          body: '',
          email_ids: [],
          meta: {
            count: 2,
            items: [
              {
                id: 'msg-1',
                subject: 'Password reset required',
                sender: 'security@fakebank.io',
                risk_level: 90,
              },
              {
                id: 'msg-2',
                subject: 'Your account will be closed',
                sender: 'support@notreallyamazon.com',
                risk_level: 88,
              },
            ],
          },
        },
      ],
    };

    const cards = mapAgentResultToCards(agentResult);

    expect(cards).toHaveLength(1);
    const card = cards[0];

    expect(card.kind).toBe('suspicious_summary');
    expect(card.title).toBe('Suspicious Emails Found');
    expect(card.meta?.count).toBe(2);
    // Items are stored in meta, not as top-level property
    const items = card.meta?.items as any[] | undefined;
    expect(items?.length).toBe(2);
    expect(items?.[0]?.subject).toContain('Password reset');
  });

  it('maps followups zero-results to a proper followups_summary card', () => {
    const agentResult: any = {
      status: 'done',
      intent: 'followups',
      metrics: {
        emails_scanned: 40,
        matches: 0,
        time_window_days: 14,
      },
      cards: [
        {
          kind: 'followups_summary',
          title: 'No Follow-ups Needed',
          body: '',
          email_ids: [],
          meta: { count: 0 },
        },
      ],
    };

    const cards = mapAgentResultToCards(agentResult);

    expect(cards).toHaveLength(1);
    const card = cards[0];

    expect(card.kind).toBe('followups_summary');
    expect(card.title).toBe('No Follow-ups Needed');
    expect(card.meta?.count).toBe(0);
    expect(card.email_ids?.length ?? 0).toBe(0);
  });

  it('maps followups non-zero results to a followups_summary card with items', () => {
    const agentResult: any = {
      status: 'done',
      intent: 'followups',
      metrics: {
        emails_scanned: 80,
        matches: 3,
        time_window_days: 14,
      },
      cards: [
        {
          kind: 'followups_summary',
          title: 'Follow-ups to Send',
          body: '',
          email_ids: [],
          meta: {
            count: 3,
            items: [
              {
                id: 'f1',
                company: 'Acme Corp',
                role: 'AI Engineer',
                last_contact_at: '2025-11-15T12:00:00Z',
              },
              {
                id: 'f2',
                company: 'ByteMethod',
                role: 'ML Engineer',
                last_contact_at: '2025-11-10T09:00:00Z',
              },
              {
                id: 'f3',
                company: 'RediMinds',
                role: 'AI Enabler Intern',
                last_contact_at: '2025-11-09T16:00:00Z',
              },
            ],
          },
        },
      ],
    };

    const cards = mapAgentResultToCards(agentResult);

    expect(cards).toHaveLength(1);
    const card = cards[0];

    expect(card.kind).toBe('followups_summary');
    expect(card.title).toBe('Follow-ups to Send');
    expect(card.meta?.count).toBe(3);
    const items = card.meta?.items as any[] | undefined;
    expect(items?.length).toBe(3);
  });

  it('maps bills zero-results to a bills_summary card with zero counts', () => {
    const agentResult: any = {
      status: 'done',
      intent: 'bills',
      metrics: {
        emails_scanned: 30,
        matches: 0,
        time_window_days: 30,
      },
      cards: [
        {
          kind: 'bills_summary',
          title: 'No Upcoming Bills Found',
          body: '',
          email_ids: [],
          meta: {
            total_count: 0,
            due_soon_count: 0,
            overdue_count: 0,
          },
        },
      ],
    };

    const cards = mapAgentResultToCards(agentResult);

    expect(cards).toHaveLength(1);
    const card = cards[0];

    expect(card.kind).toBe('bills_summary');
    expect(card.title).toBe('No Upcoming Bills Found');
    expect(card.meta?.total_count).toBe(0);
    expect(card.email_ids?.length ?? 0).toBe(0);
  });

  it('maps bills non-zero results to summary card with sections/items', () => {
    const agentResult: any = {
      status: 'done',
      intent: 'bills',
      metrics: {
        emails_scanned: 90,
        matches: 3,
        time_window_days: 30,
      },
      cards: [
        {
          kind: 'bills_summary',
          title: 'Bills to Review',
          body: '',
          email_ids: [],
          meta: {
            total_count: 3,
            due_soon_count: 2,
            overdue_count: 1,
            items: [
              {
                id: 'b1',
                label: 'Due soon',
                amount: 49.99,
                merchant: 'Spotify',
                due_date: '2025-11-22',
              },
              {
                id: 'b2',
                label: 'Due soon',
                amount: 12.99,
                merchant: 'Netflix',
                due_date: '2025-11-23',
              },
              {
                id: 'b3',
                label: 'Overdue',
                amount: 120.0,
                merchant: 'Electricity',
                due_date: '2025-11-10',
              },
            ],
          },
        },
      ],
    };

    const cards = mapAgentResultToCards(agentResult);

    expect(cards).toHaveLength(1);
    const card = cards[0];

    expect(card.kind).toBe('bills_summary');
    expect(card.title).toBe('Bills to Review');
    expect(card.meta?.total_count).toBe(3);
    const items = card.meta?.items as any[] | undefined;
    expect(items?.length).toBe(3);
  });

  it('maps followups to summary + thread_list when threads exist', () => {
    const agentResult: any = {
      status: 'done',
      intent: 'followups',
      cards: [
        {
          kind: 'followups_summary',
          title: 'Conversations Waiting on Your Reply',
          body: 'You have multiple follow-ups awaiting your reply.',
          email_ids: [],
          meta: { count: 2, time_window_days: 30 },
        },
        {
          kind: 'thread_list',
          intent: 'followups',
          title: 'Conversations Waiting on Your Reply',
          body: '',
          email_ids: [],
          meta: { count: 2, time_window_days: 30 },
          threads: [
            {
              threadId: 't1',
              subject: 'Follow-up on interview',
              from: 'recruiter@company.com',
              lastMessageAt: '2025-11-20T10:00:00Z',
              snippet: 'Looking forward to hearing back...',
            },
            {
              threadId: 't2',
              subject: 'Application status',
              from: 'hr@startup.io',
              lastMessageAt: '2025-11-19T15:30:00Z',
              snippet: 'Could you provide an update?',
            },
          ],
        },
      ],
    };

    const cards = mapAgentResultToCards(agentResult);

    expect(cards).toHaveLength(2);

    // First card: summary
    const summaryCard = cards[0];
    expect(summaryCard.kind).toBe('followups_summary');
    expect(summaryCard.meta?.count).toBe(2);

    // Second card: thread_list
    const threadCard = cards[1];
    expect(threadCard.kind).toBe('thread_list');
    expect(threadCard.intent).toBe('followups');
    expect(threadCard.threads).toHaveLength(2);
    expect(threadCard.threads?.[0]?.threadId).toBe('t1');
  });

  it('maps unsubscribe to summary + thread_list when newsletters found', () => {
    const agentResult: any = {
      status: 'done',
      intent: 'unsubscribe',
      cards: [
        {
          kind: 'generic_summary',
          title: 'Unsubscribe from Unopened Newsletters',
          body: '46 newsletters found that haven\'t been opened in 60 days.',
          email_ids: [],
          meta: { count: 46, time_window_days: 60 },
        },
        {
          kind: 'thread_list',
          intent: 'unsubscribe',
          title: 'Unsubscribe from Unopened Newsletters',
          body: '',
          email_ids: [],
          meta: { count: 46, time_window_days: 60 },
          threads: [
            {
              threadId: 'n1',
              subject: 'Weekly Newsletter #234',
              from: 'news@example.com',
              lastMessageAt: '2025-09-15T08:00:00Z',
            },
            {
              threadId: 'n2',
              subject: 'Monthly Digest',
              from: 'digest@marketing.com',
              lastMessageAt: '2025-09-10T12:00:00Z',
            },
          ],
        },
      ],
    };

    const cards = mapAgentResultToCards(agentResult);

    expect(cards).toHaveLength(2);

    const summaryCard = cards[0];
    expect(summaryCard.kind).toBe('generic_summary');
    expect(summaryCard.body).toContain('46 newsletters');

    const threadCard = cards[1];
    expect(threadCard.kind).toBe('thread_list');
    expect(threadCard.intent).toBe('unsubscribe');
    expect(threadCard.threads).toHaveLength(2);
  });

  it('returns only summary card when count is zero (no thread_list)', () => {
    const agentResult: any = {
      status: 'done',
      intent: 'suspicious',
      cards: [
        {
          kind: 'generic_summary',
          title: 'No Suspicious Emails Found',
          body: 'You\'re all caught up – I couldn\'t find anything matching this in the last 30 days.',
          email_ids: [],
          meta: { count: 0, time_window_days: 30 },
        },
      ],
    };

    const cards = mapAgentResultToCards(agentResult);

    // Only summary card, NO thread_list card when count is 0
    expect(cards).toHaveLength(1);
    expect(cards[0].kind).toBe('generic_summary');
    expect(cards[0].meta?.count).toBe(0);
  });
});
