/**
 * Phase 6: Policy Accuracy Panel Tests
 * 
 * Tests the PolicyAccuracyPanel component that shows precision bars
 * and policy performance metrics.
 */
import { test, expect } from '@playwright/test'

test('Policy Accuracy panel loads and shows bars', async ({ page }) => {
  // Mock the policy stats API
  await page.route('/api/policy/stats', route => {
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        { 
          policy_id: 1, 
          name: 'Promo auto-archive', 
          precision: 0.82, 
          approved: 41, 
          rejected: 9, 
          fired: 50 
        },
        { 
          policy_id: 2, 
          name: 'High-risk quarantine', 
          precision: 0.96, 
          approved: 48, 
          rejected: 2, 
          fired: 50 
        },
      ])
    })
  })

  await page.goto('http://localhost:5176/chat')

  // Check panel title
  await expect(page.getByText('Policy Accuracy (30d)')).toBeVisible()

  // Check first policy
  await expect(page.getByText('Promo auto-archive')).toBeVisible()
  await expect(page.getByText('82%')).toBeVisible()
  await expect(page.getByText(/fired 50/)).toBeVisible()

  // Check second policy
  await expect(page.getByText('High-risk quarantine')).toBeVisible()
  await expect(page.getByText('96%')).toBeVisible()
})

test('Policy Accuracy panel handles empty state', async ({ page }) => {
  await page.route('/api/policy/stats', route => {
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([])
    })
  })

  await page.goto('http://localhost:5176/chat')

  await expect(page.getByText('Policy Accuracy (30d)')).toBeVisible()
  await expect(page.getByText('No data yet.')).toBeVisible()
})

test('Policy Accuracy panel refresh button works', async ({ page }) => {
  let requestCount = 0

  await page.route('/api/policy/stats', route => {
    requestCount++
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        { 
          policy_id: 1, 
          name: `Policy ${requestCount}`, 
          precision: 0.82, 
          approved: 41, 
          rejected: 9, 
          fired: 50 
        },
      ])
    })
  })

  await page.goto('http://localhost:5176/chat')

  // Wait for initial load
  await expect(page.getByText('Policy 1')).toBeVisible()

  // Click refresh
  await page.getByRole('button', { name: 'Refresh' }).click()

  // Should trigger a new request
  await expect(page.getByText('Policy 2')).toBeVisible()
  expect(requestCount).toBeGreaterThanOrEqual(2)
})

test('Policy Accuracy panel handles errors', async ({ page }) => {
  await page.route('/api/policy/stats', route => {
    route.fulfill({
      status: 500,
      contentType: 'application/json',
      body: JSON.stringify({ error: 'Server error' })
    })
  })

  await page.goto('http://localhost:5176/chat')

  await expect(page.getByText('Policy Accuracy (30d)')).toBeVisible()
  await expect(page.getByText(/Failed to load policy stats/)).toBeVisible()
})
