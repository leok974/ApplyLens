import { LearningProfile } from "./types";

/**
 * Get API base URL - same logic as client.ts
 */
function getApiBase(): string {
  if (typeof window !== "undefined" && window.location.protocol === "chrome-extension:") {
    return "https://api.applylens.app";
  }
  return "http://localhost:8003";
}

/**
 * Fetch learning profile from server for a given form.
 *
 * Returns aggregated canonical mappings and style hints based on
 * historical user events for this form schema.
 *
 * @param host - The host domain (e.g., "example.com")
 * @param schemaHash - The form schema hash
 * @returns LearningProfile or null if not available
 */
export async function fetchLearningProfile(
  host: string,
  schemaHash: string
): Promise<LearningProfile | null> {
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
    // Phase 5.0: Map all style hint fields including preferred_style_id
    const styleHint = data.style_hint
      ? {
          // Legacy fields
          genStyleId: data.style_hint.gen_style_id ?? undefined,
          confidence: data.style_hint.confidence ?? undefined,
          // Phase 5.0 fields
          summaryStyle: data.style_hint.summary_style ?? undefined,
          maxLength: data.style_hint.max_length ?? undefined,
          tone: data.style_hint.tone ?? undefined,
          preferredStyleId: data.style_hint.preferred_style_id ?? undefined,
          styleStats: data.style_hint.style_stats ?? undefined,
        }
      : null;

    return {
      host: data.host ?? host,
      schemaHash: data.schema_hash ?? schemaHash,
      canonicalMap: data.canonical_map ?? {},
      styleHint,
    };
  } catch {
    // Network errors: just treat as no profile
    return null;
  }
}
