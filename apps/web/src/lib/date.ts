/**
 * Safely format a date string, avoiding invalid dates or epoch-0 (1969/1970)
 */
export function safeFormatDate(
  iso?: string | null,
  fmt: Intl.DateTimeFormat = new Intl.DateTimeFormat(undefined, {
    year: "numeric",
    month: "short",
    day: "2-digit",
    hour: "numeric",
    minute: "2-digit"
  })
): string | null {
  if (!iso) return null;
  
  const d = new Date(iso);
  
  // Check for invalid date or epoch-0 (avoid showing 1969/1970)
  if (Number.isNaN(d.getTime()) || d.getTime() === 0) return null;
  
  return fmt.format(d);
}

/**
 * Format a date as relative time (e.g., "2 hours ago", "3 days ago")
 */
export function relativeTime(iso?: string | null): string | null {
  if (!iso) return null;
  
  const d = new Date(iso);
  if (Number.isNaN(d.getTime()) || d.getTime() === 0) return null;
  
  const now = Date.now();
  const diffMs = now - d.getTime();
  const diffSec = Math.floor(diffMs / 1000);
  const diffMin = Math.floor(diffSec / 60);
  const diffHour = Math.floor(diffMin / 60);
  const diffDay = Math.floor(diffHour / 24);
  
  if (diffSec < 60) return "just now";
  if (diffMin < 60) return `${diffMin}m ago`;
  if (diffHour < 24) return `${diffHour}h ago`;
  if (diffDay < 7) return `${diffDay}d ago`;
  if (diffDay < 30) return `${Math.floor(diffDay / 7)}w ago`;
  if (diffDay < 365) return `${Math.floor(diffDay / 30)}mo ago`;
  return `${Math.floor(diffDay / 365)}y ago`;
}
