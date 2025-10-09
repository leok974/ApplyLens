import { test, expect } from './fixtures'
import { assertToast } from './utils'
import { appRow, listResponse, patchResponse } from './factories'

test.describe('Tracker note snippets', () => {
  test('click snippet chip inserts text, autosaves on blur, shows toast, persists preview', async ({
    page,
    withMockedNet,
  }) => {
    // initial row with empty note
    const row = appRow({ 
      id: 404, 
      company: 'Anthropic', 
      role: 'Research Engineer',
      source: 'Greenhouse',
      notes: '',
    })

    await withMockedNet([
      {
        url: '/api/applications',
        method: 'GET',
        body: listResponse([row]),
      },
      {
        url: '/api/applications/404',
        method: 'PATCH',
        body: patchResponse(row, { notes: 'Sent thank-you' }),
      },
    ])

    await page.goto('/tracker')
    await expect(page.getByTestId('tracker-row-404')).toBeVisible()

    // open inline editor
    await page.getByTestId('note-404-preview').click()
    const editor = page.getByTestId('note-404-editor')
    await expect(editor).toBeVisible()

    // click snippet chip to insert text
    await page.getByTestId('note-404-chip-sent-thank-you').click()
    await expect(editor).toHaveValue('Sent thank-you')

    // press Cmd+Enter to save
    await editor.press('Meta+Enter')

    // toast appears
    await assertToast(page, { title: /Note saved/i, desc: /Anthropic/i, variant: 'success' })
  })
})
