// Regression tests for logout flow
// Prevents: browser crashes, 500 errors, redirect loops
import { test, expect } from '../setup/console-listeners';

test.describe('Logout Regression', () => {
  test('logout returns 200, redirects to /welcome, and clears session (no 500, no crash)', async ({ page, context }) => {
    // Navigate to Settings page (requires auth)
    await page.goto('/settings');

    // Wait for Settings page to load
    await page.waitForSelector('[data-testid="logout-button"]', { timeout: 15000 });

    // Listen for page close events (would indicate browser crash)
    let pageClosed = false;
    page.on('close', () => { pageClosed = true; });

    // Listen for API logout call to verify it returns 200 (not 500)
    const logoutPromise = page.waitForResponse(
      response => response.url().includes('/api/auth/logout') && response.request().method() === 'POST',
      { timeout: 5000 }
    );

    // Click logout button and wait for navigation
    await Promise.all([
      page.waitForURL('**/welcome', { timeout: 10000 }),
      page.getByTestId('logout-button').click()
    ]);

    // Assert: API should have returned 200 (regression: was 500)
    const logoutResponse = await logoutPromise;
    expect(logoutResponse.status()).toBe(200);

    // Assert: Should be on welcome page (regression: browser crashed before reaching here)
    await expect(page).toHaveURL(/\/welcome$/);

    // Assert: Page should not have closed (regression: hard reload caused crash)
    expect(pageClosed).toBe(false);

    // Assert: Page should be interactive (no crash)
    await expect(page.getByRole('button', { name: /Connect Gmail/i })).toBeVisible();

    // Assert: Session cookie should be cleared
    const cookies = await context.cookies();
    const sessionCookie = cookies.find(c => c.name === 'session_id');
    expect(sessionCookie).toBeUndefined();
  });

  test('guard redirects unauthenticated users to /welcome', async ({ page, context }) => {
    // Clear all cookies to simulate unauthenticated state
    await context.clearCookies();

    // Try to navigate directly to a protected route
    await page.goto('/settings');

    // Assert: Should be redirected to /welcome
    await page.waitForURL('**/welcome', { timeout: 10000 });
    await expect(page).toHaveURL(/\/welcome$/);

    // Assert: Should see landing page content
    await expect(page.getByRole('button', { name: /Connect Gmail/i })).toBeVisible();
  });
});
