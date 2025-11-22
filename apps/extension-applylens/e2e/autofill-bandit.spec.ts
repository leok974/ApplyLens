/**
 * Phase 5.4: Epsilon-greedy bandit E2E tests
 *
 * @tags @companion @bandit
 *
 * Validates:
 * - Explore: picks competitor style_id when Math.random() < epsilon
 * - Exploit: uses preferred_style_id when Math.random() >= epsilon
 * - Policy logged correctly in sync payload
 */

import { test, expect } from "@playwright/test";

test.describe("@companion @bandit", () => {
  test("explore: picks competitor style_id and logs policy=explore", async ({
    page,
  }) => {
    let lastGenerateBody: any = null;
    let lastSyncBody: any = null;

    // Stub profile with preferred + competitor
    await page.route("**/api/extension/learning/profile**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          host: "boards.greenhouse.io",
          schema_hash: "bandit-test",
          canonical_map: {},
          style_hint: {
            preferred_style_id: "friendly_bullets_v2",
            style_stats: {
              chosen: {
                style_id: "friendly_bullets_v2",
                helpful_ratio: 0.8,
                total_runs: 20,
              },
              competitors: [
                {
                  style_id: "concise_paragraph_v1",
                  helpful_ratio: 0.7,
                  total_runs: 10,
                },
              ],
            },
          },
        }),
      });
    });

    await page.route(
      "**/api/extension/generate-form-answers**",
      async (route) => {
        const request = route.request();
        lastGenerateBody = await request.postDataJSON();
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            answers: [
              { field_id: "full_name", answer: "Test User" },
              { field_id: "summary", answer: "Smoke answer" },
            ],
          }),
        });
      }
    );

    await page.route(
      "**/api/extension/learning/sync**",
      async (route) => {
        const request = route.request();
        lastSyncBody = await request.postDataJSON();
        await route.fulfill({ status: 200, body: "{}" });
      }
    );

    // Force explore: r < ε
    await page.addInitScript(() => {
      // @ts-ignore
      Math.random = () => 0.01;
    });

    await page.goto("http://127.0.0.1:5177/demo-form.html");
    await page.click('[data-testid="al-scan-button"]');

    const panel = page.locator('[data-testid="al-panel"]');
    await expect(panel).toBeVisible({ timeout: 10000 });

    // Wait for generation request
    await page.waitForTimeout(1000);

    // Verify generation request used competitor style
    expect(lastGenerateBody).not.toBeNull();
    expect(lastGenerateBody.style_hint).toBeDefined();
    expect(lastGenerateBody.style_hint.style_id).toBe("concise_paragraph_v1");

    // Fill all to trigger sync
    await panel.getByTestId("al-fill-all").click();
    await page.waitForTimeout(500);

    // Verify sync logged explore policy
    expect(lastSyncBody).not.toBeNull();
    expect(lastSyncBody.policy).toBe("explore");
    expect(lastSyncBody.gen_style_id).toBe("concise_paragraph_v1");
  });

  test("exploit: uses preferred style_id and logs policy=exploit", async ({
    page,
  }) => {
    let lastGenerateBody: any = null;
    let lastSyncBody: any = null;

    await page.route("**/api/extension/learning/profile**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          host: "boards.greenhouse.io",
          schema_hash: "bandit-test",
          canonical_map: {},
          style_hint: {
            preferred_style_id: "friendly_bullets_v2",
            style_stats: {
              chosen: {
                style_id: "friendly_bullets_v2",
                helpful_ratio: 0.8,
                total_runs: 20,
              },
              competitors: [
                {
                  style_id: "concise_paragraph_v1",
                  helpful_ratio: 0.7,
                  total_runs: 10,
                },
              ],
            },
          },
        }),
      });
    });

    await page.route(
      "**/api/extension/generate-form-answers**",
      async (route) => {
        const request = route.request();
        lastGenerateBody = await request.postDataJSON();
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            answers: [
              { field_id: "full_name", answer: "Test User" },
              { field_id: "summary", answer: "Smoke answer" },
            ],
          }),
        });
      }
    );

    await page.route(
      "**/api/extension/learning/sync**",
      async (route) => {
        const request = route.request();
        lastSyncBody = await request.postDataJSON();
        await route.fulfill({ status: 200, body: "{}" });
      }
    );

    // Force exploit: r >= ε
    await page.addInitScript(() => {
      // @ts-ignore
      Math.random = () => 0.99;
    });

    await page.goto("http://127.0.0.1:5177/demo-form.html");
    await page.click('[data-testid="al-scan-button"]');

    const panel = page.locator('[data-testid="al-panel"]');
    await expect(panel).toBeVisible({ timeout: 10000 });

    // Wait for generation request
    await page.waitForTimeout(1000);

    // Verify generation request used preferred style
    expect(lastGenerateBody).not.toBeNull();
    expect(lastGenerateBody.style_hint).toBeDefined();
    expect(lastGenerateBody.style_hint.style_id).toBe("friendly_bullets_v2");

    // Fill all to trigger sync
    await panel.getByTestId("al-fill-all").click();
    await page.waitForTimeout(500);

    // Verify sync logged exploit policy
    expect(lastSyncBody).not.toBeNull();
    expect(lastSyncBody.policy).toBe("exploit");
    expect(lastSyncBody.gen_style_id).toBe("friendly_bullets_v2");
  });

  test("fallback: no preferred_style_id logs policy=fallback", async ({
    page,
  }) => {
    let lastSyncBody: any = null;

    await page.route("**/api/extension/learning/profile**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          host: "boards.greenhouse.io",
          schema_hash: "bandit-test",
          canonical_map: {},
          style_hint: {
            // No preferred_style_id
            summary_style: "bullets",
          },
        }),
      });
    });

    await page.route(
      "**/api/extension/generate-form-answers**",
      async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            answers: [
              { field_id: "full_name", answer: "Test User" },
              { field_id: "summary", answer: "Fallback answer" },
            ],
          }),
        });
      }
    );

    await page.route(
      "**/api/extension/learning/sync**",
      async (route) => {
        const request = route.request();
        lastSyncBody = await request.postDataJSON();
        await route.fulfill({ status: 200, body: "{}" });
      }
    );

    await page.goto("http://127.0.0.1:5177/demo-form.html");
    await page.click('[data-testid="al-scan-button"]');

    const panel = page.locator('[data-testid="al-panel"]');
    await expect(panel).toBeVisible({ timeout: 10000 });

    // Fill all to trigger sync
    await panel.getByTestId("al-fill-all").click();
    await page.waitForTimeout(500);

    // Verify sync logged fallback policy
    expect(lastSyncBody).not.toBeNull();
    expect(lastSyncBody.policy).toBe("fallback");
  });
});
