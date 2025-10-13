import * as React from "react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { getPolicies, savePolicies } from "@/lib/securityApi";
import { SecurityPolicies } from "@/types/security";
import { toast } from "sonner";

export function PolicyPanel() {
  const [pol, setPol] = React.useState<SecurityPolicies | null>(null);
  const [saving, setSaving] = React.useState(false);

  React.useEffect(() => {
    getPolicies().then(setPol).catch(() => setPol({
      autoQuarantineHighRisk: true,
      autoArchiveExpiredPromos: true,
      autoUnsubscribeInactive: { enabled: false, threshold: 10 },
    }));
  }, []);

  function update<K extends keyof SecurityPolicies>(k: K, v: SecurityPolicies[K]) {
    setPol((p) => (p ? { ...p, [k]: v } : p));
  }

  async function onSave() {
    if (!pol) return;
    try {
      setSaving(true);
      await savePolicies(pol);
      toast.success("Security policies saved");
    } catch (e: any) {
      toast.error(`Save failed: ${e?.message ?? e}`);
    } finally {
      setSaving(false);
    }
  }

  if (!pol) {
    return <Card><CardContent className="py-6 text-sm text-muted-foreground">Loading policies…</CardContent></Card>;
  }

  return (
    <Card data-testid="policy-panel">
      <CardHeader>
        <CardTitle>Security Policies</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center justify-between">
          <Label htmlFor="autoQ">Auto-quarantine high-risk (score ≥ 70)</Label>
          <Switch id="autoQ" checked={pol.autoQuarantineHighRisk}
                  onCheckedChange={(v)=>update("autoQuarantineHighRisk", v)} />
        </div>

        <div className="flex items-center justify-between">
          <Label htmlFor="autoArchive">Auto-archive expired promos (≥30d)</Label>
          <Switch id="autoArchive" checked={pol.autoArchiveExpiredPromos}
                  onCheckedChange={(v)=>update("autoArchiveExpiredPromos", v)} />
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 items-center">
          <div className="sm:col-span-2">
            <Label htmlFor="autoUnsub">Auto-unsubscribe high-volume senders I never open</Label>
            <div className="mt-2 flex items-center gap-2">
              <Switch id="autoUnsub" checked={pol.autoUnsubscribeInactive.enabled}
                      onCheckedChange={(v)=>update("autoUnsubscribeInactive", { ...pol.autoUnsubscribeInactive, enabled: v })}/>
              <span className="text-sm text-muted-foreground">Threshold (N in 60 days)</span>
              <Input
                className="w-24"
                type="number"
                min={1}
                value={pol.autoUnsubscribeInactive.threshold}
                onChange={(e)=>update("autoUnsubscribeInactive", { ...pol.autoUnsubscribeInactive, threshold: Number(e.target.value || 1) })}
              />
            </div>
          </div>
        </div>

        <div className="pt-1">
          <Button onClick={onSave} disabled={saving} data-testid="policy-save">Save</Button>
        </div>
      </CardContent>
    </Card>
  );
}
