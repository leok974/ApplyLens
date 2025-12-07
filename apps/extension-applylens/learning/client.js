// learning/client.js — Learning event batching and API sync
import { APPLYLENS_API_BASE } from "../config.js";

let eventQueue = [];

function getApiBase() {
  // If called from extension context, use APPLYLENS_API_BASE from config
  // Otherwise detect from protocol
  if (typeof APPLYLENS_API_BASE !== "undefined") return APPLYLENS_API_BASE;
  if (location.protocol === "chrome-extension:") {
    return "https://applylens.ai";
  }
  return "http://localhost:8003";
}

/**
 * Get ApplyLens Extension ID
 * Reads from meta tag set by content-loader.js (CSP-safe)
 * Or from chrome.runtime.id if in extension context
 */
function getApplyLensExtensionId() {
  // Try chrome.runtime.id first (works in extension context)
  if (typeof chrome !== "undefined" && chrome.runtime?.id) {
    console.log("[Learning] Using extension ID from chrome.runtime:", chrome.runtime.id);
    return chrome.runtime.id;
  }

  // Try window global (set by extension-id.js)
  if (typeof window !== "undefined" && window.__APPLYLENS_EXTENSION_ID__) {
    console.log("[Learning] Using extension ID from window global:", window.__APPLYLENS_EXTENSION_ID__);
    return window.__APPLYLENS_EXTENSION_ID__;
  }

  // Try reading from meta tag (set by content-loader.js)
  const meta = document.querySelector('meta[name="applylens-extension-id"]');
  if (meta && meta.content) {
    console.log("[Learning] Using extension ID from meta tag:", meta.content);
    return meta.content;
  }

  // Try reading from script data attribute
  const idScript = document.getElementById('applylens-extension-id-script');
  if (idScript && idScript.dataset.extensionId) {
    console.log("[Learning] Using extension ID from script data attribute:", idScript.dataset.extensionId);
    return idScript.dataset.extensionId;
  }

  console.error("[Learning] Extension ID not available.");
  console.error("[Learning] chrome.runtime.id:", typeof chrome !== "undefined" && chrome.runtime ? chrome.runtime.id : "chrome.runtime not available");
  console.error("[Learning] window.__APPLYLENS_EXTENSION_ID__:", typeof window !== "undefined" ? window.__APPLYLENS_EXTENSION_ID__ : "window undefined");
  console.error("[Learning] meta tag:", meta ? meta.content : "not found");
  console.error("[Learning] id script:", idScript ? idScript.dataset.extensionId : "not found");
  return null;
}

/**
 * Send message to extension background/service worker
 * Handles both direct chrome.runtime calls and bridged calls from page context
 */
async function sendExtensionMessage(message) {
  const extensionId = getApplyLensExtensionId();

  if (!extensionId) {
    throw new Error("ApplyLens extension ID not available");
  }

  // Check if we're in page context (no chrome.runtime access)
  const hasDirectAccess = typeof chrome !== "undefined" && chrome.runtime && typeof chrome.runtime.sendMessage === "function";

  if (hasDirectAccess) {
    // Direct access - we're in extension context
    console.log("[Learning] Using direct chrome.runtime.sendMessage");
    return chrome.runtime.sendMessage(extensionId, message);
  } else {
    // Page context - use postMessage bridge
    console.log("[Learning] Using postMessage bridge to extension");
    return new Promise((resolve, reject) => {
      const requestId = `req_${Date.now()}_${Math.random()}`;

      const listener = (event) => {
        if (event.source !== window) return;
        if (event.data?.type === 'APPLYLENS_FROM_EXTENSION' && event.data.requestId === requestId) {
          window.removeEventListener('message', listener);
          resolve(event.data.response);
        }
      };

      window.addEventListener('message', listener);

      // Send via bridge
      window.postMessage({
        type: 'APPLYLENS_TO_EXTENSION',
        action: 'SEND_TO_BACKGROUND',
        payload: message,
        requestId
      }, '*');

      // Timeout after 30 seconds
      setTimeout(() => {
        window.removeEventListener('message', listener);
        reject(new Error('Extension message timeout'));
      }, 30000);
    });
  }
}

export function queueLearningEvent(event) {
  eventQueue.push(event);
}

export async function flushLearningEvents() {
  if (eventQueue.length === 0) return;

  const batch = [...eventQueue];
  eventQueue = []; // Clear queue optimistically

  try {
    const apiBase = getApiBase();
    const host = batch[0]?.host || location.host;
    const schemaHash = batch[0]?.schemaHash || "unknown";
    const genStyleId = batch[0]?.genStyleId || null; // Phase 5.0
    const policy = batch[0]?.policy || "exploit"; // Phase 5.4

    // Convert camelCase to snake_case for backend
    const payload = {
      host,
      schema_hash: schemaHash,
      gen_style_id: genStyleId, // Phase 5.0
      policy: policy, // Phase 5.4: bandit policy
      events: batch.map(e => ({
        host: e.host,
        schema_hash: e.schemaHash,
        suggested_map: e.suggestedMap,
        final_map: e.finalMap,
        edit_stats: {
          total_chars_added: e.editStats.totalCharsAdded,
          total_chars_deleted: e.editStats.totalCharsDeleted,
          per_field: e.editStats.perField
        },
        duration_ms: e.durationMs,
        validation_errors: e.validationErrors || {},
        status: e.status
      }))
    };

    const res = await sendExtensionMessage({
      type: "API_PROXY",
      payload: {
        url: "/api/extension/learning/sync",
        method: "POST",
        body: payload,
      }
    });

    if (!res.ok) {
      console.warn("[LearningClient] Sync failed:", res.status, res.error || "");
      // Don't re-queue - fire and forget for now to prevent infinite retries
      return;
    }

    console.log("[LearningClient] Synced", batch.length, "events successfully");
  } catch (err) {
    console.warn("[LearningClient] Sync error:", err);
    // Don't re-queue - fire and forget to prevent crashes
  }
}

/**
 * Fetch learning profile for a specific site and schema
 * Returns aggregated learning data to show hints in the UI
 */
export async function fetchLearningProfile({ host, schemaHash }) {
  const params = new URLSearchParams({
    host,
    schema_hash: schemaHash,
  });

  const apiBase = getApiBase();
  const url = `${apiBase}/api/extension/learning/profile?${params.toString()}`;

  try {
    console.log("[Learning] Fetching profile:", host, schemaHash);
    const response = await sendExtensionMessage({
      type: "API_PROXY",
      payload: {
        url: `/api/extension/learning/profile?host=${encodeURIComponent(host)}&schema_hash=${encodeURIComponent(schemaHash)}`,
        method: "GET",
      }
    });

    if (!response.ok) {
      console.warn("[Learning] Profile fetch failed:", response.status, response.error || "");
      return null;
    }

    const data = response.data;
    console.log("[Learning] Profile:", data);
    return data;
  } catch (err) {
    console.warn("[Learning] Profile fetch error:", err);
    return null;
  }
}

/**
 * Summarize learning profile for display in UI
 * Returns summary text and confidence level
 */
export function summarizeLearningProfile(profile) {
  if (!profile) {
    return {
      summary: "No previous ApplyLens activity on this site yet. This application will help train it.",
      level: "none",
    };
  }

  const count = profile.event_count ?? profile.total_events ?? 0;
  const rate = profile.success_rate ?? profile.avg_success ?? null;
  const updated = profile.last_seen_at ?? profile.updated_at ?? null;

  let bits = [];

  bits.push(`${count} previous application${count !== 1 ? 's' : ''}`);

  if (rate != null) {
    const pct = Math.round(rate * 100);
    bits.push(`${pct}% success`);
  }

  if (updated) {
    const date = new Date(updated);
    const now = new Date();
    const daysAgo = Math.floor((now - date) / (1000 * 60 * 60 * 24));
    if (daysAgo === 0) {
      bits.push("today");
    } else if (daysAgo === 1) {
      bits.push("yesterday");
    } else if (daysAgo < 7) {
      bits.push(`${daysAgo} days ago`);
    } else {
      bits.push(`${Math.floor(daysAgo / 7)} weeks ago`);
    }
  }

  return {
    summary: `Learned from ${bits.join(" · ")} on this site.`,
    level: count >= 10 ? "high" : count >= 3 ? "medium" : "low",
  };
}
