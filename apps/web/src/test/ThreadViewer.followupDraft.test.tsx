/**
 * Tests for follow-up draft generation in ThreadViewer
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ThreadViewer } from '@/components/mail/ThreadViewer';
import type { MailThreadSummary } from '@/lib/mailThreads';
import * as api from '@/lib/api';

// Mock the API module
vi.mock('@/lib/api', () => ({
  generateFollowupDraft: vi.fn(),
}));

// Mock react-router-dom
vi.mock('react-router-dom', () => ({
  useNavigate: () => vi.fn(),
}));

// Mock sonner
vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

// Mock analytics
vi.mock('@/lib/analytics', () => ({
  track: vi.fn(),
}));

describe('ThreadViewer - Follow-up Draft', () => {
  const mockThreadSummary: MailThreadSummary = {
    threadId: 'thread-123',
    from: 'recruiter@company.com',
    to: 'me@example.com',
    subject: 'Software Engineer Opportunity',
    snippet: 'We would like to discuss the Software Engineer position...',
    lastMessageAt: '2024-01-15T10:00:00Z',
    labels: ['recruiter'],
    gmailUrl: 'https://mail.google.com/mail/u/0/#inbox/thread-123',
    riskScore: 0.1,
    applicationId: 42,
  };

  beforeEach(() => {
    vi.clearAllMocks();
    // Mock successful fetch for thread details
    global.fetch = vi.fn(() =>
      Promise.resolve({
        ok: true,
        json: async () => ({
          ...mockThreadSummary,
          messages: [],
        }),
      })
    ) as any;
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('should render draft follow-up button', () => {
    render(
      <ThreadViewer
        threadId="thread-123"
        summary={mockThreadSummary}
      />
    );

    const draftButton = screen.getByTestId('thread-viewer-draft-followup');
    expect(draftButton).toBeInTheDocument();
    expect(draftButton).toHaveTextContent('Draft follow-up');
  });

  it('should generate draft when button is clicked', async () => {
    const user = userEvent.setup();
    const mockDraft = {
      subject: 'Following Up on Software Engineer Role',
      body: 'Hi,\n\nI wanted to follow up on our conversation about the Software Engineer position. I remain very interested and would love to hear about next steps.\n\nBest regards',
    };

    vi.mocked(api.generateFollowupDraft).mockResolvedValue({
      status: 'ok',
      draft: mockDraft,
    });

    render(
      <ThreadViewer
        threadId="thread-123"
        summary={mockThreadSummary}
      />
    );

    const draftButton = screen.getByTestId('thread-viewer-draft-followup');
    await user.click(draftButton);

    // Should call API with correct params
    await waitFor(() => {
      expect(api.generateFollowupDraft).toHaveBeenCalledWith({
        thread_id: 'thread-123',
        application_id: 42,
      });
    });

    // Should display draft card after generation
    await waitFor(() => {
      expect(screen.getByText('Follow-up Draft')).toBeInTheDocument();
      expect(screen.getByText(mockDraft.subject)).toBeInTheDocument();
    });

    // Body should be present (use a partial matcher due to whitespace)
    await waitFor(() => {
      expect(screen.getByText(/I wanted to follow up on our conversation/)).toBeInTheDocument();
    });

    // Should show copy buttons
    expect(screen.getByText('Copy Full Draft')).toBeInTheDocument();
    expect(screen.getByText('Copy Body Only')).toBeInTheDocument();
  });

  it('should generate draft without application_id when not present', async () => {
    const user = userEvent.setup();
    const summaryWithoutApp = { ...mockThreadSummary, applicationId: undefined };

    vi.mocked(api.generateFollowupDraft).mockResolvedValue({
      status: 'ok',
      draft: {
        subject: 'Following Up',
        body: 'Hello...',
      },
    });

    render(
      <ThreadViewer
        threadId="thread-123"
        summary={summaryWithoutApp}
      />
    );

    const draftButton = screen.getByTestId('thread-viewer-draft-followup');
    await user.click(draftButton);

    await waitFor(() => {
      expect(api.generateFollowupDraft).toHaveBeenCalledWith({
        thread_id: 'thread-123',
        application_id: undefined,
      });
    });
  });

  it('should handle API error gracefully', async () => {
    const user = userEvent.setup();

    vi.mocked(api.generateFollowupDraft).mockResolvedValue({
      status: 'error',
      message: 'Failed to retrieve thread details',
    });

    render(
      <ThreadViewer
        threadId="thread-123"
        summary={mockThreadSummary}
      />
    );

    const draftButton = screen.getByTestId('thread-viewer-draft-followup');
    await user.click(draftButton);

    // Should not display draft card on error
    await waitFor(() => {
      expect(screen.queryByText('Follow-up Draft')).not.toBeInTheDocument();
    });

    // Button should be re-enabled
    await waitFor(() => {
      expect(draftButton).not.toBeDisabled();
      expect(draftButton).toHaveTextContent('Draft follow-up');
    });
  });

  it('should copy full draft to clipboard', async () => {
    const user = userEvent.setup();
    const mockDraft = {
      subject: 'Test Subject',
      body: 'Test Body',
    };

    vi.mocked(api.generateFollowupDraft).mockResolvedValue({
      status: 'ok',
      draft: mockDraft,
    });

    // Mock clipboard API
    const clipboardWriteTextSpy = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, 'clipboard', {
      value: {
        writeText: clipboardWriteTextSpy,
      },
      writable: true,
      configurable: true,
    });

    render(
      <ThreadViewer
        threadId="thread-123"
        summary={mockThreadSummary}
      />
    );

    // Generate draft
    const draftButton = screen.getByTestId('thread-viewer-draft-followup');
    await user.click(draftButton);

    // Wait for draft to appear
    await waitFor(() => {
      expect(screen.getByText('Copy Full Draft')).toBeInTheDocument();
    });

    // Click copy button
    const copyButton = screen.getByText('Copy Full Draft');
    await user.click(copyButton);

    // Should copy full draft with subject
    expect(clipboardWriteTextSpy).toHaveBeenCalledWith(
      'Subject: Test Subject\n\nTest Body'
    );
  });

  it('should copy body only to clipboard', async () => {
    const user = userEvent.setup();
    const mockDraft = {
      subject: 'Test Subject',
      body: 'Test Body',
    };

    vi.mocked(api.generateFollowupDraft).mockResolvedValue({
      status: 'ok',
      draft: mockDraft,
    });

    // Mock clipboard API
    const clipboardWriteTextSpy = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, 'clipboard', {
      value: {
        writeText: clipboardWriteTextSpy,
      },
      writable: true,
      configurable: true,
    });

    render(
      <ThreadViewer
        threadId="thread-123"
        summary={mockThreadSummary}
      />
    );

    // Generate draft
    const draftButton = screen.getByTestId('thread-viewer-draft-followup');
    await user.click(draftButton);

    // Wait for draft to appear
    await waitFor(() => {
      expect(screen.getByText('Copy Body Only')).toBeInTheDocument();
    });

    // Click copy body button
    const copyBodyButton = screen.getByText('Copy Body Only');
    await user.click(copyBodyButton);

    // Should copy body only
    expect(clipboardWriteTextSpy).toHaveBeenCalledWith('Test Body');
  });

  it('should clear draft when close button is clicked', async () => {
    const user = userEvent.setup();
    const mockDraft = {
      subject: 'Test Subject',
      body: 'Test Body',
    };

    vi.mocked(api.generateFollowupDraft).mockResolvedValue({
      status: 'ok',
      draft: mockDraft,
    });

    render(
      <ThreadViewer
        threadId="thread-123"
        summary={mockThreadSummary}
      />
    );

    // Generate draft
    const draftButton = screen.getByTestId('thread-viewer-draft-followup');
    await user.click(draftButton);

    // Wait for draft to appear
    await waitFor(() => {
      expect(screen.getByText('Follow-up Draft')).toBeInTheDocument();
    });

    // Find and click close button (✕)
    const closeButton = screen.getByRole('button', { name: '✕' });
    await user.click(closeButton);

    // Draft card should be removed
    expect(screen.queryByText('Follow-up Draft')).not.toBeInTheDocument();
  });

  it('should handle network errors', async () => {
    const user = userEvent.setup();

    vi.mocked(api.generateFollowupDraft).mockRejectedValue(
      new Error('Network error')
    );

    render(
      <ThreadViewer
        threadId="thread-123"
        summary={mockThreadSummary}
      />
    );

    const draftButton = screen.getByTestId('thread-viewer-draft-followup');
    await user.click(draftButton);

    // Should not crash
    await waitFor(() => {
      expect(draftButton).not.toBeDisabled();
    });

    // Should not display draft
    expect(screen.queryByText('Follow-up Draft')).not.toBeInTheDocument();
  });
});
