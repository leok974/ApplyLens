// Centralized scoring constants for demo + debug UIs.
export const LABEL_WEIGHTS: Record<string, number> = {
  offer: 4.0,
  interview: 3.0,
  rejection: 0.5,
};

export const RECENCY_HINT = "Recency: 7-day decay (gauss scale=7d, decay=0.5)";

/** Returns a copy of labels sorted by impact: offer > interview > others > rejection */
export function sortLabelsByImpact(labels: string[] = []): string[] {
  const weight = (l: string) =>
    l in LABEL_WEIGHTS ? LABEL_WEIGHTS[l] : 1.0; // "others" = 1.0
  return [...labels].sort((a, b) => weight(b) - weight(a));
}

/** Optional: human title for a label */
export function labelTitle(label: string): string {
  switch (label) {
    case "offer":
      return "Offer";
    case "interview":
      return "Interview";
    case "rejection":
      return "Rejection";
    default:
      return label.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  }
}
