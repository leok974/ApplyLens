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
    const styleHint = data.style_hint
      ? {
          genStyleId: data.style_hint.gen_style_id,
          confidence: data.style_hint.confidence,
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
