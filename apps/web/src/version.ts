// apps/web/src/version.ts

// Read from Vite env; fall back to a safe dev string.
export const APP_VERSION: string =
  (import.meta.env.VITE_APP_VERSION as string | undefined) ?? "dev-local";

// Optional: enrich with more metadata later if you want
export const buildInfo = {
  version: APP_VERSION,
  buildTime: import.meta.env.VITE_BUILD_TIME as string | undefined,
};
