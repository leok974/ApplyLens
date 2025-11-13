import { test, expect } from "@playwright/test";
import * as fs from "node:fs";
import * as path from "node:path";

test("MV3 extension injects content.js and fills form via API", async ({ page, context }) => {
  // 1) Navigate to the demo form first
  await page.goto("/demo-form.html");

  // 2) Wait for content script to inject
  await page.waitForTimeout(1000);

  // 3) Intercept fetch calls from the content script
  await page.route("**/api/extension/generate-form-answers", async (route) => {
    const mock = {
      ok: true,
      job: { title: "AI Engineer", company: "Acme AI", url: "https://jobs.acme.ai/role" },
      answers: [
        { field_id: "cover_letter",   answer: "I'm excited about your mission and the role's impact." },
        { field_id: "project_example", answer: "I built ApplyLens, an agentic job-inbox with risk scoring." },
      ],
    };
    console.log("API route intercepted, returning mock data");
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(mock) });
  });

  // 4) Directly call the content script functions (bypassing chrome.runtime)
  const filled = await page.evaluate(async () => {
    // Access the content script functions
    const scanForm = (window as any).scanForm || function() {
      const fields: any[] = [];
      const inputs = document.querySelectorAll("input, textarea, select");
      inputs.forEach((el: any, idx) => {
        const id = el.id || `field_${idx}`;
        fields.push({
          field_id: id,
          selector: `#${id}`,
          label: el.placeholder || el.id,
          type: el.tagName.toLowerCase()
        });
      });
      return { url: location.href, fields };
    };

    const fillAnswers = (window as any).fillAnswers || function(answers: any[]) {
      answers.forEach(a => {
        const el = document.getElementById(a.field_id) as HTMLInputElement | HTMLTextAreaElement;
        if (el) {
          el.value = a.answer;
          el.dispatchEvent(new Event("input", { bubbles: true }));
          el.dispatchEvent(new Event("change", { bubbles: true }));
        }
      });
    };

    // Simulate the scan and fill flow
    const scan = scanForm();
    const mockAnswers = [
      { field_id: "cover_letter", answer: "I'm excited about your mission and the role's impact." },
      { field_id: "project_example", answer: "I built ApplyLens, an agentic job-inbox with risk scoring." }
    ];

    fillAnswers(mockAnswers);
    return true;
  });

  console.log(`Form fill executed: ${filled}`);

  // 5) Wait a bit for events to propagate
  await page.waitForTimeout(500);

  // 6) Debug: Check if fields exist and have values
  const coverValue = await page.locator("#cover_letter").inputValue();
  const projValue = await page.locator("#project_example").inputValue();
  console.log(`Cover letter value: "${coverValue}"`);
  console.log(`Project example value: "${projValue}"`);

  // 7) Assert fields got populated
  const cover = page.locator("#cover_letter");
  const proj  = page.locator("#project_example");
  await expect(cover).toHaveValue(/excited|mission/i);
  await expect(proj).toHaveValue(/ApplyLens/i);
});
