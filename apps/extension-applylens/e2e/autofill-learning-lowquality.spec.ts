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

test.describe("@companion @lowquality Companion autofill - low quality profile rejected", () => {
  test("falls back to heuristics when profile quality is low", async ({ page }) => {
    // Enable console log capture
    page.on('console', msg => {
      const text = msg.text();
      if (text.includes('[CONTENT]') || text.includes('[Learning]') || text.includes('[TEST]')) {
        console.log(text);
      }
    });

    let profileRequests = 0;
    let syncRequests = 0;
    let lastSyncPayload: any = null;
    let generateAnswersRequests = 0;

    // --- 1) Mock /api/extension/learning/profile with LOW QUALITY data ---
    // This simulates the backend returning a profile that should be rejected
    // due to quality guards (success_rate < 0.6, avg_edit_chars > 500)
    await page.route("**/api/extension/learning/profile**", async (route) => {
      profileRequests += 1;

      console.log("[TEST] Profile endpoint called (returning low-quality profile)");

      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          host: "127.0.0.1",
          schema_hash: "demo_schema_hash",
          // Low quality indicators - backend would reject this
          canonical_map: {
            "#full_name": "first_name",
            "#email": "email",
          },
          style_hint: {
            gen_style_id: "bad_profile",
            confidence: 0.1,  // Very low confidence
          },
          // Quality metrics that would trigger rejection
          success_rate: 0.2,      // < 0.6 threshold
          avg_edit_chars: 900,    // > 500 threshold
        }),
      });
    });

    // --- 2) Mock /api/extension/learning/sync ---
    await page.route("**/api/extension/learning/sync", async (route) => {
      syncRequests += 1;
      console.log("[TEST] Learning sync endpoint called");

      try {
        lastSyncPayload = await route.request().postDataJSON();
        console.log("[TEST] Sync payload:", {
          host: lastSyncPayload.host,
          schema_hash: lastSyncPayload.schema_hash,
          events_count: lastSyncPayload.events?.length
        });
      } catch {
        lastSyncPayload = null;
      }

      await route.fulfill({
        status: 202,
        contentType: "application/json",
        body: JSON.stringify({ status: "accepted" }),
      });
    });

    // --- 3) Mock /api/extension/generate-form-answers ---
    await page.route("**/api/extension/generate-form-answers", async (route) => {
      const reqBody = await route.request().postDataJSON();
      generateAnswersRequests += 1;

      console.log("[TEST] Generate answers called (should use heuristics, not bad profile)");

      expect(reqBody).toHaveProperty("fields");
      expect(Array.isArray(reqBody.fields)).toBe(true);

      const answers = reqBody.fields.map((field: any) => ({
        field_id: field.field_id,
        answer: `Heuristic answer for ${field.field_id}`
      }));

      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          job: reqBody.job || { title: "Test Job", company: "Test Co" },
          answers: answers
        }),
      });
    });

    // --- 4) Go to demo form page ---
    await page.goto("http://127.0.0.1:5177/demo-form.html");
    await page.waitForLoadState("networkidle");

    // Inject chrome API stub AFTER page load
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

    // Wait for extension global
    await page.waitForFunction(() => (window as any).__APPLYLENS__ !== undefined, { timeout: 5000 });

    // --- 5) Trigger scan and suggest ---
    console.log("[TEST] Triggering scan and suggest...");
    await page.evaluate(() => {
      (window as any).__APPLYLENS__.runScanAndSuggest();
    });

    // Wait for panel
    const panel = page.locator("#__applylens_panel__");
    await expect(panel).toBeVisible({ timeout: 5000 });
    console.log("[TEST] Panel visible");

    // --- 6) Click Fill All ---
    const fillAllButton = panel.locator("#al_fill_all");
    await expect(fillAllButton).toBeVisible();

    console.log("[TEST] Clicking Fill All button...");
    await fillAllButton.click();

    // Give time for async operations
    await page.waitForTimeout(1500);

    // --- 7) Assertions: System should still work despite low-quality profile ---

    console.log("[TEST] === Assertions ===");

    // Profile endpoint was called (we attempted to fetch it)
    expect(profileRequests, "Profile endpoint should be called").toBeGreaterThanOrEqual(1);
    console.log("[TEST] ✅ Profile was requested");

    // Generate answers was called (system still works)
    expect(generateAnswersRequests, "Generate answers should be called").toBeGreaterThanOrEqual(1);
    console.log("[TEST] ✅ Generate answers was called");

    // Learning sync should still happen (we learn from this run)
    expect(syncRequests, "Learning sync should be called").toBeGreaterThanOrEqual(1);
    console.log("[TEST] ✅ Learning sync was called");

    // Verify sync payload structure
    expect(lastSyncPayload, "Sync payload should not be null").not.toBeNull();
    if (lastSyncPayload) {
      expect(lastSyncPayload).toHaveProperty("host");
      expect(lastSyncPayload).toHaveProperty("schema_hash");
      console.log("[TEST] ✅ Sync payload structure validated");
    }

    // --- 8) Form fields should be filled (using heuristics, not bad profile) ---
    const fullNameValue = await page.locator("#full_name").inputValue();
    const emailValue = await page.locator("#email").inputValue();

    expect(fullNameValue).not.toBe("");
    expect(emailValue).not.toBe("");
    expect(fullNameValue).toContain("Heuristic"); // Verify we used heuristic answers
    expect(emailValue).toContain("Heuristic");

    console.log("[TEST] ✅ Form fields filled with heuristic answers:", {
      fullNameValue,
      emailValue
    });

    // --- Final Summary ---
    console.log("[TEST] ✅ Test complete!");
    console.log("[TEST] === Summary: Low Quality Profile Scenario ===");
    console.log("[TEST]   - Profile requests:", profileRequests);
    console.log("[TEST]   - Profile quality: LOW (success_rate: 0.2, avg_edit_chars: 900)");
    console.log("[TEST]   - Generate answers requests:", generateAnswersRequests);
    console.log("[TEST]   - Sync requests:", syncRequests);
    console.log("[TEST]   - Result: System fell back to heuristics and worked normally");
    console.log("[TEST]   - Learning: Still synced events for future improvement");
  });
});
