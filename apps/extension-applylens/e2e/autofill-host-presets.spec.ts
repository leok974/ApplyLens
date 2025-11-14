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
  const data = await res.json();
  // Phase 5.0: Transform style_hint including preferred_style_id to genStyleId
  const styleHint = data.style_hint ? {
    genStyleId: data.style_hint.preferred_style_id ?? data.style_hint.gen_style_id,
    confidence: data.style_hint.confidence,
  } : undefined;
  return {
    host: data.host,
    schemaHash: data.schema_hash,
    canonicalMap: data.canonical_map || {},
    styleHint,
  };
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
};
const applyGuardrails = (answers, fields) => {
  const sanitized = {};
  for (const key in answers) {
    sanitized[key] = sanitizeGeneratedContent(answers[key]);
  }
  return sanitized;
};`
  );

  return raw;
}

test.describe("@companion @hostpreset", () => {
  test("forwards style_hint from profile to generate-form-answers", async ({ page }) => {
    // 1) Stub profile endpoint with a style_hint
    let profileCalls = 0;

    await page.route("**/api/extension/learning/profile**", async (route) => {
      profileCalls += 1;
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          host: "example-ats.com",
          schema_hash: "schema-bullets",
          canonical_map: {},
          style_hint: {
            gen_style_id: "bullets_preset",
            confidence: 0.85,
          },
        }),
      });
    });

    // 2) Capture request body sent to generate-form-answers
    let lastBody: any = null;

    await page.route("**/api/extension/generate-form-answers", async (route) => {
      const req = route.request();
      lastBody = await req.postDataJSON();

      // Return mock answers for all 4 fields in demo-form.html
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          answers: [
            { field_id: "full_name", answer: "John Doe" },
            { field_id: "email", answer: "john@example.com" },
            { field_id: "phone", answer: "(555) 123-4567" },
            { field_id: "years_experience", answer: "5" },
          ],
        }),
      });
    });

    // 3) Go to the demo form page
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

    // Wait for __APPLYLENS__ to initialize
    await page.waitForFunction(() => (window as any).__APPLYLENS__ !== undefined, { timeout: 5000 });

    // 4) Trigger scan and suggest
    await page.evaluate(() => {
      (window as any).__APPLYLENS__.runScanAndSuggest();
    });

    // Wait for panel to appear
    const panel = page.locator('[data-testid="al-panel"]');
    await expect(panel).toBeVisible();

    // Wait for answer rows
    const rows = panel.locator('[data-testid="al-answer-row"]');
    await expect(rows).toHaveCount(4); // demo-form.html has 4 fields

    // Click Fill All
    await page.getByRole("button", { name: /fill all/i }).click();
    await page.waitForTimeout(500);

    // 5) Assertions: profile was called and style_hint is forwarded
    expect(profileCalls).toBeGreaterThan(0);
    expect(lastBody).not.toBeNull();
    // The payload should have styleHint with genStyleId and confidence
    expect(lastBody.style_hint).toMatchObject({
      genStyleId: "bullets_preset",
      confidence: 0.85,
    });
  });
});
