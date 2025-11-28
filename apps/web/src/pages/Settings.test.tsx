import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import Settings from './Settings'
import * as auth from '@/api/auth'

// Mock dependencies
vi.mock('@/api/auth', () => ({
  getCurrentUser: vi.fn(),
  fetchAndCacheCurrentUser: vi.fn(),
  logout: vi.fn(),
}))

vi.mock('@/components/settings/ResumeUploadPanel', () => ({
  ResumeUploadPanel: () => <div>ResumeUploadPanel</div>,
}))

vi.mock('@/components/settings/MailboxThemePanel', () => ({
  MailboxThemePanel: () => <div>MailboxThemePanel</div>,
}))

vi.mock('@/components/settings/VersionCard', () => ({
  VersionCard: () => <div>VersionCard</div>,
}))

vi.mock('@/components/HealthBadge', () => ({
  HealthBadge: () => <div>HealthBadge</div>,
}))

vi.mock('@/components/ProfileMetrics', () => ({
  ProfileMetrics: () => <div>ProfileMetrics</div>,
}))

vi.mock('../state/searchPrefs', () => ({
  getRecencyScale: () => '7d',
  setRecencyScale: vi.fn(),
}))

vi.mock('../config/features', () => ({
  features: {
    searchScoring: false,
  },
}))

vi.mock('@/lib/flags', () => ({
  FLAGS: {
    PROFILE_METRICS: false,
  },
}))

describe('Settings - Auth Failure Handling', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('redirects to /welcome when fetchAndCacheCurrentUser returns null', async () => {
    // Arrange: mock auth to return null (no session)
    vi.mocked(auth.getCurrentUser).mockReturnValue(null)
    vi.mocked(auth.fetchAndCacheCurrentUser).mockResolvedValue(null)

    let navigatedTo: string | null = null

    // Render Settings within a router to capture navigation
    render(
      <MemoryRouter initialEntries={['/settings']}>
        <Routes>
          <Route path="/settings" element={<Settings />} />
          <Route
            path="/welcome"
            element={<div data-testid="welcome-page">Welcome Page</div>}
          />
        </Routes>
      </MemoryRouter>
    )

    // Assert: should show loading initially
    expect(screen.getByText(/loading your settings/i)).toBeInTheDocument()

    // Wait for redirect to /welcome
    await waitFor(
      () => {
        expect(screen.getByTestId('welcome-page')).toBeInTheDocument()
      },
      { timeout: 2000 }
    )

    // Verify fetchAndCacheCurrentUser was called
    expect(auth.fetchAndCacheCurrentUser).toHaveBeenCalled()
  })

  it('shows loading state while fetching user', () => {
    // Arrange: mock getCurrentUser to return null (no cache)
    vi.mocked(auth.getCurrentUser).mockReturnValue(null)
    // Make fetchAndCacheCurrentUser never resolve to stay in loading state
    vi.mocked(auth.fetchAndCacheCurrentUser).mockImplementation(
      () => new Promise(() => {}) // Never resolves
    )

    render(
      <MemoryRouter initialEntries={['/settings']}>
        <Settings />
      </MemoryRouter>
    )

    // Assert: loading message is shown
    expect(screen.getByText(/loading your settings/i)).toBeInTheDocument()
  })

  it('renders settings when user is successfully loaded from cache', async () => {
    // Arrange: mock cached user
    vi.mocked(auth.getCurrentUser).mockReturnValue({
      id: 'user-123',
      email: 'test@example.com',
      name: 'Test User',
    })

    render(
      <MemoryRouter initialEntries={['/settings']}>
        <Settings />
      </MemoryRouter>
    )

    // Wait for settings to render
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /settings/i })).toBeInTheDocument()
    })

    // Verify email is displayed
    expect(screen.getByText('test@example.com')).toBeInTheDocument()

    // Verify fetchAndCacheCurrentUser was NOT called (used cache)
    expect(auth.fetchAndCacheCurrentUser).not.toHaveBeenCalled()
  })

  it('renders settings when user is successfully fetched from API', async () => {
    // Arrange: no cached user, but API returns user
    vi.mocked(auth.getCurrentUser).mockReturnValue(null)
    vi.mocked(auth.fetchAndCacheCurrentUser).mockResolvedValue({
      id: 'user-456',
      email: 'fresh@example.com',
      name: 'Fresh User',
    })

    render(
      <MemoryRouter initialEntries={['/settings']}>
        <Settings />
      </MemoryRouter>
    )

    // Assert: loading initially
    expect(screen.getByText(/loading your settings/i)).toBeInTheDocument()

    // Wait for settings to render
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /settings/i })).toBeInTheDocument()
    })

    // Verify email is displayed
    expect(screen.getByText('fresh@example.com')).toBeInTheDocument()
  })

  it('redirects when fetchAndCacheCurrentUser throws an error', async () => {
    // Arrange: mock auth to throw error
    vi.mocked(auth.getCurrentUser).mockReturnValue(null)
    vi.mocked(auth.fetchAndCacheCurrentUser).mockRejectedValue(
      new Error('Network error')
    )

    render(
      <MemoryRouter initialEntries={['/settings']}>
        <Routes>
          <Route path="/settings" element={<Settings />} />
          <Route
            path="/welcome"
            element={<div data-testid="welcome-page">Welcome Page</div>}
          />
        </Routes>
      </MemoryRouter>
    )

    // Wait for redirect to /welcome
    await waitFor(
      () => {
        expect(screen.getByTestId('welcome-page')).toBeInTheDocument()
      },
      { timeout: 2000 }
    )
  })

  it('redirects when user exists but has no email', async () => {
    // Arrange: mock user without email (edge case)
    vi.mocked(auth.getCurrentUser).mockReturnValue(null)
    vi.mocked(auth.fetchAndCacheCurrentUser).mockResolvedValue({
      id: 'user-789',
      email: null,
      name: 'No Email User',
    } as any)

    render(
      <MemoryRouter initialEntries={['/settings']}>
        <Routes>
          <Route path="/settings" element={<Settings />} />
          <Route
            path="/welcome"
            element={<div data-testid="welcome-page">Welcome Page</div>}
          />
        </Routes>
      </MemoryRouter>
    )

    // Wait for redirect to /welcome
    await waitFor(
      () => {
        expect(screen.getByTestId('welcome-page')).toBeInTheDocument()
      },
      { timeout: 2000 }
    )
  })
})
