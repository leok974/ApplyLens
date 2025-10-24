// apps/web/tests/e2e/auth.logout.spec.ts
import { test, expect } from '@playwright/test';

async function ensureDemo(page: any) {
  await page.request.post('/auth/demo/start');
}

test('@devOnly logout clears session and returns to landing', async ({ page }) => {
  await ensureDemo(page);
  await page.goto('/');
  // Open header menu and click Logout (or call API)
  await page.request.post('/auth/logout');
  await page.goto('/');
  // Guard should redirect to /welcome
  await page.waitForURL('**/welcome');
  await expect(page.getByRole('button', { name: 'Connect Gmail' })).toBeVisible();
});
