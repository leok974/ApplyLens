// sw.js — add history persistence using chrome.storage.local
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
      if (msg?.type === "GET_PROFILE") {
        const r = await fetch(`${APPLYLENS_API_BASE}/api/profile/me`);
        const data = await r.json();
        sendResponse({ ok: r.ok, data });
      }
      else if (msg?.type === "GEN_FORM_ANSWERS") {
        const r = await apiPost(`/api/extension/generate-form-answers`, msg.payload);
        sendResponse({ ok: r.ok, data: r.ok ? await r.json() : null });
      }
      else if (msg?.type === "LOG_APPLICATION") {
        const r = await apiPost(`/api/extension/applications`, msg.payload);
        await pushHistory("applications", msg.payload);
        sendResponse({ ok: r.ok });
      }
      else if (msg?.type === "GEN_DM") {
        const r = await apiPost(`/api/extension/generate-recruiter-dm`, msg.payload);
        sendResponse({ ok: r.ok, data: r.ok ? await r.json() : null });
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
      sendResponse({ ok: false, error: String(e) });
    }
  })();
  return true; // async
});
