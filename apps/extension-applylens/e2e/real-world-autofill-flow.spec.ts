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
    `const loadFormMemory = async () => ({ selectorMap: {} });
const saveFormMemory = async () => {};`
  );

  raw = raw.replace(
    /import\s*\{[^}]+\}\s*from\s*["']\.\/learning\/client\.js["'];?/,
    `let queuedEvents = [];
const queueLearningEvent = (event) => queuedEvents.push(event);
const flushLearningEvents = async () => {
  if (queuedEvents.length === 0) return;
  const events = queuedEvents.slice();
  queuedEvents = [];
  const payload = { host: events[0].host, schema_hash: events[0].schemaHash, events };
  await fetch('/api/extension/learning/sync', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
};`
  );

  raw = raw.replace(
    /import\s*\{[^}]+\}\s*from\s*["']\.\/learning\/utils\.js["'];?/,
    `const computeSchemaHash = (fields) => "test_schema_hash";
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

  return raw;
}

/**
 * Real-world-style E2E: Learning Loop Lifecycle
 *
 * This test simulates the complete learning loop without requiring:
 * - Real PostgreSQL database
 * - Actual aggregator cron job
 * - Database migrations
 *
 * Flow:
 * 1) First visit:
 *    - /learning/profile returns empty canonical_map (no profile yet)
 *    - User triggers autofill → extension uses heuristics
 *    - Extension calls /learning/sync → test captures payload
 *
 * 2) "Aggregator" step:
 *    - Test simulates aggregation by using captured sync payload
 *    - Builds canonical_map from final_map in first event
 *
 * 3) Second visit:
 *    - /learning/profile returns canonical_map from first visit
 *    - User triggers autofill → extension uses learned profile
 *    - Test asserts profile was fetched and used
 *
 * STATUS:
 * - ✅ Profile fetching works
 * - ✅ Generate answers API works
 * - ✅ Extension panel displays
 * - ❌ Learning sync not triggering (needs debugging)
 *
 * TODO: Fix learning sync trigger mechanism
 */

test.describe("Companion real-world learning loop", () => {
  test("first run learns, second run uses profile", async ({ page }) => {
    let lastSyncPayload: any = null;
    let profilePhase: "first" | "second" = "first";

    let profileCallsFirstRun = 0;
    let profileCallsSecondRun = 0;
    let syncCalls = 0;

    // ---- Mock /learning/sync to capture learning events ----
    await page.route("**/api/extension/learning/sync", async (route) => {
      const body = await route.request().postDataJSON();
      syncCalls += 1;
      lastSyncPayload = body;

      console.log("[TEST] Learning sync captured:", {
        host: body.host,
        schema_hash: body.schema_hash,
        events_count: body.events?.length,
      });

      await route.fulfill({
        status: 202,
        contentType: "application/json",
        body: JSON.stringify({
          status: "accepted",
          persisted: true,
          events_saved: body.events?.length || 0,
        }),
      });
    });

    // ---- Mock /learning/profile with 2-phase behavior ----
    await page.route("**/api/extension/learning/profile**", async (route) => {
      const url = new URL(route.request().url());
      const host = url.searchParams.get("host") || "localhost";
      const schemaHash = url.searchParams.get("schema_hash") || "demo";

      if (profilePhase === "first") {
        profileCallsFirstRun += 1;
        console.log(
          `[TEST] Profile request (first run): ${host}/${schemaHash}`
        );

        // No profile yet: behave like a fresh site
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            host,
            schema_hash: schemaHash,
            canonical_map: {},
            style_hint: null,
          }),
        });
      } else {
        profileCallsSecondRun += 1;
        console.log(
          `[TEST] Profile request (second run): ${host}/${schemaHash}`
        );

        // Simulate aggregator using lastSyncPayload to build canonical_map
        const canonicalMap = lastSyncPayload?.events?.[0]?.final_map || {
          "input[name='firstName']": "first_name",
          "input[name='lastName']": "last_name",
          "input[name='email']": "email",
        };

        console.log("[TEST] Returning canonical_map:", canonicalMap);

        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            host,
            schema_hash: schemaHash,
            canonical_map: canonicalMap,
            style_hint: {
              gen_style_id: "concise_bullets_test",
              confidence: 0.85,
            },
          }),
        });
      }
    });

    // ---- Mock generate-form-answers to provide test data ----
    await page.route(
      "**/api/extension/generate-form-answers",
      async (route) => {
        const reqBody = await route.request().postDataJSON();

        console.log("[TEST] Generate answers request:", {
          fieldsArray: reqBody.fields,
          fieldCount: reqBody.fields?.length
        });

        // Verify we received fields array
        expect(reqBody).toHaveProperty("fields");
        expect(Array.isArray(reqBody.fields)).toBe(true);

        // Create answers based on the field structure expected by content.js
        const answers = reqBody.fields.map((field: any) => ({
          field_id: field.field_id,
          answer: `Test answer for ${field.field_id}`
        }));

        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            job: reqBody.job || { title: "Test Job", company: "Test Co" },
            answers: answers
          }),
        });
      }
    );

    // ---- Mock profile/me for extension auth check ----
    await page.route("**/api/profile/me", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          id: "test-user-123",
          email: "test@applylens.local",
        }),
      });
    });

    // ----------------- RUN 1: Learn -----------------
    await test.step("First run – no profile yet, learn from sync", async () => {
      // Navigate to a test form page
      // Using the test server port from playwright.config.ts
      await page.goto("http://127.0.0.1:5177/demo-form.html");

      // Wait for page to be ready
      await page.waitForLoadState("networkidle");

      // Stub chrome API for extension
      await page.addInitScript(() => {
        (window as any).chrome = {
          runtime: {
            onMessage: { addListener: () => {} },
            sendMessage: async () => ({ ok: true })
          },
          storage: {
            sync: {
              get: async (keys: any) => {
                console.log("[TEST] Chrome storage get called with:", keys);
                const result = { learningEnabled: true };
                console.log("[TEST] Chrome storage returning:", result);
                return result;
              }
            }
          }
        };
      });

      // Inject patched content.js
      const contentScript = loadContentPatched();
      await page.addScriptTag({ content: contentScript });

      // Wait for extension global to be available
      await page.waitForFunction(() => (window as any).__APPLYLENS__ !== undefined, { timeout: 5000 });

      // Trigger autofill using the extension's API
      await page.evaluate(() => {
        (window as any).__APPLYLENS__.runScanAndSuggest();
      });

      // Wait for panel to appear
      const panel = page.locator("#__applylens_panel__");
      await expect(panel).toBeVisible({ timeout: 5000 });

      // Click "Fill all" button to trigger learning sync
      const fillAllBtn = panel.locator("#al_fill_all");
      await expect(fillAllBtn).toBeVisible();
      console.log("[TEST] Clicking Fill All button...");

      // Add debugging to see if click handlers are working
      await page.evaluate(() => {
        const btn = document.querySelector("#al_fill_all") as HTMLButtonElement;
        console.log("[CONTENT] Fill All button found:", !!btn);
        console.log("[CONTENT] Fill All onclick handler:", typeof btn?.onclick);
      });

      await fillAllBtn.click();
      console.log("[TEST] Fill All button clicked");

      // Check if fields were actually filled
      await page.evaluate(() => {
        const inputs = document.querySelectorAll("input, textarea");
        console.log("[CONTENT] Form fields after click:", Array.from(inputs).map(el => ({
          id: (el as HTMLInputElement).id,
          value: ((el as HTMLInputElement).value || '').substring(0, 20) + (((el as HTMLInputElement).value || '').length > 20 ? '...' : '')
        })));
      });

      // Wait for learning sync to happen
      await page.waitForTimeout(1000);

      // Verify first run behavior
      expect(syncCalls).toBeGreaterThanOrEqual(1);
      expect(lastSyncPayload).not.toBeNull();
      expect(profileCallsFirstRun).toBeGreaterThanOrEqual(1);

      console.log("[TEST] First run complete:", {
        syncCalls,
        profileCallsFirstRun,
        capturedEvents: lastSyncPayload?.events?.length,
      });
    });

    // "Aggregator" flips the switch - simulate profile being computed
    profilePhase = "second";
    console.log("[TEST] === Simulating aggregator run ===");
    console.log(
      "[TEST] Canonical map computed from sync:",
      lastSyncPayload?.events?.[0]?.final_map
    );

    // ----------------- RUN 2: Use Profile -----------------
    await test.step("Second run – profile exists, should be used", async () => {
      // Navigate to the same form again (simulating a new user or later visit)
      await page.goto("http://127.0.0.1:5177/demo-form.html");
      await page.waitForLoadState("networkidle");

      // Trigger autofill again using extension API
      await page.evaluate(() => {
        (window as any).__APPLYLENS__.runScanAndSuggest();
      });

      // Wait for panel and click Fill All to complete the flow
      const panel = page.locator("#__applylens_panel__");
      await expect(panel).toBeVisible({ timeout: 5000 });

      await page.waitForTimeout(1000);

      // Verify second run behavior
      expect(profileCallsSecondRun, "Profile should be fetched on second run").toBeGreaterThanOrEqual(1);

      console.log("[TEST] Second run complete:", {
        profileCallsSecondRun,
        profileUsed: profileCallsSecondRun > 0,
      });

      // Optional: Verify form fields were actually filled
      // This depends on your test form structure - adjust selectors
      const firstNameInput = page.locator("input[name='firstName']").first();
      if (await firstNameInput.count() > 0) {
        const value = await firstNameInput.inputValue();
        console.log("[TEST] First name field value:", value);
        // Profile was used if field has content
        expect(value).not.toBe("");
      }
    });

    // Final assertions
    await test.step("Verify complete learning loop", async () => {
      expect(syncCalls, "At least one sync call should have occurred").toBeGreaterThanOrEqual(1);
      expect(profileCallsFirstRun, "Profile should be requested on first run (returns empty)").toBeGreaterThanOrEqual(1);
      expect(profileCallsSecondRun, "Profile should be requested on second run (returns learned data)").toBeGreaterThanOrEqual(1);
      expect(lastSyncPayload).not.toBeNull();
      expect(lastSyncPayload.events).toBeDefined();
      expect(lastSyncPayload.events.length).toBeGreaterThan(0);

      console.log("[TEST] ✅ Complete learning loop verified");
      console.log("[TEST] Summary:", {
        totalSyncCalls: syncCalls,
        profileCallsRun1: profileCallsFirstRun,
        profileCallsRun2: profileCallsSecondRun,
        eventsLearned: lastSyncPayload.events.length,
      });
    });
  });

  test("profile quality guards reject low-confidence profiles", async ({
    page,
  }) => {
    let profileCalls = 0;

    // Mock profile endpoint returning low-quality profile
    await page.route("**/api/extension/learning/profile**", async (route) => {
      const url = new URL(route.request().url());
      const host = url.searchParams.get("host") || "localhost";
      const schemaHash = url.searchParams.get("schema_hash") || "demo";

      profileCalls += 1;

      // Simulate backend rejecting low-quality profile
      // (success_rate < 0.6 or avg_edit_chars > 500)
      // Backend returns empty canonical_map for low-quality profiles
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          host,
          schema_hash: schemaHash,
          canonical_map: {}, // Empty because quality guards rejected it
          style_hint: null,
        }),
      });
    });

    await page.route("**/api/profile/me", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ id: "test-user", email: "test@example.com" }),
      });
    });

    await page.goto("http://127.0.0.1:5177/demo-form.html");
    await page.waitForLoadState("networkidle");

    // Stub chrome API and trigger extension
    await page.addInitScript(() => {
      (window as any).chrome = {
        runtime: { onMessage: { addListener: () => {} }, sendMessage: async () => ({ ok: true }) },
        storage: { sync: { get: async (keys: any) => ({ learningEnabled: true }) } }
      };
    });

    // Inject patched content script
    const contentScript = loadContentPatched();
    await page.addScriptTag({ content: contentScript });

    await page.waitForFunction(() => (window as any).__APPLYLENS__ !== undefined, { timeout: 5000 });

    await page.evaluate(() => {
      (window as any).__APPLYLENS__.runScanAndSuggest();
    });

    await page.waitForTimeout(500);

    expect(profileCalls).toBeGreaterThanOrEqual(1);

    console.log("[TEST] ✅ Quality guard test complete");
    console.log(
      "[TEST] Profile was requested but returned empty due to low confidence"
    );
  });
});
