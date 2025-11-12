import { APPLYLENS_API_BASE } from "./config.js";

chrome.runtime.onInstalled.addListener(() => {
  console.log("[ApplyLens] installed");
});

// In-memory profile cache per SW lifetime
let profileCache = null;
async function fetchProfile() {
  if (profileCache) return profileCache;
  const r = await fetch(`${APPLYLENS_API_BASE}/api/profile/me`);
  if (!r.ok) throw new Error(`profile fetch failed ${r.status}`);
  profileCache = await r.json();
  return profileCache;
}

// Message router
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  (async () => {
    try {
      if (msg.type === "GET_PROFILE") {
        const p = await fetchProfile();
        sendResponse({ ok: true, data: p });
      } else if (msg.type === "GEN_FORM_ANSWERS") {
        const r = await fetch(`${APPLYLENS_API_BASE}/api/extension/generate-form-answers`, {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify(msg.payload)
        });
        const data = await r.json();
        sendResponse({ ok: r.ok, data, status: r.status });
      } else if (msg.type === "LOG_APPLICATION") {
        const r = await fetch(`${APPLYLENS_API_BASE}/api/extension/applications`, {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify(msg.payload)
        });
        const data = await r.json().catch(() => ({}));
        sendResponse({ ok: r.ok, data, status: r.status });
      } else if (msg.type === "GEN_DM") {
        const r = await fetch(`${APPLYLENS_API_BASE}/api/extension/generate-recruiter-dm`, {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify(msg.payload)
        });
        const data = await r.json();
        sendResponse({ ok: r.ok, data, status: r.status });
      } else if (msg.type === "LOG_OUTREACH") {
        const r = await fetch(`${APPLYLENS_API_BASE}/api/extension/outreach`, {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify(msg.payload)
        });
        const data = await r.json().catch(() => ({}));
        sendResponse({ ok: r.ok, data, status: r.status });
      }
    } catch (e) {
      sendResponse({ ok: false, error: String(e) });
    }
  })();
  return true; // keep channel open for async
});
