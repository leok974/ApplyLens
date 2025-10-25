import type { Page } from '@playwright/test';

/**
 * Production Read-Only Guard
 *
 * Installs a network route that blocks all non-GET requests on production
 * to prevent accidental data mutations during E2E tests.
 *
 * Allowlist:
 * - GET, HEAD, OPTIONS (always safe)
 * - POST to /api/ux/heartbeat (metrics)
 * - POST to /api/ux/beacon (analytics)
 * - POST to /api/ux/chat/opened (engagement metrics)
 *
 * All other POST/PUT/PATCH/DELETE requests are aborted.
 *
 * Usage:
 * ```typescript
 * test("@prodSafe my safe test", async ({ page }) => {
 *   await installProdReadOnlyGuard(page);
 *   // ... test code
 * });
 * ```
 */
export async function installProdReadOnlyGuard(page: Page) {
  const base = process.env.E2E_BASE_URL ?? "";
  const IS_PROD = /^https:\/\/applylens\.app/.test(base);

  // Only install guard on production
  if (!IS_PROD) {
    return;
  }

  console.log("🛡️  Production read-only guard enabled");

  await page.route('**/*', (route) => {
    const req = route.request();
    const method = req.method();
    const url = req.url();

    // Allow safe methods
    const isSafeMethod = method === "GET" || method === "HEAD" || method === "OPTIONS";

    // Allow specific metrics/analytics endpoints
    const isAllowedMutation =
      method === "POST" && /\/api\/ux\/(heartbeat|beacon|chat\/opened)$/.test(url);

    if (isSafeMethod || isAllowedMutation) {
      return route.continue();
    }

    // Block all other mutations
    console.warn(`🚫 Blocked ${method} ${url} (prod read-only guard)`);
    return route.abort('failed');
  });
}

/**
 * Helper to check if we're running against production
 */
export function isProductionEnv(): boolean {
  const base = process.env.E2E_BASE_URL ?? "";
  return /^https:\/\/applylens\.app/.test(base);
}
