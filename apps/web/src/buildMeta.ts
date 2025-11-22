// apps/web/src/buildMeta.ts
export const BUILD_META = {
  env: import.meta.env.MODE,
  flavor: import.meta.env.VITE_BUILD_FLAVOR ?? "unknown",      // dev-local / prod / staging
  version: import.meta.env.VITE_APP_VERSION ?? "dev",          // from CI, fallback to dev
  gitSha: import.meta.env.VITE_BUILD_GIT_SHA ?? "local",       // short commit SHA
  builtAt: import.meta.env.VITE_BUILD_TIME ?? "unknown",       // ISO timestamp
};
