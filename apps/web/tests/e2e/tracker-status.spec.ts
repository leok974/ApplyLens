import { test, expect } from './fixtures'
import { assertToast } from './utils'

test.describe('Tracker status transitions', () => {
  test('updates status → shows contextual toast', async ({ page, withMockedNet }) => {
    let latestStatus = 'applied'

    await withMockedNet([
      {
        url: '/api/applications',
        method: 'GET',
        body: [
          {
            id: 101,
            company: 'Acme AI',
            role: 'ML Engineer',
            source: 'Lever',
            status: 'applied',
            last_email_snippet: null,
            thread_id: 'thread-abc',
            notes: null,
            created_at: '2025-10-01T12:00:00Z',
            updated_at: '2025-10-01T12:00:00Z',
          },
        ],
      },
      {
        url: '/api/applications/101',
        method: 'PATCH',
        body: () => {
          return {
            id: 101,
            company: 'Acme AI',
            role: 'ML Engineer',
            source: 'Lever',
            status: latestStatus,
            last_email_snippet: null,
            thread_id: 'thread-abc',
            notes: null,
            created_at: '2025-10-01T12:00:00Z',
            updated_at: '2025-10-01T12:05:00Z',
          }
        },
      },
    ])

    await page.goto('/tracker')

    // Row appears
    await expect(page.getByTestId('tracker-row-101')).toBeVisible()

    // Change status to Interview
    const select = page.getByTestId('status-select-101')
    await select.selectOption('interview')
    latestStatus = 'interview'

    // Expect toast: Status: Interview — Acme AI
    await assertToast(page, { title: /Status:\s*Interview/i, desc: /Acme AI/i, variant: 'success' })
  })

  test('rejected path shows error toast', async ({ page, withMockedNet }) => {
    await withMockedNet([
      {
        url: '/api/applications',
        method: 'GET',
        body: [
          {
            id: 202,
            company: 'Meta',
            role: 'AI Engineer',
            source: 'Greenhouse',
            status: 'applied',
            last_email_snippet: null,
            thread_id: null,
            notes: null,
            created_at: '2025-10-01T12:00:00Z',
            updated_at: '2025-10-01T12:00:00Z',
          },
        ],
      },
      {
        url: '/api/applications/202',
        method: 'PATCH',
        body: {
          id: 202,
          company: 'Meta',
          role: 'AI Engineer',
          source: 'Greenhouse',
          status: 'rejected',
          last_email_snippet: null,
          thread_id: null,
          notes: null,
          created_at: '2025-10-01T12:00:00Z',
          updated_at: '2025-10-01T12:05:00Z',
        },
      },
    ])

    await page.goto('/tracker')
    await expect(page.getByTestId('tracker-row-202')).toBeVisible()

    const select = page.getByTestId('status-select-202')
    await select.selectOption('rejected')

    // Expect error toast
    await assertToast(page, { title: /Status:\s*Rejected/i, desc: /Meta/i, variant: 'error' })
  })

  test('create new application shows success toast', async ({ page, withMockedNet }) => {
    await withMockedNet([
      {
        url: '/api/applications',
        method: 'GET',
        body: [],
      },
      {
        url: '/api/applications',
        method: 'POST',
        body: (input?: any) => {
          return {
            id: 303,
            company: input?.company || 'OpenAI',
            role: input?.role || 'Research Engineer',
            source: input?.source || 'LinkedIn',
            status: 'applied',
            last_email_snippet: null,
            thread_id: null,
            notes: null,
            created_at: '2025-10-01T12:00:00Z',
            updated_at: '2025-10-01T12:00:00Z',
          }
        },
      },
    ])

    await page.goto('/tracker')

    // Click New button
    await page.getByTestId('tracker-new-btn').click()

    // Fill form
    await page.getByTestId('create-company').fill('OpenAI')
    await page.getByTestId('create-role').fill('Research Engineer')
    await page.getByTestId('create-source').fill('LinkedIn')

    // Click Save
    await page.getByTestId('create-save').click()

    // Expect success toast
    await assertToast(page, { title: /OpenAI/i, desc: /Research Engineer created/i, variant: 'success' })
  })
})
