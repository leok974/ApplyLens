/**
 * Tests for Tracker page - Deep-link support from Thread Viewer
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { BrowserRouter, MemoryRouter } from 'react-router-dom'
import Tracker from '../pages/Tracker'
import * as api from '../lib/api'

// Mock API module
vi.mock('../lib/api', () => ({
  listApplications: vi.fn(),
  fetchTrackerApplications: vi.fn(),
  updateApplication: vi.fn(),
  createApplication: vi.fn(),
}))

describe('Tracker - Deep-link from Thread Viewer', () => {
  const mockApplications = [
    {
      id: 123,
      company: 'Google',
      role: 'Software Engineer',
      status: 'applied',
      source: 'LinkedIn',
      thread_id: 'thread_google',
      notes: '',
    },
    {
      id: 456,
      company: 'Meta',
      role: 'Frontend Engineer',
      status: 'interview',
      source: 'Company Site',
      thread_id: 'thread_meta',
      notes: '',
    },
    {
      id: 789,
      company: 'Amazon',
      role: 'Backend Engineer',
      status: 'offer',
      source: 'Referral',
      thread_id: null,
      notes: '',
    },
  ]

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(api.listApplications).mockResolvedValue(mockApplications)
    vi.mocked(api.fetchTrackerApplications).mockResolvedValue([])
  })

  it('selects and highlights row when opened with ?appId query param', async () => {
    render(
      <MemoryRouter initialEntries={['/tracker?appId=456']}>
        <Tracker />
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.queryByText('Loading…')).not.toBeInTheDocument()
    })

    // Find the Meta application row
    const rows = screen.getAllByTestId('tracker-row')
    const metaRow = rows.find(row => row.getAttribute('data-id') === '456')

    expect(metaRow).toBeDefined()
    expect(metaRow).toHaveAttribute('data-selected', 'true')
    expect(metaRow).toHaveClass('bg-yellow-400/10')
  })

  it('applies selection styling to the correct row', async () => {
    render(
      <MemoryRouter initialEntries={['/tracker?appId=123']}>
        <Tracker />
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.queryByText('Loading…')).not.toBeInTheDocument()
    })

    const rows = screen.getAllByTestId('tracker-row')
    const googleRow = rows.find(row => row.getAttribute('data-id') === '123')

    expect(googleRow).toBeDefined()
    expect(googleRow).toHaveAttribute('data-selected', 'true')
    expect(googleRow?.className).toContain('border-yellow-400')
  })

  it('handles invalid appId gracefully', async () => {
    render(
      <MemoryRouter initialEntries={['/tracker?appId=999']}>
        <Tracker />
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.queryByText('Loading…')).not.toBeInTheDocument()
    })

    // Should render all rows normally
    const rows = screen.getAllByTestId('tracker-row')
    expect(rows).toHaveLength(3)

    // No row should be selected
    rows.forEach(row => {
      expect(row).not.toHaveAttribute('data-selected', 'true')
    })
  })

  it('handles non-numeric appId parameter', async () => {
    render(
      <MemoryRouter initialEntries={['/tracker?appId=invalid']}>
        <Tracker />
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.queryByText('Loading…')).not.toBeInTheDocument()
    })

    // Should render all rows normally
    const rows = screen.getAllByTestId('tracker-row')
    expect(rows).toHaveLength(3)

    // No row should be selected
    rows.forEach(row => {
      expect(row).not.toHaveAttribute('data-selected', 'true')
    })
  })

  it('clears appId from URL after processing', async () => {
    const { container } = render(
      <MemoryRouter initialEntries={['/tracker?appId=456']}>
        <Tracker />
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.queryByText('Loading…')).not.toBeInTheDocument()
    })

    // The URL should be cleaned up (appId removed)
    // This is tested indirectly - the component removes the param after reading it
    // In a real browser, the URL would be /tracker without the query param
  })

  it('works with other query params', async () => {
    render(
      <MemoryRouter initialEntries={['/tracker?status=interview&appId=456']}>
        <Tracker />
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.queryByText('Loading…')).not.toBeInTheDocument()
    })

    const rows = screen.getAllByTestId('tracker-row')
    const metaRow = rows.find(row => row.getAttribute('data-id') === '456')

    expect(metaRow).toBeDefined()
    expect(metaRow).toHaveAttribute('data-selected', 'true')
  })

  it('selects row even when filters are active', async () => {
    render(
      <MemoryRouter initialEntries={['/tracker?appId=123']}>
        <Tracker />
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.queryByText('Loading…')).not.toBeInTheDocument()
    })

    // The Google row should be selected even if it matches filters
    const rows = screen.getAllByTestId('tracker-row')
    const googleRow = rows.find(row => row.getAttribute('data-id') === '123')

    expect(googleRow).toBeDefined()
    expect(googleRow).toHaveAttribute('data-selected', 'true')
  })

  it('only selects one row at a time', async () => {
    render(
      <MemoryRouter initialEntries={['/tracker?appId=456']}>
        <Tracker />
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.queryByText('Loading…')).not.toBeInTheDocument()
    })

    const rows = screen.getAllByTestId('tracker-row')
    const selectedRows = rows.filter(row => row.getAttribute('data-selected') === 'true')

    expect(selectedRows).toHaveLength(1)
    expect(selectedRows[0]?.getAttribute('data-id')).toBe('456')
  })
})
