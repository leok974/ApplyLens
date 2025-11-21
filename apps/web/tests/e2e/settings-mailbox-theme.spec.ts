/**
 * Mailbox Theme Switcher E2E Test
 *
 * Verifies the theme switcher in Settings persists and applies to /chat
 *
 * @tags @settings @mailbox-theme @authRequired @prodSafe
 */

import { test, expect } from "@playwright/test";

test.describe("@settings @mailbox-theme @authRequired @prodSafe Mailbox Theme Switcher", () => {
  test("can switch themes in Settings and persist to /chat", async ({
    page,
  }) => {
    // 1. Visit Settings page
    await page.goto("/settings");
    await page.waitForLoadState("networkidle");

    // 2. Verify theme settings panel exists
    const themePanel = page.getByTestId("mailbox-theme-settings");
    await expect(themePanel).toBeVisible();

    // 3. Verify all three theme options are present
    await expect(
      page.getByTestId("mailbox-theme-option-classic")
    ).toBeVisible();
    await expect(
      page.getByTestId("mailbox-theme-option-bananaPro")
    ).toBeVisible();
    await expect(
      page.getByTestId("mailbox-theme-option-deepSpace")
    ).toBeVisible();

    // 4. Select Banana Pro theme
    const bananaProOption = page.getByTestId("mailbox-theme-option-bananaPro");
    await bananaProOption.click();

    // 5. Verify the radio button is selected
    const bananaProRadio = page.locator(
      'input[type="radio"][value="bananaPro"]'
    );
    await expect(bananaProRadio).toBeChecked();

    // 6. Navigate to /chat
    await page.goto("/chat");
    await page.waitForLoadState("networkidle");

    // 7. Verify data-mailbox-theme attribute reflects the selection
    const chatContainer = page.locator('[data-mailbox-theme="bananaPro"]');
    await expect(chatContainer).toBeVisible();

    // 8. Switch to Deep Space theme
    await page.goto("/settings");
    await page.waitForLoadState("networkidle");

    const deepSpaceOption = page.getByTestId("mailbox-theme-option-deepSpace");
    await deepSpaceOption.click();

    const deepSpaceRadio = page.locator(
      'input[type="radio"][value="deepSpace"]'
    );
    await expect(deepSpaceRadio).toBeChecked();

    // 9. Navigate to /chat again
    await page.goto("/chat");
    await page.waitForLoadState("networkidle");

    // 10. Verify data-mailbox-theme attribute changed
    const chatContainerDeepSpace = page.locator(
      '[data-mailbox-theme="deepSpace"]'
    );
    await expect(chatContainerDeepSpace).toBeVisible();

    // 11. Refresh the page to test persistence
    await page.reload();
    await page.waitForLoadState("networkidle");

    // 12. Verify theme persisted after refresh
    const chatContainerAfterReload = page.locator(
      '[data-mailbox-theme="deepSpace"]'
    );
    await expect(chatContainerAfterReload).toBeVisible();

    // 13. Reset to Classic theme for other tests
    await page.goto("/settings");
    await page.waitForLoadState("networkidle");

    const classicOption = page.getByTestId("mailbox-theme-option-classic");
    await classicOption.click();

    await expect(
      page.locator('input[type="radio"][value="classic"]')
    ).toBeChecked();
  });

  test("Active badge shows on selected theme", async ({ page }) => {
    // Visit Settings
    await page.goto("/settings");
    await page.waitForLoadState("networkidle");

    // Classic should be default (or whatever was selected last)
    const themePanel = page.getByTestId("mailbox-theme-settings");
    await expect(themePanel).toBeVisible();

    // Select Banana Pro
    await page.getByTestId("mailbox-theme-option-bananaPro").click();

    // Verify "Active" badge appears in Banana Pro option
    const bananaProCard = page.getByTestId("mailbox-theme-option-bananaPro");
    await expect(bananaProCard.getByText("Active")).toBeVisible();

    // Verify no "Active" badge in other options
    const classicCard = page.getByTestId("mailbox-theme-option-classic");
    await expect(classicCard.getByText("Active")).not.toBeVisible();
  });
});
