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

describe('Tracker From Mailbox Filter', () => {
  const mockApplications = [
    {
      id: 1,
      company: 'Google',
      role: 'Software Engineer',
      status: 'applied',
      source: 'LinkedIn',
      thread_id: 'thread_abc123',
      gmail_thread_id: 'gmail_abc',
      notes: '',
    },
    {
      id: 2,
      company: 'Meta',
      role: 'Frontend Engineer',
      status: 'interview',
      source: 'Company Site',
      thread_id: null,
      gmail_thread_id: null,
      notes: '',
    },
    {
      id: 3,
      company: 'Amazon',
      role: 'Backend Engineer',
      status: 'applied',
      source: 'Referral',
      thread_id: 'thread_xyz789',
      gmail_thread_id: 'gmail_xyz',
      notes: '',
    },
    {
      id: 4,
      company: 'Apple',
      role: 'iOS Engineer',
      status: 'rejected',
      source: 'Indeed',
      thread_id: null,
      gmail_thread_id: null,
      notes: '',
    },
  ]

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(api.listApplications).mockResolvedValue(mockApplications)
    vi.mocked(api.fetchTrackerApplications).mockResolvedValue([])
  })

  it('should render the From Mailbox filter button', async () => {
    renderTracker()

    await waitFor(() => {
      expect(screen.queryByText('Loading…')).not.toBeInTheDocument()
    })

    const filterBtn = screen.getByTestId('filter-from-mailbox')
    expect(filterBtn).toBeInTheDocument()
    expect(filterBtn).toHaveTextContent('From Mailbox')
  })

  it('should show all applications when filter is off', async () => {
    renderTracker()

    await waitFor(() => {
      expect(screen.queryByText('Loading…')).not.toBeInTheDocument()
    })

    // All 4 companies should be visible
    expect(screen.getByText('Google')).toBeInTheDocument()
    expect(screen.getByText('Meta')).toBeInTheDocument()
    expect(screen.getByText('Amazon')).toBeInTheDocument()
    expect(screen.getByText('Apple')).toBeInTheDocument()

    // Should have 4 tracker rows
    const rows = screen.getAllByTestId('tracker-row')
    expect(rows).toHaveLength(4)
  })

  it('should show only mail-linked applications when filter is on', async () => {
    const user = userEvent.setup()
    renderTracker()

    await waitFor(() => {
      expect(screen.queryByText('Loading…')).not.toBeInTheDocument()
    })

    // Click the filter button
    const filterBtn = screen.getByTestId('filter-from-mailbox')
    await user.click(filterBtn)

    // Only Google and Amazon should be visible (they have thread_id)
    expect(screen.getByText('Google')).toBeInTheDocument()
    expect(screen.getByText('Amazon')).toBeInTheDocument()

    // Meta and Apple should not be visible (no thread_id)
    expect(screen.queryByText('Meta')).not.toBeInTheDocument()
    expect(screen.queryByText('Apple')).not.toBeInTheDocument()

    // Should have 2 tracker rows
    const rows = screen.getAllByTestId('tracker-row')
    expect(rows).toHaveLength(2)
  })

  it('should toggle filter state when clicked multiple times', async () => {
    const user = userEvent.setup()
    renderTracker()

    await waitFor(() => {
      expect(screen.queryByText('Loading…')).not.toBeInTheDocument()
    })

    const filterBtn = screen.getByTestId('filter-from-mailbox')

    // Initially all 4 visible
    expect(screen.getAllByTestId('tracker-row')).toHaveLength(4)

    // Click to enable filter - only 2 visible
    await user.click(filterBtn)
    expect(screen.getAllByTestId('tracker-row')).toHaveLength(2)

    // Click again to disable filter - back to 4 visible
    await user.click(filterBtn)
    expect(screen.getAllByTestId('tracker-row')).toHaveLength(4)

    // Click once more to enable - 2 visible
    await user.click(filterBtn)
    expect(screen.getAllByTestId('tracker-row')).toHaveLength(2)
  })

  it('should show checkmark when filter is active', async () => {
    const user = userEvent.setup()
    renderTracker()

    await waitFor(() => {
      expect(screen.queryByText('Loading…')).not.toBeInTheDocument()
    })

    const filterBtn = screen.getByTestId('filter-from-mailbox')

    // Initially no checkmark
    expect(filterBtn).not.toHaveTextContent('✓')

    // Click to enable filter
    await user.click(filterBtn)

    // Should show checkmark
    expect(filterBtn).toHaveTextContent('✓')

    // Click to disable
    await user.click(filterBtn)

    // Checkmark should be gone
    expect(filterBtn).not.toHaveTextContent('✓')
  })

  it('should apply correct styling when filter is active', async () => {
    const user = userEvent.setup()
    renderTracker()

    await waitFor(() => {
      expect(screen.queryByText('Loading…')).not.toBeInTheDocument()
    })

    const filterBtn = screen.getByTestId('filter-from-mailbox')

    // Initially should have default border styling
    expect(filterBtn.className).toContain('border-zinc')

    // Click to enable filter
    await user.click(filterBtn)

    // Should have yellow active styling
    expect(filterBtn.className).toContain('bg-yellow-400/20')
    expect(filterBtn.className).toContain('text-yellow-400')
    expect(filterBtn.className).toContain('border-yellow-400')
  })

  it('should show mail badges only for filtered applications', async () => {
    const user = userEvent.setup()
    renderTracker()

    await waitFor(() => {
      expect(screen.queryByText('Loading…')).not.toBeInTheDocument()
    })

    // Initially should have 2 mail badges (Google and Amazon)
    const initialBadges = screen.getAllByTestId('mail-linked-badge')
    expect(initialBadges).toHaveLength(2)

    // Enable filter
    const filterBtn = screen.getByTestId('filter-from-mailbox')
    await user.click(filterBtn)

    // Should still have 2 mail badges, but only for visible rows
    const filteredBadges = screen.getAllByTestId('mail-linked-badge')
    expect(filteredBadges).toHaveLength(2)

    // All visible rows should have mail badges
    const visibleRows = screen.getAllByTestId('tracker-row')
    expect(visibleRows).toHaveLength(2)
  })

  it('should handle case where no applications have thread_id', async () => {
    const user = userEvent.setup()

    // Mock applications with no thread_id
    const appsWithoutThreadId = [
      { id: 1, company: 'CompanyA', role: 'Role A', status: 'applied', source: 'Web', thread_id: null, gmail_thread_id: null, notes: '' },
      { id: 2, company: 'CompanyB', role: 'Role B', status: 'interview', source: 'Referral', thread_id: null, gmail_thread_id: null, notes: '' },
    ]
    vi.mocked(api.listApplications).mockResolvedValue(appsWithoutThreadId)

    renderTracker()

    await waitFor(() => {
      expect(screen.queryByText('Loading…')).not.toBeInTheDocument()
    })

    // Initially should see 2 rows
    expect(screen.getAllByTestId('tracker-row')).toHaveLength(2)

    // Enable filter
    const filterBtn = screen.getByTestId('filter-from-mailbox')
    await user.click(filterBtn)

    // Should show 0 rows
    expect(screen.queryAllByTestId('tracker-row')).toHaveLength(0)
  })

  it('should handle case where all applications have thread_id', async () => {
    const user = userEvent.setup()

    // Mock applications where all have thread_id
    const appsWithThreadId = [
      { id: 1, company: 'CompanyA', role: 'Role A', status: 'applied', source: 'Mail', thread_id: 'thread1', gmail_thread_id: 'gmail1', notes: '' },
      { id: 2, company: 'CompanyB', role: 'Role B', status: 'interview', source: 'Mail', thread_id: 'thread2', gmail_thread_id: 'gmail2', notes: '' },
      { id: 3, company: 'CompanyC', role: 'Role C', status: 'offer', source: 'Mail', thread_id: 'thread3', gmail_thread_id: 'gmail3', notes: '' },
    ]
    vi.mocked(api.listApplications).mockResolvedValue(appsWithThreadId)

    renderTracker()

    await waitFor(() => {
      expect(screen.queryByText('Loading…')).not.toBeInTheDocument()
    })

    // Initially should see 3 rows
    expect(screen.getAllByTestId('tracker-row')).toHaveLength(3)

    // Enable filter
    const filterBtn = screen.getByTestId('filter-from-mailbox')
    await user.click(filterBtn)

    // Should still show 3 rows (all have thread_id)
    expect(screen.getAllByTestId('tracker-row')).toHaveLength(3)
  })

  it('should work independently of status filter', async () => {
    const user = userEvent.setup()
    renderTracker()

    await waitFor(() => {
      expect(screen.queryByText('Loading…')).not.toBeInTheDocument()
    })

    // Enable From Mailbox filter - should show 2 apps (Google, Amazon)
    const fromMailboxBtn = screen.getByTestId('filter-from-mailbox')
    await user.click(fromMailboxBtn)
    expect(screen.getAllByTestId('tracker-row')).toHaveLength(2)

    // Now also select status filter = "applied"
    // This should trigger a new API call with status filter
    const statusSelect = screen.getByTestId('tracker-status-filter')
    await user.selectOptions(statusSelect, 'applied')

    // The API is called with status=applied, which will return Google and Amazon
    // both have status='applied', so we should still see 2 rows after client-side mail filter
    await waitFor(() => {
      // Note: In real scenario, API would filter server-side by status
      // Client-side mail filter would then apply on top
      expect(screen.queryByText('Loading…')).not.toBeInTheDocument()
    })
  })
})
