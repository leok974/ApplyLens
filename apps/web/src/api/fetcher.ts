/**
 * API fetch wrapper with CSRF protection.
 * 
 * Automatically includes CSRF token for state-changing requests (POST, PUT, PATCH, DELETE).
 * All requests include credentials (cookies) for session authentication.
 */

/**
 * Get a cookie value by name.
 * 
 * @param name - Cookie name to retrieve
 * @returns Cookie value or undefined if not found
 */
function getCookie(name: string): string | undefined {
  const cookies = document.cookie.split('; ');
  const cookie = cookies.find(row => row.startsWith(`${name}=`));
  return cookie?.split('=')[1];
}

/**
 * Fetch wrapper that adds CSRF protection and credentials.
 * 
 * Use this instead of raw fetch() for all API calls.
 * 
 * @param path - API endpoint path (e.g., "/auth/logout")
 * @param init - Fetch options (method, headers, body, etc.)
 * @returns Promise resolving to Response object
 * 
 * @example
 * ```ts
 * // GET request (no CSRF needed)
 * const user = await api('/auth/me').then(r => r.json());
 * 
 * // POST request (CSRF token auto-added)
 * await api('/auth/logout', { method: 'POST' });
 * 
 * // POST with JSON body
 * await api('/applications', {
 *   method: 'POST',
 *   headers: { 'Content-Type': 'application/json' },
 *   body: JSON.stringify({ company: 'Acme' })
 * });
 * ```
 */
export async function api(path: string, init: RequestInit = {}): Promise<Response> {
  // Get CSRF token from cookie
  const csrfToken = getCookie('csrf_token');
  
  // Build headers
  const headers = new Headers(init.headers || {});
  
  // Add CSRF header for state-changing requests
  if (init.method && init.method.toUpperCase() !== 'GET' && csrfToken) {
    headers.set('X-CSRF-Token', csrfToken);
  }
  
  // Make request with credentials (include session cookies)
  return fetch(path, {
    credentials: 'include',  // Always include cookies
    ...init,
    headers
  });
}
