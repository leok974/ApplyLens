/**
 * ES Module version of learning profile client
 * Integrates with existing extension learning system
 */

import { APPLYLENS_API_BASE } from "./config.js";

/**
 * Get API base URL
 */
function getApiBase() {
  return APPLYLENS_API_BASE;
}

/**
 * Fetch learning profile from server for a given form.
 *
 * Returns aggregated canonical mappings and style hints based on
 * historical user events for this form schema.
 *
 * @param {string} host - The host domain (e.g., "example.com")
 * @param {string} schemaHash - The form schema hash
 * @returns {Promise<Object|null>} LearningProfile or null if not available
 */
async function fetchLearningProfile(host, schemaHash) {
  const base = getApiBase();

  try {
    const url = new URL("/api/extension/learning/profile", base);
    url.searchParams.set("host", host);
    url.searchParams.set("schema_hash", schemaHash);

    const res = await fetch(url.toString(), {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    });

    if (!res.ok) {
      return null;
    }

    const data = await res.json();

    // Defensive normalization: convert snake_case to camelCase
    // Phase 5.0: Support both gen_style_id and preferred_style_id
    const styleHint = data.style_hint
      ? {
          genStyleId: data.style_hint.preferred_style_id ?? data.style_hint.gen_style_id,
          confidence: data.style_hint.confidence,
        }
      : null;

    return {
      host: data.host || host,
      schemaHash: data.schema_hash || schemaHash,
      canonicalMap: data.canonical_map || {},
      styleHint,
    };
  } catch (error) {
    // Network errors: just treat as no profile
    console.warn("Failed to fetch learning profile:", error);
    return null;
  }
}

// ES module export
export { fetchLearningProfile };
