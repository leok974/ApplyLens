/**
 * Tests for ThreadViewer component
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { ThreadViewer } from '@/components/mail/ThreadViewer';
import type { MailThreadSummary, MailThreadDetail } from '@/lib/mailThreads';

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
const mockFetch = vi.fn();
global.fetch = mockFetch;

const mockSummary: MailThreadSummary = {
  threadId: 'thread-123',
  subject: 'Test Thread Subject',
  from: 'alice@example.com',
  to: 'me@example.com',
  lastMessageAt: '2025-01-15T10:30:00Z',
  unreadCount: 2,
  riskScore: 0.3,
  labels: ['INBOX', 'IMPORTANT'],
  snippet: 'This is the thread preview...',
  gmailUrl: 'https://mail.google.com/mail/u/0/#inbox/thread-123',
};

const mockDetail: MailThreadDetail = {
  ...mockSummary,
  messages: [
    {
      id: 'msg-3',
      sentAt: '2025-01-15T10:30:00Z',
      from: 'alice@example.com',
      to: 'me@example.com',
      subject: 'Re: Test Thread Subject',
      bodyText: 'Most recent message body',
      isImportant: false,
    },
    {
      id: 'msg-2',
      sentAt: '2025-01-14T09:00:00Z',
      from: 'me@example.com',
      to: 'alice@example.com',
      subject: 'Re: Test Thread Subject',
      bodyText: 'Second message body',
      isImportant: false,
    },
    {
      id: 'msg-1',
      sentAt: '2025-01-13T08:00:00Z',
      from: 'alice@example.com',
      to: 'me@example.com',
      subject: 'Test Thread Subject',
      bodyText: 'First message body',
      isImportant: true,
    },
  ],
};

describe('ThreadViewer', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Set default mock to return valid detail
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => mockDetail,
    } as Response);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('shows "Select a thread" message when no thread selected', () => {
    render(<ThreadViewer threadId={null} summary={null} />);

    expect(screen.getByText('Select a thread to view details')).toBeInTheDocument();
  });

  it('renders thread header info', () => {
    render(<ThreadViewer threadId="thread-123" summary={mockSummary} />);

    expect(screen.getByText('Test Thread Subject')).toBeInTheDocument();
    expect(screen.getByText(/From:/)).toBeInTheDocument();
    expect(screen.getByText(/alice@example.com/)).toBeInTheDocument();
    expect(screen.getByText(/To:/)).toBeInTheDocument();
    expect(screen.getByText(/me@example.com/)).toBeInTheDocument();
  });

  it('renders labels', () => {
    render(<ThreadViewer threadId="thread-123" summary={mockSummary} />);

    expect(screen.getByText('INBOX')).toBeInTheDocument();
    expect(screen.getByText('IMPORTANT')).toBeInTheDocument();
  });

  it('shows risk badge for risky threads', () => {
    const riskySummary: MailThreadSummary = {
      ...mockSummary,
      riskScore: 0.85,
    };

    render(<ThreadViewer threadId="thread-123" summary={riskySummary} />);

    expect(screen.getByText('Risky')).toBeInTheDocument();
  });

  it('fetches and displays thread detail on mount', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockDetail,
    });

    render(<ThreadViewer threadId="thread-123" summary={mockSummary} />);

    // Should show loading skeleton initially
    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith('/api/threads/thread-123');
    });

    // Wait for messages to appear
    await waitFor(() => {
      expect(screen.getByText('Most recent message body')).toBeInTheDocument();
    });

    // Check that all messages are rendered
    expect(screen.getByText('Second message body')).toBeInTheDocument();
    expect(screen.getByText('First message body')).toBeInTheDocument();
  });

  it('shows error message on fetch failure', async () => {
    mockFetch.mockRejectedValueOnce(new Error('Network error'));

    render(<ThreadViewer threadId="thread-123" summary={mockSummary} />);

    await waitFor(() => {
      expect(screen.getByText(/Network error/)).toBeInTheDocument();
    });
  });

  it('renders action buttons', () => {
    render(<ThreadViewer threadId="thread-123" summary={mockSummary} />);

    expect(screen.getByText('Open in Gmail')).toBeInTheDocument();
    expect(screen.getByText('Mark Handled')).toBeInTheDocument();
    expect(screen.getByText('Copy Summary')).toBeInTheDocument();
  });

  it('shows "Mark as Safe" button for risky threads', () => {
    const riskySummary: MailThreadSummary = {
      ...mockSummary,
      riskScore: 0.85,
    };

    render(<ThreadViewer threadId="thread-123" summary={riskySummary} />);

    expect(screen.getByText('Mark as Safe')).toBeInTheDocument();
  });

  it('does not show "Mark as Safe" for non-risky threads', () => {
    render(<ThreadViewer threadId="thread-123" summary={mockSummary} />);

    expect(screen.queryByText('Mark as Safe')).not.toBeInTheDocument();
  });

  it('renders message cards with expand/collapse', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockDetail,
    });

    render(<ThreadViewer threadId="thread-123" summary={mockSummary} />);

    await waitFor(() => {
      expect(screen.getAllByTestId('message-card').length).toBe(3);
    });

    // Check for expand/collapse buttons
    const expandButtons = screen.getAllByText('Collapse');
    expect(expandButtons.length).toBeGreaterThan(0); // First message should be expanded by default
  });

  it('shows loading skeleton while fetching', async () => {
    mockFetch.mockImplementation(
      () =>
        new Promise((resolve) =>
          setTimeout(
            () =>
              resolve({
                ok: true,
                json: async () => mockDetail,
              }),
            100
          )
        )
    );

    render(<ThreadViewer threadId="thread-123" summary={mockSummary} />);

    // Loading state should be visible
    expect(screen.getByText('Message Timeline')).toBeInTheDocument();
  });

  it('refetches when threadId changes', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => mockDetail,
    });

    const { rerender } = render(<ThreadViewer threadId="thread-123" summary={mockSummary} />);

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith('/api/threads/thread-123');
    });

    // Change threadId
    const newSummary = { ...mockSummary, threadId: 'thread-456' };
    rerender(<ThreadViewer threadId="thread-456" summary={newSummary} />);

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith('/api/threads/thread-456');
    });

    expect(mockFetch).toHaveBeenCalledTimes(2);
  });
});
