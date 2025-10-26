import { test, expect } from '@playwright/test'

test.describe('Mailbox Assistant small talk', () => {
  test('responds conversationally to "hi" without backend error text @prodSafe', async ({ page }) => {
    // go to chat page
    await page.goto('https://applylens.app/chat')

    // Wait for page to be fully loaded
    await page.waitForLoadState('networkidle')

    // Find the input field - be more specific
    const input = page.locator('input[placeholder*="Ask your mailbox"]').or(page.locator('textarea'))
    await input.waitFor({ state: 'visible', timeout: 10000 })
    await input.fill('hi')
    await input.press('Enter')

    // wait for assistant bubble to appear with more time
    const assistantBubble = page.locator('text=I can:').first()
    await expect(assistantBubble).toBeVisible({ timeout: 10000 })

    // assert the "You could ask:" helper shows
    await expect(
      page.locator('text=You could ask:')
    ).toBeVisible()

    // assert we did NOT render the legacy "No emails found matching your query."
    await expect(
      page.locator('text=No emails found matching your query').first()
    ).toHaveCount(0)
  })
})
