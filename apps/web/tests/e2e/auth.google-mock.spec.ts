// apps/web/tests/e2e/auth.google-mock.spec.ts
import { test, expect } from '@playwright/test';

// This test uses route mocking to simulate OAuth callback without hitting Google

test('@devOnly google login (mock) sets session and redirects', async ({ page, context }) => {
  await page.route('**/auth/google/login', async (route) => {
    // Simulate provider redirect by forcing a navigation to callback with fake code/state
    await route.fulfill({ status: 302, headers: { location: '/auth/google/callback?code=fake&state=fake' } });
  });

  await page.route('**/auth/google/callback?**', async (route) => {
    // Fulfill callback: server would set cookie; we simulate by setting cookie here
    const cookie = { name: 'session_id', value: 'playwright', domain: 'localhost', path: '/', httpOnly: true };
    await context.addCookies([cookie]);
    await route.fulfill({ status: 302, headers: { location: '/' } });
  });

  await page.goto('/welcome');
  await page.getByRole('button', { name: 'Connect Gmail' }).click();
  await page.waitForURL('/');
});
