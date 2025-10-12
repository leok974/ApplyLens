export type BucketKey = "today" | "week" | "month" | "older";

export function bucketFor(date: Date): BucketKey {
  const now = new Date();
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const diff = startOfToday.getTime() - new Date(date.getFullYear(), date.getMonth(), date.getDate()).getTime();
  const days = Math.floor(diff / (1000*60*60*24)) * -1; // negative if in future, we clamp below
  const delta = Math.max(0, Math.abs(days));
  if (delta <= 0) return "today";
  if (delta <= 7) return "week";
  if (delta <= 31) return "month";
  return "older";
}

export function bucketLabel(b: BucketKey) {
  switch (b) {
    case "today": return "Today";
    case "week": return "This week";
    case "month": return "This month";
    default: return "Older";
  }
}
