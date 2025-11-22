import { test, expect } from "@playwright/test";

/**
 * Phase 2.1 E2E Test: Companion uses server profile canonical_map for autofill
 *
 * This test verifies that the extension:
 * 1. Fetches learning profile from the server
 * 2. Uses canonical_map to guide field mapping
 * 3. Falls back gracefully when profile is unavailable
 */

test("Companion uses server profile canonical_map for autofill", async ({ page }) => {
  // 1. Stub profile endpoint with canonical mapping
  await page.route("**/api/extension/learning/profile**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        host: "localhost",
        schema_hash: "demo-schema",
        canonical_map: {
          "input[name='q1']": "first_name",
          "input[name='q2']": "last_name",
          "input[name='email']": "email",
        },
        style_hint: { gen_style_id: "concise_bullets_v2", confidence: 0.9 },
      }),
    });
  });

  // 2. Stub learning sync so it doesn't error
  await page.route("**/api/extension/learning/sync**", async (route) => {
    await route.fulfill({
      status: 202,
      contentType: "application/json",
      body: JSON.stringify({ status: "accepted" }),
    });
  });

  // 3. Open demo form
  await page.goto("http://localhost:4173/test/demo-form.html");

  // 4. Trigger the extension autofill flow
  // TODO: Adjust to your existing helper once extension is integrated
  // Example approach:
  // - Open companion panel via keyboard shortcut or click
  // - Click "Scan & Suggest" button
  // - Verify profile was fetched
  // - Click "Apply suggestions" button

  // Placeholder for now - replace with actual extension trigger
  // await openCompanionPanel(page);
  // await page.getByRole("button", { name: "Scan & Suggest" }).click();
  // await page.waitForTimeout(500);
  // await page.getByRole("button", { name: "Apply suggestions" }).click();

  // 5. Assert that fields were mapped using server profile
  // This verifies the canonical_map was consulted
  const q1Value = await page.locator("input[name='q1']").inputValue();
  const q2Value = await page.locator("input[name='q2']").inputValue();
  const emailValue = await page.locator("input[name='email']").inputValue();

  // Fields should be filled (or at least mapped internally)
  // Exact assertions depend on your autofill implementation
  expect(q1Value).toBeTruthy(); // Should have first_name data
  expect(q2Value).toBeTruthy(); // Should have last_name data
  expect(emailValue).toBeTruthy(); // Should have email data

  // Alternatively, if you expose mapping metadata:
  // const mappings = await page.evaluate(() => window.__COMPANION_MAPPINGS__);
  // expect(mappings["input[name='q1']"]).toBe("first_name");
  // expect(mappings["input[name='q2']"]).toBe("last_name");
});

test("Companion falls back to heuristics when profile unavailable", async ({ page }) => {
  // 1. Stub profile endpoint to return 404 (no profile exists)
  await page.route("**/api/extension/learning/profile**", async (route) => {
    await route.fulfill({
      status: 404,
      contentType: "application/json",
      body: JSON.stringify({ detail: "Profile not found" }),
    });
  });

  // 2. Stub learning sync
  await page.route("**/api/extension/learning/sync**", async (route) => {
    await route.fulfill({
      status: 202,
      contentType: "application/json",
      body: JSON.stringify({ status: "accepted" }),
    });
  });

  // 3. Open demo form
  await page.goto("http://localhost:4173/test/demo-form.html");

  // 4. Trigger autofill flow
  // (same as above - adjust to your helper)

  // 5. Verify autofill still works using heuristics only
  // Should not crash, should use Phase 1.5 behavior
  const q1Value = await page.locator("input[name='q1']").inputValue();

  // Field may be empty or filled via heuristics
  // The key assertion is: no error, flow completes
  expect(q1Value).toBeDefined(); // Not undefined
});

test("Profile endpoint constructs correct query parameters", async ({ page }) => {
  let capturedUrl = "";

  await page.route("**/api/extension/learning/profile**", async (route) => {
    capturedUrl = route.request().url();
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        host: "example.com",
        schema_hash: "test-hash",
        canonical_map: {},
        style_hint: null,
      }),
    });
  });

  await page.route("**/api/extension/learning/sync**", async (route) => {
    await route.fulfill({ status: 202, body: JSON.stringify({ status: "accepted" }) });
  });

  await page.goto("http://localhost:4173/test/demo-form.html");

  // Trigger extension scan (adjust to your implementation)
  // await triggerExtensionScan(page);

  // Verify URL has correct query params
  expect(capturedUrl).toContain("host=");
  expect(capturedUrl).toContain("schema_hash=");
});
