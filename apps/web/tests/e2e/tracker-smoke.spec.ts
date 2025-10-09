import { test, expect, SMOKE } from './fixtures'
import { waitForNetworkIdle } from './network'

test.describe(`Tracker smoke ${SMOKE}`, () => {
  test('loads grid and filters', async ({ page, withMockedNet }) => {
    await withMockedNet([
      {
        url: '/api/applications', // matches both relative and absolute proxied URLs
        method: 'GET',
        body: [
          {
            id: 1,
            company: 'Acme',
            role: 'ML Eng',
            source: 'Lever',
            status: 'applied',
            created_at: '',
            updated_at: '',
          },
        ],
      },
    ])
    await page.goto('/tracker')
    await waitForNetworkIdle(page)
    await expect(page.getByText('Acme')).toBeVisible()
    await page.getByTestId('tracker-status-filter').selectOption('applied')
  })
})
