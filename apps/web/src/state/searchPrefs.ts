// Lightweight localStorage-backed search prefs
export type RecencyScale = "3d" | "7d" | "14d";
const KEY = "search.recencyScale";
const DEFAULT: RecencyScale = "7d";

export function getRecencyScale(): RecencyScale {
  const v = (typeof window !== "undefined" && window.localStorage.getItem(KEY)) || DEFAULT;
  return (["3d", "7d", "14d"].includes(v) ? (v as RecencyScale) : DEFAULT);
}

export function setRecencyScale(scale: RecencyScale) {
  if (typeof window !== "undefined") window.localStorage.setItem(KEY, scale);
}
