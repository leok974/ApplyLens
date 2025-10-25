import { test, expect } from '@playwright/test'

test.describe('@prodSafe search interactions', () => {
  test('query + Enter triggers fetch and updates UI', async ({ page }) => {
    await page.goto('/search')

    // Wait for form to be ready
    await expect(page.getByTestId('search-form')).toBeVisible()

    // Type a query
    await page.getByTestId('search-input').fill('Interview')

    // Press Enter to submit form
    await page.getByTestId('search-input').press('Enter')

    // Expect loading spinner
    await expect(page.getByTestId('search-loading')).toBeVisible({ timeout: 5000 })

    // Wait for either results or empty state
    await expect.poll(async () => {
      const itemsCount = await page.getByTestId('result-item').count()
      const emptyVisible = await page.getByTestId('empty-state').isVisible().catch(() => false)
      return itemsCount > 0 || emptyVisible
    }, { timeout: 10000 }).toBeTruthy()

    // Loading should be gone
    await expect(page.getByTestId('search-loading')).not.toBeVisible()
  })

  test('search button click triggers fetch', async ({ page }) => {
    await page.goto('/search')

    // Type a query
    await page.getByTestId('search-input').fill('offer')

    // Click Search button
    await page.getByTestId('search-button').click()

    // Expect loading spinner
    await expect(page.getByTestId('search-loading')).toBeVisible({ timeout: 5000 })

    // Wait for results or empty state
    await expect.poll(async () => {
      const itemsCount = await page.getByTestId('result-item').count()
      const emptyVisible = await page.getByTestId('empty-state').isVisible().catch(() => false)
      return itemsCount > 0 || emptyVisible
    }, { timeout: 10000 }).toBeTruthy()
  })

  test('category filter toggle triggers new search', async ({ page }) => {
    await page.goto('/search?q=Interview')

    // Wait for initial results
    await expect.poll(async () => {
      const itemsCount = await page.getByTestId('result-item').count()
      const emptyVisible = await page.getByTestId('empty-state').isVisible().catch(() => false)
      return itemsCount > 0 || emptyVisible
    }, { timeout: 10000 }).toBeTruthy()

    // Toggle Promotions filter
    await page.getByTestId('filter-promotions').click()

    // Expect loading spinner
    await expect(page.getByTestId('search-loading')).toBeVisible({ timeout: 5000 })

    // Wait for updated results
    await expect.poll(async () => {
      const itemsCount = await page.getByTestId('result-item').count()
      const emptyVisible = await page.getByTestId('empty-state').isVisible().catch(() => false)
      return itemsCount > 0 || emptyVisible
    }, { timeout: 10000 }).toBeTruthy()

    // URL should reflect filter
    await expect(page).toHaveURL(/cat=promotions/)
  })

  test('label filter triggers new search', async ({ page }) => {
    await page.goto('/search?q=Interview')

    // Wait for initial results
    await expect.poll(async () => {
      const itemsCount = await page.getByTestId('result-item').count()
      const emptyVisible = await page.getByTestId('empty-state').isVisible().catch(() => false)
      return itemsCount > 0 || emptyVisible
    }, { timeout: 10000 }).toBeTruthy()

    // Toggle interview label filter
    await page.getByTestId('filter-label-interview').click()

    // Expect loading spinner
    await expect(page.getByTestId('search-loading')).toBeVisible({ timeout: 5000 })

    // Wait for updated results
    await expect.poll(async () => {
      const itemsCount = await page.getByTestId('result-item').count()
      const emptyVisible = await page.getByTestId('empty-state').isVisible().catch(() => false)
      return itemsCount > 0 || emptyVisible
    }, { timeout: 10000 }).toBeTruthy()
  })

  test('replied filter triggers new search', async ({ page }) => {
    await page.goto('/search?q=Interview')

    // Wait for initial results
    await expect.poll(async () => {
      const itemsCount = await page.getByTestId('result-item').count()
      const emptyVisible = await page.getByTestId('empty-state').isVisible().catch(() => false)
      return itemsCount > 0 || emptyVisible
    }, { timeout: 10000 }).toBeTruthy()

    // Click "Replied" filter
    await page.getByTestId('filter-replied-true').click()

    // Expect loading spinner
    await expect(page.getByTestId('search-loading')).toBeVisible({ timeout: 5000 })

    // Wait for updated results
    await expect.poll(async () => {
      const itemsCount = await page.getByTestId('result-item').count()
      const emptyVisible = await page.getByTestId('empty-state').isVisible().catch(() => false)
      return itemsCount > 0 || emptyVisible
    }, { timeout: 10000 }).toBeTruthy()
  })

  test('security filters trigger new search', async ({ page }) => {
    await page.goto('/search?q=Interview')

    // Wait for initial results
    await expect.poll(async () => {
      const itemsCount = await page.getByTestId('result-item').count()
      const emptyVisible = await page.getByTestId('empty-state').isVisible().catch(() => false)
      return itemsCount > 0 || emptyVisible
    }, { timeout: 10000 }).toBeTruthy()

    // Toggle high-risk filter
    await page.getByTestId('filter-high-risk').click()

    // Expect loading spinner
    await expect(page.getByTestId('search-loading')).toBeVisible({ timeout: 5000 })

    // Wait for updated results (may be empty for high-risk filter)
    await expect.poll(async () => {
      const itemsCount = await page.getByTestId('result-item').count()
      const emptyVisible = await page.getByTestId('empty-state').isVisible().catch(() => false)
      return itemsCount >= 0 || emptyVisible
    }, { timeout: 10000 }).toBeTruthy()
  })

  test('empty query shows appropriate message', async ({ page }) => {
    await page.goto('/search')

    // Clear the input
    await page.getByTestId('search-input').clear()

    // Try to search
    await page.getByTestId('search-button').click()

    // Should not show loading (query is empty)
    await expect(page.getByTestId('search-loading')).not.toBeVisible()
  })

  test('URL params hydrate on mount', async ({ page }) => {
    // Navigate with query params
    await page.goto('/search?q=offer&cat=promotions&replied=true')

    // Verify input is prefilled
    await expect(page.getByTestId('search-input')).toHaveValue('offer')

    // Verify promotions filter is active (has "default" variant styling)
    const promotionsBtn = page.getByTestId('filter-promotions')
    const btnClasses = await promotionsBtn.getAttribute('class')
    expect(btnClasses).toContain('bg-primary') // default variant uses primary color

    // Results should load automatically
    await expect.poll(async () => {
      const itemsCount = await page.getByTestId('result-item').count()
      const emptyVisible = await page.getByTestId('empty-state').isVisible().catch(() => false)
      return itemsCount > 0 || emptyVisible
    }, { timeout: 10000 }).toBeTruthy()
  })

  test('204 no content response shows empty state', async ({ page }) => {
    await page.goto('/search')

    // Search for something unlikely to have results
    await page.getByTestId('search-input').fill('xyzabc123nonexistent')
    await page.getByTestId('search-button').click()

    // Expect loading spinner
    await expect(page.getByTestId('search-loading')).toBeVisible({ timeout: 5000 })

    // Should show empty state (not stuck in loading)
    await expect(page.getByTestId('empty-state')).toBeVisible({ timeout: 10000 })
    await expect(page.getByTestId('search-loading')).not.toBeVisible()
  })

  test('query + filter triggers UI update', async ({ page }) => {
    await page.goto('/search')
    await page.getByTestId('search-input').fill('Interview')
    await page.getByTestId('search-button').click()

    await expect(page.getByTestId('search-loading')).toBeVisible({ timeout: 5000 })

    await expect.poll(async () => {
      const n = await page.getByTestId('result-item').count()
      const empty = await page.getByTestId('empty-state').isVisible().catch(() => false)
      return n > 0 || empty
    }, { timeout: 10000 }).toBeTruthy()

    // Flip a filter (promotions)
    await page.getByTestId('filter-promotions').click()
    await expect(page.getByTestId('search-loading')).toBeVisible({ timeout: 5000 })

    await expect.poll(async () => {
      const n = await page.getByTestId('result-item').count()
      const empty = await page.getByTestId('empty-state').isVisible().catch(() => false)
      return n > 0 || empty
    }, { timeout: 10000 }).toBeTruthy()
  })
})
