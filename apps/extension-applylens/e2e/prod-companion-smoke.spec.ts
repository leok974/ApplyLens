/**
 * Phase 5.5: Production Companion Smoke Test
 *
 * @tags @companion @prod
 *
 * Validates ApplyLens Companion autofill in production environment.
 * This is an API-only test that doesn't require browser automation.
 *
 * Run with:
 *   $env:APPLYLENS_PROD_API_BASE = "https://api.applylens.app"
 *   npx playwright test --grep="@companion @prod"
 */

import { test, expect, request } from "@playwright/test";

const PROD_API_BASE = process.env.APPLYLENS_PROD_API_BASE;

test.describe("@companion @prod", () => {
  test("prod companion autofill smoke", async () => {
    test.skip(
      !PROD_API_BASE,
      "APPLYLENS_PROD_API_BASE not set; skipping prod companion smoke"
    );

    const api = await request.newContext({
      baseURL: PROD_API_BASE,
    });

    const job = {
      title: "Software Engineer (Companion Smoke)",
      company: "ApplyLens",
      location: "Remote",
      description:
        "Smoke test job used to validate Companion autofill in production.",
    };

    const fields = [
      { field_id: "full_name", label: "Full name" },
      { field_id: "email", label: "Email" },
      { field_id: "summary", label: "Professional Summary" },
    ];

    const styleHint = {
      style_id: "prod_smoke_v1",
    };

    // 1) Generate answers
    console.log("[Prod Smoke] Testing generate-form-answers...");
    const genResp = await api.post("/api/extension/generate-form-answers", {
      data: {
        job,
        fields,
        style_hint: styleHint,
      },
    });

    expect(genResp.ok(), `Generate failed: ${genResp.status()}`).toBeTruthy();
    const genJson = await genResp.json();
    expect(Array.isArray(genJson.answers), "Expected answers array").toBeTruthy();
    expect(genJson.answers.length, "Expected at least 1 answer").toBeGreaterThan(0);

    console.log(`[Prod Smoke] ✅ Generated ${genJson.answers.length} answers`);

    // Validate answer structure
    for (const answer of genJson.answers) {
      expect(answer.field_id, "Answer missing field_id").toBeDefined();
      expect(answer.answer, "Answer missing answer text").toBeDefined();
      expect(typeof answer.answer, "Answer text should be string").toBe("string");
    }

    // 2) Record learning event so bandit has data to work with
    console.log("[Prod Smoke] Testing learning sync...");
    const syncResp = await api.post("/api/extension/learning/sync", {
      data: {
        host: "boards.greenhouse.io",
        schema_hash: "prod-companion-smoke-v1",
        gen_style_id: styleHint.style_id,
        policy: "exploit",
        segment_key: "default",
        events: [
          {
            host: "boards.greenhouse.io",
            schema_hash: "prod-companion-smoke-v1",
            suggested_map: { "input[name='summary']": "summary" },
            final_map: { "input[name='summary']": "summary" },
            edit_stats: {
              total_chars_added: 0,
              total_chars_deleted: 0,
              per_field: {},
            },
            duration_ms: 1500,
            validation_errors: {},
            status: "ok",
          },
        ],
      },
    });

    expect(syncResp.ok(), `Sync failed: ${syncResp.status()}`).toBeTruthy();
    console.log("[Prod Smoke] ✅ Learning sync succeeded");

    // 3) Test feedback endpoint
    console.log("[Prod Smoke] Testing feedback endpoint...");
    const feedbackResp = await api.post("/api/extension/feedback/autofill", {
      data: {
        host: "boards.greenhouse.io",
        schema_hash: "prod-companion-smoke-v1",
        status: "helpful",
      },
    });

    expect(feedbackResp.ok(), `Feedback failed: ${feedbackResp.status()}`).toBeTruthy();
    console.log("[Prod Smoke] ✅ Feedback recorded");

    console.log("\n🎉 All production companion smoke tests passed!");
  });

  test("prod profile endpoint smoke", async () => {
    test.skip(
      !PROD_API_BASE,
      "APPLYLENS_PROD_API_BASE not set; skipping prod profile smoke"
    );

    const api = await request.newContext({
      baseURL: PROD_API_BASE,
    });

    console.log("[Prod Smoke] Testing learning profile endpoint...");

    // Fetch profile (may return 404 if no data exists - that's OK)
    const profileResp = await api.get(
      "/api/extension/learning/profile?host=boards.greenhouse.io&schema_hash=prod-test"
    );

    // 404 is acceptable (no profile yet), 200 is great
    const acceptableStatuses = [200, 404];
    expect(
      acceptableStatuses.includes(profileResp.status()),
      `Profile endpoint returned unexpected status: ${profileResp.status()}`
    ).toBeTruthy();

    if (profileResp.status() === 200) {
      const profileJson = await profileResp.json();
      expect(profileJson.host).toBe("boards.greenhouse.io");
      expect(profileJson.schema_hash).toBe("prod-test");
      console.log("[Prod Smoke] ✅ Profile endpoint returned valid data");
    } else {
      console.log("[Prod Smoke] ✅ Profile endpoint returned 404 (expected for new schema)");
    }
  });
});
