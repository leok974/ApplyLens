// Simple envless toggle: change once for prod builds
console.log("[ApplyLens] config.js loading on", location.hostname);

// Always use production API to avoid CSP violations in content scripts
export const APPLYLENS_API_BASE = "https://api.applylens.app";

console.log("[ApplyLens] API_BASE set to:", APPLYLENS_API_BASE);
