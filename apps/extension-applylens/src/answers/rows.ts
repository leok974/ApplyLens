/**
 * Phase 3.0: Answer Row Conversion
 *
 * Converts backend answers payload into per-field rows for panel rendering.
 */

import type { FieldAnswerRow, BackendAnswersPayload, FieldConfidence } from "../types/answers";

/**
 * Converts backend answers payload into per-field rows for panel rendering.
 *
 * @param payload - Backend response from /api/extension/generate-form-answers
 * @returns Array of FieldAnswerRow objects ready for UI rendering
 *
 * @example
 * ```typescript
 * const payload = {
 *   answers: { first_name: "John", last_name: "Doe" },
 *   fields: [
 *     { selector: "input[name='fname']", semantic_key: "first_name", label: "First Name" }
 *   ]
 * };
 * const rows = toFieldRows(payload);
 * // rows[0] = { selector: "input[name='fname']", semanticKey: "first_name", ... }
 * ```
 */
export function toFieldRows(payload: BackendAnswersPayload): FieldAnswerRow[] {
  const { answers, fields } = payload;

  return fields.map(field => {
    const hasAnswer = answers[field.semantic_key] && answers[field.semantic_key].trim().length > 0;

    return {
      selector: field.selector,
      semanticKey: field.semantic_key,
      label: field.label,
      suggestedText: answers[field.semantic_key] || "",
      accepted: true, // Default: all fields accepted
      confidence: (field.confidence as FieldConfidence) || undefined,
      source: hasAnswer ? "profile" : "heuristic",
    };
  });
}

/**
 * Filters rows to only those accepted by the user.
 * Useful before applying answers to the DOM.
 *
 * @param rows - Array of FieldAnswerRow objects
 * @returns Array containing only accepted rows
 */
export function getAcceptedRows(rows: FieldAnswerRow[]): FieldAnswerRow[] {
  return rows.filter(row => row.accepted);
}

/**
 * Counts manually edited rows.
 * Useful for tracking user engagement metrics.
 *
 * @param rows - Array of FieldAnswerRow objects
 * @returns Count of rows where source is "manual"
 */
export function countManualEdits(rows: FieldAnswerRow[]): number {
  return rows.filter(row => row.source === "manual").length;
}

/**
 * Validates that all required fields have non-empty answers.
 *
 * @param rows - Array of FieldAnswerRow objects
 * @param requiredKeys - Array of semantic keys that must have values
 * @returns Object with isValid boolean and array of missing field labels
 */
export function validateRequiredFields(
  rows: FieldAnswerRow[],
  requiredKeys: string[]
): { isValid: boolean; missing: string[] } {
  const missing: string[] = [];

  for (const key of requiredKeys) {
    const row = rows.find(r => r.semanticKey === key);
    if (!row || !row.suggestedText.trim()) {
      missing.push(row?.label || key);
    }
  }

  return {
    isValid: missing.length === 0,
    missing,
  };
}
