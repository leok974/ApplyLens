import { Button } from "@/components/ui/button";
import { Archive, ShieldCheck, ShieldAlert, X } from "lucide-react";

export function BulkBar({
  count,
  onClear,
  onArchive,
  onSafe,
  onSus,
}: {
  count: number;
  onClear: () => void;
  onArchive: () => void;
  onSafe: () => void;
  onSus: () => void;
}) {
  if (count <= 0) return null;
  return (
    <div className="sticky top-[64px] z-30 flex items-center gap-2 border-b border-[color:hsl(var(--color-border))] bg-[color:hsl(var(--color-muted))]/60 px-3 py-2 backdrop-blur">
      <div className="text-sm">
        <span className="font-medium">{count}</span> selected
      </div>
      <Button variant="outline" size="sm" onClick={onArchive}><Archive className="mr-1 h-4 w-4" />Archive</Button>
      <Button variant="outline" size="sm" onClick={onSafe}><ShieldCheck className="mr-1 h-4 w-4" />Mark safe</Button>
      <Button variant="outline" size="sm" onClick={onSus}><ShieldAlert className="mr-1 h-4 w-4" />Mark suspicious</Button>
      <div className="ml-auto" />
      <Button variant="ghost" size="sm" onClick={onClear}><X className="mr-1 h-4 w-4" />Clear</Button>
    </div>
  );
}
