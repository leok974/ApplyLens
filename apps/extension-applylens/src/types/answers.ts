/**
 * Phase 3.0: Answer Row Types
 *
 * Types for per-field answer rows in the autofill panel.
 * Used for rendering UI controls and tracking user edits.
 */

/**
 * Confidence level for field mapping
 */
export type FieldConfidence = "low" | "medium" | "high";

/**
 * Source of the suggested answer
 */
export type AnswerSource = "profile" | "heuristic" | "manual";

/**
 * Represents a single field's suggested answer in the panel.
 * Used for rendering UI controls and tracking user edits.
 */
export interface FieldAnswerRow {
  /** CSS selector for the target field (e.g. "input[name='q1']") */
  selector: string;

  /** Semantic key from learning profile (e.g. "first_name") */
  semanticKey: string;

  /** User-facing label for the field */
  label: string;

  /** Generated or suggested text answer */
  suggestedText: string;

  /** Whether this field will be applied on "Fill All" */
  accepted: boolean;

  /** Mapping confidence level */
  confidence?: FieldConfidence;

  /** Source of the suggestion */
  source?: AnswerSource;
}

/**
 * Backend response from /api/extension/generate-form-answers
 */
export interface BackendAnswersPayload {
  /** Map of semantic_key to generated answer text */
  answers: Record<string, string>;

  /** Field metadata from backend */
  fields: Array<{
    selector: string;
    semantic_key: string;
    label: string;
    confidence?: string;
    required?: boolean;
  }>;
}
