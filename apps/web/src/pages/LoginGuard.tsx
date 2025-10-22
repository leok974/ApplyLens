import { useEffect, useRef, useState } from "react";

interface LoginGuardProps {
  children: React.ReactNode;
}

type Me = { id: string; email: string } | null;

/**
 * Fetch user from /api/auth/me with proper error handling.
 *
 * - 401 → null (stable unauthenticated state, show login CTA)
 * - 5xx/network → "degraded" (retry with backoff)
 * - 200 → user object
 */
async function getMe(signal?: AbortSignal): Promise<Me | "degraded"> {
  try {
    const r = await fetch("/api/auth/me", {
      credentials: "include",
      signal,
      headers: { "Accept": "application/json" },
    });

    // 401 is a STABLE unauthenticated state - don't retry!
    if (r.status === 401) {
      console.info("[LoginGuard] User not authenticated (401)");
      return null;
    }

    // Any other non-OK status is degraded (network/backend issue)
    if (!r.ok) {
      console.warn(`[LoginGuard] Backend error ${r.status}, treating as degraded`);
      throw new Error(`HTTP ${r.status}`);
    }

    const data = await r.json();
    return data;
  } catch (err) {
    // Network error, timeout, or 5xx → degraded state
    if (err instanceof Error && err.name !== "AbortError") {
      console.warn(`[LoginGuard] Network/server error: ${err.message}`);
    }
    return "degraded";
  }
}

/**
 * LoginGuard - Auth check WITHOUT loops.
 *
 * KEY FIXES:
 * 1. 401 → Show login CTA (NO redirect, NO retry)
 * 2. 5xx/network → Show degraded UI + exponential backoff retry
 * 3. Effect runs ONCE (proper cleanup with AbortController)
 * 4. No window.location.href calls (breaks SPA navigation)
 */
export default function LoginGuard({ children }: LoginGuardProps) {
  const [authState, setAuthState] = useState<"checking" | "authenticated" | "unauthenticated" | "degraded">("checking");
  const stopRef = useRef(false);
  const ctrlRef = useRef<AbortController | null>(null);

  useEffect(() => {
    stopRef.current = false;
    let attempt = 0;

    const tick = async () => {
      if (stopRef.current) return;

      // Abort any previous in-flight request
      ctrlRef.current?.abort();
      const ctrl = new AbortController();
      ctrlRef.current = ctrl;

      const me = await getMe(ctrl.signal);

      if (stopRef.current) return; // Check again after async

      if (me === "degraded") {
        setAuthState("degraded");
        // Exponential backoff: 1s, 2s, 4s, 8s, 16s, 32s, max 60s
        const delay = Math.min(60000, 1000 * Math.pow(2, attempt++));
        console.info(`[LoginGuard] Retrying in ${delay}ms (attempt ${attempt})`);
        setTimeout(tick, delay);
        return;
      }

      // Reset attempt counter on successful response
      attempt = 0;

      if (me === null) {
        // User not authenticated - show login CTA (NO LOOP!)
        setAuthState("unauthenticated");
        return;
      }

      // User is authenticated
      setAuthState("authenticated");
    };

    tick();

    // Cleanup: stop polling and abort in-flight request
    return () => {
      stopRef.current = true;
      ctrlRef.current?.abort();
    };
  }, []); // Empty deps - runs ONCE on mount

  // Show loading or degraded UI while checking auth
  if (authState === "checking") {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-muted-foreground">Checking authentication...</p>
        </div>
      </div>
    );
  }

  if (authState === "degraded") {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center max-w-md mx-auto p-6">
          <div className="animate-pulse rounded-full h-12 w-12 bg-yellow-200 dark:bg-yellow-800 mx-auto mb-4"></div>
          <h2 className="text-xl font-semibold mb-2">Service Temporarily Unavailable</h2>
          <p className="text-muted-foreground mb-4">
            Unable to reach authentication service. Retrying automatically...
          </p>
          <p className="text-sm text-muted-foreground">
            This usually resolves within a few seconds during deployments.
          </p>
        </div>
      </div>
    );
  }

  // Unauthenticated - show login CTA (NO redirect loop!)
  if (authState === "unauthenticated") {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center max-w-md mx-auto p-6">
          <h2 className="text-2xl font-bold mb-4">Sign In Required</h2>
          <p className="text-muted-foreground mb-6">
            Please sign in to access this page.
          </p>
          <a
            href="/api/auth/google/login"
            className="inline-block px-6 py-3 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors"
          >
            Sign In with Google
          </a>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
