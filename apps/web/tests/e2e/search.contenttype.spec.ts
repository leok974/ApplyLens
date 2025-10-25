import { test, expect } from '@playwright/test'

/**
 * @prodSafe - Safe to run against production
 *
 * Verifies that the /api/search endpoint returns JSON content-type,
 * preventing regressions where HTML is returned instead of JSON
 * (which causes "Unexpected token '<'" parse errors).
 */
test.describe('@prodSafe content-type', () => {
  test('search API returns JSON', async ({ request }) => {
    const res = await request.get('/api/search?q=Interview&limit=1')

    // API may return 200, 204, 401 (auth), or 403 (forbidden) - all acceptable
    expect([200, 204, 401, 403]).toContain(res.status())

    const ct = res.headers()['content-type'] || ''

    // 204 No Content has no body, so content-type may be empty
    if (res.status() === 204) {
      // No content-type check needed for 204
      return
    }

    // For all other statuses, must be JSON
    expect(ct).toContain('application/json')
  })

  test('search API uses absolute URL (not relative)', async ({ page }) => {
    // Intercept network requests to verify URL
    const requests: string[] = []
    page.on('request', (req) => {
      const url = req.url()
      if (url.includes('/search')) {
        requests.push(url)
      }
    })

    // Navigate to search page (may fail auth, but we'll capture the request)
    await page.goto('/web/search', { waitUntil: 'networkidle' }).catch(() => {
      // Ignore auth errors - we just want to see the URL pattern
    })

    // Verify that any search requests use /api/search, NOT /web/search/ or /web/api/search
    const searchApiCalls = requests.filter(url => url.includes('/api/search'))
    const wrongCalls = requests.filter(url =>
      url.includes('/web/search/') ||
      url.includes('/web/api/search')
    )

    if (searchApiCalls.length > 0) {
      expect(searchApiCalls[0]).toMatch(/\/api\/search\?/)
    }

    expect(wrongCalls).toHaveLength(0)
  })
})
