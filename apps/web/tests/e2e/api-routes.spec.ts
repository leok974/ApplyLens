/**
 * @prodSafe: API route health checks - trailing slash behavior & content-type validation
 *
 * These tests verify that:
 * 1. Routes with trailing slashes don't redirect (FastAPI has the `/` route)
 * 2. Routes without trailing slashes don't redirect (FastAPI has no-slash route)
 * 3. All API responses are JSON (or 204 No Content), never HTML
 * 4. No redirect loops occur
 */

import { test, expect } from '@playwright/test';

test.describe('@prodSafe API route health', () => {
  test('search endpoint: /api/search/ (with slash) returns JSON or 204', async ({ request }) => {
    // apiUrl() adds trailing slash to /api/search
    const res = await request.get('/api/search/?q=Interview&limit=1', {
      maxRedirects: 0, // Don't follow redirects
      failOnStatusCode: false,
    });

    // Should not redirect
    expect(res.status()).not.toBeGreaterThanOrEqual(300);
    expect(res.status()).not.toBeLessThan(400);

    // Should return JSON (200) or No Content (204) or Auth error (401/403)
    expect([200, 204, 401, 403]).toContain(res.status());

    // If not 204, must be JSON
    if (res.status() !== 204) {
      const ct = res.headers()['content-type'] || '';
      expect(ct).toContain('application/json');
    }
  });

  test('auth endpoint: /api/auth/me (no slash) returns JSON or 401', async ({ request }) => {
    // apiUrl() does NOT add trailing slash to /api/auth/me
    const res = await request.get('/api/auth/me', {
      maxRedirects: 0, // Don't follow redirects
      failOnStatusCode: false,
    });

    // Should not redirect (most important check!)
    expect(res.status()).not.toBeGreaterThanOrEqual(300);
    expect(res.status()).not.toBeLessThan(400);
    expect(res.headers()['location']).toBeFalsy();

    // Should return JSON (200) or Unauthorized (401/403)
    expect([200, 401, 403]).toContain(res.status());

    // Must be JSON, never HTML
    const ct = res.headers()['content-type'] || '';
    expect(ct).toContain('application/json');
  });

  test('emails endpoint: /api/emails/ (with slash) returns JSON or 204', async ({ request }) => {
    // apiUrl() adds trailing slash to /api/emails
    const res = await request.get('/api/emails/?limit=1', {
      maxRedirects: 0,
      failOnStatusCode: false,
    });

    // Should not redirect
    expect(res.status()).not.toBeGreaterThanOrEqual(300);
    expect(res.status()).not.toBeLessThan(400);

    // Should return JSON or auth error
    expect([200, 204, 401, 403]).toContain(res.status());

    if (res.status() !== 204) {
      const ct = res.headers()['content-type'] || '';
      expect(ct).toContain('application/json');
    }
  });
});
