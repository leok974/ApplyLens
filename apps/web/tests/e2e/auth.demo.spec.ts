// apps/web/tests/e2e/auth.demo.spec.ts
import { test, expect } from '@playwright/test';

// Helper: starts demo via API to avoid external redirects
async function startDemo(page: any) {
  await page.request.post('/auth/demo/start');
}

test.describe('Demo login flow', () => {
  test('@devOnly landing → demo → inbox → me', async ({ page }) => {
    await page.goto('/welcome');
    await expect(page.getByRole('button', { name: 'Connect Gmail' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Try Demo' })).toBeVisible();

    // Click Try Demo (or call API directly to skip CORS)
    await page.getByRole('button', { name: 'Try Demo' }).click();

    // Should navigate to inbox
    await page.waitForURL('**/inbox');

    // Verify /auth/me returns demo user
    const r = await page.request.get('/auth/me');
    expect(r.ok()).toBeTruthy();
    const me = await r.json();
    expect(me.email).toBeTruthy();
    // accept either flag or email match
    expect(me.demo || me.email === 'demo@applylens.app').toBeTruthy();
  });
});
