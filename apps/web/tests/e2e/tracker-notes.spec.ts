import { test, expect } from './fixtures'
import { assertToast } from './utils'

test.describe('Tracker inline notes', () => {
  test('quick-edit saves on blur and shows toast', async ({ page, withMockedNet }) => {
    const row = {
      id: 303,
      company: 'Stripe',
      role: 'AI SWE',
      source: 'Lever',
      status: 'applied',
      last_email_snippet: null,
      thread_id: null,
      notes: '',
      created_at: '2025-10-01T12:00:00Z',
      updated_at: '2025-10-01T12:00:00Z',
    }

    await withMockedNet([
      {
        url: '/api/applications',
        method: 'GET',
        body: [row],
      },
      {
        url: '/api/applications/303',
        method: 'PATCH',
        body: {
          ...row,
          notes: 'Followed up with recruiter',
          updated_at: '2025-10-01T12:05:00Z',
        },
      },
    ])

    await page.goto('/tracker')
    await expect(page.getByTestId('tracker-row-303')).toBeVisible()

    // Click preview to expand editor
    await page.getByTestId('note-303-preview').click()
    const editor = page.getByTestId('note-303-editor')
    await editor.fill('Followed up with recruiter')

    // press Cmd+Enter to save
    await editor.press('Meta+Enter')

    // toast visible
    await assertToast(page, { title: /Note saved/i, desc: /Stripe/i, variant: 'success' })
  })

  test('Cmd+Enter saves, Escape cancels', async ({ page, withMockedNet }) => {
    const row = {
      id: 404,
      company: 'Meta',
      role: 'Research Scientist',
      source: 'LinkedIn',
      status: 'hr_screen',
      last_email_snippet: null,
      thread_id: null,
      notes: 'Initial contact',
      created_at: '2025-10-01T12:00:00Z',
      updated_at: '2025-10-01T12:00:00Z',
    }

    await withMockedNet([
      {
        url: '/api/applications',
        method: 'GET',
        body: [row],
      },
      {
        url: '/api/applications/404',
        method: 'PATCH',
        body: { ...row, notes: 'Updated note', updated_at: '2025-10-01T12:10:00Z' },
      },
    ])

    await page.goto('/tracker')
    await expect(page.getByTestId('tracker-row-404')).toBeVisible()

    // Test Escape cancels
    await page.getByTestId('note-404-preview').click()
    const editor = page.getByTestId('note-404-editor')
    await editor.fill('This should be cancelled')
    await editor.press('Escape')
    await expect(page.getByTestId('note-404-preview')).toContainText('Initial contact')

    // Test Cmd+Enter saves
    await page.getByTestId('note-404-preview').click()
    await editor.fill('Updated note')
    await editor.press('Meta+Enter')
    await expect(page.locator('text=Note saved')).toBeVisible()
  })
})
