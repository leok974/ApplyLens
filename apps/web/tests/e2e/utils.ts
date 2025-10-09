import type { Page } from '@playwright/test'
import { expect } from './fixtures'

type AssertToastOpts = {
  title?: RegExp | string
  desc?: RegExp | string
  variant?: 'default' | 'success' | 'warning' | 'error' | 'info'
  timeout?: number
}

export async function assertToast(page: Page, opts: AssertToastOpts) {
  const { title, desc, variant, timeout = 5000 } = opts
  const toast = page.getByTestId('toast')
  if (variant) {
    await expect(toast).toHaveAttribute('data-variant', variant, { timeout })
  }
  if (title !== undefined) {
    await expect(toast.getByTestId('toast-title')).toHaveText(title as any, { timeout })
  }
  if (desc !== undefined) {
    await expect(toast.getByTestId('toast-desc')).toHaveText(desc as any, { timeout })
  }
  // ensures it's actually visible (no-op if above checks already assert text)
  await expect(toast).toBeVisible({ timeout })
  return toast
}
