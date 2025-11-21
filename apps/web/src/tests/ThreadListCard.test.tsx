/**
 * Tests for ThreadListCard component
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ThreadListCard } from '@/components/mail/ThreadListCard';
import type { AgentCard } from '@/types/agent';
import type { MailThreadSummary } from '@/lib/mailThreads';

// Mock the mailbox theme hook
vi.mock('@/hooks/useMailboxTheme', () => ({
  useMailboxTheme: () => ({
    theme: {
      id: 'bananaPro',
      label: 'Banana Pro',
    },
    themeId: 'bananaPro',
  }),
}));

// Mock fetch
global.fetch = vi.fn(() =>
  Promise.resolve({
    ok: true,
    json: () => Promise.resolve({}),
  } as Response)
);

const mockThreads: MailThreadSummary[] = [
  {
    threadId: 'thread-1',
    subject: 'First Thread',
    from: 'alice@example.com',
    to: 'me@example.com',
    lastMessageAt: '2025-01-15T10:00:00Z',
    unreadCount: 2,
    riskScore: 0.3,
    labels: ['INBOX', 'IMPORTANT'],
    snippet: 'This is the first thread preview...',
    gmailUrl: 'https://mail.google.com/mail/u/0/#inbox/thread-1',
  },
  {
    threadId: 'thread-2',
    subject: 'Second Thread',
    from: 'bob@example.com',
    to: 'me@example.com',
    lastMessageAt: '2025-01-14T10:00:00Z',
    unreadCount: 0,
    riskScore: 0.8,
    labels: ['INBOX'],
    snippet: 'This is the second thread preview...',
    gmailUrl: 'https://mail.google.com/mail/u/0/#inbox/thread-2',
  },
  {
    threadId: 'thread-3',
    subject: 'Third Thread',
    from: 'charlie@example.com',
    to: 'me@example.com',
    lastMessageAt: '2025-01-13T10:00:00Z',
    unreadCount: 1,
    riskScore: 0.1,
    labels: ['INBOX', 'WORK'],
    snippet: 'This is the third thread preview...',
    gmailUrl: 'https://mail.google.com/mail/u/0/#inbox/thread-3',
  },
];

const mockCard: AgentCard = {
  kind: 'thread_list',
  title: 'Follow-up Threads',
  body: 'People you still owe a reply',
  email_ids: [],
  meta: { intent: 'followups' },
  threads: mockThreads,
};

describe('ThreadListCard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders with thread data', () => {
    render(<ThreadListCard card={mockCard} />);

    // Check card header
    expect(screen.getAllByText('Follow-up Threads')[0]).toBeInTheDocument();
    expect(screen.getByText('People you still owe a reply')).toBeInTheDocument();

    // Check thread count badge
    expect(screen.getByText(/3.*threads/)).toBeInTheDocument();

    // Check that threads are rendered using data-testid
    const rows = screen.getAllByTestId('thread-row');
    expect(rows).toHaveLength(3);
    expect(rows[0]).toHaveAttribute('data-thread-id', 'thread-1');
    expect(rows[1]).toHaveAttribute('data-thread-id', 'thread-2');
    expect(rows[2]).toHaveAttribute('data-thread-id', 'thread-3');
  });

  it('selects first thread by default', () => {
    render(<ThreadListCard card={mockCard} />);

    // First thread row should have data-selected="true"
    const rows = screen.getAllByTestId('thread-row');
    expect(rows[0]).toHaveAttribute('data-thread-id', 'thread-1');
    expect(rows[0]).toHaveAttribute('data-selected', 'true');
  });

  it('changes selected thread when clicking another row', async () => {
    render(<ThreadListCard card={mockCard} />);

    // Find all thread rows
    const rows = screen.getAllByTestId('thread-row');
    expect(rows).toHaveLength(3);

    // Click the second thread
    fireEvent.click(rows[1]);

    await waitFor(() => {
      // Second row should now be selected
      expect(rows[1]).toHaveAttribute('data-selected', 'true');
      expect(rows[0]).toHaveAttribute('data-selected', 'false');
    });
  });

  it('renders intent badge for non-generic intents', () => {
    render(<ThreadListCard card={mockCard} />);

    // Should show "followups" badge
    expect(screen.getByText('followups')).toBeInTheDocument();
  });

  it('renders risk badges on risky threads', () => {
    render(<ThreadListCard card={mockCard} />);

    // Thread 2 has riskScore 0.8, should show Risk badge
    const riskBadges = screen.getAllByText('Risk');
    expect(riskBadges.length).toBeGreaterThan(0);
  });

  it('renders follow-up badges for followup intent', () => {
    render(<ThreadListCard card={mockCard} />);

    // All threads in a followups card should show Follow-up badge
    const followUpBadges = screen.getAllByText('Follow-up');
    expect(followUpBadges.length).toBeGreaterThan(0);
  });

  it('renders labels for threads', () => {
    render(<ThreadListCard card={mockCard} />);

    // Check for some label badges using getAllByText since labels appear multiple times
    expect(screen.getAllByText('INBOX').length).toBeGreaterThan(0);
    expect(screen.getAllByText('IMPORTANT').length).toBeGreaterThan(0);
    expect(screen.getAllByText('WORK').length).toBeGreaterThan(0);
  });

  it('returns null for non-thread_list cards', () => {
    const nonThreadCard: AgentCard = {
      kind: 'generic_summary',
      title: 'Generic Card',
      body: 'Not a thread list',
      email_ids: [],
      meta: {},
    };

    const { container } = render(<ThreadListCard card={nonThreadCard} />);
    expect(container.firstChild).toBeNull();
  });

  it('shows thread count as "1 thread" for single thread', () => {
    const singleThreadCard: AgentCard = {
      ...mockCard,
      threads: [mockThreads[0]],
    };

    render(<ThreadListCard card={singleThreadCard} />);
    expect(screen.getByText('1 thread')).toBeInTheDocument();
  });
});
