/**
 * @prodSafe: Auth endpoint behavior tests
 *
 * These tests verify that:
 * 1. /api/auth/me returns JSON or 401 (never redirects to HTML login page)
 * 2. /api/auth/session returns JSON or 401 (never redirects)
 * 3. No redirect loops occur when unauthenticated
 */

import { test, expect } from '@playwright/test';

test.describe('@prodSafe Auth endpoints', () => {
  test('/api/auth/me returns JSON or 401 (no redirect)', async ({ request }) => {
    const res = await request.get('/api/auth/me', {
      maxRedirects: 0, // Critical: don't follow redirects
      failOnStatusCode: false,
    });

    // MUST NOT redirect (most important check)
    expect(res.status()).toBeLessThan(300); // Not 3xx
    expect(res.headers()['location']).toBeFalsy();

    // Should return 200 (with JSON) or 401/403 (with JSON error)
    expect([200, 401, 403]).toContain(res.status());

    // MUST be JSON, never HTML
    const ct = res.headers()['content-type'] || '';
    expect(ct).toContain('application/json');
    expect(ct).not.toContain('text/html');
  });

  test('/api/auth/me returns valid user object when authenticated', async ({ page }) => {
    // This test only runs if there's a valid session
    const response = await page.goto('/api/auth/me');

    if (response?.status() === 200) {
      const data = await response.json();

      // Should have user object with required fields
      expect(data).toHaveProperty('email');
      expect(data).toHaveProperty('id');
    }
  });

  test('LoginGuard handles unauthenticated gracefully (no crash)', async ({ page }) => {
    // Clear cookies to simulate unauthenticated state
    await page.context().clearCookies();

    // Load protected page
    await page.goto('/web/search');

    // Should show login CTA, not crash
    const errorText = await page.locator('body').textContent();
    expect(errorText).not.toContain('Unexpected token');
    expect(errorText).not.toContain('is not valid JSON');

    // Should show login UI
    await expect(page.locator('text=/log.*in/i')).toBeVisible({ timeout: 5000 });
  });

  test('LoginGuard handles HTML response gracefully (nginx misconfiguration)', async ({ page }) => {
    // Intercept /api/auth/me and return HTML instead of JSON
    await page.route('**/api/auth/me', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'text/html',
        body: '<!doctype html><html><body>Error</body></html>',
      });
    });

    // Load protected page
    await page.goto('/web/search');

    // Should NOT crash with "Unexpected token '<'"
    const errorText = await page.locator('body').textContent();
    expect(errorText).not.toContain('Unexpected token');
    expect(errorText).not.toContain('is not valid JSON');

    // Should treat HTML response as unauthenticated
    await expect(page.locator('text=/log.*in/i')).toBeVisible({ timeout: 5000 });
  });

  test('LoginGuard handles 307 redirect gracefully', async ({ page }) => {
    // Intercept /api/auth/me and return 307 redirect
    await page.route('**/api/auth/me', (route) => {
      route.fulfill({
        status: 307,
        headers: { 'location': '/web/auth/login' },
        body: '',
      });
    });

    // Load protected page
    await page.goto('/web/search');

    // Should treat redirect as unauthenticated (not follow it)
    const errorText = await page.locator('body').textContent();
    expect(errorText).not.toContain('Unexpected token');

    // Should show login UI
    await expect(page.locator('text=/log.*in/i')).toBeVisible({ timeout: 5000 });
  });
});
