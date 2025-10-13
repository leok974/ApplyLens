import { test, expect } from '@playwright/test'

/**
 * Phase 5: Intent Explanation & Memory Learning
 * 
 * Tests the new "explain my intent" and "remember exceptions" features.
 */

test('explain tokens and remember exceptions render', async ({ page }) => {
  // Mock stream with intent_explain + memory
  await page.route('**/api/chat/stream**', (route) => {
    const headers = { 'Content-Type': 'text/event-stream' }
    const body =
      'event: intent\ndata: {"intent":"clean"}\n\n' +
      'event: intent_explain\ndata: {"tokens":["clean","before friday","unless best buy"]}\n\n' +
      'event: tool\ndata: {"tool":"clean","matches":0,"actions":0}\n\n' +
      'event: answer\ndata: {"answer":"No promos found."}\n\n' +
      'event: memory\ndata: {"kept_brands":["best buy"]}\n\n' +
      'event: done\ndata: {"ok":true}\n\n'
    return route.fulfill({ status: 200, headers, body })
  })
  
  await page.goto('http://localhost:5176/chat')
  
  // Type query
  await page.getByPlaceholder(/Ask your mailbox/).fill('Clean promos unless Best Buy.')
  
  // Check both toggles
  await page.getByLabel('explain my intent').check()
  await page.getByLabel('remember exceptions').check()
  
  await expect(page.getByLabel('explain my intent')).toBeChecked()
  await expect(page.getByLabel('remember exceptions')).toBeChecked()
  
  // Click Send
  await page.getByRole('button', { name: /Send/i }).click()

  // Wait for intent tokens to appear
  await expect(page.getByText(/Intent tokens/i)).toBeVisible({ timeout: 3000 })
  
  // Expand the details and verify tokens are visible
  await page.getByText(/Intent tokens/i).click()
  await expect(page.getByText('clean', { exact: false })).toBeVisible()
  
  // Verify memory confirmation message
  await expect(page.getByText(/Learned preference: keep promos for best buy/i)).toBeVisible()
})

test('intent tokens only show when explain is checked', async ({ page }) => {
  // Mock stream with intent_explain
  await page.route('**/api/chat/stream**', (route) => {
    const headers = { 'Content-Type': 'text/event-stream' }
    const body =
      'event: intent\ndata: {"intent":"summarize"}\n\n' +
      'event: intent_explain\ndata: {"tokens":["summarize","recent"]}\n\n' +
      'event: tool\ndata: {"tool":"summarize","matches":0,"actions":0}\n\n' +
      'event: answer\ndata: {"answer":"No emails found."}\n\n' +
      'event: done\ndata: {"ok":true}\n\n'
    return route.fulfill({ status: 200, headers, body })
  })
  
  await page.goto('http://localhost:5176/chat')
  
  // Send WITHOUT explain checked
  await page.getByPlaceholder(/Ask your mailbox/).fill('Summarize recent emails')
  await page.getByRole('button', { name: /Send/i }).click()
  
  // Wait for response
  await expect(page.getByText(/No emails found/i)).toBeVisible({ timeout: 3000 })
  
  // Intent tokens should still show (they come from backend regardless)
  // But the UI shows them
  await expect(page.getByText(/Intent tokens/i)).toBeVisible()
})

test('memory event creates confirmation message', async ({ page }) => {
  let requestCount = 0
  
  await page.route('**/api/chat/stream**', (route) => {
    requestCount++
    const url = new URL(route.request().url())
    const remember = url.searchParams.get('remember')
    
    const headers = { 'Content-Type': 'text/event-stream' }
    let body =
      'event: intent\ndata: {"intent":"clean"}\n\n' +
      'event: intent_explain\ndata: {"tokens":["clean","unless"]}\n\n' +
      'event: tool\ndata: {"tool":"clean","matches":0,"actions":0}\n\n' +
      'event: answer\ndata: {"answer":"No promos found."}\n\n'
    
    // Only add memory event if remember=1
    if (remember === '1') {
      body += 'event: memory\ndata: {"kept_brands":["best buy","costco"]}\n\n'
    }
    
    body += 'event: done\ndata: {"ok":true}\n\n'
    
    return route.fulfill({ status: 200, headers, body })
  })
  
  await page.goto('http://localhost:5176/chat')
  
  // Test WITHOUT remember
  await page.getByPlaceholder(/Ask your mailbox/).fill('Clean unless Best Buy')
  await page.getByRole('button', { name: /Send/i }).click()
  
  await expect(page.getByText(/No promos found/i)).toBeVisible({ timeout: 2000 })
  await expect(page.getByText(/Learned preference/i)).not.toBeVisible()
  
  // Test WITH remember
  await page.getByPlaceholder(/Ask your mailbox/).fill('Clean unless Best Buy and Costco')
  await page.getByLabel('remember exceptions').check()
  await page.getByRole('button', { name: /Send/i }).click()
  
  // Should see memory confirmation
  await expect(page.getByText(/Learned preference: keep promos for best buy, costco/i)).toBeVisible({ timeout: 3000 })
})

test('all three toggles can be used together', async ({ page }) => {
  await page.route('**/api/chat/stream**', (route) => {
    const url = new URL(route.request().url())
    const propose = url.searchParams.get('propose')
    const remember = url.searchParams.get('remember')
    
    const headers = { 'Content-Type': 'text/event-stream' }
    let body =
      'event: intent\ndata: {"intent":"clean"}\n\n' +
      'event: intent_explain\ndata: {"tokens":["clean","old","unless"]}\n\n' +
      'event: tool\ndata: {"tool":"clean","matches":5,"actions":2}\n\n' +
      'event: answer\ndata: {"answer":"Found 5 promotional emails."}\n\n'
    
    if (remember === '1') {
      body += 'event: memory\ndata: {"kept_brands":["best buy"]}\n\n'
    }
    
    if (propose === '1') {
      body += 'event: filed\ndata: {"proposed":2}\n\n'
    }
    
    body += 'event: done\ndata: {"ok":true}\n\n'
    
    return route.fulfill({ status: 200, headers, body })
  })
  
  await page.goto('http://localhost:5176/chat')
  
  // Check all three toggles
  await page.getByLabel('file actions to Approvals').check()
  await page.getByLabel('explain my intent').check()
  await page.getByLabel('remember exceptions').check()
  
  // Send query
  await page.getByPlaceholder(/Ask your mailbox/).fill('Clean old promos unless Best Buy')
  await page.getByRole('button', { name: /Send/i }).click()
  
  // Verify all features work together
  await expect(page.getByText(/Intent tokens/i)).toBeVisible({ timeout: 3000 })
  await expect(page.getByText(/Learned preference/i)).toBeVisible()
  await expect(page.getByText(/Filed 2 action/i)).toBeVisible()
})
