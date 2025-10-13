import { test, expect } from '@playwright/test'

test('mode=money is appended to SSE URL and shows export link', async ({ page }) => {
  let requestedUrl = ''
  await page.route('/api/chat/stream**', route => {
    requestedUrl = route.request().url()
    route.fulfill({ status: 200, headers: {'Content-Type':'text/event-stream'}, body: 'event: done\ndata: {"ok":true}\n\n' })
  })
  await page.goto('http://localhost:5176/chat')
  await page.getByLabel('assistant mode').selectOption('money')
  await page.getByPlaceholder('Ask your mailbox…').fill('Summarize receipts.')
  await page.getByRole('button', { name: 'Send' }).click()
  await expect.poll(()=>requestedUrl.includes('mode=money')).toBeTruthy()
  await expect(page.getByText('Export receipts (CSV)')).toBeVisible()
})
