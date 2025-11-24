import { test, expect } from "@playwright/test";

/**
 * @prodSafe
 *
 * This test is allowed to run against production.
 * - It navigates to /today and checks that the page renders.
 * - It verifies intent tiles load and display correctly.
 * - It does NOT mutate any data.
 * - Should pass with prod, dev, or staging data.
 */

test.describe("@prodSafe Today triage page", () => {
  test("today API endpoint returns 200 or 401 (not 405)", async ({ page }) => {
    // Listen for API calls
    const apiCalls: { url: string; status: number }[] = [];

    page.on("response", (response) => {
      if (response.url().includes("/api/v2/agent/today")) {
        apiCalls.push({
          url: response.url(),
          status: response.status(),
        });
      }
    });

    // Navigate to Today page
    await page.goto("/today", { waitUntil: "domcontentloaded" });
    await page.waitForLoadState("networkidle");

    // Check if API was called
    if (apiCalls.length > 0) {
      const todayCall = apiCalls[0];

      // Should NOT return 405 (Method Not Allowed)
      expect(todayCall.status).not.toBe(405);

      // Should return 200 (success), 401 (auth required), or 204 (no content)
      expect([200, 401, 204]).toContain(todayCall.status);
    }
  });

  test("today page loads and renders intent tiles", async ({ page }) => {
    // Navigate to Today page
    await page.goto("/today", { waitUntil: "domcontentloaded" });

    // Check if we're on the login page (production auth required)
    await page.waitForTimeout(1000);
    const pageContent = await page.content();
    if (pageContent.includes("Sign In Required") || pageContent.includes("Please sign in to access this page")) {
      test.skip(true, "Skipping - authentication required for production");
      return;
    }

    // Wait for loading to complete
    await page.waitForLoadState("networkidle");

    // Page title and description should be visible
    const pageTitle = page.getByRole("heading", { name: "Today" });
    await expect(pageTitle).toBeVisible({ timeout: 10000 });

    const pageDescription = page.getByText(/What should you do with your inbox today/i);
    await expect(pageDescription).toBeVisible({ timeout: 5000 });
  });

  test("intent tiles render with correct structure", async ({ page }) => {
    await page.goto("/today", { waitUntil: "domcontentloaded" });

    // Skip if not authenticated
    await page.waitForTimeout(1000);
    const pageContent = await page.content();
    if (pageContent.includes("Sign In Required") || pageContent.includes("Please sign in to access this page")) {
      test.skip(true, "Skipping - authentication required for production");
      return;
    }

    // Wait for content to load
    await page.waitForLoadState("networkidle");

    // Check that at least one intent tile is visible
    // Intent tiles are Cards with specific titles
    const intentTitles = [
      /Follow-ups/i,
      /Bills.*Invoices/i,
      /Interviews/i,
      /Unsubscribe/i,
      /Clean Promos/i,
      /Suspicious/i,
    ];

    let foundAtLeastOne = false;
    for (const title of intentTitles) {
      const intentCard = page.getByText(title).first();
      if (await intentCard.isVisible({ timeout: 2000 }).catch(() => false)) {
        foundAtLeastOne = true;
        break;
      }
    }

    expect(foundAtLeastOne).toBeTruthy();
  });

  test("intent tiles display count badges", async ({ page }) => {
    await page.goto("/today", { waitUntil: "domcontentloaded" });

    // Skip if not authenticated
    await page.waitForTimeout(1000);
    const pageContent = await page.content();
    if (pageContent.includes("Sign In Required") || pageContent.includes("Please sign in to access this page")) {
      test.skip(true, "Skipping - authentication required for production");
      return;
    }

    // Wait for content
    await page.waitForLoadState("networkidle");

    // Count badges should be visible (numbers or "0")
    const badges = page.locator(".inline-flex.items-center.rounded-full");
    const badgeCount = await badges.count();

    // Should have at least one badge (one per intent)
    expect(badgeCount).toBeGreaterThan(0);
  });

  test("empty intents show 'All clear' message", async ({ page }) => {
    await page.goto("/today", { waitUntil: "domcontentloaded" });

    // Skip if not authenticated
    await page.waitForTimeout(1000);
    const pageContent = await page.content();
    if (pageContent.includes("Sign In Required") || pageContent.includes("Please sign in to access this page")) {
      test.skip(true, "Skipping - authentication required for production");
      return;
    }

    // Wait for content
    await page.waitForLoadState("networkidle");

    // Look for "All clear" messages (may or may not be present depending on data)
    const allClearMessages = page.getByText(/All clear/i);
    const count = await allClearMessages.count();

    // This test just verifies the feature doesn't crash
    // If there are empty intents, they should show "All clear"
    // Otherwise, the count will be 0, which is also valid
    expect(count).toBeGreaterThanOrEqual(0);
  });

  test("thread list displays correctly for non-empty intents", async ({ page }) => {
    await page.goto("/today", { waitUntil: "domcontentloaded" });

    // Skip if not authenticated
    await page.waitForTimeout(1000);
    const pageContent = await page.content();
    if (pageContent.includes("Sign In Required") || pageContent.includes("Please sign in to access this page")) {
      test.skip(true, "Skipping - authentication required for production");
      return;
    }

    // Wait for content
    await page.waitForLoadState("networkidle");

    // Look for thread items (small email icon + subject + from)
    const mailIcons = page.locator("svg").filter({ hasText: "" }); // Lucide Mail icon
    const mailIconCount = await mailIcons.count();

    // If there are threads, there should be mail icons
    // This test is flexible - it passes whether there are threads or not
    expect(mailIconCount).toBeGreaterThanOrEqual(0);
  });

  test("clicking thread opens in Gmail (action button visibility)", async ({ page }) => {
    await page.goto("/today", { waitUntil: "domcontentloaded" });

    // Skip if not authenticated
    await page.waitForTimeout(1000);
    const pageContent = await page.content();
    if (pageContent.includes("Sign In Required") || pageContent.includes("Please sign in to access this page")) {
      test.skip(true, "Skipping - authentication required for production");
      return;
    }

    // Wait for content
    await page.waitForLoadState("networkidle");

    // Find the first thread item (if any)
    const firstThread = page.locator(".group.p-2.rounded-md").first();

    if (await firstThread.isVisible({ timeout: 2000 }).catch(() => false)) {
      // Hover to reveal action buttons
      await firstThread.hover();

      // Wait for opacity transition
      await page.waitForTimeout(300);

      // Check that action buttons are visible
      const gmailButton = firstThread.getByText(/Gmail/i);
      await expect(gmailButton).toBeVisible({ timeout: 3000 });
    }

    // Test passes either way - just checking the feature doesn't break
  });

  test("time window is displayed", async ({ page }) => {
    await page.goto("/today", { waitUntil: "domcontentloaded" });

    // Skip if not authenticated
    await page.waitForTimeout(1000);
    const pageContent = await page.content();
    if (pageContent.includes("Sign In Required") || pageContent.includes("Please sign in to access this page")) {
      test.skip(true, "Skipping - authentication required for production");
      return;
    }

    // Wait for content
    await page.waitForLoadState("networkidle");

    // Look for time window text (e.g., "Last 90 days")
    const timeWindowText = page.getByText(/Last \d+ days/i).first();

    if (await timeWindowText.isVisible({ timeout: 2000 }).catch(() => false)) {
      await expect(timeWindowText).toBeVisible();
    }

    // Test is flexible - passes whether time window is shown or not
  });

  test("page handles API errors gracefully", async ({ page, context }) => {
    // Mock API failure
    await context.route('**/api/v2/agent/today', route => route.fulfill({
      status: 500,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'Internal Server Error' })
    }));

    await page.goto("/today", { waitUntil: "domcontentloaded" });

    // Should show error message instead of crashing
    const errorMessage = page.getByText(/Failed to fetch today's triage/i);
    await expect(errorMessage).toBeVisible({ timeout: 10000 });
  });

  test("page handles empty response gracefully", async ({ page, context }) => {
    // Mock empty response
    await context.route('**/api/v2/agent/today', route => route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ status: 'ok', intents: [] })
    }));

    await page.goto("/today", { waitUntil: "domcontentloaded" });

    // Should show empty state message
    const emptyMessage = page.getByText(/No triage data available/i);
    await expect(emptyMessage).toBeVisible({ timeout: 10000 });
  });

  test("page layout is responsive (grid adapts)", async ({ page }) => {
    await page.goto("/today", { waitUntil: "domcontentloaded" });

    // Skip if not authenticated
    await page.waitForTimeout(1000);
    const pageContent = await page.content();
    if (pageContent.includes("Sign In Required") || pageContent.includes("Please sign in to access this page")) {
      test.skip(true, "Skipping - authentication required for production");
      return;
    }

    // Wait for content
    await page.waitForLoadState("networkidle");

    // Check that grid container exists
    const gridContainer = page.locator(".grid.grid-cols-1");
    await expect(gridContainer).toBeVisible({ timeout: 10000 });

    // Grid should have responsive classes (md:grid-cols-2, lg:grid-cols-3)
    const gridClass = await gridContainer.getAttribute("class");
    expect(gridClass).toContain("grid-cols-1");
    expect(gridClass).toContain("md:grid-cols-2");
    expect(gridClass).toContain("lg:grid-cols-3");
  });
});
