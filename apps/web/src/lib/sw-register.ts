/**
 * Service Worker Registration with Reload Guards
 *
 * Prevents infinite reload loops by:
 * - Only reloading ONCE per build ID
 * - Disabling SW in development (localhost)
 * - Reloading only on activated state (not on updatefound)
 * - Using sessionStorage to track reload attempts
 */

/**
 * Get the current build ID from meta tag or environment
 */
function getBuildId(): string {
  // Check meta tag first
  const metaTag = document.querySelector('meta[name="build-id"]');
  if (metaTag) {
    return metaTag.getAttribute('content') || 'unknown';
  }

  // Fallback to global variable if set by build process
  if ((window as any).__BUILD_ID__) {
    return (window as any).__BUILD_ID__;
  }

  // Last resort: use timestamp-based ID
  return `build-${Date.now()}`;
}

/**
 * Setup controlled reload on service worker activation
 * Only reloads once per build ID to prevent infinite loops
 */
function setupSwReloadOnce() {
  const buildId = getBuildId();
  const reloadKey = `sw_reload_${buildId}`;

  navigator.serviceWorker?.addEventListener('controllerchange', () => {
    // Check if we've already reloaded for this build
    if (sessionStorage.getItem(reloadKey)) {
      console.log('[SW] Already reloaded for build', buildId, '- skipping');
      return;
    }

    // Mark that we're reloading for this build
    sessionStorage.setItem(reloadKey, '1');
    console.log('[SW] New service worker activated - reloading once for build', buildId);
    window.location.reload();
  });
}

/**
 * Register service worker with safe reload logic
 *
 * Features:
 * - Disabled on localhost to avoid dev issues
 * - Only registers in browsers that support SW
 * - Reload guard prevents infinite loops
 * - Logs registration status for debugging
 */
export async function registerServiceWorker(): Promise<void> {
  // Skip if service workers not supported
  if (!('serviceWorker' in navigator)) {
    console.log('[SW] Service workers not supported');
    return;
  }

  // Skip on localhost (development)
  if (location.hostname === 'localhost' || location.hostname === '127.0.0.1') {
    console.log('[SW] Skipping service worker registration on localhost');
    return;
  }

  try {
    // Setup reload guard before registering
    setupSwReloadOnce();

    // Register the service worker
    const registration = await navigator.serviceWorker.register('/sw.js', {
      scope: '/'
    });

    console.log('[SW] Service worker registered successfully', registration.scope);

    // Listen for updates but don't reload immediately
    // Let controllerchange handle the reload
    registration.addEventListener('updatefound', () => {
      const newWorker = registration.installing;
      console.log('[SW] Update found - new worker installing');

      newWorker?.addEventListener('statechange', () => {
        console.log('[SW] Worker state changed to:', newWorker.state);
      });
    });

    // Check for updates periodically (every hour)
    setInterval(() => {
      registration.update().catch(err => {
        console.warn('[SW] Update check failed:', err);
      });
    }, 60 * 60 * 1000);

  } catch (error) {
    console.warn('[SW] Service worker registration failed:', error);
  }
}

/**
 * Unregister all service workers (for debugging/cleanup)
 */
export async function unregisterServiceWorker(): Promise<void> {
  if (!('serviceWorker' in navigator)) return;

  const registrations = await navigator.serviceWorker.getRegistrations();
  for (const registration of registrations) {
    await registration.unregister();
    console.log('[SW] Unregistered service worker');
  }
}
