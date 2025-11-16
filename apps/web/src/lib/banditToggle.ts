// apps/web/src/lib/banditToggle.ts

const STORAGE_KEY = "applylens:banditEnabled";

// Default behavior if nothing is stored yet
const DEFAULT_ENABLED = true;

declare global {
  interface Window {
    __APPLYLENS_BANDIT_ENABLED?: boolean;
  }
}

/**
 * Read the current bandit-enabled setting from localStorage.
 * Falls back to DEFAULT_ENABLED when unset or malformed.
 */
export function readBanditEnabledFromStorage(): boolean {
  if (typeof window === "undefined") return DEFAULT_ENABLED;

  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (raw === "true") return true;
    if (raw === "false") return false;
  } catch {
    // ignore storage errors and fall back
  }
  return DEFAULT_ENABLED;
}

/**
 * Persist the setting to localStorage and mirror it onto the window global.
 */
export function writeBanditEnabled(enabled: boolean): void {
  if (typeof window === "undefined") return;

  try {
    window.localStorage.setItem(STORAGE_KEY, enabled ? "true" : "false");
  } catch {
    // ignore storage errors
  }

  window.__APPLYLENS_BANDIT_ENABLED = enabled;
}

/**
 * Initialize the window global from storage.
 * Call this once on app bootstrap or when the settings page mounts.
 */
export function initBanditFlagFromStorage(): boolean {
  const enabled = readBanditEnabledFromStorage();
  if (typeof window !== "undefined") {
    window.__APPLYLENS_BANDIT_ENABLED = enabled;
  }
  return enabled;
}
