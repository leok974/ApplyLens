/** TypeScript types for the Companion learning loop. */

export type SelectorMap = Record<string, string>;

export interface FormMemoryStats {
  totalRuns: number;
  lastUsedAt: string; // ISO string
}

export interface FormMemoryEntry {
  host: string;
  schemaHash: string;
  selectorMap: SelectorMap;
  stylePrefs?: {
    genStyleId?: string;
  };
  stats: FormMemoryStats;
}

export interface LearningSyncEvent {
  host: string;
  schemaHash: string;
  suggestedMap: SelectorMap;
  finalMap: SelectorMap;
  genStyleId?: string;
  editStats: {
    totalCharsAdded: number;
    totalCharsDeleted: number;
    perField: Record<string, { added: number; deleted: number }>;
  };
  durationMs: number;
  validationErrors: Record<string, unknown>;
  status: "ok" | "validation_error" | "cancelled";
}

export interface LearningProfile {
  host: string;
  schemaHash: string;
  canonicalMap: SelectorMap;
  styleHint?: {
    genStyleId?: string;
    confidence: number;
  } | null;
}
