import { useEffect, useState } from "react";
import { fetchTracker, TrackerApplication } from "../lib/api";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { NavTabs } from "../components/NavTabs";
import { HeaderSettingsDropdown } from "../components/HeaderSettingsDropdown";

// Consistent stage badge variant mapping for visual polish
function getStageVariant(stage?: string): "default" | "secondary" | "destructive" | "outline" {
  if (!stage) return "outline";

  const s = stage.toLowerCase();
  if (s === "offer") return "default"; // Will style as green with custom class
  if (s === "interview") return "secondary";
  if (s === "rejected") return "destructive";

  // applied, submitted, ghosted, etc.
  return "outline";
}

// Check if stage should get green styling (offer = win)
function isOfferStage(stage?: string): boolean {
  return stage?.toLowerCase() === "offer";
}

export default function TrackerPage() {
  const [applications, setApplications] = useState<TrackerApplication[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchTracker()
      .then((data) => setApplications(data.applications || []))
      .catch(() => setApplications([]))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="p-4 md:p-6 max-w-[1600px] mx-auto">
      <header className="mb-6 flex items-start justify-between px-4 pt-4 pb-2 border-b border-border/50 bg-background/60 backdrop-blur-xl rounded-t-lg">
        <div className="flex flex-col gap-2">
          <NavTabs />
          <p className="text-[11px] text-muted-foreground">
            Review offers, track pipeline, mute junk.
          </p>
        </div>
        <HeaderSettingsDropdown />
      </header>

      <div className="px-4">{loading ? (
        <div className="text-sm text-muted-foreground">Loading applications...</div>
      ) : applications.length === 0 ? (
        <Card className="p-8 bg-card/50 border-border/50 text-center">
          <div className="text-muted-foreground">
            <p className="text-sm mb-2">No tracked applications yet.</p>
            <p className="text-xs">
              As you get outreach from recruiters and engage with them, we'll
              automatically track your applications here.
            </p>
          </div>
        </Card>
      ) : (
        <div className="space-y-3">
          {applications.map((app) => (
            <Card
              key={app.id}
              className="p-4 bg-card/50 border-border/50 hover:bg-card/70 transition-colors"
            >
              <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-white font-semibold">
                      {app.company}
                    </span>
                    <Badge 
                      variant={getStageVariant(app.stage)}
                      className={isOfferStage(app.stage) ? "bg-green-600/20 text-green-200 border-green-700" : ""}
                    >
                      {app.stage || "unknown"}
                    </Badge>
                  </div>
                  <div className="text-sm text-muted-foreground mt-1">
                    {app.role}
                  </div>
                  <div className="flex items-center gap-3 mt-2 text-xs text-muted-foreground">
                    {app.source && (
                      <span className="text-[11px] text-muted-foreground/80">
                        via {app.source}
                      </span>
                    )}
                    {app.last_activity_at && (
                      <span className="text-[11px] text-muted-foreground/60">
                        Last activity{" "}
                        {new Date(app.last_activity_at).toLocaleString()}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
      </div>
    </div>
  );
}
