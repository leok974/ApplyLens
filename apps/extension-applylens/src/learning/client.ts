/** Learning client - batches and syncs learning events to the backend. */

import { LearningSyncEvent } from "./types";

// In a real implementation, this would import from config.js
// For now, we'll detect it at runtime like the main extension does
function getApiBase(): string {
  // Same logic as config.js
  if (typeof window !== "undefined" && window.location.protocol === "chrome-extension:") {
    return "https://api.applylens.app";
  }
  return "http://localhost:8003";
}

let pendingEvents: LearningSyncEvent[] = [];

export function queueLearningEvent(event: LearningSyncEvent) {
  pendingEvents.push(event);
}

export async function flushLearningEvents(): Promise<void> {
  if (!pendingEvents.length) return;

  const batch = [...pendingEvents];
  pendingEvents = [];

  const { host, schemaHash } = batch[0];
  const body = {
    host,
    schema_hash: schemaHash,
    events: batch.map((e) => ({
      host: e.host,
      schema_hash: e.schemaHash,
      suggested_map: e.suggestedMap,
      final_map: e.finalMap,
      gen_style_id: e.genStyleId,
      edit_stats: {
        total_chars_added: e.editStats.totalCharsAdded,
        total_chars_deleted: e.editStats.totalCharsDeleted,
        per_field: e.editStats.perField,
      },
      duration_ms: e.durationMs,
      validation_errors: e.validationErrors,
      status: e.status,
    })),
  };

  try {
    const res = await fetch(`${getApiBase()}/api/extension/learning/sync`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
      credentials: "omit",
    });

    if (!res.ok) {
      // Best-effort: re-queue on failure
      pendingEvents.push(...batch);
    }
  } catch (err) {
    // Re-queue on network error
    pendingEvents.push(...batch);
  }
}
