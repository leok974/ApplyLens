import { EmailRow } from "./EmailRow";
import { Skeleton } from "@/components/ui/skeleton";
import { bucketFor, bucketLabel, BucketKey } from "@/lib/dateBuckets";

type Item = {
  id: string;
  subject: string;
  sender: string;
  preview: string;
  receivedAtISO: string; // ISO string
  reason?: string;
  risk?: "low"|"med"|"high";
};

function groupByBucket(items: Item[]) {
  const map = new Map<BucketKey, Item[]>();
  items.forEach((it) => {
    const b = bucketFor(new Date(it.receivedAtISO));
    map.set(b, [...(map.get(b) ?? []), it]);
  });
  const order: BucketKey[] = ["today", "week", "month", "older"];
  return order.filter((k) => map.get(k)?.length).map((k) => ({ key: k, items: map.get(k)! }));
}

export function EmailList({
  items,
  loading,
  selected,
  onToggleSelect,
  activeId,
  onSetActive,
  onOpen,
  onArchive,
  onSafe,
  onSus,
  onExplain,
  density = "comfortable",
}: {
  items: Item[];
  loading?: boolean;
  selected: Set<string>;
  onToggleSelect: (id: string, value?: boolean) => void;
  activeId?: string;
  onSetActive?: (id: string) => void;
  onOpen?: (id: string) => void;
  onArchive?: (id: string) => void;
  onSafe?: (id: string) => void;
  onSus?: (id: string) => void;
  onExplain?: (id: string) => void;
  density?: "compact"|"comfortable";
}) {
  if (loading) {
    return (
      <div className="container-readable space-y-3 py-4">
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className="surface-card density-x density-y">
            <div className="flex items-center gap-3">
              <Skeleton className="h-8 w-8 rounded-full" />
              <Skeleton className="h-3 w-40" />
            </div>
            <Skeleton className="mt-3 h-3 w-3/4" />
            <Skeleton className="mt-2 h-3 w-2/3" />
          </div>
        ))}
      </div>
    );
  }

  if (!items?.length) {
    return (
      <div className="container-readable flex h-[60vh] items-center justify-center">
        <div className="text-center">
          <div className="text-lg font-semibold text-[color:hsl(var(--foreground))]">No emails yet</div>
          <div className="mt-1 text-sm text-[color:hsl(var(--muted-foreground))]">Try adjusting filters or syncing Gmail.</div>
        </div>
      </div>
    );
  }

  const groups = groupByBucket(items);

  return (
    <div className="container-readable py-4">
      {groups.map((g) => (
        <section key={g.key} className="mb-6">
          <div className="sticky top-[106px] z-10 mb-3">
            <div className="inline-flex items-center gap-2 rounded-full border border-[color:hsl(var(--border))] bg-[color:hsl(var(--card))] px-3 py-1 text-xs font-semibold text-[color:hsl(var(--muted-foreground))] shadow-sm">
              <span className="h-1.5 w-1.5 rounded-full bg-[color:hsl(var(--ring))]" />
              {bucketLabel(g.key)}
            </div>
          </div>
          <div className="space-y-3">{g.items.map((m) => (
              <EmailRow
                key={m.id}
                id={m.id}
                active={activeId === m.id}
                checked={selected.has(m.id)}
                onCheckChange={(v) => onToggleSelect(m.id, v)}
                onOpen={() => onOpen?.(m.id)}
                subject={m.subject}
                sender={m.sender}
                preview={m.preview}
                receivedAt={new Date(m.receivedAtISO).toLocaleString()}
                reason={m.reason}
                risk={m.risk}
                density={density}
                onArchive={() => onArchive?.(m.id)}
                onSafe={() => onSafe?.(m.id)}
                onSus={() => onSus?.(m.id)}
                onExplain={() => onExplain?.(m.id)}
              />
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}
