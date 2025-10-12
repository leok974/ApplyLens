import { test, expect } from "@playwright/test";
import { API } from "./utils/env";

test.describe("Search result highlighting", () => {
  test("subject/snippet render <mark> highlights", async ({ page, context }) => {
    await context.route(`${API}/search/**`, route => {
      route.fulfill({
        json: {
          total: 1,
          hits: [{
            id: "1",
            subject: "Interview scheduled",
            subject_highlight: " <mark>Interview</mark> scheduled ",
            body_highlight: " Your <mark>interview</mark> is tomorrow ",
            category: "ats",
            sender: "hr@company.com",
            received_at: "2025-01-15T10:00:00Z",
            score: 10.5
          }]
        }
      });
    });

    await page.goto("/search?q=interview");
    
    // Wait for results to load
    await page.waitForSelector("[data-testid='search-result-item']", { timeout: 5000 });

    // Check that mark tags are rendered in subject
    const subject = page.locator("h3, [data-testid='subject']").first();
    await expect(subject.locator("mark")).toHaveText(/Interview/i);

    // Check that mark tags are rendered in body snippet
    const snippet = page.locator("[data-testid='snippet']").or(page.locator(".text-muted-foreground").filter({ hasText: /interview/i }));
    await expect(snippet.locator("mark").first()).toHaveText(/interview/i);
  });

  test("highlights are XSS-safe", async ({ page, context }) => {
    await context.route(`${API}/search/**`, route => {
      route.fulfill({
        json: {
          total: 1,
          hits: [{
            id: "2",
            subject: "Test subject",
            subject_highlight: "<script>alert('xss')</script> <mark>Test</mark> subject",
            body_highlight: "<img src=x onerror=alert('xss')> Safe <mark>text</mark>",
            category: "other",
            sender: "test@example.com",
            received_at: "2025-01-15T10:00:00Z",
            score: 5.0
          }]
        }
      });
    });

    await page.goto("/search?q=test");
    await page.waitForSelector("[data-testid='search-result-item']", { timeout: 5000 });

    // Check that script tags are escaped
    const html = await page.content();
    expect(html).not.toContain("<script>alert");
    expect(html).not.toContain("<img src=x onerror");

    // But mark tags should be present
    expect(html).toContain("<mark>Test</mark>");
    expect(html).toContain("<mark>text</mark>");
  });

  test("multiple highlights in body snippets", async ({ page, context }) => {
    await context.route(`${API}/search/**`, route => {
      route.fulfill({
        json: {
          total: 1,
          hits: [{
            id: "3",
            subject: "Application status",
            subject_highlight: "<mark>Application</mark> status",
            body_highlight: "Your <mark>application</mark> has been reviewed ... We are excited about your <mark>application</mark> ... Next steps for your <mark>application</mark>",
            category: "ats",
            sender: "jobs@company.com",
            received_at: "2025-01-15T10:00:00Z",
            score: 8.0
          }]
        }
      });
    });

    await page.goto("/search?q=application");
    await page.waitForSelector("[data-testid='search-result-item']", { timeout: 5000 });

    // Check multiple mark tags in body
    const marks = page.locator("mark");
    await expect(marks).toHaveCount(4); // 1 in subject + 3 in body
  });

  test("no highlights when query doesn't match", async ({ page, context }) => {
    await context.route(`${API}/search/**`, route => {
      route.fulfill({
        json: {
          total: 1,
          hits: [{
            id: "4",
            subject: "No match here",
            subject_highlight: null, // No highlight
            body_highlight: null,
            category: "other",
            sender: "test@example.com",
            received_at: "2025-01-15T10:00:00Z",
            score: 1.0
          }]
        }
      });
    });

    await page.goto("/search?q=nomatch");
    await page.waitForSelector("[data-testid='search-result-item']", { timeout: 5000 });

    // Should display subject without marks
    await expect(page.getByText("No match here")).toBeVisible();
    const marks = page.locator("mark");
    await expect(marks).toHaveCount(0);
  });
});
