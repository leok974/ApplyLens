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

test.describe('Phase 3: LLM Provider Telemetry', () => {
  test('assistant returns llm_used field in response @prodSafe', async ({ page }) => {
    await page.goto('https://applylens.app/chat')
    await page.waitForLoadState('networkidle')

    // Listen for API responses to capture llm_used field
    let llmUsedField: string | null = null
    let apiResponseReceived = false

    page.on('response', async (response) => {
      if (response.url().includes('/assistant/query') && response.request().method() === 'POST') {
        try {
          const json = await response.json()
          apiResponseReceived = true
          if (json.llm_used) {
            llmUsedField = json.llm_used
            console.log(`✓ llm_used field: ${json.llm_used}`)
          }
        } catch (e) {
          // Ignore parse errors
        }
      }
    })

    // Find input and send a query that will hit the backend
    // (NOT a greeting, which is handled client-side)
    const input = page.locator('[data-testid="mailbox-input"]')
    await input.waitFor({ state: 'visible', timeout: 10000 })
    await input.fill('show suspicious emails')

    const sendButton = page.locator('[data-testid="mailbox-send"]')
    await sendButton.click()

    // Wait for actual response (not just typing indicator)
    await expect(
      page.locator('text=In the last').or(page.locator('text=emails').or(page.locator('text=found')))
    ).toBeVisible({ timeout: 15000 })

    // Assert API was called
    expect(apiResponseReceived).toBeTruthy()

    // Assert llm_used field is present and valid
    // In CI we don't require "ollama" specifically - could be "openai" or "template"
    // In production, manual verification confirms it's "ollama"
    expect(llmUsedField).toBeTruthy()
    expect(['ollama', 'openai', 'template']).toContain(llmUsedField)
  })
})

test.describe('Phase 3: Typing indicator', () => {
  test('shows typing indicator during assistant response @prodSafe', async ({ page }) => {
    await page.goto('https://applylens.app/chat')
    await page.waitForLoadState('networkidle')

    // Listen for API responses to capture llm_used field
    let llmUsedField: string | null = null
    page.on('response', async (response) => {
      if (response.url().includes('/assistant/query')) {
        try {
          const json = await response.json()
          if (json.llm_used) {
            llmUsedField = json.llm_used
            console.log(`✓ llm_used field: ${json.llm_used}`)
          }
        } catch (e) {
          // Ignore parse errors
        }
      }
    })

    // Find input and send a query that will hit the backend
    const input = page.locator('input[placeholder*="Ask your mailbox"]').or(page.locator('textarea'))
    await input.waitFor({ state: 'visible', timeout: 10000 })
    await input.fill('show suspicious emails')

    // Start listening for the typing indicator BEFORE pressing Enter
    const typingIndicator = page.locator('text=Assistant is thinking')

    await input.press('Enter')

    // Typing indicator should appear quickly
    await expect(typingIndicator).toBeVisible({ timeout: 2000 })

    // Wait for actual response
    await expect(
      page.locator('text=In the last').or(page.locator('text=emails'))
    ).toBeVisible({ timeout: 15000 })

    // Typing indicator should disappear after response
    await expect(typingIndicator).not.toBeVisible({ timeout: 2000 })

    // Assert llm_used field is present and valid
    // Allow any value in CI (ollama/openai/fallback) since we may not have Ollama in CI
    expect(llmUsedField).toBeTruthy()
    expect(['ollama', 'openai', 'fallback']).toContain(llmUsedField)
  })
})

test.describe('Phase 3: Short-term memory', () => {
  test('remembers context for follow-up queries @prodSafe', async ({ page }) => {
    await page.goto('https://applylens.app/chat')
    await page.waitForLoadState('networkidle')

    const input = page.locator('input[placeholder*="Ask your mailbox"]').or(page.locator('textarea'))
    await input.waitFor({ state: 'visible', timeout: 10000 })

    // First query: establish context
    await input.fill('show suspicious emails')
    await input.press('Enter')

    // Wait for first response
    await expect(
      page.locator('text=In the last').or(page.locator('text=emails'))
    ).toBeVisible({ timeout: 15000 })

    // Follow-up query with anaphora
    await input.fill('mute them')
    await input.press('Enter')

    // Response should acknowledge the context
    await expect(
      page.locator('text=suspicious').or(page.locator('text=previous').or(page.locator('text=referring')))
    ).toBeVisible({ timeout: 15000 })
  })
})
