// sw.js — Service worker for ApplyLens Companion
// Handles message routing between popup/content script and backend API
//
// Dogfood v0.1 gaps addressed (from COMPANION_EXTENSION_AUDIT_2025-12.md):
// - Added CHECK_HEALTH message type for backend connectivity verification
// - Improved error handling with structured error responses
// - All API calls now return consistent {ok, data?, error?} format

import { APPLYLENS_API_BASE } from "./config.js";

const HISTORY_MAX = 50;

async function pushHistory(kind, item) {
  const key = kind === "applications" ? "history_applications" : "history_outreach";
  const now = new Date().toISOString();
  const withTs = { ...item, ts: now };
  const cur = (await chrome.storage.local.get([key]))[key] || [];
  cur.unshift(withTs);
  const trimmed = cur.slice(0, HISTORY_MAX);
  await chrome.storage.local.set({ [key]: trimmed });
}

async function apiPost(path, json) {
  const res = await fetch(`${APPLYLENS_API_BASE}${path}`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(json),
    credentials: "omit",
  });
  return res;
}

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  (async () => {
    try {
      if (msg?.type === "API_PROXY") {
        // Proxy API calls from content scripts to avoid CSP violations
        try {
          const { url, method = "GET", body, headers = {} } = msg.payload;
          const fetchOptions = {
            method,
            credentials: "include",
            headers: { "Content-Type": "application/json", ...headers },
          };
          if (body) {
            fetchOptions.body = JSON.stringify(body);
          }

          const r = await fetch(`${APPLYLENS_API_BASE}${url}`, fetchOptions);
          const data = await r.json();

          if (r.ok) {
            sendResponse({ ok: true, data, status: r.status });
          } else {
            sendResponse({ ok: false, error: `HTTP ${r.status}`, data, status: r.status });
          }
        } catch (err) {
          sendResponse({ ok: false, error: String(err), networkError: true });
        }
        return;
      }

      if (msg?.type === "CHECK_HEALTH") {
        // Dogfood v0.1: Use profile endpoint as health check (simpler than dedicated /health)
        try {
          const r = await fetch(`${APPLYLENS_API_BASE}/api/profile/me`, {
            method: "GET",
            credentials: "include",
          });
          if (r.ok) {
            const data = await r.json();
            sendResponse({ ok: true, data });
          } else {
            sendResponse({ ok: false, error: `HTTP ${r.status}`, httpStatus: r.status });
          }
        } catch (err) {
          sendResponse({ ok: false, error: String(err), networkError: true });
        }
      }
      else if (msg?.type === "GET_PROFILE") {
        const r = await fetch(`${APPLYLENS_API_BASE}/api/profile/me`);
        if (!r.ok) {
          sendResponse({ ok: false, error: `HTTP ${r.status}`, httpStatus: r.status });
          return;
        }
        const data = await r.json();
        sendResponse({ ok: r.ok, data });
      }
      else if (msg?.type === "GEN_FORM_ANSWERS") {
        const r = await apiPost(`/api/extension/generate-form-answers`, msg.payload);
        if (!r.ok) {
          sendResponse({ ok: false, error: `HTTP ${r.status}`, httpStatus: r.status });
          return;
        }
        const data = await r.json();
        sendResponse({ ok: true, data });
      }
      else if (msg?.type === "LOG_APPLICATION") {
        const r = await apiPost(`/api/extension/applications`, msg.payload);
        await pushHistory("applications", msg.payload);
        sendResponse({ ok: r.ok });
      }
      else if (msg?.type === "GEN_DM") {
        const r = await apiPost(`/api/extension/generate-recruiter-dm`, msg.payload);
        if (!r.ok) {
          sendResponse({ ok: false, error: `HTTP ${r.status}`, httpStatus: r.status });
          return;
        }
        const data = await r.json();
        sendResponse({ ok: true, data });
      }
      else if (msg?.type === "LOG_OUTREACH") {
        const r = await apiPost(`/api/extension/outreach`, msg.payload);
        await pushHistory("outreach", msg.payload);
        sendResponse({ ok: r.ok });
      }
      else if (msg?.type === "SCAN_AND_SUGGEST") {
        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
        if (tab?.id) await chrome.tabs.sendMessage(tab.id, { type: "SCAN_AND_SUGGEST" });
        sendResponse({ ok: true });
      }
      else if (msg?.type === "GET_HISTORY") {
        const { history_applications = [], history_outreach = [] } = await chrome.storage.local.get(["history_applications", "history_outreach"]);
        sendResponse({ ok: true, applications: history_applications, outreach: history_outreach });
      }
    } catch (e) {
      console.error("[SW] Message handler error:", e);
      sendResponse({ ok: false, error: String(e), networkError: true });
    }
  })();
  return true; // async
});

// Handle messages from externally connected scripts (web_accessible_resources in page context)
// These scripts use chrome.runtime.sendMessage(extensionId, ...) and trigger onMessageExternal
chrome.runtime.onMessageExternal.addListener((msg, sender, sendResponse) => {
  console.log("[SW] External message received:", msg.type, "from:", sender.url);

  // Reuse the same handler as onMessage
  // All our message types (API_PROXY, etc.) work the same regardless of source
  (async () => {
    try {
      if (msg?.type === "API_PROXY") {
        // Proxy API calls from content scripts to avoid CSP violations
        try {
          const { url, method = "GET", body, headers = {} } = msg.payload;
          const fetchOptions = {
            method,
            credentials: "include",
            headers: { "Content-Type": "application/json", ...headers },
          };
          if (body) {
            fetchOptions.body = JSON.stringify(body);
          }

          const r = await fetch(`${APPLYLENS_API_BASE}${url}`, fetchOptions);
          const data = await r.json();

          if (r.ok) {
            sendResponse({ ok: true, data, status: r.status });
          } else {
            sendResponse({ ok: false, error: `HTTP ${r.status}`, data, status: r.status });
          }
        } catch (err) {
          sendResponse({ ok: false, error: String(err), networkError: true });
        }
        return;
      }

      // For other message types, we can add handlers as needed
      console.warn("[SW] Unhandled external message type:", msg.type);
      sendResponse({ ok: false, error: "Unhandled message type" });
    } catch (e) {
      console.error("[SW] External message handler error:", e);
      sendResponse({ ok: false, error: String(e), networkError: true });
    }
  })();
  return true; // async
});
