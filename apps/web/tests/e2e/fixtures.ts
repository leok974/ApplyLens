import { test as base } from '@playwright/test'

type Mock = {
  /** substring or regex to match full request URL (post-proxy too) */
  url: RegExp | string
  method?: string
  status?: number
  /** can be a JSON value or a function returning a JSON value */
  body?: any | (() => any)
  headers?: Record<string, string>
}

export const test = base.extend<{
  mockApi: (mocks: Mock[]) => Promise<void>
  enforceNetworkPolicy: () => Promise<void>
  withMockedNet: (mocks: Mock[]) => Promise<void>
}>({
  mockApi: async ({ page }, use) => {
    async function install(mocks: Mock[]) {
      await page.route('**/*', async (route) => {
        const req = route.request()
        const fullUrl = req.url()
        const method = req.method().toUpperCase()
        const match = mocks.find((m) => {
          const methodOk = m.method ? method === m.method.toUpperCase() : true
          if (!methodOk) return false
          if (typeof m.url === 'string') {
            return fullUrl.includes(m.url)
          }
          return m.url.test(fullUrl)
        })
        if (!match) return route.continue()
        const payload = typeof match.body === 'function' ? match.body() : match.body ?? {}
        const body = typeof payload === 'string' ? payload : JSON.stringify(payload)
        return route.fulfill({
          status: match.status ?? 200,
          body,
          headers: { 'content-type': 'application/json', ...(match.headers ?? {}) },
        })
      })
    }
    await use((mocks: Mock[]) => install(mocks))
  },
  /**
   * Deny-by-default network policy. Whitelist localhost/baseURL and data/about/blob.
   * Opt-out by setting PW_ALLOW_NET=1 for a test or job.
   */
  enforceNetworkPolicy: async ({ page }, use) => {
    const allowNet = process.env.PW_ALLOW_NET === '1'
    if (allowNet) {
      await use(async () => {})
      return
    }
    const baseUrl = (process.env.BASE_URL || 'http://localhost:5173').replace(/\/+$/, '')
    const allowedOrigins = new Set<string>([
      new URL(baseUrl).origin, // e.g., http://localhost:5173
    ])
    const allowedSchemes = ['data:', 'about:', 'blob:']

    await page.route('**/*', async (route, request) => {
      const url = request.url()
      try {
        const u = new URL(url)
        if (allowedOrigins.has(u.origin)) return route.continue()
        // allow static Vite HMR endpoints in dev
        if (u.origin === 'ws://localhost:5173' || u.protocol === 'ws:') return route.continue()
      } catch {
        // non-URL (data:, about:, blob:)
        if (allowedSchemes.some((s) => url.startsWith(s))) return route.continue()
      }
      // Block with helpful message
      return route.fulfill({
        status: 418,
        body: JSON.stringify({
          error: 'Blocked outbound network request by policy',
          url,
          hint: 'Mock this call via test.mockApi([...]) or set PW_ALLOW_NET=1 to temporarily allow.',
        }),
        headers: { 'content-type': 'application/json' },
      })
    })
    await use(async () => {})
  },
  /**
   * Convenience: install mocks first, then enforce network policy.
   * Use this if you want deny-by-default without ordering footguns.
   */
  withMockedNet: async ({ mockApi, enforceNetworkPolicy }, use) => {
    await use(async (mocks: Mock[]) => {
      await mockApi(mocks)
      await enforceNetworkPolicy()
    })
  },
})

// ---- Global beforeEach lock (opt-in) ----
// If PW_LOCK_NET=1, enforce deny-by-default before each test.
// Tests that need mocks should use withMockedNet([...]) which
// installs routes AFTER this lock and therefore take precedence.
test.beforeEach(async ({ enforceNetworkPolicy }, testInfo) => {
  if (process.env.PW_LOCK_NET === '1') {
    await enforceNetworkPolicy()
  }
})

export const expect = base.expect

// Tag helpers:
// Run with: npx playwright test --grep @smoke
export const SMOKE = '@smoke'
export const E2E = '@e2e'
