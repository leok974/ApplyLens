/**
 * Production Smoke Tests (Read-Only & Safe)
 *
 * These tests run against production to verify basic functionality
 * without modifying any data or requiring dev routes.
 *
 * Usage:
 *   PROD_BASE_URL=https://applylens.app npm run test:prod:smoke
 *
 * Safe for production because:
 *   - No writes to database
 *   - No dev routes (/api/dev/*)
 *   - No demo login (only checks public pages)
 *   - No data seeding
 */

import { test, expect, request } from '@playwright/test';

const BASE = process.env.PROD_BASE_URL ?? 'https://applylens.app';
const api = (path: string) => `${BASE}${path}`;

// Configure for production
test.use({
  baseURL: BASE,
});

test.describe('Production Health Checks', () => {
  test('health endpoints respond with 200', async () => {
    const ctx = await request.newContext();

    // Web health
    const webHealth = await ctx.get(api('/health'));
    expect(webHealth.status()).toBe(200);

    // API health
    const apiHealth = await ctx.get(api('/api/healthz'));
    expect(apiHealth.status()).toBe(200);

    const body = await apiHealth.json();
    expect(body).toMatchObject({
      status: 'ok'
    });

    // Optional: Check version
    if (body.version) {
      expect(body.version).toMatch(/^\d+\.\d+\.\d+$/);
    }
  });

  test('CSRF endpoint returns token', async () => {
    const ctx = await request.newContext();
    const resp = await ctx.get(api('/api/auth/csrf'));

    expect(resp.status()).toBe(200);

    // Should return JSON with csrf_token
    const body = await resp.json();
    expect(body).toHaveProperty('csrf_token');
    expect(typeof body.csrf_token).toBe('string');
    expect(body.csrf_token.length).toBeGreaterThan(0);

    // Should set cookie
    const cookies = resp.headers()['set-cookie'];
    expect(cookies).toBeTruthy();
  });
});

test.describe('Public Pages', () => {
  test('welcome page renders without console errors', async ({ page }) => {
    const errors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });

    const resp = await page.goto(api('/welcome'), {
      waitUntil: 'domcontentloaded',
      timeout: 15000
    });

    expect(resp?.status()).toBe(200);

    // Page should show ApplyLens branding or CTA
    await expect(page.locator('body')).toContainText(/ApplyLens|Try Demo|Welcome|Connect Gmail/i);

    // No console errors
    expect(errors).toEqual([]);
  });

  test('root path responds with 200', async ({ page }) => {
    const resp = await page.goto(api('/'), {
      waitUntil: 'domcontentloaded',
      timeout: 15000
    });

    expect(resp?.status()).toBe(200);

    // Should contain some expected content
    await expect(page.locator('body')).toContainText(/ApplyLens/i);
  });

  test('404 page handles gracefully', async ({ page }) => {
    const resp = await page.goto(api('/nonexistent-page-12345'), {
      waitUntil: 'domcontentloaded',
      timeout: 15000
    });

    // Should return 404 or redirect to valid page
    expect([200, 404]).toContain(resp?.status() ?? 0);
  });
});

test.describe('SEO & Metadata', () => {
  test('robots.txt exists', async () => {
    const ctx = await request.newContext();
    const resp = await ctx.get(api('/robots.txt'));

    // 200, 204, or 304 are acceptable
    expect([200, 204, 304]).toContain(resp.status());

    if (resp.status() === 200) {
      const text = await resp.text();
      expect(text.length).toBeGreaterThan(0);
    }
  });

  test('sitemap.xml exists (optional)', async () => {
    const ctx = await request.newContext();
    const resp = await ctx.get(api('/sitemap.xml'));

    // 200, 204, 304, or 404 are acceptable
    // 404 is OK if sitemap not published yet
    expect([200, 204, 304, 404]).toContain(resp.status());
  });

  test('welcome page has proper meta tags', async ({ page }) => {
    await page.goto(api('/welcome'), { waitUntil: 'domcontentloaded' });

    // Check for title
    const title = await page.title();
    expect(title.length).toBeGreaterThan(0);

    // Check for meta description (optional)
    const description = await page.locator('meta[name="description"]').getAttribute('content');
    if (description) {
      expect(description.length).toBeGreaterThan(0);
    }
  });
});

test.describe('API Endpoints (Read-Only)', () => {
  test('auth/me returns 401 for unauthenticated', async () => {
    const ctx = await request.newContext();
    const resp = await ctx.get(api('/api/auth/me'));

    // Should return 401 without session
    expect(resp.status()).toBe(401);
  });

  test('protected routes redirect or return 401', async ({ page }) => {
    // Try to access protected route without auth
    const resp = await page.goto(api('/inbox'), {
      waitUntil: 'domcontentloaded',
      timeout: 15000
    });

    // Should either:
    // 1. Redirect to /welcome (200 after redirect)
    // 2. Show login page
    expect(resp?.status()).toBe(200);

    // Should be on welcome or login page
    const url = page.url();
    expect(url).toMatch(/\/(welcome|login|auth)/i);
  });
});

test.describe('Performance & Response Times', () => {
  test('health endpoint responds quickly', async () => {
    const ctx = await request.newContext();

    const start = Date.now();
    const resp = await ctx.get(api('/api/healthz'));
    const duration = Date.now() - start;

    expect(resp.status()).toBe(200);
    expect(duration).toBeLessThan(2000); // Should be < 2s
  });

  test('welcome page loads within reasonable time', async ({ page }) => {
    const start = Date.now();
    await page.goto(api('/welcome'), {
      waitUntil: 'domcontentloaded',
      timeout: 15000
    });
    const loadTime = Date.now() - start;

    // Should load in < 5 seconds
    expect(loadTime).toBeLessThan(5000);
  });
});

test.describe('Error Handling', () => {
  test('API returns proper JSON errors', async () => {
    const ctx = await request.newContext();

    // Try invalid endpoint
    const resp = await ctx.get(api('/api/nonexistent-endpoint-xyz'));

    // Should return 404
    expect(resp.status()).toBe(404);

    // Should be JSON (not HTML error page)
    const contentType = resp.headers()['content-type'];
    expect(contentType).toMatch(/application\/json/);
  });

  test('CORS headers present (if applicable)', async () => {
    const ctx = await request.newContext();
    const resp = await ctx.get(api('/api/healthz'));

    // Check for security headers
    const headers = resp.headers();

    // These are optional but recommended
    if (headers['x-frame-options']) {
      expect(headers['x-frame-options']).toMatch(/DENY|SAMEORIGIN/i);
    }

    if (headers['x-content-type-options']) {
      expect(headers['x-content-type-options']).toBe('nosniff');
    }
  });
});
