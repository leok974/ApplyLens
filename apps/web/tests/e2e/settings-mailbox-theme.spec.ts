/**
 * Mailbox Theme Switcher E2E Test
 *
 * Verifies the theme switcher in Settings persists and applies to /chat
 *
 * @tags @settings @mailbox-theme @authRequired @prodSafe
 */

import { test, expect } from "@playwright/test";

const baseUrl = process.env.E2E_BASE_URL ?? "http://127.0.0.1:5173";

test.describe("@settings @mailbox-theme @authRequired @prodSafe Mailbox Theme Switcher", () => {
  test("applies Banana Pro theme from Settings to Chat", async ({ page }) => {
    // Go to Settings (auth should be handled by storageState/E2E_AUTH_STATE)
    await page.goto(`${baseUrl}/settings`);
    await page.waitForLoadState("networkidle");

    // Click Banana Pro theme card
    const bananaOption = page.getByTestId("mailbox-theme-option-bananaPro");
    await bananaOption.click();

    // Wait for it to be selected (Radix sets data-state="checked" on RadioGroupItem)
    const bananaRadio = page.locator('input[type="radio"][value="bananaPro"]');
    await expect(bananaRadio).toBeChecked();

    // Small delay to ensure localStorage is written
    await page.waitForTimeout(500);

    // Navigate to chat and assert theme is applied
    await page.goto(`${baseUrl}/chat`);
    await page.waitForLoadState("networkidle");

    // Wait for chat to be fully loaded
    await page.waitForSelector('[data-testid="chat-root"]', { timeout: 10000 });

    // 1) Theme id should be reflected on chat-root
    const chatRoot = page.getByTestId("chat-root");
    await expect(chatRoot).toHaveAttribute("data-mailbox-theme", "bananaPro");

    // 2) Chat shell should be visible
    const chatShell = page.getByTestId("chat-shell");
    await expect(chatShell).toBeVisible();
  });

  test("applies Deep Space theme from Settings to Chat", async ({ page }) => {
    await page.goto(`${baseUrl}/settings`);
    await page.waitForLoadState("networkidle");

    const deepSpaceOption = page.getByTestId("mailbox-theme-option-deepSpace");
    await deepSpaceOption.click();

    const deepSpaceRadio = page.locator('input[type="radio"][value="deepSpace"]');
    await expect(deepSpaceRadio).toBeChecked();

    // Small delay to ensure localStorage is written
    await page.waitForTimeout(500);

    await page.goto(`${baseUrl}/chat`);
    await page.waitForLoadState("networkidle");

    // Wait for chat to be fully loaded
    await page.waitForSelector('[data-testid="chat-root"]', { timeout: 10000 });

    const chatRoot = page.getByTestId("chat-root");
    await expect(chatRoot).toHaveAttribute("data-mailbox-theme", "deepSpace");

    const chatShell = page.getByTestId("chat-shell");
    await expect(chatShell).toBeVisible();
  });

  test("theme persists after page reload", async ({ page }) => {
    // Set to Banana Pro
    await page.goto(`${baseUrl}/settings`);
    await page.waitForLoadState("networkidle");

    await page.getByTestId("mailbox-theme-option-bananaPro").click();

    const bananaRadio = page.locator('input[type="radio"][value="bananaPro"]');
    await expect(bananaRadio).toBeChecked();

    // Small delay to ensure localStorage is written
    await page.waitForTimeout(500);

    // Navigate to chat
    await page.goto(`${baseUrl}/chat`);
    await page.waitForLoadState("networkidle");

    // Wait for chat to be fully loaded
    await page.waitForSelector('[data-testid="chat-root"]', { timeout: 10000 });

    // Reload the page
    await page.reload();
    await page.waitForLoadState("networkidle");

    // Wait for chat to be fully loaded after reload
    await page.waitForSelector('[data-testid="chat-root"]', { timeout: 10000 });

    // Theme should still be Banana Pro (from localStorage)
    const chatRoot = page.getByTestId("chat-root");
    await expect(chatRoot).toHaveAttribute("data-mailbox-theme", "bananaPro");
  });

  test("Active badge shows on selected theme", async ({ page }) => {
    await page.goto(`${baseUrl}/settings`);
    await page.waitForLoadState("networkidle");

    // Select Banana Pro
    await page.getByTestId("mailbox-theme-option-bananaPro").click();

    // Verify "Active" badge appears in Banana Pro option
    const bananaProCard = page.getByTestId("mailbox-theme-option-bananaPro");
    await expect(bananaProCard.getByText("Active")).toBeVisible();

    // Verify no "Active" badge in Classic option
    const classicCard = page.getByTestId("mailbox-theme-option-classic");
    await expect(classicCard.getByText("Active")).not.toBeVisible();
  });

  test("persists theme selection to localStorage", async ({ page }) => {
    // Go to Settings
    await page.goto(`${baseUrl}/settings`);
    await page.waitForLoadState("networkidle");

    // Clear any existing theme key so we start clean
    await page.evaluate(() => {
      localStorage.removeItem('applylens:mailbox-theme');
    });

    // Click Banana Pro theme card
    const bananaOption = page.getByTestId('mailbox-theme-option-bananaPro');
    await bananaOption.click();

    // Ensure RadioGroup has actually selected it
    await expect(bananaOption).toHaveAttribute('data-state', 'checked');

    // Read localStorage from the browser context
    const storedTheme = await page.evaluate(() => {
      return localStorage.getItem('applylens:mailbox-theme');
    });

    expect(storedTheme).toBe('bananaPro');
  });
});
