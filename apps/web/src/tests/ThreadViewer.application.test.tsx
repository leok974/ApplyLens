/**
 * Tests for ThreadViewer component - Application tracking features
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { ThreadViewer } from '@/components/mail/ThreadViewer';
import type { MailThreadSummary } from '@/lib/mailThreads';

// Mock fetch
global.fetch = vi.fn(() =>
  Promise.resolve({
    ok: true,
    json: () => Promise.resolve({
      threadId: 'thread-1',
      subject: 'Test Thread',
      from: 'alice@example.com',
      messages: [],
    }),
  } as Response)
);

describe('ThreadViewer - Application tracking', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const renderWithRouter = (props: any) => {
    return render(
      <MemoryRouter>
        <ThreadViewer {...props} />
      </MemoryRouter>
    );
  };

  it('shows "Application linked" badge when thread has applicationId', () => {
    const linkedSummary: MailThreadSummary = {
      threadId: 'thread-1',
      subject: 'Interview Follow-up',
      from: 'recruiter@example.com',
      lastMessageAt: '2025-01-15T10:00:00Z',
      labels: ['INBOX'],
      snippet: 'Following up on your application...',
      gmailUrl: 'https://mail.google.com/mail/u/0/#inbox/thread-1',
      applicationId: 42,
      applicationStatus: 'active',
    };

    renderWithRouter({
      threadId: 'thread-1',
      summary: linkedSummary,
    });

    const badge = screen.getByTestId('thread-viewer-app-badge');
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveTextContent('Application linked');
  });

  it('does not show application badge when thread has no applicationId', () => {
    const unlinkedSummary: MailThreadSummary = {
      threadId: 'thread-2',
      subject: 'Regular Email',
      from: 'someone@example.com',
      lastMessageAt: '2025-01-15T10:00:00Z',
      labels: ['INBOX'],
      snippet: 'Just a normal email...',
      gmailUrl: 'https://mail.google.com/mail/u/0/#inbox/thread-2',
    };

    renderWithRouter({
      threadId: 'thread-2',
      summary: unlinkedSummary,
    });

    const badge = screen.queryByTestId('thread-viewer-app-badge');
    expect(badge).not.toBeInTheDocument();
  });

  it('shows "Open in Tracker" button when thread is linked', () => {
    const linkedSummary: MailThreadSummary = {
      threadId: 'thread-1',
      subject: 'Interview Follow-up',
      from: 'recruiter@example.com',
      lastMessageAt: '2025-01-15T10:00:00Z',
      labels: ['INBOX'],
      snippet: 'Following up...',
      gmailUrl: 'https://mail.google.com/mail/u/0/#inbox/thread-1',
      applicationId: 123,
    };

    renderWithRouter({
      threadId: 'thread-1',
      summary: linkedSummary,
    });

    const button = screen.getByTestId('thread-viewer-open-tracker');
    expect(button).toBeInTheDocument();
    expect(button).toHaveTextContent('Open in Tracker');
  });

  it('shows "Create application" button when thread is not linked and handler provided', () => {
    const unlinkedSummary: MailThreadSummary = {
      threadId: 'thread-2',
      subject: 'Interview Invitation',
      from: 'recruiter@example.com',
      lastMessageAt: '2025-01-15T10:00:00Z',
      labels: ['INBOX'],
      snippet: 'We would like to invite you...',
      gmailUrl: 'https://mail.google.com/mail/u/0/#inbox/thread-2',
    };

    const mockHandler = vi.fn();

    renderWithRouter({
      threadId: 'thread-2',
      summary: unlinkedSummary,
      onCreateApplication: mockHandler,
    });

    const button = screen.getByTestId('thread-viewer-create-app');
    expect(button).toBeInTheDocument();
    expect(button).toHaveTextContent('Create application');
  });

  it('does not show "Create application" button when no handler provided', () => {
    const unlinkedSummary: MailThreadSummary = {
      threadId: 'thread-3',
      subject: 'Regular Email',
      from: 'someone@example.com',
      lastMessageAt: '2025-01-15T10:00:00Z',
      labels: ['INBOX'],
      snippet: 'Just a message...',
      gmailUrl: 'https://mail.google.com/mail/u/0/#inbox/thread-3',
    };

    renderWithRouter({
      threadId: 'thread-3',
      summary: unlinkedSummary,
    });

    const button = screen.queryByTestId('thread-viewer-create-app');
    expect(button).not.toBeInTheDocument();
  });

  it('calls onCreateApplication when "Create application" button is clicked', () => {
    const unlinkedSummary: MailThreadSummary = {
      threadId: 'thread-4',
      subject: 'Job Opportunity',
      from: 'hr@company.com',
      lastMessageAt: '2025-01-15T10:00:00Z',
      labels: ['INBOX'],
      snippet: 'We have an opening...',
      gmailUrl: 'https://mail.google.com/mail/u/0/#inbox/thread-4',
    };

    const mockHandler = vi.fn();

    renderWithRouter({
      threadId: 'thread-4',
      summary: unlinkedSummary,
      onCreateApplication: mockHandler,
    });

    const button = screen.getByTestId('thread-viewer-create-app');
    fireEvent.click(button);

    expect(mockHandler).toHaveBeenCalledWith('thread-4');
  });

  it('shows both application badge and Open in Tracker button when linked', () => {
    const linkedSummary: MailThreadSummary = {
      threadId: 'thread-5',
      subject: 'Follow-up Interview',
      from: 'recruiter@company.com',
      lastMessageAt: '2025-01-15T10:00:00Z',
      labels: ['INBOX', 'IMPORTANT'],
      snippet: 'Looking forward to our chat...',
      gmailUrl: 'https://mail.google.com/mail/u/0/#inbox/thread-5',
      applicationId: 999,
      applicationStatus: 'phone_screen',
    };

    renderWithRouter({
      threadId: 'thread-5',
      summary: linkedSummary,
    });

    // Should show both badge and button
    expect(screen.getByTestId('thread-viewer-app-badge')).toBeInTheDocument();
    expect(screen.getByTestId('thread-viewer-open-tracker')).toBeInTheDocument();

    // Should NOT show create button
    expect(screen.queryByTestId('thread-viewer-create-app')).not.toBeInTheDocument();
  });
});
