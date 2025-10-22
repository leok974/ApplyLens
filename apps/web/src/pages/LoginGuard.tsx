import { useEffect, useState } from "react";

interface LoginGuardProps {
  children: React.ReactNode;
}

/**
 * LoginGuard checks authentication status without reloading the page on errors.
 *
 * Previously, any network error (including 502s from backend unavailability) would
 * redirect to /welcome, causing an infinite reload loop. Now, we:
 * 1. Treat 5xx as "degraded" state (show loading/retry, don't redirect)
 * 2. Only redirect to /welcome on 401 (unauthenticated) or empty email
 * 3. Never call window.location.href on network errors
 */
export default function LoginGuard({ children }: LoginGuardProps) {
  const [authState, setAuthState] = useState<"checking" | "authenticated" | "degraded">("checking");

  useEffect(() => {
    let mounted = true;
    let retryTimeout: NodeJS.Timeout | null = null;

    const checkAuth = async (attempt = 0) => {
      try {
        const r = await fetch("/api/auth/me", { credentials: "include" });

        if (!mounted) return;

        // 5xx: backend degraded, retry with backoff (don't redirect)
        if (r.status >= 500 && r.status < 600) {
          console.warn(`[LoginGuard] Backend unavailable (${r.status}), retrying...`);
          setAuthState("degraded");

          // Exponential backoff: 2s, 4s, 8s, 16s, max 30s
          const delay = Math.min(30000, 2000 * Math.pow(2, attempt));
          retryTimeout = setTimeout(() => checkAuth(attempt + 1), delay);
          return;
        }

        // 401/403: not authenticated, redirect to welcome
        if (r.status === 401 || r.status === 403) {
          window.location.href = "/welcome";
          return;
        }

        // 4xx other than 401/403: treat as degraded
        if (r.status >= 400 && r.status < 500) {
          console.warn(`[LoginGuard] Unexpected status ${r.status}, treating as degraded`);
          setAuthState("degraded");
          const delay = Math.min(30000, 2000 * Math.pow(2, attempt));
          retryTimeout = setTimeout(() => checkAuth(attempt + 1), delay);
          return;
        }

        const me = await r.json();

        // No email: not authenticated, redirect
        if (!me?.email) {
          window.location.href = "/welcome";
          return;
        }

        // Success: authenticated
        setAuthState("authenticated");

      } catch (err) {
        // Network error (DNS, timeout, etc.): retry with backoff
        if (!mounted) return;

        console.warn(`[LoginGuard] Network error: ${err}, retrying...`);
        setAuthState("degraded");

        const delay = Math.min(30000, 2000 * Math.pow(2, attempt));
        retryTimeout = setTimeout(() => checkAuth(attempt + 1), delay);
      }
    };

    checkAuth();

    return () => {
      mounted = false;
      if (retryTimeout) clearTimeout(retryTimeout);
    };
  }, []);

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

  return <>{children}</>;
}
