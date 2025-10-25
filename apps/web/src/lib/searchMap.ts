/**
 * Utility helpers for search results normalization
 *
 * Provides clean subject derivation when missing and consistent mapping
 * of Elasticsearch hits to a predictable shape for the UI.
 */

export type RawHit = {
  id?: string;
  gmail_id?: string;
  _id?: string;
  subject?: string | null;
  subject_highlight?: string | null;
  snippet?: string | null;
  body?: string | null;
  body_highlight?: string | null;
  body_preview?: string | null;
  preview?: string | null;
  from?: string | null;
  from_email?: string | null;
  from_addr?: string | null;
  sender?: string | null;
  date?: string | number | null;
  sent_at?: string | number | null;
  received_at?: string | number | null;
  score?: number | null;
  replied?: boolean;
  time_to_response_hours?: number | null;
  first_user_reply_at?: string | null;
  labels?: string[];
  label_heuristics?: string[];
  label?: string;
  category?: string;
  expires_at?: string | null;
  event_start_at?: string | null;
  risk_score?: number | null;
  quarantined?: boolean;
  highlight?: {
    subject?: string[];
    body?: string[];
    body_text?: string[];
    body_sayt?: string[];
  };
  _source?: any;
};

/**
 * Strip HTML tags from a string
 */
const stripHtml = (s: string): string => s.replace(/<[^>]+>/g, "");

/**
 * Collapse multiple whitespace into single spaces and trim
 */
const squish = (s: string): string => s.replace(/\s+/g, " ").trim();

/**
 * Derive a friendly subject line when it's missing or empty
 *
 * Priority:
 * 1. Highlighted subject
 * 2. Regular subject
 * 3. Highlighted body snippet
 * 4. Regular snippet
 * 5. Body preview (first 140 chars)
 * 6. Fallback: "[No subject]"
 */
export function deriveSubject(hit: RawHit): string {
  // Try direct subject fields first
  const directSubject = (hit.subject_highlight ?? hit.subject ?? "").trim();
  if (directSubject) return directSubject;

  // Prefer highlighted snippets, then snippet, then body preview
  const candidates = [
    hit.highlight?.subject?.[0],
    hit.highlight?.body?.[0],
    hit.highlight?.body_text?.[0],
    hit.highlight?.body_sayt?.[0],
    hit.body_highlight,
    hit.snippet,
    hit.preview,
    hit.body_preview,
    hit.body ? hit.body.slice(0, 140) : null,
  ]
    .filter(Boolean)
    .map((t) => squish(stripHtml(String(t))));

  const candidate = candidates.find((t) => t.length > 0);
  return candidate || "[No subject]";
}

/**
 * Map a raw Elasticsearch hit to a consistent, UI-friendly shape
 *
 * Handles all the field variations we've seen in production:
 * - subject vs subject_highlight
 * - from vs from_email vs from_addr vs sender
 * - date vs sent_at vs received_at
 * - id vs gmail_id vs _id
 */
export function mapHit(hit: RawHit) {
  // Unwrap _source if present (native ES shape)
  const source = hit._source ?? hit;

  // Track if subject was originally missing (for test hooks)
  const hadSubject = !!(source.subject_highlight ?? source.subject ?? "").trim();
  const subject = deriveSubject(source);

  return {
    id: String(source.id ?? source.gmail_id ?? source._id ?? ""),
    subject,
    snippet: source.snippet ?? source.preview ?? source.body_preview ?? "",
    from: source.from_email ?? source.from_addr ?? source.sender ?? source.from ?? "",
    date: source.received_at ?? source.sent_at ?? source.date ?? null,
    score: source.score ?? undefined,
    replied: source.replied ?? false,
    time_to_response_hours: source.time_to_response_hours ?? null,
    first_user_reply_at: source.first_user_reply_at ?? null,
    labels: source.label_heuristics ?? source.labels ?? (source.label ? [source.label] : []),
    category: source.category ?? null,
    expires_at: source.expires_at ?? null,
    event_start_at: source.event_start_at ?? null,
    risk_score: source.risk_score ?? null,
    quarantined: source.quarantined ?? false,
    derived: !hadSubject, // <-- for tests to detect derived subjects
    _raw: hit,
  };
}

/**
 * Type for the mapped hit result
 */
export type MappedHit = ReturnType<typeof mapHit>;
