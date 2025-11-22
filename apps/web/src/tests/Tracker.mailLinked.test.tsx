import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import Tracker from '../pages/Tracker'
import * as api from '../lib/api'

// Mock the API module
vi.mock('../lib/api', () => ({
  listApplications: vi.fn(),
  fetchTrackerApplications: vi.fn(),
  updateApplication: vi.fn(),
  createApplication: vi.fn(),
}))

describe('Tracker - Mail Linked Badge', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should not render mail badge when thread_id is absent', async () => {
    vi.mocked(api.listApplications).mockResolvedValue([
      {
        id: 1,
        company: 'TechCorp',
        role: 'Engineer',
        status: 'applied',
        source: 'LinkedIn',
        // No thread_id
      },
    ])
    vi.mocked(api.fetchTrackerApplications).mockResolvedValue([])

    render(
      <MemoryRouter>
        <Tracker />
      </MemoryRouter>
    )

    // Wait for applications to load
    await screen.findByText('TechCorp')

    // Badge should not be present
    const badge = screen.queryByTestId('mail-linked-badge')
    expect(badge).toBeNull()
  })

  it('should render mail badge when thread_id is present', async () => {
    vi.mocked(api.listApplications).mockResolvedValue([
      {
        id: 1,
        company: 'TechCorp',
        role: 'Engineer',
        status: 'applied',
        source: 'LinkedIn',
        thread_id: '18d4c9a1b2e3f456',
      },
    ])
    vi.mocked(api.fetchTrackerApplications).mockResolvedValue([])

    render(
      <MemoryRouter>
        <Tracker />
      </MemoryRouter>
    )

    // Wait for applications to load
    await screen.findByText('TechCorp')

    // Badge should be present
    const badge = screen.getByTestId('mail-linked-badge')
    expect(badge).toBeInTheDocument()
    expect(badge).toHaveTextContent('Mail')
  })

  it('should have correct accessibility attributes on badge', async () => {
    const threadId = '18d4c9a1b2e3f456'
    vi.mocked(api.listApplications).mockResolvedValue([
      {
        id: 1,
        company: 'Acme Corp',
        role: 'Developer',
        status: 'applied',
        thread_id: threadId,
      },
    ])
    vi.mocked(api.fetchTrackerApplications).mockResolvedValue([])

    render(
      <MemoryRouter>
        <Tracker />
      </MemoryRouter>
    )

    await screen.findByText('Acme Corp')

    const badge = screen.getByTestId('mail-linked-badge')

    // Check for title attribute (tooltip)
    expect(badge).toHaveAttribute('title')
    expect(badge.getAttribute('title')).toContain('Mailbox Assistant')

    // Check for aria-label
    expect(badge).toHaveAttribute('aria-label')
    expect(badge.getAttribute('aria-label')).toContain('Acme Corp')
    expect(badge.getAttribute('aria-label')).toContain('Gmail')
  })

  it('should open Gmail in new tab when badge is clicked', async () => {
    const threadId = '18d4c9a1b2e3f456'
    vi.mocked(api.listApplications).mockResolvedValue([
      {
        id: 1,
        company: 'StartupXYZ',
        role: 'Backend Engineer',
        status: 'interview',
        thread_id: threadId,
      },
    ])
    vi.mocked(api.fetchTrackerApplications).mockResolvedValue([])

    // Mock window.open
    const mockOpen = vi.fn()
    vi.stubGlobal('open', mockOpen)

    render(
      <MemoryRouter>
        <Tracker />
      </MemoryRouter>
    )

    await screen.findByText('StartupXYZ')

    const badge = screen.getByTestId('mail-linked-badge')
    fireEvent.click(badge)

    // Verify Gmail URL was opened
    expect(mockOpen).toHaveBeenCalledWith(
      `https://mail.google.com/mail/u/0/#inbox/${threadId}`,
      '_blank'
    )

    vi.unstubAllGlobals()
  })

  it('should show correct styling for mail badge', async () => {
    vi.mocked(api.listApplications).mockResolvedValue([
      {
        id: 1,
        company: 'DevShop',
        role: 'Full Stack',
        status: 'applied',
        thread_id: 'abc123',
      },
    ])
    vi.mocked(api.fetchTrackerApplications).mockResolvedValue([])

    render(
      <MemoryRouter>
        <Tracker />
      </MemoryRouter>
    )

    await screen.findByText('DevShop')

    const badge = screen.getByTestId('mail-linked-badge')

    // Check for yellow accent color classes (matches ThreadList/ThreadViewer design)
    expect(badge.className).toContain('yellow')
    expect(badge.className).toContain('rounded-full')
    expect(badge.className).toContain('border')
  })

  it('should handle multiple applications with mixed thread_id presence', async () => {
    vi.mocked(api.listApplications).mockResolvedValue([
      {
        id: 1,
        company: 'WithMail',
        role: 'Engineer A',
        status: 'applied',
        thread_id: 'thread-1',
      },
      {
        id: 2,
        company: 'NoMail',
        role: 'Engineer B',
        status: 'applied',
        // No thread_id
      },
      {
        id: 3,
        company: 'AlsoMail',
        role: 'Engineer C',
        status: 'interview',
        thread_id: 'thread-2',
      },
    ])
    vi.mocked(api.fetchTrackerApplications).mockResolvedValue([])

    render(
      <MemoryRouter>
        <Tracker />
      </MemoryRouter>
    )

    await screen.findByText('WithMail')
    await screen.findByText('NoMail')
    await screen.findByText('AlsoMail')

    const badges = screen.queryAllByTestId('mail-linked-badge')

    // Only 2 badges should be present (for WithMail and AlsoMail)
    expect(badges).toHaveLength(2)
  })
})
