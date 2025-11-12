/**
 * API Base URL Configuration
 *
 * This module provides the base URL for API calls, configured via environment variables.
 *
 * Environment Configurations:
 * - Local dev (.env.local): VITE_API_BASE=http://localhost:8003
 * - Docker (.env.docker): VITE_API_BASE=http://api:8003
 * - Fallback: '/api' (uses Vite proxy or same-origin Nginx)
 *
 * Usage:
 * import { API_BASE } from '@/lib/apiBase'
 * const response = await fetch(`${API_BASE}/actions/tray`)
 *
 * Or use apiFetch for automatic CSRF handling:
 * import { apiFetch } from '@/lib/apiBase'
 * const data = await apiFetch('/actions/tray')
 */

import { ensureCsrf, readCsrfFromCookie } from './csrf'

export const API_BASE = import.meta.env.VITE_API_BASE ?? '/api'

// Log configuration in development
if (import.meta.env.DEV) {
  console.log('[API Config] Base URL:', API_BASE)
}

type FetchOpts = RequestInit & { csrf?: boolean }

/**
 * Fetch wrapper with automatic CSRF and credential handling
 * @param path - API path (can be relative or absolute URL)
 * @param opts - Fetch options with optional csrf flag
 * @returns Promise resolving to JSON or text response
 */
export async function apiFetch(path: string, opts: FetchOpts = {}) {
  // Build full URL
  const url = path.startsWith('http')
    ? path
    : `${API_BASE}${path.startsWith('/') ? '' : '/'}${path}`

  // Always include credentials so cookies (session + csrf) flow
  const baseOpts: RequestInit = {
    credentials: 'include',
    ...opts,
    headers: {
      ...(opts.headers || {}),
    },
  }

  // Determine if CSRF is needed
  const method = (opts.method || 'GET').toUpperCase()
  const needsCsrf = opts.csrf ?? ['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)

  if (needsCsrf) {
    // Ensure CSRF cookie exists
    await ensureCsrf(API_BASE)

    // Optional: attach header if cookie is present
    const csrf = readCsrfFromCookie()
    if (csrf) {
      (baseOpts.headers as Record<string, string>)['X-CSRF-Token'] = csrf
    }
  }

  const res = await fetch(url, baseOpts)

  if (!res.ok) {
    // Bubble useful info for tests and UI
    const text = await res.text().catch(() => '')
    throw new Error(`apiFetch ${method} ${url} -> ${res.status}: ${text}`)
  }

  // Try json, fallback to text
  const contentType = res.headers.get('content-type') || ''
  return contentType.includes('application/json') ? res.json() : res.text()
}
