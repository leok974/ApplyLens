// Centralized settings for the Applications Tracker UI.
// Tweak these arrays/labels to customize behavior without touching components.

// Check for environment variable to allow runtime configuration
const ENV_SNIPPETS = (import.meta as any).env?.VITE_TRACKER_SNIPPETS as string | undefined
// Example: VITE_TRACKER_SNIPPETS="Sent thank-you|Follow-up scheduled|Left voicemail"

export const NOTE_SNIPPETS: string[] = ENV_SNIPPETS
  ? ENV_SNIPPETS.split('|').map((s) => s.trim()).filter(Boolean)
  : [
      'Sent thank-you',
      'Follow-up scheduled',
      'Left voicemail',
      'Recruiter screen scheduled',
      'Sent take-home',
      'Referred by X',
      'Declined offer',
    ]

// Example: you can also centralize other tracker UI strings here later, e.g.:
// export const STATUS_LABEL: Record<string, string> = { ... }
// export const STATUS_TO_VARIANT: Record<string, "default"|"success"|"warning"|"error"|"info"> = { ... }

// Tip:
// If you want environment-specific snippets, you can read from process.env (Node)
// or import.meta.env (Vite) and split a CSV, falling back to this array.
// This config already supports VITE_TRACKER_SNIPPETS environment variable:
//   - Set in .env.development or .env.production
//   - Format: pipe-delimited string "Snippet 1|Snippet 2|Snippet 3"
//   - Empty strings are filtered out automatically
