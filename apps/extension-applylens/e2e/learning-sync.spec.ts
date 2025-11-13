// e2e/learning-sync.spec.ts
import { test, expect } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

const ROOT = path.resolve(__dirname, "..");
const CONTENT_JS = path.join(ROOT, "content.js");

/**
 * Load content.js and stub imports for testing
 * Replaces imports with inline stubs to avoid module resolution issues
 */
function loadContentPatched(): string {
  let raw = fs.readFileSync(CONTENT_JS, "utf8");

  // Replace APPLYLENS_API_BASE import
  raw = raw.replace(
    /import\s*\{\s*APPLYLENS_API_BASE\s*\}\s*from\s*["']\.\/config\.js["'];?/,
    'const APPLYLENS_API_BASE = "http://127.0.0.1:8003";'
  );

  // Replace learning module imports with inline stubs
  raw = raw.replace(
    /import\s*\{[^}]+\}\s*from\s*["']\.\/learning\/formMemory\.js["'];?/,
    `const loadFormMemory = async () => null;
const saveFormMemory = async () => {};`
  );

  raw = raw.replace(
    /import\s*\{[^}]+\}\s*from\s*["']\.\/learning\/client\.js["'];?/,
    `const queueLearningEvent = () => {};
const flushLearningEvents = async () => {};`
  );

  raw = raw.replace(
    /import\s*\{[^}]+\}\s*from\s*["']\.\/learning\/utils\.js["'];?/,
    `const computeSchemaHash = (fields) => "test_schema_hash";
const editDistance = (a, b) => Math.abs(a.length - b.length);`
  );

  // Wrap in IIFE
  return `(function() {\n${raw}\n})();`;
}

test.describe("Learning sync - POST to /api/extension/learning/sync", () => {
  test("queues and flushes learning event after autofill", async ({ page }) => {
    let syncPayload: any = null;

    // 1) Mock generate-form-answers API
    await page.route("**/api/extension/generate-form-answers", async (route) => {
      const body = route.request().postDataJSON() as any;
      const fields = (body?.fields ?? []) as Array<{ field_id: string }>;

      const answers = fields.map(f => ({
        field_id: f.field_id,
        answer: "Generated answer for " + f.field_id
      }));

      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ job: body?.job ?? {}, answers })
      });
    });

    // 2) Mock learning sync API and capture payload
    await page.route("**/api/extension/learning/sync", async (route) => {
      syncPayload = route.request().postDataJSON();

      await route.fulfill({
        status: 202,
        contentType: "application/json",
        body: JSON.stringify({ synced: true })
      });
    });

    // 3) Go to demo page
    await page.goto("http://127.0.0.1:5177/demo-form.html");

    // 4) Stub chrome API
    await page.addInitScript(() => {
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

    // 5) Inject patched content.js
    const contentScript = loadContentPatched();
    await page.addScriptTag({ content: contentScript });

    // 6) Wait for script to load
    await page.waitForFunction(() => (window as any).__APPLYLENS__ !== undefined);

    // 7) Trigger scan and suggest
    await page.evaluate(() => {
      (window as any).__APPLYLENS__.runScanAndSuggest();
    });

    // 8) Wait for panel to appear
    const panel = page.locator("#__applylens_panel__");
    await expect(panel).toBeVisible({ timeout: 5000 });

    // 9) Click "Fill all" button
    const fillAllBtn = panel.locator("#al_fill_all");
    await fillAllBtn.click();

    // 10) Wait for learning sync request
    await page.waitForTimeout(1000); // Give time for async flush

    // 11) Verify sync payload was sent
    expect(syncPayload).not.toBeNull();
    expect(syncPayload).toHaveProperty("host");
    expect(syncPayload).toHaveProperty("schema_hash");
    expect(syncPayload).toHaveProperty("events");
    expect(Array.isArray(syncPayload.events)).toBe(true);
    expect(syncPayload.events.length).toBeGreaterThan(0);

    // 12) Verify event structure
    const event = syncPayload.events[0];
    expect(event).toHaveProperty("suggested_map");
    expect(event).toHaveProperty("final_map");
    expect(event).toHaveProperty("edit_stats");
    expect(event).toHaveProperty("duration_ms");
    expect(event).toHaveProperty("status");
    expect(event.status).toBe("ok");
  });

  test("does not sync when learning is disabled", async ({ page }) => {
    let syncCalled = false;

    // 1) Mock generate-form-answers API
    await page.route("**/api/extension/generate-form-answers", async (route) => {
      const body = route.request().postDataJSON() as any;
      const fields = (body?.fields ?? []) as Array<{ field_id: string }>;

      const answers = fields.map(f => ({
        field_id: f.field_id,
        answer: "Test answer"
      }));

      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ job: body?.job ?? {}, answers })
      });
    });

    // 2) Mock learning sync API
    await page.route("**/api/extension/learning/sync", async (route) => {
      syncCalled = true;
      await route.fulfill({
        status: 202,
        contentType: "application/json",
        body: JSON.stringify({ synced: true })
      });
    });

    // 3) Go to demo page
    await page.goto("http://127.0.0.1:5177/demo-form.html");

    // 4) Stub chrome API with learning DISABLED
    await page.addInitScript(() => {
      (window as any).chrome = {
        runtime: {
          onMessage: { addListener: () => {} },
          sendMessage: async () => ({ ok: true })
        },
        storage: {
          sync: {
            get: async () => ({ learningEnabled: false })
          }
        }
      };
    });

    // 5) Inject content script
    const contentScript = loadContentPatched();
    await page.addScriptTag({ content: contentScript });

    // 6) Wait for script
    await page.waitForFunction(() => (window as any).__APPLYLENS__ !== undefined);

    // 7) Trigger scan
    await page.evaluate(() => {
      (window as any).__APPLYLENS__.runScanAndSuggest();
    });

    // 8) Wait for panel
    const panel = page.locator("#__applylens_panel__");
    await expect(panel).toBeVisible({ timeout: 5000 });

    // 9) Click Fill all
    const fillAllBtn = panel.locator("#al_fill_all");
    await fillAllBtn.click();

    // 10) Wait a bit
    await page.waitForTimeout(1000);

    // 11) Verify sync was NOT called
    expect(syncCalled).toBe(false);
  });
});
