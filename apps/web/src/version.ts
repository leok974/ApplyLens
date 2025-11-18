// apps/web/src/version.ts

// Read from Vite env; fall back to a safe dev string.
export const APP_VERSION: string =
  (import.meta.env.VITE_APP_VERSION as string | undefined) ?? "dev-local";

// Build metadata for debugging and version tracking
export const BUILD_META = {
  env: import.meta.env.MODE,
  flavor: import.meta.env.VITE_BUILD_FLAVOR ?? "unknown",      // dev-local / prod / staging
  version: import.meta.env.VITE_BUILD_VERSION ?? "dev",        // e.g. 0.4.3
  gitSha: import.meta.env.VITE_BUILD_GIT_SHA ?? "local",       // short commit
  builtAt: import.meta.env.VITE_BUILD_TIME ?? "",              // ISO datetime
};

// Backwards compatibility
export const buildInfo = {
  version: APP_VERSION,
  buildTime: import.meta.env.VITE_BUILD_TIME as string | undefined,
};
