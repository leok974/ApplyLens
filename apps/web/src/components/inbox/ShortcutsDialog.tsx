import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Kbd } from "@/components/ui/kbd";

export function ShortcutsDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (v: boolean) => void; }) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader><DialogTitle>Keyboard shortcuts</DialogTitle></DialogHeader>
        <div className="space-y-2 text-sm">
          <div className="flex items-center justify-between"><span>Next / Previous</span><span><Kbd>j</Kbd> / <Kbd>k</Kbd></span></div>
          <div className="flex items-center justify-between"><span>Select email</span><span><Kbd>x</Kbd></span></div>
          <div className="flex items-center justify-between"><span>Archive</span><span><Kbd>e</Kbd></span></div>
          <div className="flex items-center justify-between"><span>Explain why</span><span><Kbd>Enter</Kbd></span></div>
          <div className="flex items-center justify-between"><span>Help</span><span><Kbd>?</Kbd></span></div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
