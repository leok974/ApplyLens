import { useEffect, useState } from "react";
import {
  fetchExtApplications,
  fetchExtOutreach,
  pingProfile,
  ExtApplication,
  ExtOutreach,
} from "@/lib/extension";

export default function CompanionSettings() {
  const [apiOk, setApiOk] = useState<boolean | null>(null);
  const [apps, setApps] = useState<ExtApplication[] | null>(null);
  const [outs, setOuts] = useState<ExtOutreach[] | null>(null);
  const [err, setErr] = useState<string | null>(null);

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
    </div>
  );
}
