import { useEffect, useState } from "react";
import {
  fetchExtApplications,
  fetchExtOutreach,
  pingProfile,
  ExtApplication,
  ExtOutreach,
} from "@/lib/extension";
import { fetchStyleExplanation, StyleChoiceExplanation } from "@/api/companion";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { Info } from "lucide-react";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { useBanditToggle } from "@/lib/useBanditToggle";

/**
 * Phase 5.3: Debug panel for style choice transparency
 */
function StyleDebugPanel() {
  const [host, setHost] = useState("boards.greenhouse.io");
  const [schemaHash, setSchemaHash] = useState("");
  const [explanation, setExplanation] = useState<StyleChoiceExplanation | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFetch = async () => {
    if (!host || !schemaHash) {
      setError("Both host and schema hash are required");
      return;
    }

    setLoading(true);
    setError(null);
    setExplanation(null);

    try {
      const result = await fetchStyleExplanation({ host, schemaHash });
      setExplanation(result);
    } catch (e: any) {
      setError(e?.message ?? "Failed to fetch explanation");
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="rounded-2xl border p-5" data-testid="style-debug-panel">
      <h2 className="font-medium mb-3">Style Choice Explanation (Debug)</h2>
      <p className="text-sm text-muted-foreground mb-4">
        Phase 5.3: Shows why a particular autofill style was chosen for a form.
      </p>

      <div className="grid md:grid-cols-2 gap-4 mb-4">
        <div>
          <label className="block text-sm font-medium mb-1">Host</label>
          <input
            type="text"
            className="w-full px-3 py-2 border rounded"
            placeholder="e.g., boards.greenhouse.io"
            value={host}
            onChange={(e) => setHost(e.target.value)}
            data-testid="style-debug-host-input"
          />
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">Schema Hash</label>
          <input
            type="text"
            className="w-full px-3 py-2 border rounded"
            placeholder="e.g., abc123def456"
            value={schemaHash}
            onChange={(e) => setSchemaHash(e.target.value)}
            data-testid="style-debug-hash-input"
          />
        </div>
      </div>

      <button
        onClick={handleFetch}
        disabled={loading || !host || !schemaHash}
        className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
        data-testid="style-debug-fetch-btn"
      >
        {loading ? "Loading..." : "Fetch Explanation"}
      </button>

      {error && (
        <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded text-sm text-red-700" data-testid="style-debug-error">
          {error}
        </div>
      )}

      {explanation && (
        <div className="mt-4 space-y-4" data-testid="style-debug-result">
          <div className="grid md:grid-cols-2 gap-3 text-sm">
            <div>
              <span className="font-medium">Host Family:</span>{" "}
              <span className="font-mono">{explanation.host_family}</span>
            </div>
            <div>
              <span className="font-medium">Segment:</span>{" "}
              <span className="font-mono">{explanation.segment_key ?? "—"}</span>
            </div>
            <div>
              <span className="font-medium">Source:</span>{" "}
              <span className="font-mono" data-testid="style-debug-source">{explanation.source}</span>
            </div>
            <div>
              <span className="font-medium">Chosen Style:</span>{" "}
              <span className="font-mono" data-testid="style-debug-style-id">{explanation.chosen_style_id ?? "none"}</span>
            </div>
          </div>

          <div className="p-3 bg-blue-50 border border-blue-200 rounded text-sm">
            <p className="font-medium mb-1">Explanation:</p>
            <p className="whitespace-pre-wrap" data-testid="style-debug-text">{explanation.explanation}</p>
          </div>

          {explanation.considered_styles.length > 0 && (
            <div>
              <h3 className="font-medium mb-2 text-sm">Considered Styles:</h3>
              <div className="overflow-x-auto">
                <table className="w-full text-xs border" data-testid="style-debug-stats-table">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="text-left p-2 border-b">Style ID</th>
                      <th className="text-left p-2 border-b">Runs</th>
                      <th className="text-left p-2 border-b">Helpful</th>
                      <th className="text-left p-2 border-b">Ratio</th>
                      <th className="text-left p-2 border-b">Avg Edit Chars</th>
                      <th className="text-left p-2 border-b">Winner</th>
                    </tr>
                  </thead>
                  <tbody>
                    {explanation.considered_styles.map((style) => (
                      <tr
                        key={style.style_id}
                        className={style.is_winner ? "bg-green-50" : ""}
                        data-testid={`style-row-${style.style_id}`}
                      >
                        <td className="p-2 border-b font-mono">{style.style_id}</td>
                        <td className="p-2 border-b" data-testid={`style-runs-${style.style_id}`}>{style.total_runs}</td>
                        <td className="p-2 border-b">
                          {style.helpful_runs}/{style.total_runs}
                        </td>
                        <td className="p-2 border-b" data-testid={`style-ratio-${style.style_id}`}>
                          {(style.helpful_ratio * 100).toFixed(1)}%
                        </td>
                        <td className="p-2 border-b">
                          {style.avg_edit_chars?.toFixed(1) ?? "—"}
                        </td>
                        <td className="p-2 border-b">
                          {style.is_winner ? "✓" : ""}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}
    </section>
  );
}

export default function CompanionSettings() {
  const [apiOk, setApiOk] = useState<boolean | null>(null);
  const [apps, setApps] = useState<ExtApplication[] | null>(null);
  const [outs, setOuts] = useState<ExtOutreach[] | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const { enabled: experimentalStylesEnabled, setEnabled: setExperimentalStylesEnabled } =
    useBanditToggle();

  useEffect(() => {
    (async () => {
      try {
        setApiOk(await pingProfile());
        const [a, o] = await Promise.all([
          fetchExtApplications(10),
          fetchExtOutreach(10),
        ]);
        setApps(a);
        setOuts(o);
      } catch (e: any) {
        setErr(e?.message ?? "Failed to load");
      }
    })();
  }, []);

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-8">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold">Browser Companion</h1>
        <p className="text-sm text-muted-foreground">
          Install the ApplyLens Companion to autofill ATS forms and draft
          recruiter DMs.
        </p>
      </header>

      <section className="grid md:grid-cols-2 gap-6">
        <div className="rounded-2xl border p-5">
          <h2 className="font-medium mb-3">Install</h2>
          <ol className="list-decimal list-inside space-y-2 text-sm">
            <li>
              Open <span className="font-mono">chrome://extensions</span>
            </li>
            <li>
              Toggle <b>Developer mode</b>
            </li>
            <li>
              Click <b>Load unpacked</b> → select{" "}
              <span className="font-mono">apps/extension-applylens</span>
            </li>
            <li>
              Open a job page → click the extension → "Scan form &amp; suggest
              answers"
            </li>
          </ol>
          <div className="mt-3 text-sm">
            API connectivity:{" "}
            {apiOk === null ? (
              <span>…</span>
            ) : apiOk ? (
              <span className="text-green-600">OK</span>
            ) : (
              <span className="text-red-600">offline</span>
            )}
          </div>
        </div>

        <div className="rounded-2xl border p-5">
          <h2 className="font-medium mb-3">Tips</h2>
          <ul className="list-disc list-inside text-sm space-y-2">
            <li>Reload the page after reloading the extension</li>
            <li>For LinkedIn, use "Draft recruiter DM" then paste</li>
            <li>Check DevTools → Network if answers don't appear</li>
          </ul>
          {err && <p className="mt-3 text-sm text-red-600">Error: {err}</p>}
        </div>
      </section>

      <section className="rounded-2xl border p-5">
        <h2 className="font-medium mb-3">Recent Applications</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-muted-foreground">
              <tr>
                <th className="text-left py-2">When</th>
                <th className="text-left">Company</th>
                <th className="text-left">Role</th>
                <th className="text-left">Source</th>
              </tr>
            </thead>
            <tbody>
              {(apps ?? []).map((a) => (
                <tr key={a.id} className="border-t">
                  <td className="py-2">
                    {new Date(a.created_at).toLocaleString()}
                  </td>
                  <td>{a.company ?? "—"}</td>
                  <td>{a.role ?? "—"}</td>
                  <td>{a.source ?? "—"}</td>
                </tr>
              ))}
              {(apps ?? []).length === 0 && (
                <tr>
                  <td className="py-3 text-muted-foreground" colSpan={4}>
                    No applications yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section className="rounded-2xl border p-5">
        <h2 className="font-medium mb-3">Recent Outreach</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-muted-foreground">
              <tr>
                <th className="text-left py-2">When</th>
                <th className="text-left">Company</th>
                <th className="text-left">Role</th>
                <th className="text-left">Recruiter</th>
              </tr>
            </thead>
            <tbody>
              {(outs ?? []).map((o) => (
                <tr key={o.id} className="border-t">
                  <td className="py-2">
                    {new Date(o.created_at).toLocaleString()}
                  </td>
                  <td>{o.company ?? "—"}</td>
                  <td>{o.role ?? "—"}</td>
                  <td>{o.recruiter_name ?? "—"}</td>
                </tr>
              ))}
              {(outs ?? []).length === 0 && (
                <tr>
                  <td className="py-3 text-muted-foreground" colSpan={4}>
                    No outreach yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      {/* Phase 5.4/5.5: Autofill learning toggle */}
      <Card data-testid="companion-autofill-learning-card">
        <CardHeader>
          <div className="flex items-start justify-between gap-3">
            <div>
              <CardTitle>Autofill learning</CardTitle>
              <CardDescription>
                ApplyLens learns your preferred writing style over time and occasionally
                tries small variations to improve results.
              </CardDescription>
            </div>

            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <button
                    type="button"
                    className="inline-flex h-8 w-8 items-center justify-center rounded-full border border-border/40 text-muted-foreground hover:bg-muted/40"
                    aria-label="What does experimental styles mean?"
                    data-testid="companion-experimental-styles-tooltip-trigger"
                  >
                    <Info className="h-4 w-4" />
                  </button>
                </TooltipTrigger>
                <TooltipContent side="left" className="max-w-xs text-xs" data-testid="companion-experimental-styles-tooltip-content">
                  <p className="mb-1 font-medium">What this means</p>
                  <ul className="list-disc space-y-1 pl-4">
                    <li>Sometimes tries alternate phrasing or layout (~15% of the time).</li>
                    <li>You can turn this off at any time.</li>
                    <li>
                      Your data stays within ApplyLens and its configured AI providers.
                    </li>
                  </ul>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </div>
        </CardHeader>

        <CardContent className="flex items-center justify-between gap-4">
          <div className="space-y-1">
            <p className="text-sm font-medium">Allow experimental styles</p>
            <p className="text-xs text-muted-foreground">
              When enabled, ApplyLens occasionally explores new styles to find what works
              best for you. When disabled, it uses your current preferred style only.
            </p>
          </div>

          <Switch
            checked={experimentalStylesEnabled}
            onCheckedChange={(value: boolean) => setExperimentalStylesEnabled(value)}
            data-testid="companion-experimental-styles-toggle"
          />
        </CardContent>
      </Card>

      {/* Phase 5.3: Style choice transparency debug panel */}
      <StyleDebugPanel />
    </div>
  );
}
