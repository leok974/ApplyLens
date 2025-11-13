// Simple envless toggle: change once for prod builds
export const APPLYLENS_API_BASE =
  (typeof chrome !== "undefined" && chrome.runtime?.id && location.protocol === "chrome-extension:")
    ? "https://api.applylens.app" // prod default
    : "http://localhost:8003";     // dev default
