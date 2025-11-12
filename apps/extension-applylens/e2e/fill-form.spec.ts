import { test, expect } from "@playwright/test";
import * as path from "node:path";
import * as fs from "node:fs";

const contentJs = fs.readFileSync(path.resolve(__dirname, "..", "content.js"), "utf8");

test("content script fills answers end-to-end", async ({ page }) => {
  // 1) Go to demo form
  await page.goto("/demo-form.html");

  // 2) Mark page as test-mode and mock API
  await page.addInitScript(() => { (window as any).__APPLYLENS_TEST = 1; });

  // Intercept API call made by content.js and return canned answers
  await page.route("**/api/extension/generate-form-answers", async route => {
    const json = {
      ok: true,
      data: {
        answers: [
          { field_id: "cover_letter",   answer: "I'm excited about your mission and impact." },
          { field_id: "project_example", answer: "I built ApplyLens, an agentic job-inbox..." }
        ]
      }
    };
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(json) });
  });

  // 3) Inject content.js
  await page.addScriptTag({ content: contentJs, type: "module" });

  // 4) Fire the test hook event to simulate popup → content scan
  await page.evaluate(() => window.postMessage({ type: "APPLYLENS_TEST_SCAN" }, "*"));

  // 5) Assert fields are populated
  const cover = page.locator("textarea[name='cover_letter']");
  const proj  = page.locator("textarea[name='project_example']");
  await expect(cover).toHaveValue(/excited|mission/i);
  await expect(proj).toHaveValue(/ApplyLens/i);
});
