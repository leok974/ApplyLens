// apps/web/tests/e2e/auth.logout.spec.ts
import { test, expect } from '../setup/console-listeners';

test('@devOnly logout clears session and returns to landing', async ({ page, context }) => {
  // Global setup has already authenticated, so we can go directly to the app

  // Navigate to Settings page
  await page.goto('/settings');

  // Wait for Settings page to load and show the logout button
  await page.waitForSelector('[data-testid="logout-button"]', { timeout: 15000 });

  // Click logout button and wait for navigation
  await Promise.all([
    page.waitForURL('**/welcome', { timeout: 10000 }),
    page.getByTestId('logout-button').click()
  ]);

  // Verify we're on welcome page
  await expect(page).toHaveURL(/\/welcome$/);
  await expect(page.getByRole('button', { name: 'Connect Gmail' })).toBeVisible();

  // Verify session cookie is cleared
  const cookies = await context.cookies();
  const sessionCookie = cookies.find(c => c.name === 'session_id');
  expect(sessionCookie).toBeUndefined();
});
