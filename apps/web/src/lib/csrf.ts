/**
 * CSRF token management for browser requests
 *
 * Ensures CSRF cookie is set before state-changing requests (POST/PUT/DELETE).
 * Works with same-origin Nginx proxy setup where API is at /api/*.
 */

/**
 * Fetches CSRF token from API to set cookie
 * @param base - API base URL (default: VITE_API_BASE env var or '/api')
 */
export async function ensureCsrf(base = import.meta.env.VITE_API_BASE || '/api') {
  // Hit CSRF endpoint to set cookie
  const res = await fetch(`${base}/auth/csrf`, {
    method: 'GET',
    credentials: 'include', // Critical to receive/set cookies
  });

  // Some backends echo token as JSON, others rely on cookie-only
  // We don't hard-require JSON here; cookie is enough for dev
  try {
    await res.json();
  } catch {
    /* ignore parse errors */
  }
}

/**
 * Reads CSRF token from cookie (for optional header support)
 * @param name - Cookie name (default: 'csrf_token')
 * @returns Token string or null if not found
 */
export function readCsrfFromCookie(name = 'csrf_token'): string | null {
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]+)`));
  return match ? decodeURIComponent(match[1]) : null;
}
