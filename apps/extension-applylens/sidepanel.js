import { APPLYLENS_API_BASE } from "./config.js";
(async () => {
  const el = document.getElementById("status");
  try {
    const r = await fetch(`${APPLYLENS_API_BASE}/api/profile/me`);
    el.textContent = r.ok ? "Connected ✅" : `API error ${r.status}`;
  } catch (e) {
    el.textContent = "Offline";
  }
})();
