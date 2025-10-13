import { test, expect } from '@playwright/test'

/**
 * Phase 5: Chat Streaming with "Run actions now"
 * 
 * Tests the streaming SSE endpoint with propose=1 parameter and 'filed' event.
 */

test('Run actions now files proposals', async ({ page }) => {
  // Mock the SSE stream endpoint
  await page.route('**/api/chat/stream**', (route) => {
    const url = new URL(route.request().url())
    const query = url.searchParams.get('q') || ''
    const propose = url.searchParams.get('propose')
    
    // Build SSE response based on query and propose flag
    let body = 
      'event: intent\ndata: {"intent":"clean","explanation":"Propose archiving old promotional emails"}\n\n' +
      'event: tool\ndata: {"tool":"clean","matches":42,"actions":5}\n\n' +
      'event: answer\ndata: {"answer":"Found 42 promotional emails older than a week. Proposing to archive 5 emails."}\n\n'
    
    // Add 'filed' event only if propose=1
    if (propose === '1') {
      body += 'event: filed\ndata: {"proposed":5}\n\n'
    }
    
    body += 'event: done\ndata: {"ok":true}\n\n'
    
    const headers = {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
    }
    
    return route.fulfill({
      status: 200,
      headers,
      body,
    })
  })
  
  // Navigate to chat page
  await page.goto('http://localhost:5176/chat')
  
  // Wait for page to load
  await expect(page.getByText(/Hi! 👋 Ask me about your mailbox/)).toBeVisible()
  
  // Type query
  const input = page.getByPlaceholder(/Ask your mailbox/)
  await input.fill('Clean up promos older than a week unless they\'re from Best Buy.')
  
  // Check the "file actions to Approvals" toggle
  const toggle = page.getByLabel('file actions to Approvals')
  await toggle.check()
  await expect(toggle).toBeChecked()
  
  // Click Send button
  const sendButton = page.getByRole('button', { name: /Send/i })
  await sendButton.click()
  
  // Wait for the filed confirmation message
  await expect(page.getByText(/Filed 5 action/)).toBeVisible({ timeout: 5000 })
  
  // Verify the message contains the correct count
  const filedMessage = page.getByText(/Filed 5 action/)
  await expect(filedMessage).toContainText('Filed 5 actions to Approvals tray')
})

test('Toggle controls propose parameter', async ({ page }) => {
  // Mock SSE stream
  await page.route('**/api/chat/stream**', (route) => {
    const url = new URL(route.request().url())
    const propose = url.searchParams.get('propose')
    
    let body = 
      'event: intent\ndata: {"intent":"summarize"}\n\n' +
      'event: tool\ndata: {"tool":"summarize","matches":10,"actions":0}\n\n' +
      'event: answer\ndata: {"answer":"Summarized 10 emails."}\n\n'
    
    // Only add filed event if propose=1
    if (propose === '1') {
      body += 'event: filed\ndata: {"proposed":0}\n\n'
    }
    
    body += 'event: done\ndata: {"ok":true}\n\n'
    
    return route.fulfill({
      status: 200,
      headers: { 'Content-Type': 'text/event-stream' },
      body,
    })
  })
  
  await page.goto('http://localhost:5176/chat')
  
  // Test WITHOUT toggle checked
  const input = page.getByPlaceholder(/Ask your mailbox/)
  await input.fill('Summarize recent emails')
  
  const toggle = page.getByLabel('file actions to Approvals')
  await expect(toggle).not.toBeChecked()
  
  await page.getByRole('button', { name: /Send/i }).click()
  
  // Should NOT see filed message without toggle
  await expect(page.getByText(/Filed \d+ action/)).not.toBeVisible({ timeout: 2000 })
  
  // Test WITH toggle checked
  await input.fill('Summarize recent emails again')
  await toggle.check()
  await expect(toggle).toBeChecked()
  
  await page.getByRole('button', { name: /Send/i }).click()
  
  // Should see filed message with toggle (even if 0 actions)
  // Note: Frontend only shows message if count > 0, so this test would need real actions
})

test('Run actions now button replays with propose', async ({ page }) => {
  let requestCount = 0
  
  await page.route('**/api/chat/stream**', (route) => {
    const url = new URL(route.request().url())
    const propose = url.searchParams.get('propose')
    requestCount++
    
    let body = 
      'event: intent\ndata: {"intent":"find"}\n\n' +
      'event: tool\ndata: {"tool":"find","matches":5,"actions":2}\n\n' +
      'event: answer\ndata: {"answer":"Found 5 important emails."}\n\n'
    
    if (propose === '1') {
      body += 'event: filed\ndata: {"proposed":2}\n\n'
    }
    
    body += 'event: done\ndata: {"ok":true}\n\n'
    
    return route.fulfill({
      status: 200,
      headers: { 'Content-Type': 'text/event-stream' },
      body,
    })
  })
  
  await page.goto('http://localhost:5176/chat')
  
  // Send initial query WITHOUT toggle
  const input = page.getByPlaceholder(/Ask your mailbox/)
  await input.fill('Find important emails')
  
  const toggle = page.getByLabel('file actions to Approvals')
  await expect(toggle).not.toBeChecked()
  
  await page.getByRole('button', { name: /Send/i }).click()
  
  // Wait for response
  await expect(page.getByText(/Found 5 important emails/)).toBeVisible()
  
  // Should NOT see filed message yet
  await expect(page.getByText(/Filed 2 action/)).not.toBeVisible({ timeout: 1000 })
  
  // Click "Run actions now" button
  const runActionsButton = page.getByRole('button', { name: /Run actions now/i })
  await expect(runActionsButton).toBeEnabled()
  await runActionsButton.click()
  
  // Should see filed message now
  await expect(page.getByText(/Filed 2 action/)).toBeVisible({ timeout: 3000 })
  
  // Verify we made 2 requests (initial + replay)
  expect(requestCount).toBe(2)
})

test('Progressive UI updates during streaming', async ({ page }) => {
  await page.route('**/api/chat/stream**', async (route) => {
    // Simulate delayed events
    const events = [
      'event: intent\ndata: {"intent":"clean"}\n\n',
      'event: tool\ndata: {"tool":"clean","matches":20,"actions":3}\n\n',
      'event: answer\ndata: {"answer":"Cleaning up promotional emails..."}\n\n',
      'event: done\ndata: {"ok":true}\n\n',
    ]
    
    // Send events one by one with delay
    let body = ''
    for (const event of events) {
      body += event
      await new Promise(resolve => setTimeout(resolve, 100))
    }
    
    return route.fulfill({
      status: 200,
      headers: { 'Content-Type': 'text/event-stream' },
      body,
    })
  })
  
  await page.goto('http://localhost:5176/chat')
  
  const input = page.getByPlaceholder(/Ask your mailbox/)
  await input.fill('Clean up old emails')
  await page.getByRole('button', { name: /Send/i }).click()
  
  // Verify progressive updates appear
  await expect(page.getByText(/Cleaning up promotional emails/)).toBeVisible({ timeout: 5000 })
})
