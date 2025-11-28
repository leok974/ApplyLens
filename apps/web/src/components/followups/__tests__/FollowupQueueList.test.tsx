import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { FollowupQueueList } from '../FollowupQueueList';
import type { QueueItem } from '@/lib/api';

const mockItems: QueueItem[] = [
  {
    thread_id: 'thread-1',
    application_id: 1,
    priority: 'medium',
    reason_tags: ['no_response'],
    company: 'Acme Corp',
    role: 'Senior Engineer',
    subject: 'Application for Senior Engineer',
    snippet: 'Thank you for your application...',
    last_message_at: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString(), // 2 days ago
    status: 'applied',
    gmail_url: 'https://mail.google.com/mail/u/0/#inbox/thread-1',
    is_done: false,
  },
  {
    thread_id: 'thread-2',
    priority: 'low',
    reason_tags: ['upcoming_deadline'],
    subject: 'Follow-up needed',
    snippet: 'This is a test snippet',
    last_message_at: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000).toISOString(), // 5 days ago
    gmail_url: 'https://mail.google.com/mail/u/0/#inbox/thread-2',
    is_done: false,
  },
  {
    thread_id: 'thread-3',
    application_id: 3,
    priority: 'high',
    reason_tags: ['interview_scheduled'],
    company: 'Beta Inc',
    role: 'Product Manager',
    subject: 'Interview scheduled',
    snippet: 'Looking forward to our chat',
    last_message_at: new Date().toISOString(), // Today
    status: 'interview',
    gmail_url: 'https://mail.google.com/mail/u/0/#inbox/thread-3',
    is_done: true,
  },
];

describe('FollowupQueueList', () => {
  it('renders all items', () => {
    const onSelect = vi.fn();
    const onToggleDone = vi.fn();

    render(
      <FollowupQueueList
        items={mockItems}
        selectedItem={null}
        onSelect={onSelect}
        onToggleDone={onToggleDone}
      />
    );

    const rows = screen.getAllByTestId('followup-row');
    expect(rows).toHaveLength(3);
  });

  it('displays company and role when available', () => {
    const onSelect = vi.fn();
    const onToggleDone = vi.fn();

    render(
      <FollowupQueueList
        items={[mockItems[0]]}
        selectedItem={null}
        onSelect={onSelect}
        onToggleDone={onToggleDone}
      />
    );

    expect(screen.getByText('Acme Corp - Senior Engineer')).toBeInTheDocument();
  });

  it('falls back to subject when company/role not available', () => {
    const onSelect = vi.fn();
    const onToggleDone = vi.fn();

    render(
      <FollowupQueueList
        items={[mockItems[1]]}
        selectedItem={null}
        onSelect={onSelect}
        onToggleDone={onToggleDone}
      />
    );

    expect(screen.getByText('Follow-up needed')).toBeInTheDocument();
  });

  it('shows status badge when status is present', () => {
    const onSelect = vi.fn();
    const onToggleDone = vi.fn();

    render(
      <FollowupQueueList
        items={[mockItems[0]]}
        selectedItem={null}
        onSelect={onSelect}
        onToggleDone={onToggleDone}
      />
    );

    expect(screen.getByText('Applied')).toBeInTheDocument();
  });

  it('shows priority badges with correct labels', () => {
    const onSelect = vi.fn();
    const onToggleDone = vi.fn();

    render(
      <FollowupQueueList
        items={mockItems}
        selectedItem={null}
        onSelect={onSelect}
        onToggleDone={onToggleDone}
      />
    );

    expect(screen.getByText('High')).toBeInTheDocument(); // priority 'high'
    expect(screen.getByText('Medium')).toBeInTheDocument(); // priority 'medium'
    expect(screen.getByText('Low')).toBeInTheDocument(); // priority 'low'
  });

  it('shows age chips', () => {
    const onSelect = vi.fn();
    const onToggleDone = vi.fn();

    render(
      <FollowupQueueList
        items={mockItems}
        selectedItem={null}
        onSelect={onSelect}
        onToggleDone={onToggleDone}
      />
    );

    expect(screen.getByText('Today')).toBeInTheDocument();
    expect(screen.getByText('2d ago')).toBeInTheDocument();
    expect(screen.getByText('5d ago')).toBeInTheDocument();
  });

  it('calls onSelect when item is clicked', async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    const onToggleDone = vi.fn();

    render(
      <FollowupQueueList
        items={[mockItems[0]]}
        selectedItem={null}
        onSelect={onSelect}
        onToggleDone={onToggleDone}
      />
    );

    const row = screen.getByTestId('followup-row');
    await user.click(row);

    expect(onSelect).toHaveBeenCalledWith(mockItems[0]);
  });

  it('calls onToggleDone when done button is clicked', async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    const onToggleDone = vi.fn();

    render(
      <FollowupQueueList
        items={[mockItems[0]]}
        selectedItem={null}
        onSelect={onSelect}
        onToggleDone={onToggleDone}
      />
    );

    const doneButton = screen.getByTestId('toggle-done-button');
    await user.click(doneButton);

    expect(onToggleDone).toHaveBeenCalledWith(mockItems[0], true);
    expect(onSelect).not.toHaveBeenCalled(); // Should not trigger row selection
  });

  it('shows checked icon for done items', () => {
    const onSelect = vi.fn();
    const onToggleDone = vi.fn();

    render(
      <FollowupQueueList
        items={[mockItems[2]]} // is_done = true
        selectedItem={null}
        onSelect={onSelect}
        onToggleDone={onToggleDone}
      />
    );

    // Check for opacity and line-through classes on done item
    const row = screen.getByTestId('followup-row');
    expect(row).toHaveClass('opacity-50');
    expect(row).toHaveClass('line-through');
  });

  it('highlights selected item', () => {
    const onSelect = vi.fn();
    const onToggleDone = vi.fn();

    render(
      <FollowupQueueList
        items={mockItems}
        selectedItem={mockItems[0]}
        onSelect={onSelect}
        onToggleDone={onToggleDone}
      />
    );

    const selectedRow = screen.getByTestId('followup-queue-list').querySelector('[data-thread-id="thread-1"]');
    expect(selectedRow).toHaveClass('bg-zinc-800');
  });
});
