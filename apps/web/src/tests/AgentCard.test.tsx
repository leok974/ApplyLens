/**
 * Tests for AgentCard component - card metadata & subtitles
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { AgentResultCard } from '@/components/AgentCard';
import type { AgentCard } from '@/types/agent';

describe('AgentCard - metadata pill', () => {
  it('renders pill for scan summary card with count and time_window_days', () => {
    const card: AgentCard = {
      kind: 'followups_summary',
      title: 'Follow-ups',
      body: 'Conversations waiting on your reply',
      email_ids: [],
      meta: {
        count: 10,
        time_window_days: 90
      },
      intent: 'followups',
    };

    render(<AgentResultCard card={card} />);

    const pill = screen.getByTestId('agent-card-meta-pill');
    expect(pill).toBeInTheDocument();
    expect(pill.textContent).toContain('10 items');
    expect(pill.textContent).toContain('90 days');
  });

  it('renders "1 item" for singular count', () => {
    const card: AgentCard = {
      kind: 'bills_summary',
      title: 'Bills',
      body: 'Upcoming payment',
      email_ids: [],
      meta: {
        count: 1,
        time_window_days: 30
      },
      intent: 'bills',
    };

    render(<AgentResultCard card={card} />);

    const pill = screen.getByTestId('agent-card-meta-pill');
    expect(pill.textContent).toContain('1 item');
    expect(pill.textContent).not.toContain('items');
  });

  it('does not render pill when meta is missing', () => {
    const card: AgentCard = {
      kind: 'generic_summary',
      title: 'Generic Summary',
      body: 'Some content',
      email_ids: [],
      meta: {},
    };

    render(<AgentResultCard card={card} />);

    const pill = screen.queryByTestId('agent-card-meta-pill');
    expect(pill).not.toBeInTheDocument();
  });

  it('does not render pill when count is missing', () => {
    const card: AgentCard = {
      kind: 'followups_summary',
      title: 'Follow-ups',
      body: 'Some followups',
      email_ids: [],
      meta: {
        time_window_days: 90
      },
      intent: 'followups',
    };

    render(<AgentResultCard card={card} />);

    const pill = screen.queryByTestId('agent-card-meta-pill');
    expect(pill).not.toBeInTheDocument();
  });

  it('does not render pill when time_window_days is missing', () => {
    const card: AgentCard = {
      kind: 'followups_summary',
      title: 'Follow-ups',
      body: 'Some followups',
      email_ids: [],
      meta: {
        count: 5
      },
      intent: 'followups',
    };

    render(<AgentResultCard card={card} />);

    const pill = screen.queryByTestId('agent-card-meta-pill');
    expect(pill).not.toBeInTheDocument();
  });
});

describe('AgentCard - intent subtitles', () => {
  it('renders correct subtitle for followups intent', () => {
    const card: AgentCard = {
      kind: 'followups_summary',
      title: 'Follow-ups',
      body: 'Some body text',
      email_ids: [],
      meta: { count: 5, time_window_days: 90 },
      intent: 'followups',
    };

    render(<AgentResultCard card={card} />);

    const subtitle = screen.getByTestId('agent-card-subtitle');
    expect(subtitle).toBeInTheDocument();
    expect(subtitle.textContent).toBe('Conversations waiting on your reply');
  });

  it('renders correct subtitle for unsubscribe intent', () => {
    const card: AgentCard = {
      kind: 'generic_summary',
      title: 'Newsletters',
      body: 'Some body text',
      email_ids: [],
      meta: { count: 12, time_window_days: 30 },
      intent: 'unsubscribe',
    };

    render(<AgentResultCard card={card} />);

    const subtitle = screen.getByTestId('agent-card-subtitle');
    expect(subtitle.textContent).toBe("Newsletters you haven't opened recently");
  });

  it('renders correct subtitle for clean_promos intent', () => {
    const card: AgentCard = {
      kind: 'generic_summary',
      title: 'Promotions',
      body: 'Some body text',
      email_ids: [],
      meta: { count: 20, time_window_days: 30 },
      intent: 'clean_promos',
    };

    render(<AgentResultCard card={card} />);

    const subtitle = screen.getByTestId('agent-card-subtitle');
    expect(subtitle.textContent).toBe('Promotions you may want to archive');
  });

  it('renders correct subtitle for bills intent', () => {
    const card: AgentCard = {
      kind: 'bills_summary',
      title: 'Bills',
      body: 'Some body text',
      email_ids: [],
      meta: { count: 3, time_window_days: 30 },
      intent: 'bills',
    };

    render(<AgentResultCard card={card} />);

    const subtitle = screen.getByTestId('agent-card-subtitle');
    expect(subtitle.textContent).toBe('Bills and payment reminders from your inbox');
  });

  it('renders correct subtitle for interviews intent', () => {
    const card: AgentCard = {
      kind: 'interviews_summary',
      title: 'Interviews',
      body: 'Some body text',
      email_ids: [],
      meta: { count: 2, time_window_days: 30 },
      intent: 'interviews',
    };

    render(<AgentResultCard card={card} />);

    const subtitle = screen.getByTestId('agent-card-subtitle');
    expect(subtitle.textContent).toBe('Interview and recruiter threads');
  });

  it('renders correct subtitle for suspicious intent', () => {
    const card: AgentCard = {
      kind: 'suspicious_summary',
      title: 'Suspicious Emails',
      body: 'Some body text',
      email_ids: [],
      meta: { count: 1, time_window_days: 7 },
      intent: 'suspicious',
    };

    render(<AgentResultCard card={card} />);

    const subtitle = screen.getByTestId('agent-card-subtitle');
    expect(subtitle.textContent).toBe('Emails that might be risky');
  });

  it('does not render subtitle for generic intent', () => {
    const card: AgentCard = {
      kind: 'generic_summary',
      title: 'Summary',
      body: 'Some body text',
      email_ids: [],
      meta: {},
      intent: 'generic',
    };

    render(<AgentResultCard card={card} />);

    const subtitle = screen.queryByTestId('agent-card-subtitle');
    expect(subtitle).not.toBeInTheDocument();
  });

  it('does not render subtitle when no intent is specified', () => {
    const card: AgentCard = {
      kind: 'generic_summary',
      title: 'Summary',
      body: 'Some body text',
      email_ids: [],
      meta: {},
    };

    render(<AgentResultCard card={card} />);

    const subtitle = screen.queryByTestId('agent-card-subtitle');
    expect(subtitle).not.toBeInTheDocument();
  });

  it('infers intent from kind when intent field is missing', () => {
    const card: AgentCard = {
      kind: 'followups_summary',
      title: 'Follow-ups',
      body: 'Some body text',
      email_ids: [],
      meta: {},
    };

    render(<AgentResultCard card={card} />);

    const subtitle = screen.getByTestId('agent-card-subtitle');
    expect(subtitle).toBeInTheDocument();
    expect(subtitle.textContent).toBe('Conversations waiting on your reply');
  });
});

describe('AgentCard - combined features', () => {
  it('renders both pill and subtitle for complete scan card', () => {
    const card: AgentCard = {
      kind: 'followups_summary',
      title: 'Follow-ups',
      body: 'People you still owe a reply',
      email_ids: [],
      meta: {
        count: 10,
        time_window_days: 90
      },
      intent: 'followups',
    };

    render(<AgentResultCard card={card} />);

    // Verify pill
    const pill = screen.getByTestId('agent-card-meta-pill');
    expect(pill).toBeInTheDocument();
    expect(pill.textContent).toContain('10 items');
    expect(pill.textContent).toContain('90 days');

    // Verify subtitle
    const subtitle = screen.getByTestId('agent-card-subtitle');
    expect(subtitle).toBeInTheDocument();
    expect(subtitle.textContent).toBe('Conversations waiting on your reply');

    // Verify both are in dark theme (low contrast)
    expect(pill.className).toContain('slate-300/80');
    expect(subtitle.className).toContain('slate-300/80');
  });

  it('renders card title and body correctly', () => {
    const card: AgentCard = {
      kind: 'bills_summary',
      title: 'Upcoming Bills',
      body: 'You have 3 bills due soon',
      email_ids: [],
      meta: {
        count: 3,
        time_window_days: 30
      },
      intent: 'bills',
    };

    render(<AgentResultCard card={card} />);

    expect(screen.getByText('Upcoming Bills')).toBeInTheDocument();
    expect(screen.getByText('You have 3 bills due soon')).toBeInTheDocument();
  });

  it('renders kind label badge', () => {
    const card: AgentCard = {
      kind: 'suspicious_summary',
      title: 'Suspicious Emails',
      body: 'Found risky emails',
      email_ids: [],
      meta: {
        count: 2,
        time_window_days: 7
      },
      intent: 'suspicious',
    };

    render(<AgentResultCard card={card} />);

    expect(screen.getByText('Suspicious emails')).toBeInTheDocument();
  });
});
