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

  // Replace learning module imports with inline implementations
  raw = raw.replace(
    /import\s*\{[^}]+\}\s*from\s*["']\.\/learning\/formMemory\.js["'];?/,
    `const loadFormMemory = async () => ({ selectorMap: {} });
const saveFormMemory = async () => {};`
  );

  raw = raw.replace(
    /import\s*\{[^}]+\}\s*from\s*["']\.\/learning\/client\.js["'];?/,
    `let queuedEvents = [];
const queueLearningEvent = (event) => {
  console.log('[CONTENT] Learning event queued:', event);
  queuedEvents.push(event);
};
const flushLearningEvents = async () => {
  console.log('[CONTENT] flushLearningEvents called, queued:', queuedEvents.length);
  if (queuedEvents.length === 0) return;
  const events = queuedEvents.slice();
  queuedEvents = [];
  const payload = { host: events[0].host, schema_hash: events[0].schemaHash, events };
  console.log('[CONTENT] Sending learning sync...', payload);
  await fetch('/api/extension/learning/sync', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  console.log('[CONTENT] Learning sync sent');
};`
  );

  raw = raw.replace(
    /import\s*\{[^}]+\}\s*from\s*["']\.\/learning\/utils\.js["'];?/,
    `const computeSchemaHash = (fields) => "demo_schema_hash";
const editDistance = (a, b) => Math.abs(a.length - b.length);`
  );

  // Replace new profile client imports
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

/**
 * This spec validates Phase 3.0:
 * - Per-field rows are rendered in the panel
 * - Unchecking a field prevents it from being filled
 * - Editing text in a row is what gets applied on Fill All
 *
 * Assumptions (adapt these to your implementation):
 * - There is a test page at /test/demo-form.html
 * - Content script injects an "Open ApplyLens" button
 *   with role=button and name matching /applylens/i
 * - The panel root has data-testid="al-panel"
 * - Each answer row has data-testid="al-answer-row"
 *   and data-selector="<css-selector-of-target-field>"
 * - Each row contains:
 *   - [data-testid="al-answer-checkbox"]
 *   - [data-testid="al-answer-textarea"]
 * - Fill All button is role=button, name /fill all/i
 */

test.describe("@companion @ux Panel UX - per-field accept/edit", () => {
  test("per-field accept/edit controls drive Fill All behavior", async ({ page }) => {
    // Enable console log capturing from the browser
    page.on('console', msg => {
      const text = msg.text();
      if (text.includes('[CONTENT]') || text.includes('[Learning]') || text.includes('[TEST]')) {
        console.log(text);
      }
    });

    // 1) Mock generate-form-answers so we get deterministic content
    await page.route("**/api/extension/generate-form-answers", async (route) => {
      const json = {
        answers: [
          { field_id: "full_name", answer: "E2E-FirstName" },
          { field_id: "cover_letter", answer: "E2E-Summary" },
        ],
      };
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(json)
      });
    });

    // Learning/profile endpoints can be stubbed or allowed to pass through;
    // here we just return an empty profile so heuristics/local map are used.
    await page.route("**/api/extension/learning/profile**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          host: "localhost",
          schema_hash: "demo-schema",
          canonical_map: {},
          style_hint: null,
        }),
      });
    });

    // Mock learning sync endpoint
    await page.route("**/api/extension/learning/sync", async (route) => {
      await route.fulfill({
        status: 202,
        contentType: "application/json",
        body: JSON.stringify({ synced: true })
      });
    });

    // 2) Open the demo form and Companion panel
    await page.goto("http://127.0.0.1:5177/demo-form.html");
    await page.waitForLoadState("networkidle");

    // Inject chrome API stub AFTER page load to ensure it's available
    await page.evaluate(() => {
      (window as any).chrome = {
        runtime: {
          onMessage: { addListener: () => {} },
          sendMessage: async () => {
            console.log("[CONTENT] chrome.runtime.sendMessage called");
            return { ok: true };
          }
        },
        storage: {
          sync: {
            get: async (keys: any) => {
              console.log("[CONTENT] chrome.storage.sync.get called with:", keys);
              const result = { learningEnabled: true };
              console.log("[CONTENT] chrome.storage.sync.get returning:", result);
              return result;
            }
          }
        }
      };
      console.log("[CONTENT] Chrome API stubbed successfully");
    });

    // Inject patched content.js
    const contentScript = loadContentPatched();
    await page.addScriptTag({ content: contentScript });

    // Wait for extension global to be available
    await page.waitForFunction(() => (window as any).__APPLYLENS__ !== undefined, { timeout: 5000 });

    // Trigger scan and suggest using the extension's global API
    console.log("[TEST] Triggering scan and suggest...");
    await page.evaluate(() => {
      (window as any).__APPLYLENS__.runScanAndSuggest();
    });

    // Wait for panel to render
    const panel = page.locator("#__applylens_panel__");
    await expect(panel).toBeVisible({ timeout: 10000 });

    // Wait for rows to populate
    await page.waitForTimeout(1000);

    const rows = panel.locator('[data-testid="al-answer-row"]');
    const rowCount = await rows.count();
    console.log(`[TEST] Found ${rowCount} answer rows`);

    // For this test, we need at least 2 rows to test checkbox/edit behavior
    expect(rowCount).toBeGreaterThanOrEqual(2);

    // Grab first and second rows
    const firstRow = rows.nth(0);
    const secondRow = rows.nth(1);

    const firstSelector = await firstRow.getAttribute("data-selector");
    const secondSelector = await secondRow.getAttribute("data-selector");

    console.log(`[TEST] First row selector: ${firstSelector}`);
    console.log(`[TEST] Second row selector: ${secondSelector}`);

    // Sanity checks for selectors (panel must expose them)
    expect(firstSelector, "firstRow must expose data-selector").toBeTruthy();
    expect(secondSelector, "secondRow must expose data-selector").toBeTruthy();

    // 3) Uncheck the first row so it should NOT be applied
    const firstCheckbox = firstRow.locator('[data-testid="al-answer-checkbox"]');
    await firstCheckbox.uncheck();
    console.log(`[TEST] Unchecked first row (${firstSelector})`);

    // 4) Edit the second row text so we can assert the edit is applied
    const secondTextarea = secondRow.locator('[data-testid="al-answer-textarea"]');
    const editedText = "Edited summary from UX E2E";
    await secondTextarea.fill(editedText);
    console.log(`[TEST] Edited second row (${secondSelector}) to: "${editedText}"`);

    // 5) Click Fill All
    const fillAllButton = panel.locator('button', { hasText: /fill all/i });
    await fillAllButton.click();
    console.log("[TEST] Clicked Fill All");

    // Wait for fill operation to complete
    await page.waitForTimeout(1000);

    // 6) Assert DOM fields reflect what we chose:
    // - Field mapped to firstRow selector should remain empty
    // - Field mapped to secondRow selector should equal editedText

    if (firstSelector) {
      const firstField = page.locator(firstSelector);
      const firstValue = await firstField.inputValue();
      console.log(`[TEST] Field ${firstSelector} value: "${firstValue}"`);
      await expect(firstField, `Field ${firstSelector} should remain untouched`).toHaveValue("");
    }

    if (secondSelector) {
      const secondField = page.locator(secondSelector);
      const secondValue = await secondField.inputValue();
      console.log(`[TEST] Field ${secondSelector} value: "${secondValue}"`);
      await expect(secondField, `Field ${secondSelector} should get edited value`).toHaveValue(editedText);
    }

    console.log("[TEST] ✅ UX panel controls validated successfully");
  });
});
