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

test.describe("@companion @dm @ux", () => {
  test("user can accept/edit recruiter DM lines before inserting", async ({ page }) => {
    // Enable console logging
    page.on('console', msg => {
      const text = msg.text();
      if (text.includes('[CONTENT]') || text.includes('[Learning]') || text.includes('[TEST]')) {
        console.log(text);
      }
    });

    // 1) Mock DM generation endpoint
    await page.route("**/api/extension/generate-recruiter-dm", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          dm: [
            "Hi Alex, I came across your role at ExampleCorp.",
            "I worked at FakeCorp doing similar AI work.",
            "Would love to connect and learn more!",
          ],
        }),
      });
    });

    // Profile/learning endpoints can be no-op or stubbed
    await page.route("**/api/extension/learning/profile**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          host: "localhost",
          schema_hash: "dm-demo",
          canonical_map: {},
          style_hint: null,
        }),
      });
    });

    // 2) Go to demo DM page
    await page.goto("http://127.0.0.1:5177/demo-dm.html");
    await page.waitForLoadState("networkidle");

    // Stub chrome API
    await page.evaluate(() => {
      (window as any).chrome = {
        runtime: {
          onMessage: { addListener: () => {} },
          sendMessage: async () => ({ ok: true })
        }
      };
    });

    // Inject content script
    const contentScript = loadContentPatched();
    await page.addScriptTag({ content: contentScript });

    // Wait for extension global
    await page.waitForFunction(() => (window as any).__APPLYLENS__ !== undefined, { timeout: 5000 });

    // 3) Open Companion DM panel
    await page.getByRole("button", { name: /open recruiter dm/i }).click();

    const panel = page.locator('[data-testid="al-dm-panel"]');
    await expect(panel).toBeVisible();

    const rows = panel.locator('[data-testid="al-dm-row"]');
    await expect(rows).toHaveCount(3);

    const firstRow = rows.nth(0);
    const secondRow = rows.nth(1);
    const thirdRow = rows.nth(2);

    // Checkbox + textarea per row
    const firstCheckbox = firstRow.locator('[data-testid="al-dm-checkbox"]');
    const secondCheckbox = secondRow.locator('[data-testid="al-dm-checkbox"]');
    const thirdCheckbox = thirdRow.locator('[data-testid="al-dm-checkbox"]');

    const firstTextarea = firstRow.locator('[data-testid="al-dm-textarea"]');
    const secondTextarea = secondRow.locator('[data-testid="al-dm-textarea"]');
    const thirdTextarea = thirdRow.locator('[data-testid="al-dm-textarea"]');

    // 4) User behavior:
    // - Uncheck second line (the one that would mention FakeCorp - but it's sanitized!)
    // - Edit third line to add a more specific ask
    await secondCheckbox.uncheck();
    const editedThird = "Would love to connect this week for 15 minutes!";
    await thirdTextarea.fill(editedThird);

    // 5) Click "Insert DM"
    await page.getByRole("button", { name: /insert dm/i }).click();

    // 6) Assert message field only contains line 1 + edited line 3, joined with newlines
    const messageField = page.locator('textarea[name="recruiter_message"]');
    const value = await messageField.inputValue();

    console.log("[TEST] Message field value:", value);

    expect(value).toContain("Hi Alex, I came across your role at ExampleCorp.");
    expect(value).toContain(editedThird);

    // Excluded line should not appear (note: "I worked at" is already sanitized by guardrails)
    expect(value).not.toContain("FakeCorp doing similar AI work");

    console.log("[TEST] ✅ DM UX test passed");
  });
});
