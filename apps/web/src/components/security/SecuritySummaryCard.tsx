import * as React from "react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { getSecurityStats } from "@/lib/securityApi";
import { ShieldAlert, ShieldX } from "lucide-react";

type Stats = {
  highRiskCount: number;
  quarantinedCount: number;
  averageRiskScore?: number;
};

export function SecuritySummaryCard() {
  const [stats, setStats] = React.useState<Stats>({
    highRiskCount: 0,
    quarantinedCount: 0,
  });
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    getSecurityStats()
      .then((data: any) => {
        setStats({
          highRiskCount: data.high_risk_count ?? 0,
          quarantinedCount: data.total_quarantined ?? 0,
          averageRiskScore: data.average_risk_score,
        });
      })
      .catch(() => {
        // Silently fail - card will show zeros
      })
      .finally(() => {
        setLoading(false);
      });
  }, []);

  return (
    <Card data-testid="security-summary" className="border-border/60">
      <CardHeader className="pb-3">
        <CardTitle className="text-base flex items-center gap-2">
          <ShieldAlert className="h-4 w-4" />
          Security Overview
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <div className="flex items-baseline gap-1">
              <div className="text-3xl font-bold tabular-nums text-amber-500">
                {loading ? "..." : stats.highRiskCount}
              </div>
              <ShieldAlert className="h-4 w-4 text-amber-500/60" />
            </div>
            <div className="mt-1 text-xs text-muted-foreground">
              High-risk emails
            </div>
          </div>

          <div>
            <div className="flex items-baseline gap-1">
              <div className="text-3xl font-bold tabular-nums text-red-500">
                {loading ? "..." : stats.quarantinedCount}
              </div>
              <ShieldX className="h-4 w-4 text-red-500/60" />
            </div>
            <div className="mt-1 text-xs text-muted-foreground">
              Quarantined
            </div>
          </div>
        </div>

        {stats.averageRiskScore !== undefined && (
          <div className="mt-4 pt-3 border-t border-border/60">
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Avg. risk score</span>
              <span className="font-semibold tabular-nums">
                {stats.averageRiskScore.toFixed(1)}
              </span>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
