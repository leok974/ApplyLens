/**
 * Tests for ThreadViewer component - Application tracking features
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter, useNavigate } from 'react-router-dom';
import { ThreadViewer } from '@/components/mail/ThreadViewer';
import type { MailThreadSummary } from '@/lib/mailThreads';

// Mock useNavigate
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

// Mock fetch for thread details
global.fetch = vi.fn((url) => {
  // Handle metrics endpoint
  if (typeof url === 'string' && url.includes('/metrics/thread-to-tracker-click')) {
    return Promise.resolve({
      ok: true,
      json: () => Promise.resolve({ ok: true }),
    } as Response);
  }

  // Handle thread details endpoint
  return Promise.resolve({
    ok: true,
    json: () => Promise.resolve({
      threadId: 'thread-1',
      subject: 'Test Thread',
      from: 'alice@example.com',
      messages: [],
    }),
  } as Response);
});

describe('ThreadViewer - Application tracking', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockNavigate.mockClear();
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

  it('navigates to /tracker?appId=<id> when "Open in Tracker" is clicked', () => {
    const linkedSummary: MailThreadSummary = {
      threadId: 'thread-6',
      subject: 'Application Status',
      from: 'hiring@company.com',
      lastMessageAt: '2025-01-15T10:00:00Z',
      labels: ['INBOX'],
      snippet: 'Update on your application...',
      gmailUrl: 'https://mail.google.com/mail/u/0/#inbox/thread-6',
      applicationId: 456,
    };

    renderWithRouter({
      threadId: 'thread-6',
      summary: linkedSummary,
    });

    const button = screen.getByTestId('thread-viewer-open-tracker');
    fireEvent.click(button);

    expect(mockNavigate).toHaveBeenCalledWith('/tracker?appId=456');
  });

  it('navigates with correct appId for different applications', () => {
    const linkedSummary: MailThreadSummary = {
      threadId: 'thread-7',
      subject: 'Interview Confirmation',
      from: 'recruiter@tech.com',
      lastMessageAt: '2025-01-15T10:00:00Z',
      labels: ['INBOX'],
      snippet: 'Confirming our interview...',
      gmailUrl: 'https://mail.google.com/mail/u/0/#inbox/thread-7',
      applicationId: 789,
    };

    renderWithRouter({
      threadId: 'thread-7',
      summary: linkedSummary,
    });

    const button = screen.getByTestId('thread-viewer-open-tracker');
    fireEvent.click(button);

    expect(mockNavigate).toHaveBeenCalledWith('/tracker?appId=789');
  });

  describe('Metrics tracking', () => {
    beforeEach(() => {
      vi.clearAllMocks();
    });

    it('calls metrics endpoint when "Open in Tracker" is clicked with intent', async () => {
      const linkedSummary: MailThreadSummary = {
        threadId: 'thread-metrics-1',
        subject: 'Follow-up Email',
        from: 'recruiter@company.com',
        lastMessageAt: '2025-01-15T10:00:00Z',
        labels: ['INBOX'],
        snippet: 'Following up...',
        gmailUrl: 'https://mail.google.com/mail/u/0/#inbox/thread-metrics-1',
        applicationId: 123,
      };

      renderWithRouter({
        threadId: 'thread-metrics-1',
        summary: linkedSummary,
        intent: 'followups',
      });

      const button = screen.getByTestId('thread-viewer-open-tracker');
      fireEvent.click(button);

      // Should call metrics endpoint with POST method and correct body
      expect(global.fetch).toHaveBeenCalledWith(
        '/metrics/thread-to-tracker-click',
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            application_id: 123,
            intent: 'followups',
          }),
        }
      );

      // Should also navigate
      expect(mockNavigate).toHaveBeenCalledWith('/tracker?appId=123');
    });

    it('calls metrics endpoint without intent when intent is not provided', async () => {
      const linkedSummary: MailThreadSummary = {
        threadId: 'thread-metrics-2',
        subject: 'Application Update',
        from: 'hr@company.com',
        lastMessageAt: '2025-01-15T10:00:00Z',
        labels: ['INBOX'],
        snippet: 'Update on your application...',
        gmailUrl: 'https://mail.google.com/mail/u/0/#inbox/thread-metrics-2',
        applicationId: 456,
      };

      renderWithRouter({
        threadId: 'thread-metrics-2',
        summary: linkedSummary,
        // No intent prop
      });

      const button = screen.getByTestId('thread-viewer-open-tracker');
      fireEvent.click(button);

      // Should call metrics endpoint with POST method and undefined intent
      expect(global.fetch).toHaveBeenCalledWith(
        '/metrics/thread-to-tracker-click',
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            application_id: 456,
            intent: undefined,
          }),
        }
      );

      expect(mockNavigate).toHaveBeenCalledWith('/tracker?appId=456');
    });

    it('navigates even if metrics endpoint fails', async () => {
      // Make fetch fail for metrics endpoint
      const mockFetch = vi.fn((url) => {
        if (typeof url === 'string' && url.includes('/metrics/thread-to-tracker-click')) {
          return Promise.reject(new Error('Network error'));
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ threadId: 'thread-metrics-3', messages: [] }),
        } as Response);
      });
      global.fetch = mockFetch;

      const linkedSummary: MailThreadSummary = {
        threadId: 'thread-metrics-3',
        subject: 'Interview Schedule',
        from: 'recruiter@tech.com',
        lastMessageAt: '2025-01-15T10:00:00Z',
        labels: ['INBOX'],
        snippet: 'Interview scheduled...',
        gmailUrl: 'https://mail.google.com/mail/u/0/#inbox/thread-metrics-3',
        applicationId: 789,
      };

      renderWithRouter({
        threadId: 'thread-metrics-3',
        summary: linkedSummary,
        intent: 'interviews',
      });

      const button = screen.getByTestId('thread-viewer-open-tracker');
      fireEvent.click(button);

      // Metrics endpoint was called
      expect(mockFetch).toHaveBeenCalledWith(
        '/metrics/thread-to-tracker-click',
        expect.any(Object)
      );

      // Navigation still happens despite fetch failure
      expect(mockNavigate).toHaveBeenCalledWith('/tracker?appId=789');
    });

    it('calls metrics with correct application_id for different intents', async () => {
      const billsSummary: MailThreadSummary = {
        threadId: 'thread-bills',
        subject: 'Invoice Due',
        from: 'billing@service.com',
        lastMessageAt: '2025-01-15T10:00:00Z',
        labels: ['INBOX'],
        snippet: 'Your invoice is due...',
        gmailUrl: 'https://mail.google.com/mail/u/0/#inbox/thread-bills',
        applicationId: 999,
      };

      renderWithRouter({
        threadId: 'thread-bills',
        summary: billsSummary,
        intent: 'bills',
      });

      const button = screen.getByTestId('thread-viewer-open-tracker');
      fireEvent.click(button);

      expect(global.fetch).toHaveBeenCalledWith(
        '/metrics/thread-to-tracker-click',
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            application_id: 999,
            intent: 'bills',
          }),
        }
      );
    });

    it('does not call metrics endpoint when Create Application button is clicked', async () => {
      const unlinkedSummary: MailThreadSummary = {
        threadId: 'thread-no-metrics',
        subject: 'Job Opportunity',
        from: 'hr@startup.com',
        lastMessageAt: '2025-01-15T10:00:00Z',
        labels: ['INBOX'],
        snippet: 'We have an opening...',
        gmailUrl: 'https://mail.google.com/mail/u/0/#inbox/thread-no-metrics',
      };

      const mockHandler = vi.fn();

      renderWithRouter({
        threadId: 'thread-no-metrics',
        summary: unlinkedSummary,
        onCreateApplication: mockHandler,
        intent: 'followups',
      });

      const button = screen.getByTestId('thread-viewer-create-app');
      fireEvent.click(button);

      // Metrics endpoint should NOT be called
      expect(global.fetch).not.toHaveBeenCalledWith(
        '/metrics/thread-to-tracker-click',
        expect.any(Object)
      );

      // But handler should still be called
      expect(mockHandler).toHaveBeenCalledWith('thread-no-metrics');
    });
  });
});
