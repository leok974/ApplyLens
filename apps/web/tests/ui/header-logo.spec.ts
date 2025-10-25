import { test, expect } from "@playwright/test";
import { installProdReadOnlyGuard } from "../utils/prodGuard";

test.describe("Header and Inbox Logo Layout", () => {
  test("@prodSafe header logo is large and inbox hero logo removed", async ({ page }) => {
    await installProdReadOnlyGuard(page);

    // Set desktop viewport to ensure we're testing the larger logo size
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.goto("/inbox");

    // Wait for page to load
    await page.waitForLoadState("networkidle");

    // Allow entrance animation to complete
    await page.waitForTimeout(120);

    // Check header brand is visible
    const brand = page.getByTestId("header-brand");
    await expect(brand).toBeVisible();

    // Header logo should be large (>= 48px on desktop)
    const img = brand.locator("img").first();
    await expect(img).toBeVisible();

    const box = await img.boundingBox();
    expect(box).not.toBeNull();
    // Header logo should be at least 48px tall
    expect(box?.height ?? 0).toBeGreaterThanOrEqual(48);

    // Verify logo is the ApplyLens PNG
    const src = await img.getAttribute("src");
    expect(src).toMatch(/applylens|ApplyLensLogo/i);

    // Hero logo block should no longer be present
    // Check for various possible selectors that might have been used
    const heroLogoCount = await page.locator('[data-testid="inbox-hero-logo"]').count();
    // Inbox hero logo with data-testid should not exist
    expect(heroLogoCount).toBe(0);

    // Check for the old grid layout with logo column
    const logoColumnCount = await page.locator('.md\\:col-span-2:has(img[src*="ApplyLensLogo"])').count();
    // Large logo column in inbox grid should not exist
    expect(logoColumnCount).toBe(0);

    // Verify inbox title is present (proving page loaded correctly)
    const inboxTitle = page.locator('h1:has-text("Gmail Inbox")');
    await expect(inboxTitle).toBeVisible();
  });

  test("@prodSafe header logo scales appropriately on mobile", async ({ page }) => {
    await installProdReadOnlyGuard(page);
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto("/inbox");

    await page.waitForLoadState("networkidle");

    // Header logo should still be visible but smaller
    const brand = page.getByTestId("header-brand");
    await expect(brand).toBeVisible();

    const img = brand.locator("img").first();
    await expect(img).toBeVisible();

    const box = await img.boundingBox();
    expect(box).not.toBeNull();

    // On mobile, logo should be h-12 (48px) as per h-12 class
    expect(box?.height ?? 0).toBeGreaterThanOrEqual(40);
    expect(box?.height ?? 0).toBeLessThanOrEqual(56);
  });

  test("@prodSafe header has increased height to accommodate larger logo", async ({ page }) => {
    await installProdReadOnlyGuard(page);
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.goto("/inbox");

    await page.waitForLoadState("networkidle");

    // Header should have h-16 class (64px)
    const header = page.locator('header').first();
    const headerInner = header.locator('div.flex').first();

    const box = await headerInner.boundingBox();
    expect(box).not.toBeNull();
    // Header should be at least 60px tall (h-16 = 64px)
    expect(box?.height ?? 0).toBeGreaterThanOrEqual(60);
  });

  test("@prodSafe wordmark text is larger and properly spaced", async ({ page }) => {
    await installProdReadOnlyGuard(page);
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.goto("/inbox");

    await page.waitForLoadState("networkidle");

    const brand = page.getByTestId("header-brand");
    const wordmark = brand.locator('span:has-text("ApplyLens")');

    await expect(wordmark).toBeVisible();

    // Check font size (should be text-xl or text-2xl on desktop)
    const fontSize = await wordmark.evaluate((el) => {
      return window.getComputedStyle(el).fontSize;
    });

    const fontSizeNum = parseFloat(fontSize);
    // Wordmark should be at least 18px (text-xl)
    expect(fontSizeNum).toBeGreaterThanOrEqual(18);
  });

  test("@prodSafe inbox page layout is single column without hero logo", async ({ page }) => {
    await installProdReadOnlyGuard(page);
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.goto("/inbox");

    await page.waitForLoadState("networkidle");

    // Should not have the 12-column grid with separate logo column
    const gridContainer = page.locator('.grid.grid-cols-12');
    // Old 12-column grid layout should be removed
    await expect(gridContainer).toHaveCount(0);

    // Inbox title should be in a simple flex layout
    const titleContainer = page.locator('h1:has-text("Gmail Inbox")').locator('..');
    const display = await titleContainer.evaluate((el) => {
      return window.getComputedStyle(el).display;
    });

    expect(['flex', 'block']).toContain(display);
  });

  test("@prodSafe no gradient halo effect remnants from old hero logo", async ({ page }) => {
    await installProdReadOnlyGuard(page);
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.goto("/inbox");

    await page.waitForLoadState("networkidle");

    // The old hero had a gradient halo with blur
    const haloElements = page.locator('.bg-gradient-to-br.from-primary\\/10.blur-xl');
    // Gradient halo effect should be removed
    await expect(haloElements).toHaveCount(0);
  });
});

test.describe("Header Brand Consistency", () => {
  test("@prodSafe header logo appears consistently across all pages", async ({ page }) => {
    await installProdReadOnlyGuard(page);
    const pages = ["/inbox", "/search", "/chat", "/tracker", "/settings"];

    for (const path of pages) {
      await page.goto(path);
      await page.waitForLoadState("networkidle");

      const brand = page.getByTestId("header-brand");
      await expect(brand).toBeVisible();

      const img = brand.locator("img").first();
      await expect(img).toBeVisible();

      const box = await img.boundingBox();
      // Header logo should be large on all pages
      expect(box?.height ?? 0).toBeGreaterThanOrEqual(48);
    }
  });
});
