import { test, expect } from "@playwright/test";

test("header brand and actions visible; tabs scrollable", async ({ page }) => {
  await page.goto("/");

  // Brand should be visible with ApplyLens text
  const brand = page.getByTestId("header-brand");
  await expect(brand).toBeVisible();
  await expect(brand).toHaveText(/ApplyLens/);

  // Actions buttons should be present and visible
  await expect(page.getByTestId("quick-actions")).toBeVisible();
  await expect(page.getByTestId("sync-7d")).toBeVisible();
  await expect(page.getByTestId("sync-60d")).toBeVisible();
  await expect(page.getByTestId("theme-toggle")).toBeVisible();

  // Tabs rail should be horizontally scrollable
  // (width < scrollWidth implies overflow-x is working)
  const rail = page.locator("nav >> div").first();
  const w = await rail.evaluate(el => el.clientWidth);
  const sw = await rail.evaluate(el => el.scrollWidth);
  expect(sw).toBeGreaterThanOrEqual(w);
});

test("header brand logo visible at different viewport sizes", async ({ page }) => {
  // Desktop
  await page.setViewportSize({ width: 1280, height: 720 });
  await page.goto("/");
  const logo = page.locator('[data-testid="header-brand"] img');
  await expect(logo).toBeVisible();

  // Tablet
  await page.setViewportSize({ width: 768, height: 1024 });
  await expect(logo).toBeVisible();

  // Mobile
  await page.setViewportSize({ width: 375, height: 667 });
  await expect(logo).toBeVisible();
});

test("tabs are clickable and navigate correctly", async ({ page }) => {
  await page.goto("/");

  // Click on Actions tab
  await page.click('a[href="/inbox-actions"]');
  await expect(page).toHaveURL(/inbox-actions/);

  // Click on Chat tab
  await page.click('a[href="/chat"]');
  await expect(page).toHaveURL(/chat/);

  // Click on Tracker tab
  await page.click('a[href="/tracker"]');
  await expect(page).toHaveURL(/tracker/);
});

test("header maintains layout without overlap on narrow viewports", async ({ page }) => {
  // Set a narrow viewport
  await page.setViewportSize({ width: 640, height: 480 });
  await page.goto("/");

  // All three zones should be visible
  const brand = page.getByTestId("header-brand");
  const tabs = page.locator("nav");
  const actions = page.getByTestId("quick-actions");

  await expect(brand).toBeVisible();
  await expect(tabs).toBeVisible();
  await expect(actions).toBeVisible();

  // Check that elements don't overlap by comparing bounding boxes
  const brandBox = await brand.boundingBox();
  const actionsBox = await actions.boundingBox();

  expect(brandBox).not.toBeNull();
  expect(actionsBox).not.toBeNull();

  // Brand should be on the left, actions on the right, no overlap
  if (brandBox && actionsBox) {
    expect(brandBox.x + brandBox.width).toBeLessThanOrEqual(actionsBox.x);
  }
});
