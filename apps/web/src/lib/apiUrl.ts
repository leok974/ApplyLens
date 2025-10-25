/**
 * Build absolute API URL (ignores router basename)
 *
 * This ensures API calls always use absolute URLs from the origin,
 * preventing issues with relative path resolution when the app
 * is mounted at a non-root path (e.g., /web/).
 *
 * Additionally, adds trailing slashes to specific /api/* paths that FastAPI
 * expects with trailing slashes (to prevent 307 redirects).
 *
 * @example
 * apiUrl('/api/search', new URLSearchParams({ q: 'test' }))
 * // => 'https://applylens.app/api/search/?q=test'
 */
export function apiUrl(path: string, params?: URLSearchParams): string {
  // Ensure path starts with /
  let p = path.startsWith('/') ? path : `/${path}`

  // Add trailing slash ONLY to specific routes that need it
  // Most FastAPI routes DON'T need trailing slashes
  // Only add for collection/list endpoints that FastAPI defines with trailing slash
  const needsTrailingSlash = [
    '/api/search',      // FastAPI: @router.get("/search/")
    '/api/emails',      // FastAPI: prefix="/emails" + @router.get("/")
    '/api/labels',      // FastAPI: TBD (verify if needed)
    '/api/ux/events',   // FastAPI: TBD (verify if needed)
  ]

  if (needsTrailingSlash.includes(p) && !p.endsWith('/')) {
    p = `${p}/`
  }

  const url = new URL(p, window.location.origin)
  if (params) url.search = params.toString()
  return url.toString()
}
