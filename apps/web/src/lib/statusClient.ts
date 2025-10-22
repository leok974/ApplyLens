/**
 * Status client with exponential backoff and graceful degradation.
 *
 * Never reloads the page on 5xx errors. Instead, surfaces a degraded state
 * to the UI and retries with exponential backoff (2s → 4s → 8s → max 60s).
 *
 * This prevents the infinite reload loop that occurs when the backend returns
 * 502 errors during deployment or database outages.
 */

export type GmailStatus = "ok" | "paused" | "degraded";

export interface Status {
  ok: boolean;
  gmail?: GmailStatus;
  message?: string;
}

/**
 * Fetch status from /api/status endpoint with 5xx handling.
 *
 * Returns degraded state on network errors or 5xx responses instead of throwing.
 * This allows the UI to show a "Paused" banner instead of crashing/reloading.
 */
export async function fetchStatus(signal?: AbortSignal): Promise<Status> {
  try {
    const r = await fetch("/api/status", { signal });

    // On 5xx or network error, treat as degraded (not fatal)
    if (!r.ok) {
      if (r.status >= 500 && r.status < 600) {
        console.warn(`[StatusClient] Backend returned ${r.status} - treating as degraded`);

        // Try to parse JSON response (nginx @api_unavailable handler returns JSON)
        try {
          const data = await r.json();
          return {
            ok: false,
            gmail: "degraded",
            message: data.message || `Backend unavailable (HTTP ${r.status})`
          };
        } catch {
          // If JSON parsing fails, return generic message
          return {
            ok: false,
            gmail: "degraded",
            message: `Backend unavailable (HTTP ${r.status})`
          };
        }
      }

      // 4xx errors (e.g., 401, 403) might still be auth issues
      // but we shouldn't reload - let LoginGuard handle it
      return {
        ok: false,
        gmail: "degraded",
        message: `HTTP ${r.status}`
      };
    }

    const data = await r.json();

    // Map /status or /ready response to our Status interface
    // Example: { ok: true, gmail: "ok" } or { status: "ready", db: "ok", es: "ok" }
    if (data.ok === true || data.status === "ready" || data.db === "ok") {
      return { ok: true, gmail: "ok" };
    }

    return {
      ok: false,
      gmail: "degraded",
      message: data.errors?.join(", ") || "Services degraded"
    };

  } catch (err) {
    // Network unreachable, DNS failure, timeout, etc.
    // Treat as degraded state - DO NOT reload or throw
    const message = err instanceof Error ? err.message : "Network error";
    console.warn(`[StatusClient] Fetch error: ${message}`);
    return { ok: false, gmail: "degraded", message };
  }
}

/**
 * Start polling /api/status with exponential backoff on errors.
 *
 * - Healthy (ok=true, gmail="ok"): poll every 2s
 * - Degraded (ok=false or gmail="degraded"): backoff 2s → 4s → 8s → 16s → 32s → 60s max
 *
 * Returns a stop function to cancel the polling loop.
 *
 * @example
 * ```tsx
 * const stopPoll = startStatusPoll((status) => {
 *   setGmailStatus(status.gmail || "paused");
 *   if (!status.ok) {
 *     setBannerMessage(status.message || "Backend unavailable");
 *   }
 * });
 *
 * // Later: cleanup
 * stopPoll();
 * ```
 */
export function startStatusPoll(onUpdate: (s: Status) => void): () => void {
  let attempt = 0;
  let stopped = false;
  const ctrl = new AbortController();

  const tick = async () => {
    if (stopped) return;

    const status = await fetchStatus(ctrl.signal);
    onUpdate(status);

    const isHealthy = status.ok && status.gmail !== "degraded";

    if (isHealthy) {
      // Reset backoff when healthy
      attempt = 0;
    }

    // Compute next delay:
    // - Healthy: 2s
    // - Degraded: exponential backoff up to 60s
    const delay = isHealthy
      ? 2000
      : Math.min(60000, 1000 * Math.pow(2, attempt++));

    setTimeout(tick, delay);
  };

  // Start immediately
  tick();

  return () => {
    stopped = true;
    ctrl.abort();
  };
}
