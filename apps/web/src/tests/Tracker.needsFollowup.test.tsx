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

describe('Tracker Needs Follow-up Filter', () => {
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
      thread_id: 'thread_apple999',
      notes: '',
    },
    {
      id: 5,
      company: 'Netflix',
      role: 'Backend Engineer',
      status: 'hr_screen',
      source: 'LinkedIn',
      thread_id: null, // No thread
      notes: '',
    },
    {
      id: 6,
      company: 'Stripe',
      role: 'Full Stack',
      status: 'applied',
      source: 'Website',
      thread_id: null, // No thread
      notes: '',
    },
  ]

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(api.listApplications).mockResolvedValue(mockApplications)
    vi.mocked(api.fetchTrackerApplications).mockResolvedValue([])
  })

  it('should render the Needs follow-up filter button', async () => {
    renderTracker()

    await waitFor(() => {
      expect(screen.queryByText('Loading…')).not.toBeInTheDocument()
    })

    const filterBtn = screen.getByTestId('filter-needs-followup')
    expect(filterBtn).toBeInTheDocument()
    expect(filterBtn).toHaveTextContent('Needs follow-up')
  })

  it('should show all applications when filter is off', async () => {
    renderTracker()

    await waitFor(() => {
      expect(screen.queryByText('Loading…')).not.toBeInTheDocument()
    })

    // All 6 companies should be visible
    expect(screen.getByText('Google')).toBeInTheDocument()
    expect(screen.getByText('Meta')).toBeInTheDocument()
    expect(screen.getByText('Amazon')).toBeInTheDocument()
    expect(screen.getByText('Apple')).toBeInTheDocument()
    expect(screen.getByText('Netflix')).toBeInTheDocument()
    expect(screen.getByText('Stripe')).toBeInTheDocument()

    // Should have 6 tracker rows
    const rows = screen.getAllByTestId('tracker-row')
    expect(rows).toHaveLength(6)
  })

  it('should show only apps with thread_id and early-stage status when filter is on', async () => {
    const user = userEvent.setup()
    renderTracker()

    await waitFor(() => {
      expect(screen.queryByText('Loading…')).not.toBeInTheDocument()
    })

    // Click the filter button
    const filterBtn = screen.getByTestId('filter-needs-followup')
    await user.click(filterBtn)

    // Only Google (applied+thread) and Meta (interview+thread) should be visible
    expect(screen.getByText('Google')).toBeInTheDocument()
    expect(screen.getByText('Meta')).toBeInTheDocument()

    // Amazon (offer), Apple (rejected), Netflix (no thread), Stripe (no thread) should NOT be visible
    expect(screen.queryByText('Amazon')).not.toBeInTheDocument()
    expect(screen.queryByText('Apple')).not.toBeInTheDocument()
    expect(screen.queryByText('Netflix')).not.toBeInTheDocument()
    expect(screen.queryByText('Stripe')).not.toBeInTheDocument()

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

    const filterBtn = screen.getByTestId('filter-needs-followup')

    // Initially all 6 visible
    expect(screen.getAllByTestId('tracker-row')).toHaveLength(6)

    // Click to enable filter - only 2 visible (Google, Meta)
    await user.click(filterBtn)
    expect(screen.getAllByTestId('tracker-row')).toHaveLength(2)

    // Click again to disable filter - back to 6 visible
    await user.click(filterBtn)
    expect(screen.getAllByTestId('tracker-row')).toHaveLength(6)

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

    const filterBtn = screen.getByTestId('filter-needs-followup')

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

    const filterBtn = screen.getByTestId('filter-needs-followup')

    // Initially should have default border styling
    expect(filterBtn.className).toContain('border-zinc')

    // Click to enable filter
    await user.click(filterBtn)

    // Should have cyan active styling
    expect(filterBtn.className).toContain('bg-cyan-400/20')
    expect(filterBtn.className).toContain('text-cyan-400')
    expect(filterBtn.className).toContain('border-cyan-400')
  })

  it('should work in combination with From Mailbox filter', async () => {
    const user = userEvent.setup()
    renderTracker()

    await waitFor(() => {
      expect(screen.queryByText('Loading…')).not.toBeInTheDocument()
    })

    // Enable From Mailbox filter - should show 4 apps with thread_id
    const fromMailboxBtn = screen.getByTestId('filter-from-mailbox')
    await user.click(fromMailboxBtn)
    expect(screen.getAllByTestId('tracker-row')).toHaveLength(4) // Google, Meta, Amazon, Apple

    // Also enable Needs follow-up filter - should show 2 apps (Google, Meta)
    const needsFollowupBtn = screen.getByTestId('filter-needs-followup')
    await user.click(needsFollowupBtn)
    expect(screen.getAllByTestId('tracker-row')).toHaveLength(2)

    // Only Google and Meta should be visible
    expect(screen.getByText('Google')).toBeInTheDocument()
    expect(screen.getByText('Meta')).toBeInTheDocument()
    expect(screen.queryByText('Amazon')).not.toBeInTheDocument() // offer status
    expect(screen.queryByText('Apple')).not.toBeInTheDocument() // rejected status
  })

  it('should show helper text when needs follow-up filter is active', async () => {
    const user = userEvent.setup()
    renderTracker()

    await waitFor(() => {
      expect(screen.queryByText('Loading…')).not.toBeInTheDocument()
    })

    // Enable needs follow-up filter
    const filterBtn = screen.getByTestId('filter-needs-followup')
    await user.click(filterBtn)

    // Should show helper text
    expect(screen.getByText(/Showing applications in early stages/i)).toBeInTheDocument()
  })

  it('should handle edge case where no apps need follow-up', async () => {
    const user = userEvent.setup()

    // Mock applications with no apps that need follow-up
    const appsNoFollowup = [
      { id: 1, company: 'CompanyA', role: 'Role A', status: 'offer', source: 'Web', thread_id: 'thread1', notes: '' },
      { id: 2, company: 'CompanyB', role: 'Role B', status: 'rejected', source: 'Referral', thread_id: 'thread2', notes: '' },
      { id: 3, company: 'CompanyC', role: 'Role C', status: 'ghosted', source: 'Direct', thread_id: null, notes: '' },
    ]
    vi.mocked(api.listApplications).mockResolvedValue(appsNoFollowup)

    renderTracker()

    await waitFor(() => {
      expect(screen.queryByText('Loading…')).not.toBeInTheDocument()
    })

    // Initially should see 3 rows
    expect(screen.getAllByTestId('tracker-row')).toHaveLength(3)

    // Enable needs follow-up filter
    const filterBtn = screen.getByTestId('filter-needs-followup')
    await user.click(filterBtn)

    // Should show 0 rows
    expect(screen.queryAllByTestId('tracker-row')).toHaveLength(0)
  })

  it('should only count early-stage statuses for follow-up', async () => {
    const user = userEvent.setup()

    // Test that only applied, hr_screen, interview count as needing follow-up
    const mixedApps = [
      { id: 1, company: 'A', role: 'R', status: 'applied', source: 'S', thread_id: 't1', notes: '' },
      { id: 2, company: 'B', role: 'R', status: 'hr_screen', source: 'S', thread_id: 't2', notes: '' },
      { id: 3, company: 'C', role: 'R', status: 'interview', source: 'S', thread_id: 't3', notes: '' },
      { id: 4, company: 'D', role: 'R', status: 'offer', source: 'S', thread_id: 't4', notes: '' },
      { id: 5, company: 'E', role: 'R', status: 'rejected', source: 'S', thread_id: 't5', notes: '' },
      { id: 6, company: 'F', role: 'R', status: 'on_hold', source: 'S', thread_id: 't6', notes: '' },
      { id: 7, company: 'G', role: 'R', status: 'ghosted', source: 'S', thread_id: 't7', notes: '' },
    ]
    vi.mocked(api.listApplications).mockResolvedValue(mixedApps)

    renderTracker()

    await waitFor(() => {
      expect(screen.queryByText('Loading…')).not.toBeInTheDocument()
    })

    // Enable needs follow-up filter
    const filterBtn = screen.getByTestId('filter-needs-followup')
    await user.click(filterBtn)

    // Should show exactly 3 rows (applied, hr_screen, interview)
    expect(screen.getAllByTestId('tracker-row')).toHaveLength(3)
    expect(screen.getByText('A')).toBeInTheDocument()
    expect(screen.getByText('B')).toBeInTheDocument()
    expect(screen.getByText('C')).toBeInTheDocument()
  })
})
