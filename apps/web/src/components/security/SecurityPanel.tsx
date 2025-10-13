import * as React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { RiskBadge } from "./RiskBadge";
import { EvidenceModal } from "./EvidenceModal";
import { rescanEmail } from "@/lib/securityApi";
import { RiskFlag } from "@/types/security";
import { RotateCw } from "lucide-react";
import { toast } from "sonner";

type Props = {
  emailId: string;
  riskScore: number;
  quarantined?: boolean;
  flags?: RiskFlag[];
  onRefresh?: () => void; // parent can fetch latest email
};

export function SecurityPanel({ emailId, riskScore, quarantined, flags, onRefresh }: Props) {
  const [busy, setBusy] = React.useState(false);

  async function handleRescan() {
    try {
      setBusy(true);
      await rescanEmail(emailId);
      toast.success("Email rescanned");
      onRefresh?.();
    } catch (e: any) {
      toast.error(`Rescan failed: ${e?.message ?? e}`);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card data-testid="security-panel" className="border-border/60">
      <CardHeader className="flex-row items-center justify-between py-3">
        <CardTitle className="text-base">Security</CardTitle>
        <div className="flex items-center gap-2">
          <RiskBadge score={riskScore ?? 0} quarantined={quarantined} />
          <Button
            data-testid="rescan-btn"
            variant="outline"
            size="sm"
            onClick={handleRescan}
            disabled={busy}
            className="gap-1.5"
          >
            <RotateCw className={`h-4 w-4 ${busy ? "animate-spin" : ""}`} />
            Rescan
          </Button>
        </div>
      </CardHeader>
      <Separator />
      <CardContent className="py-3">
        <div className="flex flex-wrap items-center gap-2">
          <EvidenceModal flags={flags ?? []} />
          {quarantined ? (
            <span className="rounded-md bg-red-500/15 text-red-300 border border-red-600/30 px-2 py-1 text-xs">
              Quarantined: hidden from Inbox
            </span>
          ) : (
            <span className="rounded-md bg-emerald-500/10 text-emerald-300 border border-emerald-600/30 px-2 py-1 text-xs">
              Not quarantined
            </span>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
