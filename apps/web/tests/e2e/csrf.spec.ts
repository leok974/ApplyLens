/**
 * E2E tests for CSRF protection.
 * 
 * Validates that:
 * - State-changing requests require CSRF token
 * - CSRF cookie is issued on first visit
 * - Requests with valid CSRF token succeed
 * - Requests without CSRF token fail with 403
 */

import { test, expect } from '@playwright/test';

test.describe('CSRF Protection', () => {
  test('mutations require CSRF token', async ({ page, request }) => {
    // Try logout without CSRF token (should fail)
    const noTokenResponse = await request.post('/auth/logout', {
      headers: {},
      failOnStatusCode: false
    });
    
    expect(noTokenResponse.status()).toBe(403);
    const noTokenBody = await noTokenResponse.text();
    expect(noTokenBody).toContain('CSRF');
  });

  test('CSRF cookie is issued on page visit', async ({ page }) => {
    // Visit page to get CSRF cookie
    await page.goto('/welcome');
    
    // Check that csrf_token cookie was set
    const cookies = await page.context().cookies();
    const csrfCookie = cookies.find(c => c.name === 'csrf_token');
    
    expect(csrfCookie).toBeDefined();
    expect(csrfCookie?.value).toBeTruthy();
    expect(csrfCookie?.httpOnly).toBe(false); // JS needs to read it
  });

  test('mutations succeed with valid CSRF token', async ({ page }) => {
    // Visit page to get CSRF cookie
    await page.goto('/welcome');
    
    // Extract CSRF token from cookie
    const csrfToken = await page.evaluate(() => {
      const cookie = document.cookie
        .split('; ')
        .find(row => row.startsWith('csrf_token='));
      return cookie?.split('=')[1];
    });
    
    expect(csrfToken).toBeTruthy();
    
    // Make POST request with CSRF token
    const response = await page.request.post('/auth/demo/start', {
      headers: {
        'X-CSRF-Token': csrfToken!
      }
    });
    
    expect(response.ok()).toBeTruthy();
  });

  test('CSRF protection integrates with demo login flow', async ({ page }) => {
    // Start from welcome page
    await page.goto('/welcome');
    
    // Click demo button (should work because fetcher adds CSRF token)
    await page.click('button:has-text("Try Demo")');
    
    // Should redirect to inbox
    await page.waitForURL('/inbox');
    
    // Verify we're logged in
    const response = await page.request.get('/auth/me');
    expect(response.ok()).toBeTruthy();
    
    const user = await response.json();
    expect(user.email).toBe('demo@applylens.app');
  });

  test('CSRF token persists across requests', async ({ page }) => {
    // Visit page
    await page.goto('/welcome');
    
    // Get initial token
    const token1 = await page.evaluate(() => {
      return document.cookie
        .split('; ')
        .find(row => row.startsWith('csrf_token='))
        ?.split('=')[1];
    });
    
    // Navigate to another page
    await page.goto('/');
    
    // Token should still be present
    const token2 = await page.evaluate(() => {
      return document.cookie
        .split('; ')
        .find(row => row.startsWith('csrf_token='))
        ?.split('=')[1];
    });
    
    expect(token2).toBeTruthy();
    expect(token2).toBe(token1); // Same token (not rotated on GET)
  });

  test('logout requires CSRF token', async ({ page }) => {
    // Start demo session
    await page.goto('/welcome');
    await page.click('button:has-text("Try Demo")');
    await page.waitForURL('/inbox');
    
    // Try to logout via API without token (should fail)
    const failResponse = await page.request.post('/auth/logout', {
      headers: {},
      failOnStatusCode: false
    });
    expect(failResponse.status()).toBe(403);
    
    // Logout via UI (uses fetcher with CSRF token, should succeed)
    // This assumes there's a logout button in the UI
    // If not, we can skip this part or just test the API directly
    
    // Get CSRF token
    const csrfToken = await page.evaluate(() => {
      return document.cookie
        .split('; ')
        .find(row => row.startsWith('csrf_token='))
        ?.split('=')[1];
    });
    
    // Logout with token (should succeed)
    const successResponse = await page.request.post('/auth/logout', {
      headers: {
        'X-CSRF-Token': csrfToken!
      }
    });
    expect(successResponse.ok()).toBeTruthy();
  });
});
