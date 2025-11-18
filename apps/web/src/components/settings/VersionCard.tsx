// apps/web/src/components/settings/VersionCard.tsx
import * as React from "react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge, badgeVariants } from "@/components/ui/badge";
import type { VariantProps } from "class-variance-authority";
import { fetchVersionInfo, type VersionInfo } from "@/lib/version";
import { BUILD_META } from "@/version";

type State = {
  loading: boolean;
  data: VersionInfo | null;
};

export function VersionCard() {
  const [state, setState] = React.useState<State>({
    loading: true,
    data: null,
  });

  React.useEffect(() => {
    const controller = new AbortController();

    fetchVersionInfo(controller.signal)
      .then((data) => {
        setState({ loading: false, data });
      })
      .catch(() => {
        setState({ loading: false, data: null });
      });

    return () => controller.abort();
  }, []);

  const data = state.data;

  const appName = data?.app ?? "applylens-api";
  const version = data?.version ?? BUILD_META.version ?? "unknown";
  const commit = data?.sha?.slice(0, 7) ?? BUILD_META.gitSha?.slice(0, 7) ?? "unknown";
  const env = BUILD_META.env ?? "unknown";
  const buildTime = data?.built_at ?? BUILD_META.builtAt ?? "unknown";

  return (
    <Card data-testid="version-card" className="h-full">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between gap-2">
          <CardTitle className="text-sm">Version</CardTitle>
          <Badge variant="outline" className="text-[11px] font-normal">
            {env}
          </Badge>
        </div>
        <p className="text-xs text-muted-foreground">
          Backend + build metadata for debugging and support.
        </p>
      </CardHeader>

      <CardContent className="space-y-1.5 text-xs text-muted-foreground">
        {state.loading ? (
          <p className="text-[11px] italic">Loading version info…</p>
        ) : (
          <>
            <Row label="Service">
              <code className="rounded bg-muted px-1.5 py-0.5 text-[11px]">
                {appName}
              </code>
            </Row>

            <Row label="Version">
              <code className="rounded bg-muted px-1.5 py-0.5 text-[11px]">
                {version}
              </code>
            </Row>

            <Row label="Commit">
              <code className="rounded bg-muted px-1.5 py-0.5 text-[11px]">
                {commit}
              </code>
            </Row>

            <Row label="Built at">
              <span className="truncate">{buildTime}</span>
            </Row>

            <Row label="Web version">
              <code className="rounded bg-muted px-1.5 py-0.5 text-[11px]">
                {BUILD_META.version}
              </code>
            </Row>

            <Row label="Web commit">
              <code className="rounded bg-muted px-1.5 py-0.5 text-[11px]">
                {BUILD_META.gitSha?.slice(0, 7) ?? "unknown"}
              </code>
            </Row>
          </>
        )}
      </CardContent>
    </Card>
  );
}

function Row(props: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <span className="text-[11px] font-medium text-muted-foreground/80">
        {props.label}
      </span>
      <div className="max-w-[60%] text-right">{props.children}</div>
    </div>
  );
}
