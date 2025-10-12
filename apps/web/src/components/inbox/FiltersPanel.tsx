import * as React from "react";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";

export function FiltersPanel({
  q, setQ,
  onlyPromo, setOnlyPromo,
  onlyBills, setOnlyBills,
  onlySafe, setOnlySafe,
  onApply, onReset
}: {
  q: string; setQ: (v: string) => void;
  onlyPromo: boolean; setOnlyPromo: (v: boolean) => void;
  onlyBills: boolean; setOnlyBills: (v: boolean) => void;
  onlySafe: boolean; setOnlySafe: (v: boolean) => void;
  onApply: () => void; onReset: () => void;
}) {
  return (
    <div className="sticky top-[64px] h-[calc(100vh-64px)] w-72 shrink-0 border-r border-[color:hsl(var(--color-border))] bg-card p-4">
      <div className="text-sm font-semibold text-slate-700 dark:text-slate-200">Filters</div>

      <div className="mt-4 space-y-2">
        <Label className="text-xs text-slate-500 dark:text-slate-400">Search</Label>
        <Input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Query…"
          className="h-9"
        />
      </div>

      <Separator className="my-4" />

      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-sm text-slate-700 dark:text-slate-200">Promotions</span>
          <Switch checked={onlyPromo} onCheckedChange={setOnlyPromo} />
        </div>
        <div className="flex items-center justify-between">
          <span className="text-sm text-slate-700 dark:text-slate-200">Bills</span>
          <Switch checked={onlyBills} onCheckedChange={setOnlyBills} />
        </div>
        <div className="flex items-center justify-between">
          <span className="text-sm text-slate-700 dark:text-slate-200">Safe senders</span>
          <Switch checked={onlySafe} onCheckedChange={setOnlySafe} />
        </div>
      </div>

      <div className="mt-6 flex gap-2">
        <Button className="flex-1" onClick={onApply}>Apply</Button>
        <Button className="flex-1" variant="secondary" onClick={onReset}>Reset</Button>
      </div>
    </div>
  );
}
