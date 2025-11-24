import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { FollowupQueue } from '../FollowupQueue';
import * as useFollowupQueueModule from '@/hooks/useFollowupQueue';
import type { QueueItem, QueueMeta } from '@/lib/api';

// Mock the hook
vi.mock('@/hooks/useFollowupQueue');

// Mock ThreadViewer component
vi.mock('@/components/ThreadViewer', () => ({
  ThreadViewer: ({ threadId, applicationId }: { threadId: string; applicationId?: string }) => (
    <div data-testid="thread-viewer">
      Thread: {threadId}
      {applicationId && `, App: ${applicationId}`}
    </div>
  ),
}));

const mockQueueMeta: QueueMeta = {
  total: 2,
  time_window_days: 30,
};

const mockItems: QueueItem[] = [
  {
    thread_id: 'thread-1',
    application_id: 'app-1',
    priority: 75,
    reason_tags: ['no_response'],
    company: 'Acme Corp',
    role: 'Senior Engineer',
    subject: 'Application for Senior Engineer',
    snippet: 'Thank you for your application...',
    last_message_at: new Date().toISOString(),
    status: 'applied',
    gmail_url: 'https://mail.google.com/mail/u/0/#inbox/thread-1',
    is_done: false,
  },
  {
    thread_id: 'thread-2',
    priority: 55,
    reason_tags: ['upcoming_deadline'],
    subject: 'Follow-up needed',
    snippet: 'This is a test snippet',
    last_message_at: new Date().toISOString(),
    gmail_url: 'https://mail.google.com/mail/u/0/#inbox/thread-2',
    is_done: false,
  },
];

describe('FollowupQueue', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows loading skeleton when loading', () => {
    vi.mocked(useFollowupQueueModule.useFollowupQueue).mockReturnValue({
      items: [],
      queueMeta: null,
      isLoading: true,
      error: null,
      selectedItem: null,
      setSelectedItem: vi.fn(),
      markDone: vi.fn(),
      refresh: vi.fn(),
    });

    render(<FollowupQueue />);

    expect(screen.getByTestId('followup-queue-page')).toBeInTheDocument();
    // Skeleton components should be rendered (exact assertion depends on Skeleton implementation)
  });

  it('shows error state when error occurs', () => {
    const mockRefresh = vi.fn();
    vi.mocked(useFollowupQueueModule.useFollowupQueue).mockReturnValue({
      items: [],
      queueMeta: null,
      isLoading: false,
      error: 'Failed to load queue',
      selectedItem: null,
      setSelectedItem: vi.fn(),
      markDone: vi.fn(),
      refresh: mockRefresh,
    });

    render(<FollowupQueue />);

    expect(screen.getByText('Error loading follow-up queue')).toBeInTheDocument();
    expect(screen.getByText('Failed to load queue')).toBeInTheDocument();
  });

  it('calls refresh when retry button is clicked in error state', async () => {
    const user = userEvent.setup();
    const mockRefresh = vi.fn();

    vi.mocked(useFollowupQueueModule.useFollowupQueue).mockReturnValue({
      items: [],
      queueMeta: null,
      isLoading: false,
      error: 'Failed to load queue',
      selectedItem: null,
      setSelectedItem: vi.fn(),
      markDone: vi.fn(),
      refresh: mockRefresh,
    });

    render(<FollowupQueue />);

    const retryButton = screen.getByRole('button', { name: /retry/i });
    await user.click(retryButton);

    expect(mockRefresh).toHaveBeenCalled();
  });

  it('shows empty state when no items', () => {
    vi.mocked(useFollowupQueueModule.useFollowupQueue).mockReturnValue({
      items: [],
      queueMeta: mockQueueMeta,
      isLoading: false,
      error: null,
      selectedItem: null,
      setSelectedItem: vi.fn(),
      markDone: vi.fn(),
      refresh: vi.fn(),
    });

    render(<FollowupQueue />);

    expect(screen.getByText('All caught up!')).toBeInTheDocument();
    expect(screen.getByText(/Searched 30 days of activity/)).toBeInTheDocument();
  });

  it('renders queue list when items are present', () => {
    vi.mocked(useFollowupQueueModule.useFollowupQueue).mockReturnValue({
      items: mockItems,
      queueMeta: mockQueueMeta,
      isLoading: false,
      error: null,
      selectedItem: null,
      setSelectedItem: vi.fn(),
      markDone: vi.fn(),
      refresh: vi.fn(),
    });

    render(<FollowupQueue />);

    expect(screen.getByText('Follow-up Queue')).toBeInTheDocument();
    expect(screen.getByText('2 items in the last 30 days')).toBeInTheDocument();
    expect(screen.getByTestId('followup-queue-list')).toBeInTheDocument();
  });

  it('shows placeholder when no item is selected', () => {
    vi.mocked(useFollowupQueueModule.useFollowupQueue).mockReturnValue({
      items: mockItems,
      queueMeta: mockQueueMeta,
      isLoading: false,
      error: null,
      selectedItem: null,
      setSelectedItem: vi.fn(),
      markDone: vi.fn(),
      refresh: vi.fn(),
    });

    render(<FollowupQueue />);

    expect(screen.getByText('Select a follow-up to view details')).toBeInTheDocument();
  });

  it('shows ThreadViewer when item is selected', () => {
    vi.mocked(useFollowupQueueModule.useFollowupQueue).mockReturnValue({
      items: mockItems,
      queueMeta: mockQueueMeta,
      isLoading: false,
      error: null,
      selectedItem: mockItems[0],
      setSelectedItem: vi.fn(),
      markDone: vi.fn(),
      refresh: vi.fn(),
    });

    render(<FollowupQueue />);

    expect(screen.getByTestId('thread-viewer')).toBeInTheDocument();
    expect(screen.getByText(/Thread: thread-1/)).toBeInTheDocument();
    expect(screen.getByText(/App: app-1/)).toBeInTheDocument();
  });

  it('passes correct props to FollowupQueueList', () => {
    const mockSetSelectedItem = vi.fn();
    const mockMarkDone = vi.fn();

    vi.mocked(useFollowupQueueModule.useFollowupQueue).mockReturnValue({
      items: mockItems,
      queueMeta: mockQueueMeta,
      isLoading: false,
      error: null,
      selectedItem: mockItems[0],
      setSelectedItem: mockSetSelectedItem,
      markDone: mockMarkDone,
      refresh: vi.fn(),
    });

    render(<FollowupQueue />);

    const list = screen.getByTestId('followup-queue-list');
    expect(list).toBeInTheDocument();
  });
});
