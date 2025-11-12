export type DevDiagPreset = "chat" | "embed" | "app" | "full";

export async function runDevDiag(url: string, preset: DevDiagPreset = "app", suppress?: string[]) {
  const res = await fetch("/api/ops/diag", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ url, preset, suppress, tenant: "applylens" })
  });
  const text = await res.text();
  if (!res.ok) throw new Error(`DevDiag failed (${res.status}): ${text}`);
  return JSON.parse(text) as { ok: boolean; url: string; preset: DevDiagPreset; result: any };
}

export async function devdiagHealth(): Promise<boolean> {
  try {
    const r = await fetch("/api/ops/diag/health");
    return r.ok;
  } catch {
    return false;
  }
}
