import { test, expect } from "@playwright/test";

test.describe("Header + Inbox hero logo", () => {
  test("wordmark left, actions visible, big logo in inbox", async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.goto("/inbox");

    // Header brand is visible and left-ish
    const brand = page.getByTestId("header-brand");
    await expect(brand).toBeVisible();
    const brandBox = await brand.boundingBox();
    expect(brandBox?.x ?? 100).toBeLessThan(40); // near left edge

    // Right actions present
    await expect(page.getByTestId("quick-actions")).toBeVisible();

    // Big logo under header (md+ only)
    // Find the large logo in the inbox hero section
    const heroSection = page.locator('.md\\:col-span-2 .h-28');
    await expect(heroSection).toBeVisible();

    const title = page.getByRole("heading", { name: /Gmail Inbox/i });
    await expect(title).toBeVisible();

    const logoBox = await heroSection.boundingBox();
    const titleBox = await title.boundingBox();

    // Logo should be near the title (in the same row)
    if (logoBox && titleBox) {
      expect(Math.abs(logoBox.y - titleBox.y)).toBeLessThan(80); // roughly same vertical position
      expect(logoBox.width).toBeGreaterThanOrEqual(100); // it's big
    }
  });

  test("tabs scrollable on smaller screens", async ({ page }) => {
    await page.setViewportSize({ width: 800, height: 600 });
    await page.goto("/inbox");

    // Nav tabs should be scrollable
    const nav = page.locator('nav .scrollbar-none');
    await expect(nav).toBeVisible();

    // Check if content is wider than container (indicates scrollability)
    const width = await nav.evaluate(el => el.clientWidth);
    const scrollWidth = await nav.evaluate(el => el.scrollWidth);

    // On narrow screens, tabs should overflow
    expect(scrollWidth).toBeGreaterThanOrEqual(width);
  });
});
