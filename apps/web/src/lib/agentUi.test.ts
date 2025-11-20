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
});
