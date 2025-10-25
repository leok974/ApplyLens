import { test, expect } from '@playwright/test'

/**
 * Smoke test: Verify search page renders results list when API returns hits
 *
 * This test locks in the critical rendering path:
 * - Results render when not loading and items exist
 * - Not gated on suggestions or "hasSearched" flags
 * - Handles all plausible response shapes (items, results, hits)
 */
test.describe('@prodSafe Search results rendering', () => {
  test('search renders list when API has hits', async ({ page }) => {
    // Navigate to search page
    await page.goto('/search')

    // Search input should be visible and ready
    const searchInput = page.getByTestId('search-input')
    await searchInput.waitFor({ state: 'visible' })

    // Enter wildcard query to match all documents
    await searchInput.fill('*')
    await page.keyboard.press('Enter')

    // Results list should appear
    await page.getByTestId('results-list').waitFor({ state: 'visible', timeout: 10000 })

    // Should have at least one result item
    const count = await page.getByTestId('result-item').count()
    expect(count).toBeGreaterThan(0)

    console.log(`✓ Search rendered ${count} result items`)
  })

  test('results render immediately on page load with default query', async ({ page }) => {
    // Navigate to search with pre-filled query
    await page.goto('/search?q=Interview')

    // Results should render without needing to click Search
    await page.getByTestId('results-list').waitFor({ state: 'visible', timeout: 10000 })

    const count = await page.getByTestId('result-item').count()
    expect(count).toBeGreaterThan(0)

    console.log(`✓ Auto-search rendered ${count} result items`)
  })

  test('wildcard search shows all results (match-all behavior)', async ({ page }) => {
    await page.goto('/search')

    const searchInput = page.getByTestId('search-input')
    await searchInput.waitFor({ state: 'visible' })

    // Enter explicit wildcard
    await searchInput.clear()
    await searchInput.fill('*')

    // Submit search
    await page.getByTestId('search-button').click()

    // Should show results
    await page.getByTestId('results-list').waitFor({ state: 'visible', timeout: 10000 })

    const count = await page.getByTestId('result-item').count()
    expect(count).toBeGreaterThan(0)

    console.log(`✓ Wildcard search rendered ${count} result items`)
  })

  test('results list is not hidden by overlays or CSS', async ({ page }) => {
    await page.goto('/search?q=Interview')

    // Wait for results
    const resultsList = page.getByTestId('results-list')
    await resultsList.waitFor({ state: 'visible', timeout: 10000 })

    // Check if list is actually visible in the viewport
    const isInViewport = await resultsList.boundingBox()
    expect(isInViewport).not.toBeNull()
    expect(isInViewport!.width).toBeGreaterThan(0)
    expect(isInViewport!.height).toBeGreaterThan(0)

    // Check computed styles
    const display = await resultsList.evaluate(el => getComputedStyle(el).display)
    const visibility = await resultsList.evaluate(el => getComputedStyle(el).visibility)
    const opacity = await resultsList.evaluate(el => getComputedStyle(el).opacity)

    expect(display).not.toBe('none')
    expect(visibility).not.toBe('hidden')
    expect(parseFloat(opacity)).toBeGreaterThan(0)

    console.log(`✓ Results list is visible and not hidden by CSS`)
  })

  test('suggestion failures do not prevent results rendering', async ({ page }) => {
    // Block suggestions endpoint
    await page.route('**/api/suggest/**', route => {
      route.abort('failed')
    })

    await page.goto('/search')

    const searchInput = page.getByTestId('search-input')
    await searchInput.fill('Interview')
    await page.keyboard.press('Enter')

    // Results should still render
    await page.getByTestId('results-list').waitFor({ state: 'visible', timeout: 10000 })

    const count = await page.getByTestId('result-item').count()
    expect(count).toBeGreaterThan(0)

    console.log(`✓ Results rendered despite suggestion failure: ${count} items`)
  })

  test('@prodSafe API smoke: /api/search wildcard returns 200', async ({ request }) => {
    const response = await request.get('/api/search/?q=*&scale=all&limit=1')
    expect(response.status()).toBe(200)

    const json = await response.json()
    console.log(`✓ API smoke test passed, response keys: ${Object.keys(json).join(', ')}`)
  })
})
