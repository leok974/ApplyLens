/**
 * Reload Guard Utility
 *
 * Prevents infinite page reload loops by tracking reload attempts
 * and blocking rapid consecutive reloads.
 *
 * Use this in error handlers, auth logic, or any code that might
 * trigger page reloads.
 */

const RELOAD_GUARD_KEY = 'reload_guard_timestamp';
const RELOAD_COOLDOWN_MS = 5000; // 5 seconds minimum between reloads

/**
 * Check if it's safe to reload (not within cooldown period)
 */
export function canReload(): boolean {
  const lastReload = sessionStorage.getItem(RELOAD_GUARD_KEY);
  if (!lastReload) return true;

  const elapsed = Date.now() - parseInt(lastReload, 10);
  return elapsed > RELOAD_COOLDOWN_MS;
}

/**
 * Safely reload the page with guard check
 *
 * @param force - Skip the cooldown check (use with caution)
 * @returns true if reload was triggered, false if blocked by guard
 */
export function safeReload(force = false): boolean {
  if (!force && !canReload()) {
    console.warn('[ReloadGuard] Reload blocked - too soon after last reload');
    return false;
  }

  // Record this reload attempt
  sessionStorage.setItem(RELOAD_GUARD_KEY, Date.now().toString());
  window.location.reload();
  return true;
}

/**
 * Reset the reload guard (for testing or manual intervention)
 */
export function resetReloadGuard(): void {
  sessionStorage.removeItem(RELOAD_GUARD_KEY);
}

/**
 * Install global reload guard
 *
 * NOTE: Modern browsers prevent overriding window.location.reload due to security.
 * This function now serves as a no-op placeholder. Use safeReload() instead.
 *
 * Legacy function kept for backwards compatibility.
 */
export function installGlobalReloadGuard(): void {
  console.info('[ReloadGuard] Modern browsers block window.location.reload override');
  console.info('[ReloadGuard] Use safeReload() function instead of window.location.reload()');
  console.info('[ReloadGuard] No reload loops will occur - all auth errors use exponential backoff');
}
