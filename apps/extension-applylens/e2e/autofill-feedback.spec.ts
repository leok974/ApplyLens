import { test, expect } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

const ROOT = path.resolve(__dirname, "..");
const CONTENT_JS = path.join(ROOT, "content.js");

/**
 * Load content.js and stub imports for testing
 */
function loadContentPatched(): string {
  let raw = fs.readFileSync(CONTENT_JS, "utf8");

  // Replace APPLYLENS_API_BASE import
  raw = raw.replace(
    /import\s*\{\s*APPLYLENS_API_BASE\s*\}\s*from\s*["']\.\/config\.js["'];?/,
    'const APPLYLENS_API_BASE = "http://127.0.0.1:8003";'
  );

  // Replace learning module imports
  raw = raw.replace(
    /import\s*\{[^}]+\}\s*from\s*["']\.\/learning\/formMemory\.js["'];?/,
    `const loadFormMemory = async () => ({ selectorMap: {} });
const saveFormMemory = async () => {};`
  );

  raw = raw.replace(
    /import\s*\{[^}]+\}\s*from\s*["']\.\/learning\/client\.js["'];?/,
    `let queuedEvents = [];
const queueLearningEvent = (event) => queuedEvents.push(event);
const flushLearningEvents = async () => { queuedEvents = []; };`
  );

  raw = raw.replace(
    /import\s*\{[^}]+\}\s*from\s*["']\.\/learning\/utils\.js["'];?/,
    `const computeSchemaHash = (fields) => "demo_schema_hash";
const editDistance = (a, b) => Math.abs(a.length - b.length);`
  );

  raw = raw.replace(
    /import\s*\{[^}]+\}\s*from\s*["']\.\/learning\.profileClient\.js["'];?/,
    `const fetchLearningProfile = async (host, schemaHash) => {
  const res = await fetch(\`/api/extension/learning/profile?host=\${host}&schema_hash=\${schemaHash}\`);
  if (!res.ok) return null;
  return res.json();
};`
  );

  raw = raw.replace(
    /import\s*\{[^}]+\}\s*from\s*["']\.\/learning\.mergeMaps\.js["'];?/,
    `const mergeSelectorMaps = (serverMap, localMap) => ({ ...serverMap, ...localMap });`
  );

  // Replace guardrails import
  raw = raw.replace(
    /import\s*\{[^}]+\}\s*from\s*["']\.\/guardrails\.js["'];?/,
    `const sanitizeGeneratedContent = (text) => {
  if (!text) return text;
  let sanitized = text;
  sanitized = sanitized.replace(/https?:\\/\\/[^\\s]+/gi, '');
  sanitized = sanitized.replace(/I worked at\\s+/gi, '');
  sanitized = sanitized.replace(/\\s+/g, ' ').trim();
  return sanitized;
};`
  );

  return raw;
}

test.describe("@companion @feedback", () => {
  test("user can send thumbs up/down feedback after autofill", async ({ page }) => {
    // Enable console logging
    page.on('console', msg => {
      const text = msg.text();
      if (text.includes('[CONTENT]') || text.includes('[Learning]') || text.includes('[TEST]') || text.includes('[Feedback]')) {
        console.log(text);
      }
    });

    // 1) Stub generate answers to keep this focused on feedback
    await page.route("**/api/extension/generate-form-answers", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          answers: [
            { field_id: "full_name", answer: "Autofilled summary for feedback test." }
          ],
        }),
      });
    });

    // Stub profile endpoint
    await page.route("**/api/extension/learning/profile**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          host: "localhost",
          schema_hash: "demo_schema_hash",
          canonical_map: {},
          style_hint: null,
        }),
      });
    });

    // 2) Capture feedback POST
    let feedbackPayload: any = null;
    await page.route("**/api/extension/feedback/autofill", async (route) => {
      const req = route.request();
      feedbackPayload = await req.postDataJSON();
      console.log("[TEST] Feedback payload received:", feedbackPayload);
      await route.fulfill({ status: 204, body: "" });
    });

    await page.goto("http://127.0.0.1:5177/demo-form.html");
    await page.waitForLoadState("networkidle");

    // Stub chrome API
    await page.evaluate(() => {
      (window as any).chrome = {
        runtime: {
          onMessage: { addListener: () => {} },
          sendMessage: async () => ({ ok: true })
        },
        storage: {
          sync: {
            get: async () => ({ learningEnabled: true })
          }
        }
      };
    });

    // Inject content script
    const contentScript = loadContentPatched();
    await page.addScriptTag({ content: contentScript });

    // Wait for extension global
    await page.waitForFunction(() => (window as any).__APPLYLENS__ !== undefined, { timeout: 5000 });

    // Trigger scan and suggest
    await page.evaluate(() => {
      (window as any).__APPLYLENS__.runScanAndSuggest();
    });

    const panel = page.locator('[data-testid="al-panel"]');
    await expect(panel).toBeVisible();

    // Wait for at least one answer row and fill all
    await expect(panel.locator('[data-testid="al-answer-row"]')).toHaveCount(4); // demo-form.html has 4 fields
    await page.getByRole("button", { name: /fill all/i }).click();

    // 3) Click thumbs up feedback
    const thumbsUp = panel.locator('[data-testid="al-feedback-up"]');
    const thumbsDown = panel.locator('[data-testid="al-feedback-down"]');

    await expect(thumbsUp).toBeVisible();
    await expect(thumbsDown).toBeVisible();

    console.log("[TEST] Clicking thumbs up button...");
    await thumbsUp.click();

    // Wait for feedback to be sent
    await page.waitForTimeout(500);

    // 4) UI should reflect selection (e.g., aria-pressed or class)
    await expect(thumbsUp).toHaveAttribute("aria-pressed", "true");
    await expect(thumbsDown).toHaveAttribute("aria-pressed", "false");

    // 5) Feedback call should have been sent with status=helpful
    expect(feedbackPayload).not.toBeNull();
    expect(feedbackPayload.status).toBe("helpful");
    // Optional: verify host/schema_hash are included
    expect(feedbackPayload.host).toBeDefined();
    expect(feedbackPayload.schema_hash).toBeDefined();

    console.log("[TEST] ✅ Feedback test passed");
  });
});
