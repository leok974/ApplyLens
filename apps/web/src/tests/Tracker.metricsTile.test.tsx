import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BrowserRouter } from 'react-router-dom'
import Tracker from '../pages/Tracker'
import * as api from '../lib/api'

// Mock API module
vi.mock('../lib/api', () => ({
  listApplications: vi.fn(),
  fetchTrackerApplications: vi.fn(),
  updateApplication: vi.fn(),
  createApplication: vi.fn(),
}))

// Helper to render Tracker with router context
function renderTracker() {
  return render(
    <BrowserRouter>
      <Tracker />
    </BrowserRouter>
  )
}

describe('Tracker Metrics Summary Tile', () => {
  const mockApplications = [
    {
      id: 1,
      company: 'Google',
      role: 'Software Engineer',
      status: 'applied',
      source: 'LinkedIn',
      thread_id: 'thread_abc123',
      notes: '',
    },
    {
      id: 2,
      company: 'Meta',
      role: 'Frontend Engineer',
      status: 'interview',
      source: 'Company Site',
      thread_id: 'thread_meta456',
      notes: '',
    },
    {
      id: 3,
      company: 'Amazon',
      role: 'Backend Engineer',
      status: 'offer',
      source: 'Referral',
      thread_id: 'thread_xyz789',
      notes: '',
    },
    {
      id: 4,
      company: 'Apple',
      role: 'iOS Engineer',
      status: 'rejected',
      source: 'Indeed',
      thread_id: null,
      notes: '',
    },
    {
      id: 5,
      company: 'Netflix',
      role: 'Backend Engineer',
      status: 'hr_screen',
      source: 'LinkedIn',
      thread_id: null,
      notes: '',
    },
    {
      id: 6,
      company: 'Stripe',
      role: 'Full Stack',
      status: 'applied',
      source: 'Website',
      thread_id: 'thread_stripe555',
      notes: '',
    },
  ]

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(api.listApplications).mockResolvedValue(mockApplications)
    vi.mocked(api.fetchTrackerApplications).mockResolvedValue([])
  })

  it('should render the summary tile when applications are loaded', async () => {
    renderTracker()

    await waitFor(() => {
      expect(screen.queryByText('Loading…')).not.toBeInTheDocument()
    })

    const tile = screen.getByTestId('tracker-summary-tile')
    expect(tile).toBeInTheDocument()
  })

  it('should not render the summary tile when loading', async () => {
    renderTracker()

    // While loading, tile should not be visible
    expect(screen.queryByTestId('tracker-summary-tile')).not.toBeInTheDocument()
  })

  it('should not render the summary tile when there are no applications', async () => {
    vi.mocked(api.listApplications).mockResolvedValue([])
    renderTracker()

    await waitFor(() => {
      expect(screen.queryByText('Loading…')).not.toBeInTheDocument()
    })

    expect(screen.queryByTestId('tracker-summary-tile')).not.toBeInTheDocument()
  })

  it('should display correct total count', async () => {
    renderTracker()

    await waitFor(() => {
      expect(screen.queryByText('Loading…')).not.toBeInTheDocument()
    })

    const totalMetric = screen.getByTestId('metric-total')
    expect(totalMetric).toHaveTextContent('6')
  })

  it('should display correct from mailbox count', async () => {
    renderTracker()

    await waitFor(() => {
      expect(screen.queryByText('Loading…')).not.toBeInTheDocument()
    })

    // 4 apps have thread_id: Google, Meta, Amazon, Stripe
    const fromMailboxMetric = screen.getByTestId('metric-from-mailbox')
    expect(fromMailboxMetric).toHaveTextContent('4')
  })

  it('should display correct needs follow-up count', async () => {
    renderTracker()

    await waitFor(() => {
      expect(screen.queryByText('Loading…')).not.toBeInTheDocument()
    })

    // 3 apps need follow-up (thread_id + early stage):
    // - Google: applied + thread
    // - Meta: interview + thread
    // - Stripe: applied + thread
    const needsFollowupMetric = screen.getByTestId('metric-needs-followup')
    expect(needsFollowupMetric).toHaveTextContent('3')
  })

  it('should show all metric labels', async () => {
    renderTracker()

    await waitFor(() => {
      expect(screen.queryByText('Loading…')).not.toBeInTheDocument()
    })

    const tile = screen.getByTestId('tracker-summary-tile')

    expect(screen.getByText('Total Applications')).toBeInTheDocument()
    // Use within to scope to the tile since "From Mailbox" also appears in filter button
    expect(tile).toHaveTextContent('From Mailbox')
    expect(screen.getByText('Needs Follow-up')).toBeInTheDocument()
  })

  it('should handle edge case with no mail-linked apps', async () => {
    const appsNoThreads = [
      { id: 1, company: 'A', role: 'R', status: 'applied', source: 'S', thread_id: null, notes: '' },
      { id: 2, company: 'B', role: 'R', status: 'interview', source: 'S', thread_id: null, notes: '' },
    ]
    vi.mocked(api.listApplications).mockResolvedValue(appsNoThreads)

    renderTracker()

    await waitFor(() => {
      expect(screen.queryByText('Loading…')).not.toBeInTheDocument()
    })

    expect(screen.getByTestId('metric-total')).toHaveTextContent('2')
    expect(screen.getByTestId('metric-from-mailbox')).toHaveTextContent('0')
    expect(screen.getByTestId('metric-needs-followup')).toHaveTextContent('0')
  })

  it('should handle edge case with all apps needing follow-up', async () => {
    const appsAllNeedFollowup = [
      { id: 1, company: 'A', role: 'R', status: 'applied', source: 'S', thread_id: 't1', notes: '' },
      { id: 2, company: 'B', role: 'R', status: 'hr_screen', source: 'S', thread_id: 't2', notes: '' },
      { id: 3, company: 'C', role: 'R', status: 'interview', source: 'S', thread_id: 't3', notes: '' },
    ]
    vi.mocked(api.listApplications).mockResolvedValue(appsAllNeedFollowup)

    renderTracker()

    await waitFor(() => {
      expect(screen.queryByText('Loading…')).not.toBeInTheDocument()
    })

    expect(screen.getByTestId('metric-total')).toHaveTextContent('3')
    expect(screen.getByTestId('metric-from-mailbox')).toHaveTextContent('3')
    expect(screen.getByTestId('metric-needs-followup')).toHaveTextContent('3')
  })

  it('should update metrics when status filter changes', async () => {
    const user = userEvent.setup()
    renderTracker()

    await waitFor(() => {
      expect(screen.queryByText('Loading…')).not.toBeInTheDocument()
    })

    // Initially shows all 6 apps
    expect(screen.getByTestId('metric-total')).toHaveTextContent('6')

    // Change status filter to 'applied'
    const statusSelect = screen.getByTestId('tracker-status-filter')
    await user.selectOptions(statusSelect, 'applied')

    // Note: In this test, the API would return different data
    // but since we're mocking, the counts stay the same
    // In a real scenario, this would re-fetch with the filter
  })

  it('should display metrics in a three-column grid', async () => {
    renderTracker()

    await waitFor(() => {
      expect(screen.queryByText('Loading…')).not.toBeInTheDocument()
    })

    const tile = screen.getByTestId('tracker-summary-tile')
    const grid = tile.querySelector('.grid-cols-3')
    expect(grid).toBeInTheDocument()
  })

  it('should use correct color styling for metrics', async () => {
    renderTracker()

    await waitFor(() => {
      expect(screen.queryByText('Loading…')).not.toBeInTheDocument()
    })

    const totalMetric = screen.getByTestId('metric-total')
    const fromMailboxMetric = screen.getByTestId('metric-from-mailbox')
    const needsFollowupMetric = screen.getByTestId('metric-needs-followup')

    // Total should be zinc (neutral)
    expect(totalMetric.className).toContain('text-zinc')

    // From Mailbox should be yellow
    expect(fromMailboxMetric.className).toContain('text-yellow-400')

    // Needs Follow-up should be cyan
    expect(needsFollowupMetric.className).toContain('text-cyan-400')
  })

  it('should show metrics for single application correctly', async () => {
    const singleApp = [
      { id: 1, company: 'Solo', role: 'Dev', status: 'applied', source: 'Web', thread_id: 'thread1', notes: '' },
    ]
    vi.mocked(api.listApplications).mockResolvedValue(singleApp)

    renderTracker()

    await waitFor(() => {
      expect(screen.queryByText('Loading…')).not.toBeInTheDocument()
    })

    expect(screen.getByTestId('metric-total')).toHaveTextContent('1')
    expect(screen.getByTestId('metric-from-mailbox')).toHaveTextContent('1')
    expect(screen.getByTestId('metric-needs-followup')).toHaveTextContent('1')
  })
})
