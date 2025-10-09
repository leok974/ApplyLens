import { Page } from '@playwright/test'

/**
 * Waits until there are <= inflight requests for a sustained quiet period.
 * More reliable than page.waitForLoadState('networkidle') with SPAs.
 */
export async function waitForNetworkIdle(
  page: Page,
  { idleMs = 300, inflight = 0, timeout = 5000 }: { idleMs?: number; inflight?: number; timeout?: number } = {}
) {
  let pending = 0
  let resolve!: () => void
  let idleTimer: NodeJS.Timeout | null = null
  const done = new Promise<void>((r) => (resolve = r))
  const start = Date.now()

  function tryResolve() {
    if (pending <= inflight) {
      if (idleTimer) clearTimeout(idleTimer)
      idleTimer = setTimeout(() => resolve(), idleMs)
    }
  }

  const onReq = () => {
    pending++
    if (idleTimer) {
      clearTimeout(idleTimer)
      idleTimer = null
    }
  }
  const onDone = () => {
    pending = Math.max(0, pending - 1)
    tryResolve()
  }

  page.on('request', onReq)
  page.on('requestfinished', onDone)
  page.on('requestfailed', onDone)

  tryResolve()
  try {
    await Promise.race([
      done,
      new Promise((_, rej) =>
        setTimeout(() => rej(new Error(`waitForNetworkIdle timeout after ${timeout}ms`)), timeout)
      ),
    ])
  } finally {
    page.off('request', onReq)
    page.off('requestfinished', onDone)
    page.off('requestfailed', onDone)
    if (idleTimer) clearTimeout(idleTimer)
  }
}
