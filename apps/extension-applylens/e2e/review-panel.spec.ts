// e2e/review-panel.spec.ts
import { test, expect } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

const ROOT = path.resolve(__dirname, "..");
const CONTENT_JS = path.join(ROOT, "content.js");

// Minimal helper to load content.js into the page but replace the import line.
// We stub APPLYLENS_API_BASE to anything; the test will route() and mock the API.
function loadContentPatched(): string {
  const raw = fs.readFileSync(CONTENT_JS, "utf8");
  // Replace `import { APPLYLENS_API_BASE } from "./config.js";` with const stub
  let patched = raw.replace(
    /import\s*\{\s*APPLYLENS_API_BASE\s*\}\s*from\s*["']\.\/config\.js["'];?/,
    'const APPLYLENS_API_BASE = "http://127.0.0.1:8003";'
  );

  // Wrap in IIFE to ensure it executes and exposes globals immediately
  patched = `(function() {\n${patched}\n})();`;

  return patched;
}

test.describe("Review panel - Fill all populates fields", () => {
  test("mounts panel and fills form", async ({ page }) => {
    // 1) Mock the answers API that content.js will call
    await page.route("**/api/extension/generate-form-answers", async (route) => {
      const req = route.request();
      const body = req.postDataJSON() as any;
      const fields = (body?.fields ?? []) as Array<{ field_id: string; label?: string; selector?: string }>;

      // Simple generator: email-like fields get an email, others get "John Doe…" style text.
      const answers = fields.map((f) => {
        const label = (f.label || "").toLowerCase();
        const fid = f.field_id || "";
        const isEmail = label.includes("email") || fid.toLowerCase().includes("email");
        const isUrl = label.includes("website") || fid.toLowerCase().includes("website") || label.includes("portfolio");
        const value = isEmail
          ? "tester@example.com"
          : isUrl
          ? "https://example.com"
          : "John Doe – motivated engineer with strong interest in agents.";
        return { field_id: fid, answer: value };
      });

      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ job: body?.job ?? {}, answers }),
      });
    });

    // 2) Go to the demo page served by the webServer
    await page.goto("http://127.0.0.1:5177/demo-form.html");

    // Sanity: ensure the demo inputs exist
    const fullName = page.locator('#full_name');
    const email = page.locator('#email');
    await expect(fullName).toBeVisible();
    await expect(email).toBeVisible();

    // 3) Stub chrome API before injecting content.js
    await page.evaluate(() => {
      (window as any).chrome = {
        runtime: {
          sendMessage: () => Promise.resolve({ ok: true }),
          onMessage: { addListener: () => {} }
        }
      };
    });

    // 4) Inject content.js (patched and wrapped in IIFE)
    const patched = loadContentPatched();
    await page.addScriptTag({ content: patched });

    // Wait a moment for the script to fully execute
    await page.waitForTimeout(100);

    // 5) Call the exported helper to open the panel
    await page.evaluate(() => (window as any).__APPLYLENS__.runScanAndSuggest());

    // 6) Expect the review panel to appear
    const panel = page.locator("#__applylens_panel__");
    await expect(panel).toBeVisible({ timeout: 10000 });

    // 7) Click "Fill all"
    const fillAll = panel.locator("#al_fill_all");
    await fillAll.click();

    // 8) Assert values were populated
    //   We expect our mocked answers to be used (email gets tester@example.com, others get a generic text)
    await expect(email).toHaveValue(/tester@example\.com/i);
    // Name/other text fields receive our default summary text
    await expect(fullName).not.toHaveValue("");

    // optional: take a screenshot for debugging
    // await page.screenshot({ path: "panel-after-fill.png", fullPage: true });
  });
});
