/**
 * Phase 5.3: Companion extension learning API client
 *
 * Provides type-safe access to the learning endpoints including
 * the new style explanation API for transparency.
 */

import { api } from "./fetcher";

/**
 * Statistics for a single autofill style candidate
 */
export interface StyleChoiceStyleStats {
  style_id: string;
  source: "form" | "segment" | "family" | "none";
  segment_key: string | null;
  total_runs: number;
  helpful_runs: number;
  unhelpful_runs: number;
  helpful_ratio: number;
  avg_edit_chars: number | null;
  is_winner: boolean;
}

/**
 * Complete explanation of why a style was chosen for a form
 */
export interface StyleChoiceExplanation {
  host: string;
  schema_hash: string;
  host_family: string;
  segment_key: string | null;
  chosen_style_id: string | null;
  source: "form" | "segment" | "family" | "none";
  considered_styles: StyleChoiceStyleStats[];
  explanation: string;
}

/**
 * Fetch explanation for why a particular style was chosen for a form
 *
 * @param params - Form identifier (host + schemaHash)
 * @returns Detailed explanation with metrics for all considered styles
 */
export async function fetchStyleExplanation(params: {
  host: string;
  schemaHash: string;
}): Promise<StyleChoiceExplanation> {
  const url = `/api/extension/learning/explain-style?host=${encodeURIComponent(
    params.host
  )}&schema_hash=${encodeURIComponent(params.schemaHash)}`;

  const response = await api(url, {
    method: "GET",
    headers: {
      "X-Dev-Mode": "true", // Required for dev-only endpoint
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch style explanation: ${response.statusText}`);
  }

  return response.json();
}
