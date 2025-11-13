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

    // Convert camelCase to snake_case for backend
    const payload = {
      host,
      schema_hash: schemaHash,
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

    const res = await fetch(`${apiBase}/api/extension/learning/sync`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(payload),
      credentials: "include"
    });

    if (!res.ok) {
      console.warn("[LearningClient] Sync failed:", res.status);
      // Re-queue events for retry
      eventQueue.push(...batch);
    }
  } catch (err) {
    console.warn("[LearningClient] Sync error:", err);
    // Re-queue events for retry
    eventQueue.push(...batch);
  }
}
