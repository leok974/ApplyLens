import { test, expect } from './fixtures'
import { appRow, listResponse } from './factories'

test.describe('Email Extraction Feature', () => {
  test('extracts and prefills fields from email', async ({ page, withMockedNet }) => {
    // Mock the applications list with one row that has a thread_id
    const existingRow = appRow({
      id: 501,
      company: 'OldCo',
      role: 'Old Role',
      thread_id: 'thread_abc123',
    })

    await withMockedNet([
      {
        url: '/api/applications',
        method: 'GET',
        body: listResponse([existingRow]),
      },
      {
        url: '/api/applications/extract',
        method: 'POST',
        body: {
          company: 'acme',
          role: 'Senior Software Engineer',
          source: 'Greenhouse',
          source_confidence: 0.95,
          debug: {
            from: 'recruiter@acme.ai',
            subject: 'Application for Senior Software Engineer',
            has_text: true,
            has_html: false,
          },
        },
      },
    ])

    await page.goto('/tracker')
    await page.waitForSelector('text=OldCo')

    // Click the "Prefill Only" button
    const prefillButton = page.locator('button:has-text("Prefill Only")')
    await prefillButton.click()

    // Wait for the create dialog to open
    await page.waitForSelector('#create-dialog[open]')

    // Verify extracted fields are prefilled in the form
    const companyInput = page.locator('#create-dialog input[name="company"]')
    const roleInput = page.locator('#create-dialog input[name="role"]')
    const sourceInput = page.locator('#create-dialog input[name="source"]')

    await expect(companyInput).toHaveValue('acme')
    await expect(roleInput).toHaveValue('Senior Software Engineer')
    await expect(sourceInput).toHaveValue('Greenhouse')

    // Verify toast notification
    await page.waitForSelector('[data-testid="toast"]:has-text("Extracted: acme - Senior Software Engineer")')
  })

  test('creates application directly from email', async ({ page, withMockedNet }) => {
    // Mock the applications list
    const existingRow = appRow({
      id: 502,
      company: 'TempCo',
      role: 'Temp Role',
      thread_id: 'thread_xyz789',
    })

    // Mock the backfill endpoint
    const newApp = appRow({
      id: 503,
      company: 'Acme Corp',
      role: 'ML Engineer',
      source: 'Lever',
      source_confidence: 0.95,
      thread_id: 'thread_xyz789',
    })

    await withMockedNet([
      {
        url: '/api/applications',
        method: 'GET',
        body: listResponse([existingRow]),
      },
      {
        url: '/api/applications/backfill-from-email',
        method: 'POST',
        body: {
          saved: newApp,
          extracted: {
            company: 'Acme Corp',
            role: 'ML Engineer',
            source: 'Lever',
            source_confidence: 0.95,
          },
          updated: false,
        },
      },
    ])

    await page.goto('/tracker')
    await page.waitForSelector('text=TempCo')

    // Click the "Create from Email" button
    const createButton = page.locator('button:has-text("Create from Email")')
    await createButton.click()

    // Verify success toast appears
    await page.waitForSelector('[data-testid="toast"]:has-text("Application created: Acme Corp - ML Engineer")')

    // Verify the new application appears in the list
    await page.waitForSelector('text=Acme Corp')
    await page.waitForSelector('text=ML Engineer')
  })

  test('shows error toast on extraction failure', async ({ page, withMockedNet }) => {
    const existingRow = appRow({
      id: 504,
      company: 'TestCo',
      role: 'Test Role',
      thread_id: 'thread_error',
    })

    await withMockedNet([
      {
        url: '/api/applications',
        method: 'GET',
        body: listResponse([existingRow]),
      },
      {
        url: '/api/applications/extract',
        method: 'POST',
        status: 500,
        body: { error: 'Internal server error' },
      },
    ])

    await page.goto('/tracker')
    await page.waitForSelector('text=TestCo')

    // Click the "Prefill Only" button
    const prefillButton = page.locator('button:has-text("Prefill Only")')
    await prefillButton.click()

    // Verify error toast appears
    await page.waitForSelector('[data-testid="toast"][data-variant="error"]:has-text("Could not extract application details")')
  })

  test('shows error toast on backfill failure', async ({ page, withMockedNet }) => {
    const existingRow = appRow({
      id: 505,
      company: 'TestCo2',
      role: 'Test Role 2',
      thread_id: 'thread_error2',
    })

    await withMockedNet([
      {
        url: '/api/applications',
        method: 'GET',
        body: listResponse([existingRow]),
      },
      {
        url: '/api/applications/backfill-from-email',
        method: 'POST',
        status: 400,
        body: { error: 'Invalid request' },
      },
    ])

    await page.goto('/tracker')
    await page.waitForSelector('text=TestCo2')

    // Click the "Create from Email" button
    const createButton = page.locator('button:has-text("Create from Email")')
    await createButton.click()

    // Verify error toast appears
    await page.waitForSelector('[data-testid="toast"][data-variant="error"]:has-text("Could not create application from email")')
  })

  test('only shows buttons for rows with thread_id', async ({ page, withMockedNet }) => {
    // Mock applications list with mixed thread_id presence
    const withThreadId = appRow({
      id: 506,
      company: 'WithThread',
      role: 'Role A',
      thread_id: 'thread_has_id',
    })

    const withoutThreadId = appRow({
      id: 507,
      company: 'NoThread',
      role: 'Role B',
      thread_id: null,
    })

    await withMockedNet([
      {
        url: '/api/applications',
        method: 'GET',
        body: listResponse([withThreadId, withoutThreadId]),
      },
    ])

    await page.goto('/tracker')
    await page.waitForSelector('text=WithThread')
    await page.waitForSelector('text=NoThread')

    // Count visible extraction buttons
    const createButtons = page.locator('button:has-text("Create from Email")')
    const prefillButtons = page.locator('button:has-text("Prefill Only")')

    // Should have 1 of each button (only for row with thread_id)
    await expect(createButtons).toHaveCount(1)
    await expect(prefillButtons).toHaveCount(1)
  })

  test('disables buttons during extraction/creation', async ({ page, withMockedNet }) => {
    const row = appRow({
      id: 508,
      company: 'LoadingTest',
      role: 'Test Role',
      thread_id: 'thread_loading',
    })

    await withMockedNet([
      {
        url: '/api/applications',
        method: 'GET',
        body: listResponse([row]),
      },
      {
        url: '/api/applications/extract',
        method: 'POST',
        body: {
          company: 'LoadingTest',
          role: 'Test Role',
          source: 'Email',
          source_confidence: 0.5,
          debug: {},
        },
      },
    ])

    await page.goto('/tracker')
    await page.waitForSelector('text=LoadingTest')

    const prefillButton = page.locator('button:has-text("Prefill Only")')
    const createButton = page.locator('button:has-text("Create from Email")')

    // Click prefill button
    await prefillButton.click()

    // Both buttons should be disabled during extraction
    await expect(prefillButton).toBeDisabled()
    await expect(createButton).toBeDisabled()

    // Verify loading text appears
    await page.waitForSelector('button:has-text("Extracting...")')
  })
})
