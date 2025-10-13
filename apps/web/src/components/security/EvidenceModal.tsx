import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Info } from "lucide-react";
import { RiskFlag } from "@/types/security";

export function EvidenceModal({ flags }: { flags: RiskFlag[] }) {
  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button
          data-testid="evidence-open"
          variant="ghost"
          size="sm"
          className="gap-1 text-muted-foreground hover:text-foreground"
        >
          <Info className="h-4 w-4" />
          Why flagged?
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-xl">
        <DialogHeader>
          <DialogTitle>Why was this email flagged?</DialogTitle>
        </DialogHeader>
        <ScrollArea className="max-h-[60vh] pr-2">
          <ul className="space-y-2" data-testid="evidence-list">
            {flags?.length ? flags.map((f, i) => (
              <li key={`${f.signal}-${i}`} className="rounded-xl border border-border/60 p-3">
                <div className="flex items-center justify-between">
                  <span className="font-medium">{f.signal}</span>
                  <span className="text-xs text-muted-foreground">weight {f.weight >= 0 ? `+${f.weight}` : f.weight}</span>
                </div>
                <p className="mt-1 text-sm text-muted-foreground break-words">{f.evidence}</p>
              </li>
            )) : (
              <li className="text-sm text-muted-foreground">No evidence available.</li>
            )}
          </ul>
        </ScrollArea>
      </DialogContent>
    </Dialog>
  );
}
