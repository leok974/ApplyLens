/**
 * Tests for Today page - Inbox triage panel
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Today from '@/pages/Today';

// Mock useNavigate
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

describe('Today Page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockNavigate.mockClear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  const renderWithRouter = () => {
    return render(
      <MemoryRouter>
        <Today />
      </MemoryRouter>
    );
  };

  it('renders loading state initially', () => {
    global.fetch = vi.fn(() => new Promise(() => {})); // Never resolves

    renderWithRouter();

    expect(screen.getByText(/Preparing today's triage/i)).toBeInTheDocument();
  });

  it('renders error state when API call fails', async () => {
    global.fetch = vi.fn(() =>
      Promise.resolve({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
      } as Response)
    );

    renderWithRouter();

    await waitFor(() => {
      expect(screen.getByText(/Failed to fetch today's triage/i)).toBeInTheDocument();
    });
  });

  it('renders authentication error when 401 returned', async () => {
    global.fetch = vi.fn(() =>
      Promise.resolve({
        ok: false,
        status: 401,
        statusText: 'Unauthorized',
      } as Response)
    );

    renderWithRouter();

    await waitFor(() => {
      expect(screen.getByText(/Not authenticated/i)).toBeInTheDocument();
    });
  });

  it('renders empty state when no intents returned', async () => {
    global.fetch = vi.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ status: 'ok', intents: [] }),
      } as Response)
    );

    renderWithRouter();

    await waitFor(() => {
      expect(screen.getByText(/No triage data available/i)).toBeInTheDocument();
    });
  });

  it('renders intent tiles with correct data', async () => {
    const mockResponse = {
      status: 'ok',
      intents: [
        {
          intent: 'followups',
          summary: { count: 3, time_window_days: 90 },
          threads: [
            {
              threadId: 'thread-1',
              subject: 'Follow up needed',
              from: 'alice@example.com',
              lastMessageAt: '2025-11-20T10:00:00Z',
              labels: ['INBOX'],
              snippet: 'Just checking in...',
              gmailUrl: 'https://mail.google.com/mail/u/0/#inbox/thread-1',
            },
            {
              threadId: 'thread-2',
              subject: 'Re: Interview follow-up',
              from: 'recruiter@tech.com',
              lastMessageAt: '2025-11-19T14:30:00Z',
              labels: ['INBOX'],
              snippet: 'Thanks for your time...',
              gmailUrl: 'https://mail.google.com/mail/u/0/#inbox/thread-2',
              applicationId: 123,
              applicationStatus: 'active',
            },
          ],
        },
        {
          intent: 'bills',
          summary: { count: 0, time_window_days: 90 },
          threads: [],
        },
      ],
    };

    global.fetch = vi.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      } as Response)
    );

    renderWithRouter();

    await waitFor(() => {
      // Page title
      expect(screen.getByText('Today')).toBeInTheDocument();
      expect(screen.getByText(/What should you do with your inbox today/i)).toBeInTheDocument();

      // Follow-ups tile
      expect(screen.getByText('Follow-ups')).toBeInTheDocument();
      expect(screen.getByText('3')).toBeInTheDocument(); // Count badge

      // Bills tile
      expect(screen.getByText('Bills & Invoices')).toBeInTheDocument();
      expect(screen.getByText('0')).toBeInTheDocument(); // Count badge
      expect(screen.getByText(/No bills pending/i)).toBeInTheDocument();
    });
  });

  it('renders thread list correctly', async () => {
    const mockResponse = {
      status: 'ok',
      intents: [
        {
          intent: 'followups',
          summary: { count: 2, time_window_days: 90 },
          threads: [
            {
              threadId: 'thread-1',
              subject: 'Follow up needed',
              from: 'alice@example.com',
              lastMessageAt: '2025-11-20T10:00:00Z',
              labels: ['INBOX'],
              snippet: 'Just checking in...',
              gmailUrl: 'https://mail.google.com/mail/u/0/#inbox/thread-1',
            },
          ],
        },
      ],
    };

    global.fetch = vi.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      } as Response)
    );

    renderWithRouter();

    await waitFor(() => {
      expect(screen.getByText('Follow up needed')).toBeInTheDocument();
      expect(screen.getByText('alice@example.com')).toBeInTheDocument();
      expect(screen.getByText('Just checking in...')).toBeInTheDocument();
    });
  });

  it('limits threads to 5 per intent and shows overflow count', async () => {
    const mockResponse = {
      status: 'ok',
      intents: [
        {
          intent: 'unsubscribe',
          summary: { count: 10, time_window_days: 90 },
          threads: Array.from({ length: 5 }, (_, i) => ({
            threadId: `thread-${i}`,
            subject: `Newsletter ${i}`,
            from: `sender${i}@example.com`,
            lastMessageAt: '2025-11-20T10:00:00Z',
            labels: ['INBOX'],
            snippet: 'Unsubscribe...',
            gmailUrl: `https://mail.google.com/mail/u/0/#inbox/thread-${i}`,
          })),
        },
      ],
    };

    global.fetch = vi.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      } as Response)
    );

    renderWithRouter();

    await waitFor(() => {
      // Should show "+5 more" since count is 10 but only 5 threads rendered
      expect(screen.getByText('+5 more')).toBeInTheDocument();
    });
  });

  it('sends correct POST request to /v2/agent/today', async () => {
    const mockResponse = {
      status: 'ok',
      intents: [],
    };

    const fetchSpy = vi.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      } as Response)
    );
    global.fetch = fetchSpy;

    renderWithRouter();

    await waitFor(() => {
      expect(fetchSpy).toHaveBeenCalledWith(
        expect.stringContaining('/v2/agent/today'),
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({ time_window_days: 90 }),
        }
      );
    });
  });

  it('displays time window correctly', async () => {
    const mockResponse = {
      status: 'ok',
      intents: [
        {
          intent: 'interviews',
          summary: { count: 1, time_window_days: 90 },
          threads: [],
        },
      ],
    };

    global.fetch = vi.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      } as Response)
    );

    renderWithRouter();

    await waitFor(() => {
      expect(screen.getByText('Last 90 days')).toBeInTheDocument();
    });
  });

  it('renders all 6 intent types correctly', async () => {
    const mockResponse = {
      status: 'ok',
      intents: [
        { intent: 'followups', summary: { count: 1, time_window_days: 90 }, threads: [] },
        { intent: 'bills', summary: { count: 2, time_window_days: 90 }, threads: [] },
        { intent: 'interviews', summary: { count: 3, time_window_days: 90 }, threads: [] },
        { intent: 'unsubscribe', summary: { count: 4, time_window_days: 90 }, threads: [] },
        { intent: 'clean_promos', summary: { count: 5, time_window_days: 90 }, threads: [] },
        { intent: 'suspicious', summary: { count: 6, time_window_days: 90 }, threads: [] },
      ],
    };

    global.fetch = vi.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      } as Response)
    );

    renderWithRouter();

    await waitFor(() => {
      expect(screen.getByText('Follow-ups')).toBeInTheDocument();
      expect(screen.getByText('Bills & Invoices')).toBeInTheDocument();
      expect(screen.getByText('Interviews')).toBeInTheDocument();
      expect(screen.getByText('Unsubscribe')).toBeInTheDocument();
      expect(screen.getByText('Clean Promos')).toBeInTheDocument();
      expect(screen.getByText('Suspicious')).toBeInTheDocument();
    });
  });

  describe('Follow-ups Summary', () => {
    it('renders follow-ups summary card when data is present', async () => {
      global.fetch = vi.fn(() =>
        Promise.resolve({
          ok: true,
          json: async () => ({
            status: 'ok',
            intents: [],
            followups: {
              total: 10,
              done_count: 4,
              remaining_count: 6,
              time_window_days: 90,
            },
          }),
        } as Response)
      );

      renderWithRouter();

      await waitFor(() => {
        expect(screen.getByTestId('today-followups-card')).toBeInTheDocument();
      });

      expect(screen.getByText('4 / 10 done')).toBeInTheDocument();
      expect(screen.getByText(/6 remaining · last 90 days/i)).toBeInTheDocument();
      expect(screen.getByText('40%')).toBeInTheDocument();
    });

    it('navigates to /followups when Open queue button is clicked', async () => {
      global.fetch = vi.fn(() =>
        Promise.resolve({
          ok: true,
          json: async () => ({
            status: 'ok',
            intents: [],
            followups: {
              total: 5,
              done_count: 2,
              remaining_count: 3,
              time_window_days: 90,
            },
          }),
        } as Response)
      );

      const { user } = render(<Today />, { wrapper: MemoryRouter });

      await waitFor(() => {
        expect(screen.getByTestId('today-followups-card')).toBeInTheDocument();
      });

      const openQueueButton = screen.getByTestId('today-followups-open-queue');
      await user.click(openQueueButton);

      expect(mockNavigate).toHaveBeenCalledWith('/followups');
    });

    it('does not render follow-ups card when data is not present', async () => {
      global.fetch = vi.fn(() =>
        Promise.resolve({
          ok: true,
          json: async () => ({
            status: 'ok',
            intents: [],
            // no followups field
          }),
        } as Response)
      );

      renderWithRouter();

      await waitFor(() => {
        expect(screen.queryByTestId('today-followups-card')).not.toBeInTheDocument();
      });
    });
  });
});
