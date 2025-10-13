import { Page, test } from "@playwright/test";

export function guardConsole(page: Page) {
  const badLevels = new Set(["error", "warning"]);
  const ignore = [
    // keep allowlist tight; add lines here for noisy libs if truly harmless
    /React Router Future Flag Warning/, // can remove once you flip v7 flags
    /Failed to load resource.*404/i, // 404s - APIs are stubbed, assets not shipped in preview
    /The above error occurred in/, // React error boundary messages (we'll see the real error)
    /Consider adding an error boundary/, // React error boundary advice
    /Visit https:\/\/reactjs.org/, // React docs links
  ];

  page.on("console", msg => {
    const type = msg.type();
    if (!badLevels.has(type)) return;
    const text = msg.text();
    if (ignore.some(r => r.test(text))) return;
    test.info().attach("console", { body: `[${type}] ${text}` });
    throw new Error(`Console ${type}: ${text}`);
  });
}
