import { test, expect } from "@playwright/test";
import { waitForApp } from "./utils/waitApp";

test.describe("Search result highlighting", () => {
  test("subject/snippet show <mark> highlights", async ({ page, context }) => {
    await context.route('**/api/search/**', route => {
      route.fulfill({
        json: {
          total: 1,
          hits: [{
            id: "1",
            subject: "Interview scheduled",
            subject_highlight: "<mark>Interview</mark> scheduled",
            body_highlight: "Your <mark>interview</mark> is tomorrow",
            category: "ats",
          }]
        }
      });
    });

    await page.goto("/search?q=interview", { waitUntil: "domcontentloaded" });
    await waitForApp(page);
    
    const subject = page.getByTestId("subject").first();
    await expect(subject.locator("mark")).toHaveText(/Interview/i);
    
    const snippet = page.getByTestId("snippet").first();
    await expect(snippet.locator("mark")).toHaveText(/interview/i);
  });

  test("highlights are XSS-safe", async ({ page, context }) => {
    await context.route('**/api/search/**', route => {
      route.fulfill({
        json: {
          total: 1,
          hits: [{
            id: "2",
            subject: "Test XSS",
            subject_highlight: "<script>alert('xss')</script><mark>Test</mark>",
            body_highlight: "<mark>safe</mark> content",
            category: "ats",
          }]
        }
      });
    });

    await page.goto("/search?q=test", { waitUntil: "domcontentloaded" });
    await waitForApp(page);
    
    // Check that script tags are escaped (should not execute)
    const html = await page.content();
    expect(html).toContain("&lt;script&gt;");
    
    // Mark tags should still work
    await expect(page.getByTestId("subject").locator("mark")).toBeVisible();
  });

  test("multiple highlights in body snippets", async ({ page, context }) => {
    await context.route('**/api/search/**', route => {
      route.fulfill({
        json: {
          total: 1,
          hits: [{
            id: "3",
            subject: "Application update",
            subject_highlight: "<mark>Application</mark> update",
            body_highlight: "Your <mark>application</mark> for the role has been reviewed. We'll contact you about your <mark>application</mark> soon.",
            category: "ats",
          }]
        }
      });
    });

    await page.goto("/search?q=application", { waitUntil: "domcontentloaded" });
    await waitForApp(page);
    
    // Check multiple mark tags in body
    const marks = page.getByTestId("snippet").locator("mark");
    await expect(marks).toHaveCount(2);
  });

  test("no highlights when query doesn't match", async ({ page, context }) => {
    await context.route('**/api/search/**', route => {
      route.fulfill({
        json: {
          total: 1,
          hits: [{
            id: "4",
            subject: "No match here",
            body_preview: "Just regular text",
            category: "promotions",
          }]
        }
      });
    });

    await page.goto("/search?q=nomatch", { waitUntil: "domcontentloaded" });
    await waitForApp(page);
    
    // Should display subject without marks
    await expect(page.getByText("No match here")).toBeVisible();
    
    // No mark tags should exist
    const marks = page.locator("mark");
    await expect(marks).toHaveCount(0);
  });
});
