// apps/web/src/lib/version.ts
export type VersionInfo = {
  app?: string;
  version?: string;
  sha?: string;
  built_at?: string;
};

export async function fetchVersionInfo(
  signal?: AbortSignal
): Promise<VersionInfo | null> {
  try {
    const res = await fetch("/api/version", {
      method: "GET",
      headers: { "Accept": "application/json" },
      signal,
    });

    if (!res.ok) {
      // 404 / 5xx → just treat as "no version info"
      return null;
    }

    return (await res.json()) as VersionInfo;
  } catch {
    // Network errors → no version info, but don't crash UI
    return null;
  }
}
