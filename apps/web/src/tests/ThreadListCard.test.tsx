/**
 * Tests for ThreadListCard component
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { ThreadListCard } from '@/components/mail/ThreadListCard';
import type { AgentCard } from '@/types/agent';
import type { MailThreadSummary } from '@/lib/mailThreads';
import * as api from '@/lib/api';

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

// Mock sonner toast
vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

// Mock API
vi.mock('@/lib/api', () => ({
  createApplicationFromEmail: vi.fn(),
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
  const renderWithRouter = (card: AgentCard) => {
    return render(
      <MemoryRouter>
        <ThreadListCard card={card} />
      </MemoryRouter>
    );
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders with thread data', () => {
    renderWithRouter(mockCard);

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
    renderWithRouter(mockCard);

    // First thread row should have data-selected="true"
    const rows = screen.getAllByTestId('thread-row');
    expect(rows[0]).toHaveAttribute('data-thread-id', 'thread-1');
    expect(rows[0]).toHaveAttribute('data-selected', 'true');
  });

  it('changes selected thread when clicking another row', async () => {
    renderWithRouter(mockCard);

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
    renderWithRouter(mockCard);

    // Should show "followups" badge
    expect(screen.getByText('followups')).toBeInTheDocument();
  });

  it('renders risk badges on risky threads', () => {
    renderWithRouter(mockCard);

    // Thread 2 has riskScore 0.8, should show Risk badge
    const riskBadges = screen.getAllByText('Risk');
    expect(riskBadges.length).toBeGreaterThan(0);
  });

  it('renders follow-up badges for followup intent', () => {
    renderWithRouter(mockCard);

    // All threads in a followups card should show Follow-up badge
    const followUpBadges = screen.getAllByText('Follow-up');
    expect(followUpBadges.length).toBeGreaterThan(0);
  });

  it('renders labels for threads', () => {
    renderWithRouter(mockCard);

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

    const { container } = renderWithRouter(nonThreadCard);
    expect(container.firstChild).toBeNull();
  });

  it('shows thread count as "1 thread" for single thread', () => {
    const singleThreadCard: AgentCard = {
      ...mockCard,
      threads: [mockThreads[0]],
    };

    renderWithRouter(singleThreadCard);
    expect(screen.getByText('1 thread')).toBeInTheDocument();
  });

  it('renders metadata pill when count and time_window_days are present', () => {
    const cardWithMeta: AgentCard = {
      ...mockCard,
      meta: {
        intent: 'followups',
        count: 10,
        time_window_days: 90
      },
    };

    renderWithRouter(cardWithMeta);

    const pill = screen.getByTestId('agent-card-meta-pill');
    expect(pill).toBeInTheDocument();
    expect(pill.textContent).toContain('10 items');
    expect(pill.textContent).toContain('90 days');
  });

  it('renders "1 item" for singular count in pill', () => {
    const cardWithMeta: AgentCard = {
      ...mockCard,
      meta: {
        intent: 'followups',
        count: 1,
        time_window_days: 30
      },
    };

    renderWithRouter(cardWithMeta);

    const pill = screen.getByTestId('agent-card-meta-pill');
    expect(pill.textContent).toContain('1 item');
    expect(pill.textContent).not.toContain('items');
  });

  it('does not render pill when count is missing', () => {
    const cardWithoutCount: AgentCard = {
      ...mockCard,
      meta: {
        intent: 'followups',
        time_window_days: 90
      },
    };

    renderWithRouter(cardWithoutCount);

    const pill = screen.queryByTestId('agent-card-meta-pill');
    expect(pill).not.toBeInTheDocument();
  });

  it('does not render pill when time_window_days is missing', () => {
    const cardWithoutTimeWindow: AgentCard = {
      ...mockCard,
      meta: {
        intent: 'followups',
        count: 10
      },
    };

    renderWithRouter(cardWithoutTimeWindow);

    const pill = screen.queryByTestId('agent-card-meta-pill');
    expect(pill).not.toBeInTheDocument();
  });

  it('renders UX hint for thread_list cards with intent', () => {
    const cardWithIntent: AgentCard = {
      ...mockCard,
      intent: 'followups',
    };

    renderWithRouter(cardWithIntent);

    expect(
      screen.getByText('Click a conversation to see details here, or open it in Gmail to reply.')
    ).toBeInTheDocument();
  });

  it('does not render UX hint when intent is missing', () => {
    const cardWithoutIntent: AgentCard = {
      ...mockCard,
      intent: undefined,
      meta: {},
    };

    renderWithRouter(cardWithoutIntent);

    expect(
      screen.queryByText('Click a conversation to see details here, or open it in Gmail to reply.')
    ).not.toBeInTheDocument();
  });

  // Application tracking integration tests
  describe('Application tracking', () => {
    const renderWithRouter = (card: AgentCard) => {
      return render(
        <MemoryRouter>
          <ThreadListCard card={card} />
        </MemoryRouter>
      );
    };

    it('shows "Create application" button for followups intent when not linked', () => {
      const followupsCard: AgentCard = {
        ...mockCard,
        meta: { intent: 'followups' },
      };

      renderWithRouter(followupsCard);

      const createButtons = screen.getAllByTestId('thread-action-create');
      expect(createButtons.length).toBeGreaterThan(0);
      expect(createButtons[0]).toHaveTextContent('Create application');
    });

    it('shows "Create application" button for interviews intent when not linked', () => {
      const interviewsCard: AgentCard = {
        ...mockCard,
        meta: { intent: 'interviews' },
        threads: mockThreads,
      };

      renderWithRouter(interviewsCard);

      const createButtons = screen.getAllByTestId('thread-action-create');
      expect(createButtons.length).toBeGreaterThan(0);
    });

    it('does not show application buttons for other intents', () => {
      const billsCard: AgentCard = {
        ...mockCard,
        meta: { intent: 'bills' },
      };

      renderWithRouter(billsCard);

      expect(screen.queryByTestId('thread-action-create')).not.toBeInTheDocument();
      expect(screen.queryByTestId('thread-action-open-tracker')).not.toBeInTheDocument();
    });

    it('shows "Open in Tracker" button when thread is linked to application', () => {
      const linkedThreads: MailThreadSummary[] = [
        {
          ...mockThreads[0],
          applicationId: 42,
          applicationStatus: 'active',
        },
      ];

      const linkedCard: AgentCard = {
        ...mockCard,
        threads: linkedThreads,
      };

      renderWithRouter(linkedCard);

      const openButton = screen.getByTestId('thread-action-open-tracker');
      expect(openButton).toBeInTheDocument();
      expect(openButton).toHaveTextContent('Open in Tracker');
      expect(openButton).toHaveAttribute('data-application-id', '42');
    });

    it('calls createApplicationFromEmail when Create application is clicked', async () => {
      const mockCreate = vi.spyOn(api, 'createApplicationFromEmail').mockResolvedValue({
        application_id: 123,
        linked_email_id: 1,
      });

      renderWithRouter(mockCard);

      const createButton = screen.getAllByTestId('thread-action-create')[0];
      fireEvent.click(createButton);

      await waitFor(() => {
        expect(mockCreate).toHaveBeenCalled();
      });
    });

    it('updates button to "Open in Tracker" after successful creation', async () => {
      vi.spyOn(api, 'createApplicationFromEmail').mockResolvedValue({
        application_id: 999,
        linked_email_id: 1,
      });

      renderWithRouter(mockCard);

      const createButton = screen.getAllByTestId('thread-action-create')[0];
      fireEvent.click(createButton);

      await waitFor(() => {
        const openButton = screen.getByTestId('thread-action-open-tracker');
        expect(openButton).toBeInTheDocument();
        expect(openButton).toHaveAttribute('data-application-id', '999');
      });
    });

    it('shows toast error when application creation fails', async () => {
      const { toast } = await import('sonner');
      vi.spyOn(api, 'createApplicationFromEmail').mockRejectedValue(
        new Error('Failed to create')
      );

      renderWithRouter(mockCard);

      const createButton = screen.getAllByTestId('thread-action-create')[0];
      fireEvent.click(createButton);

      await waitFor(() => {
        expect(toast.error).toHaveBeenCalledWith('Failed to create application');
      });
    });
  });
});
