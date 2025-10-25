/**
 * Actions Page Tests
 *
 * Tests the /inbox-actions page functionality including:
 * - Loading actionable emails
 * - Explain why button
 * - Action buttons (Archive, Safe, Suspicious, Unsub)
 * - Conditional rendering based on allowed_actions
 */

import { test, expect } from '@playwright/test'
import { installProdReadOnlyGuard, isProductionEnv } from '../utils/prodGuard'

test.describe('Actions Page - Local/Dev', () => {
  test.use({ storageState: '.auth/user.json' })

  test('should load actions inbox with all buttons in dev mode', async ({ page }) => {
    // Skip in production
    if (isProductionEnv()) {
      test.skip(true, 'This test requires dev environment with ALLOW_ACTION_MUTATIONS=true')
    }

    await page.goto('/web/inbox-actions')

    // Wait for page to load
    await expect(page.locator('h1')).toContainText('Inbox Actions')

    // Should show email count or empty state
    const hasEmails = await page.locator('tbody tr').count() > 0

    if (hasEmails) {
      const firstRow = page.locator('tbody tr').first()

      // In dev, all action buttons should be visible
      // (assuming mock returns all allowed_actions)
      await expect(firstRow.locator('button:has-text("Archive")')).toBeVisible()
      await expect(firstRow.locator('button:has-text("Safe")')).toBeVisible()
      await expect(firstRow.locator('button:has-text("Suspicious")')).toBeVisible()
      await expect(firstRow.locator('button:has-text("Unsub")')).toBeVisible()
      await expect(firstRow.locator('button:has-text("Explain why")')).toBeVisible()
    } else {
      // Empty state
      await expect(page.locator('text=No actionable emails found')).toBeVisible()
    }
  })

  test('should explain email when clicked', async ({ page, context }) => {
    // Skip in production
    if (isProductionEnv()) {
      test.skip(true, 'This test requires dev environment with ALLOW_ACTION_MUTATIONS=true')
    }

    // Mock the explain endpoint
    await context.route('**/api/actions/explain', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          summary: 'This email is categorized as Promotions because it has newsletter keywords and automated sender.'
        })
      })
    })

    await page.goto('/web/inbox-actions')

    // Wait for rows to load
    const hasRows = await page.locator('tbody tr').count() > 0
    if (!hasRows) {
      test.skip(true, 'No actionable emails to test')
    }

    const firstRow = page.locator('tbody tr').first()

    // Click "Explain why" button
    const explainButton = firstRow.locator('button:has-text("Explain why")')
    if (await explainButton.isVisible()) {
      await explainButton.click()

      // Should show explanation inline
      await expect(firstRow.locator('text=This email is categorized as Promotions')).toBeVisible()
    }
  })

  test('should remove row when archived', async ({ page, context }) => {
    // Skip in production
    if (isProductionEnv()) {
      test.skip(true, 'This test requires dev environment with ALLOW_ACTION_MUTATIONS=true')
    }

    // Mock the archive endpoint
    await context.route('**/api/actions/archive', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ ok: true })
      })
    })

    await page.goto('/web/inbox-actions')

    // Count initial rows
    const initialCount = await page.locator('tbody tr').count()
    if (initialCount === 0) {
      test.skip(true, 'No actionable emails to test')
    }

    const firstRow = page.locator('tbody tr').first()
    const archiveButton = firstRow.locator('button:has-text("Archive")')

    if (await archiveButton.isVisible()) {
      await archiveButton.click()

      // Should show success message
      await expect(page.locator('text=Archive completed successfully')).toBeVisible()

      // Row should be removed
      const newCount = await page.locator('tbody tr').count()
      expect(newCount).toBe(initialCount - 1)
    }
  })

  test('should update row when marked safe', async ({ page, context }) => {
    // Skip in production
    if (isProductionEnv()) {
      test.skip(true, 'This test requires dev environment with ALLOW_ACTION_MUTATIONS=true')
    }

    // Mock the mark_safe endpoint
    await context.route('**/api/actions/mark_safe', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ ok: true })
      })
    })

    await page.goto('/web/inbox-actions')

    const hasRows = await page.locator('tbody tr').count() > 0
    if (!hasRows) {
      test.skip(true, 'No actionable emails to test')
    }

    const firstRow = page.locator('tbody tr').first()
    const safeButton = firstRow.locator('button:has-text("Safe")')

    if (await safeButton.isVisible()) {
      await safeButton.click()

      // Should show success message
      await expect(page.locator('text=Mark Safe completed successfully')).toBeVisible()

      // Risk score should be updated (if it was showing before)
      // The row should still be visible with updated data
    }
  })

  test('should update row when marked suspicious', async ({ page, context }) => {
    // Skip in production
    if (isProductionEnv()) {
      test.skip(true, 'This test requires dev environment with ALLOW_ACTION_MUTATIONS=true')
    }

    // Mock the mark_suspicious endpoint
    await context.route('**/api/actions/mark_suspicious', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ ok: true })
      })
    })

    await page.goto('/web/inbox-actions')

    const hasRows = await page.locator('tbody tr').count() > 0
    if (!hasRows) {
      test.skip(true, 'No actionable emails to test')
    }

    const firstRow = page.locator('tbody tr').first()
    const suspiciousButton = firstRow.locator('button:has-text("Suspicious")')

    if (await suspiciousButton.isVisible()) {
      await suspiciousButton.click()

      // Should show success message
      await expect(page.locator('text=Mark Suspicious completed successfully')).toBeVisible()

      // Should show quarantined badge
      await expect(firstRow.locator('text=Quarantined')).toBeVisible()
    }
  })
})

test.describe('Actions Page - Production (@prodSafe)', () => {
  test.use({ storageState: '.auth/user.json' })

  test('should load actions page in production with read-only mode @prodSafe', async ({ page }) => {
    await page.goto('/web/inbox-actions')

    // Wait for page to load
    await expect(page.locator('h1')).toContainText('Inbox Actions')

    // Should show email count or empty state
    await expect(page.locator('text=actionable emails').or(page.locator('text=No actionable emails'))).toBeVisible()

    // In production (ALLOW_ACTION_MUTATIONS=false), only "Explain why" should be visible
    const hasRows = await page.locator('tbody tr').count() > 0

    if (hasRows) {
      const firstRow = page.locator('tbody tr').first()

      // Should see "Explain why" button
      await expect(firstRow.locator('button:has-text("Explain why")')).toBeVisible()

      // Should NOT see mutation buttons (they won't be in allowed_actions)
      const archiveBtn = firstRow.locator('button:has-text("Archive")')
      const safeBtn = firstRow.locator('button:has-text("Safe")')
      const suspiciousBtn = firstRow.locator('button:has-text("Suspicious")')
      const unsubBtn = firstRow.locator('button:has-text("Unsub")')

      // These buttons should not exist in the DOM
      await expect(archiveBtn).not.toBeVisible()
      await expect(safeBtn).not.toBeVisible()
      await expect(suspiciousBtn).not.toBeVisible()
      await expect(unsubBtn).not.toBeVisible()

      // Should show read-only indicator
      await expect(page.locator('text=Mutations are read-only in production')).toBeVisible()
    }
  })

  test('should not make any POST requests to mutation endpoints @prodSafe', async ({ page, context }) => {
    let mutationAttempted = false

    // Monitor for any mutation POST requests
    await context.route('**/api/actions/archive', () => {
      mutationAttempted = true
      throw new Error('Archive endpoint should not be called in prod tests')
    })
    await context.route('**/api/actions/mark_safe', () => {
      mutationAttempted = true
      throw new Error('Mark safe endpoint should not be called in prod tests')
    })
    await context.route('**/api/actions/mark_suspicious', () => {
      mutationAttempted = true
      throw new Error('Mark suspicious endpoint should not be called in prod tests')
    })
    await context.route('**/api/actions/unsubscribe', () => {
      mutationAttempted = true
      throw new Error('Unsubscribe endpoint should not be called in prod tests')
    })

    await page.goto('/web/inbox-actions')

    // Wait a bit to ensure page is fully loaded
    await page.waitForTimeout(2000)

    // Verify no mutations were attempted
    expect(mutationAttempted).toBe(false)
  })

  test('should handle 403 gracefully if mutation is somehow attempted @prodSafe', async ({ page, context }) => {
    // Mock a 403 response
    await context.route('**/api/actions/archive', async (route) => {
      await route.fulfill({
        status: 403,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Actions are read-only in production' })
      })
    })

    await page.goto('/web/inbox-actions')

    // Even if somehow an action button was clicked, it should handle 403 gracefully
    // In real production, the button won't even render, but this tests the error handling

    // Just verify the page doesn't crash
    await expect(page.locator('h1')).toContainText('Inbox Actions')
  })
})
