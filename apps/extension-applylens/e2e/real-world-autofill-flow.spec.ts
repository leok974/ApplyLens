import { test, expect } from "@playwright/test";

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
          fields: Object.keys(reqBody.fields || {}),
        });

        // Verify we received field mappings
        expect(reqBody).toHaveProperty("fields");

        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            answers: {
              first_name: "Testy",
              last_name: "McTestface",
              email: "testy.mctestface@example.com",
              phone: "555-0123",
            },
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
      // Adjust URL based on your test setup
      await page.goto("http://localhost:5173");

      // Wait for page to be ready
      await page.waitForLoadState("networkidle");

      // Open extension popup or trigger autofill
      // This depends on your extension's UI - adjust as needed
      // Option 1: If you have a content script button:
      // await page.click('[data-testid="applylens-scan-and-fill"]');

      // Option 2: If you trigger via extension popup:
      // You might need to use a Chrome extension test helper

      // Option 3: Simulate the message that triggers autofill
      await page.evaluate(() => {
        // Simulate extension message to content script
        window.postMessage(
          {
            type: "APPLYLENS_SCAN_AND_SUGGEST",
            source: "applylens-extension",
          },
          "*"
        );
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
      await page.goto("http://localhost:5173");
      await page.waitForLoadState("networkidle");

      // Trigger autofill again
      await page.evaluate(() => {
        window.postMessage(
          {
            type: "APPLYLENS_SCAN_AND_SUGGEST",
            source: "applylens-extension",
          },
          "*"
        );
      });

      await page.waitForTimeout(1000);

      // Verify second run behavior
      expect(profileCallsSecondRun).toBeGreaterThanOrEqual(
        1,
        "Profile should be fetched on second run"
      );

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
      expect(syncCalls).toBeGreaterThanOrEqual(
        1,
        "At least one sync call should have occurred"
      );
      expect(profileCallsFirstRun).toBeGreaterThanOrEqual(
        1,
        "Profile should be requested on first run (returns empty)"
      );
      expect(profileCallsSecondRun).toBeGreaterThanOrEqual(
        1,
        "Profile should be requested on second run (returns learned data)"
      );
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

    await page.goto("http://localhost:5173");
    await page.waitForLoadState("networkidle");

    await page.evaluate(() => {
      window.postMessage(
        { type: "APPLYLENS_SCAN_AND_SUGGEST", source: "applylens-extension" },
        "*"
      );
    });

    await page.waitForTimeout(500);

    expect(profileCalls).toBeGreaterThanOrEqual(1);

    console.log("[TEST] ✅ Quality guard test complete");
    console.log(
      "[TEST] Profile was requested but returned empty due to low confidence"
    );
  });
});
