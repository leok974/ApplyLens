import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ThreadList } from '@/components/mail/ThreadList';
import type { MailThreadSummary } from '@/lib/mailThreads';

describe('ThreadList - Application Status Badges', () => {
  const baseThread: MailThreadSummary = {
    threadId: 'thread-1',
    subject: 'Re: Software Engineer Position',
    from: 'recruiter@example.com',
    lastMessageAt: new Date().toISOString(),
    labels: [],
    snippet: 'Looking forward to hearing from you',
    gmailUrl: 'https://mail.google.com/mail/u/0/#inbox/thread-1',
  };

  it('should not show status badge when applicationStatus is absent', () => {
    const threads = [baseThread];

    render(
      <ThreadList
        threads={threads}
        selectedId={null}
        onSelect={() => {}}
        intent="followups"
      />
    );

    expect(screen.queryByTestId('thread-app-status-badge')).not.toBeInTheDocument();
  });

  it('should show "Applied" badge with correct styling', () => {
    const threads = [
      {
        ...baseThread,
        applicationId: 123,
        applicationStatus: 'applied',
      },
    ];

    render(
      <ThreadList
        threads={threads}
        selectedId={null}
        onSelect={() => {}}
        intent="followups"
      />
    );

    const badge = screen.getByTestId('thread-app-status-badge');
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveTextContent('Applied');
    expect(badge).toHaveClass('border-slate-400/30');
    expect(badge).toHaveClass('text-slate-400');
  });

  it('should show "Interview" badge with correct styling', () => {
    const threads = [
      {
        ...baseThread,
        applicationId: 456,
        applicationStatus: 'interview',
      },
    ];

    render(
      <ThreadList
        threads={threads}
        selectedId={null}
        onSelect={() => {}}
        intent="interviews"
      />
    );

    const badge = screen.getByTestId('thread-app-status-badge');
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveTextContent('Interview');
    expect(badge).toHaveClass('border-blue-400/30');
    expect(badge).toHaveClass('text-blue-400');
  });

  it('should show "Offer" badge with correct styling', () => {
    const threads = [
      {
        ...baseThread,
        applicationId: 789,
        applicationStatus: 'offer',
      },
    ];

    render(
      <ThreadList
        threads={threads}
        selectedId={null}
        onSelect={() => {}}
        intent="followups"
      />
    );

    const badge = screen.getByTestId('thread-app-status-badge');
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveTextContent('Offer');
    expect(badge).toHaveClass('border-emerald-400/30');
    expect(badge).toHaveClass('text-emerald-400');
  });

  it('should show "Rejected" badge with correct styling', () => {
    const threads = [
      {
        ...baseThread,
        applicationId: 101,
        applicationStatus: 'rejected',
      },
    ];

    render(
      <ThreadList
        threads={threads}
        selectedId={null}
        onSelect={() => {}}
        intent="followups"
      />
    );

    const badge = screen.getByTestId('thread-app-status-badge');
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveTextContent('Rejected');
    expect(badge).toHaveClass('border-red-400/30');
    expect(badge).toHaveClass('text-red-400');
  });

  it('should show "HR Screen" badge with formatted text', () => {
    const threads = [
      {
        ...baseThread,
        applicationId: 202,
        applicationStatus: 'hr_screen',
      },
    ];

    render(
      <ThreadList
        threads={threads}
        selectedId={null}
        onSelect={() => {}}
        intent="followups"
      />
    );

    const badge = screen.getByTestId('thread-app-status-badge');
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveTextContent('HR Screen');
    expect(badge).toHaveClass('border-cyan-400/30');
    expect(badge).toHaveClass('text-cyan-400');
  });

  it('should show "On Hold" badge with formatted text', () => {
    const threads = [
      {
        ...baseThread,
        applicationId: 303,
        applicationStatus: 'on_hold',
      },
    ];

    render(
      <ThreadList
        threads={threads}
        selectedId={null}
        onSelect={() => {}}
        intent="followups"
      />
    );

    const badge = screen.getByTestId('thread-app-status-badge');
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveTextContent('On Hold');
    expect(badge).toHaveClass('border-orange-400/30');
    expect(badge).toHaveClass('text-orange-400');
  });

  it('should show "Ghosted" badge with correct styling', () => {
    const threads = [
      {
        ...baseThread,
        applicationId: 404,
        applicationStatus: 'ghosted',
      },
    ];

    render(
      <ThreadList
        threads={threads}
        selectedId={null}
        onSelect={() => {}}
        intent="followups"
      />
    );

    const badge = screen.getByTestId('thread-app-status-badge');
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveTextContent('Ghosted');
    expect(badge).toHaveClass('border-slate-500/30');
    expect(badge).toHaveClass('text-slate-500');
  });

  it('should show both Follow-up and status badges together', () => {
    const threads = [
      {
        ...baseThread,
        applicationId: 999,
        applicationStatus: 'interview',
      },
    ];

    render(
      <ThreadList
        threads={threads}
        selectedId={null}
        onSelect={() => {}}
        intent="followups"
      />
    );

    // Both badges should be present
    expect(screen.getByText('Follow-up')).toBeInTheDocument();
    expect(screen.getByTestId('thread-app-status-badge')).toBeInTheDocument();
    expect(screen.getByTestId('thread-app-status-badge')).toHaveTextContent('Interview');
  });

  it('should handle multiple threads with different statuses', () => {
    const threads = [
      {
        ...baseThread,
        threadId: 'thread-1',
        applicationId: 1,
        applicationStatus: 'applied',
      },
      {
        ...baseThread,
        threadId: 'thread-2',
        applicationId: 2,
        applicationStatus: 'interview',
      },
      {
        ...baseThread,
        threadId: 'thread-3',
        applicationId: 3,
        applicationStatus: 'offer',
      },
    ];

    render(
      <ThreadList
        threads={threads}
        selectedId={null}
        onSelect={() => {}}
        intent="followups"
      />
    );

    const badges = screen.getAllByTestId('thread-app-status-badge');
    expect(badges).toHaveLength(3);
    expect(badges[0]).toHaveTextContent('Applied');
    expect(badges[1]).toHaveTextContent('Interview');
    expect(badges[2]).toHaveTextContent('Offer');
  });
});
