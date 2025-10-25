import { test, expect } from '@playwright/test'

test.describe('@prodSafe search smoke', () => {
  test('search button updates UI', async ({ page }) => {
    await page.goto('/search?q=Interview')

    // Wait a moment for hydration
    await page.waitForTimeout(1000)

    // Click search button
    await page.getByTestId('search-button').click()

    // Should show loading
    await expect(page.getByTestId('search-loading')).toBeVisible({ timeout: 5000 })

    // Should show either results or empty state
    await expect.poll(async () => {
      const n = await page.getByTestId('result-item').count()
      const empty = await page.getByTestId('empty-state').isVisible().catch(() => false)
      return n > 0 || empty
    }, { timeout: 10000 }).toBeTruthy()
  })

  test('typing query and pressing Enter triggers search', async ({ page }) => {
    await page.goto('/search')

    // Type a query
    await page.getByTestId('search-input').fill('offer')

    // Press Enter
    await page.getByTestId('search-input').press('Enter')

    // Should show loading
    await expect(page.getByTestId('search-loading')).toBeVisible({ timeout: 5000 })

    // Should show results or empty
    await expect.poll(async () => {
      const n = await page.getByTestId('result-item').count()
      const empty = await page.getByTestId('empty-state').isVisible().catch(() => false)
      return n > 0 || empty
    }, { timeout: 10000 }).toBeTruthy()
  })

  test('category filter toggle triggers new search', async ({ page }) => {
    await page.goto('/search?q=Interview')

    // Wait for initial load
    await page.waitForTimeout(2000)

    // Toggle promotions filter
    await page.getByTestId('filter-promotions').click()

    // Should show loading
    await expect(page.getByTestId('search-loading')).toBeVisible({ timeout: 5000 })

    // Should show results or empty
    await expect.poll(async () => {
      const n = await page.getByTestId('result-item').count()
      const empty = await page.getByTestId('empty-state').isVisible().catch(() => false)
      return n > 0 || empty
    }, { timeout: 10000 }).toBeTruthy()
  })
})
