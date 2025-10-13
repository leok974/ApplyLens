/**
 * Phase 6: Chat Mode Tests
 * 
 * Tests the mode selector (networking/money/off) and verifies it's
 * properly wired to the SSE stream URL.
 */
import { test, expect } from '@playwright/test'

test('Chat mode toggles are wired to SSE URL', async ({ page }) => {
  let requestedUrl = ''

  await page.route('/api/chat/stream**', route => {
    requestedUrl = route.request().url()
    const headers = { 'Content-Type': 'text/event-stream' }
    const body = 'event: done\ndata: {"ok":true}\n\n'
    route.fulfill({ status: 200, headers, body })
  })

  await page.goto('http://localhost:5176/chat')

  // Select money mode
  await page.getByLabel('assistant mode').selectOption('money')

  // Type a query
  await page.getByPlaceholder('Ask your mailbox anything...').fill('Summarize receipts.')

  // Send
  await page.getByRole('button', { name: 'Send' }).click()

  // Verify mode is in URL
  await expect.poll(() => requestedUrl.includes('mode=money')).toBeTruthy()
})

test('Money mode shows receipts export link', async ({ page }) => {
  await page.goto('http://localhost:5176/chat')

  // Initially no export link
  await expect(page.getByText('Export receipts (CSV)')).not.toBeVisible()

  // Select money mode
  await page.getByLabel('assistant mode').selectOption('money')

  // Now export link appears
  await expect(page.getByText('Export receipts (CSV)')).toBeVisible()

  // Verify link href
  const link = page.getByRole('link', { name: 'Export receipts (CSV)' })
  await expect(link).toHaveAttribute('href', '/api/money/receipts.csv')
})

test('Networking mode is wired to SSE URL', async ({ page }) => {
  let requestedUrl = ''

  await page.route('/api/chat/stream**', route => {
    requestedUrl = route.request().url()
    const headers = { 'Content-Type': 'text/event-stream' }
    const body = 'event: done\ndata: {"ok":true}\n\n'
    route.fulfill({ status: 200, headers, body })
  })

  await page.goto('http://localhost:5176/chat')

  // Select networking mode
  await page.getByLabel('assistant mode').selectOption('networking')

  // Type a query
  await page.getByPlaceholder('Ask your mailbox anything...').fill('Show upcoming events.')

  // Send
  await page.getByRole('button', { name: 'Send' }).click()

  // Verify mode is in URL
  await expect.poll(() => requestedUrl.includes('mode=networking')).toBeTruthy()
})

test('Mode off does not add mode parameter', async ({ page }) => {
  let requestedUrl = ''

  await page.route('/api/chat/stream**', route => {
    requestedUrl = route.request().url()
    const headers = { 'Content-Type': 'text/event-stream' }
    const body = 'event: done\ndata: {"ok":true}\n\n'
    route.fulfill({ status: 200, headers, body })
  })

  await page.goto('http://localhost:5176/chat')

  // Ensure mode is off
  await page.getByLabel('assistant mode').selectOption('')

  // Type a query
  await page.getByPlaceholder('Ask your mailbox anything...').fill('Show my emails.')

  // Send
  await page.getByRole('button', { name: 'Send' }).click()

  // Verify mode is NOT in URL
  await expect.poll(() => !requestedUrl.includes('mode=')).toBeTruthy()
})

test('Mode selector persists across queries', async ({ page }) => {
  await page.route('/api/chat/stream**', route => {
    const headers = { 'Content-Type': 'text/event-stream' }
    const body = 'event: done\ndata: {"ok":true}\n\n'
    route.fulfill({ status: 200, headers, body })
  })

  await page.goto('http://localhost:5176/chat')

  // Set to networking mode
  await page.getByLabel('assistant mode').selectOption('networking')

  // Send first query
  await page.getByPlaceholder('Ask your mailbox anything...').fill('First query.')
  await page.getByRole('button', { name: 'Send' }).click()

  // Wait a moment
  await page.waitForTimeout(500)

  // Mode should still be networking
  await expect(page.getByLabel('assistant mode')).toHaveValue('networking')

  // Change to money mode
  await page.getByLabel('assistant mode').selectOption('money')

  // Send second query
  await page.getByPlaceholder('Ask your mailbox anything...').fill('Second query.')
  await page.getByRole('button', { name: 'Send' }).click()

  // Mode should still be money
  await expect(page.getByLabel('assistant mode')).toHaveValue('money')
})
