// Sticky UI state for /search (labels, dates, replied, sort)
export type RepliedFilter = "all" | "true" | "false";
export type UiState = {
  labels: string[];
  date_from?: string;
  date_to?: string;
  replied: RepliedFilter;
  sort: "relevance" | "received_desc" | "received_asc" | "ttr_asc" | "ttr_desc";
};

const KEY = "search.ui";
const DEFAULT: UiState = {
  labels: [],
  replied: "all",
  sort: "relevance",
};

export function loadUiState(): UiState {
  if (typeof window === "undefined") return DEFAULT;
  try {
    const raw = window.localStorage.getItem(KEY);
    if (!raw) return DEFAULT;
    const parsed = JSON.parse(raw);
    return { ...DEFAULT, ...parsed };
  } catch {
    return DEFAULT;
  }
}

export function saveUiState(state: UiState) {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(KEY, JSON.stringify(state));
  } catch {}
}
