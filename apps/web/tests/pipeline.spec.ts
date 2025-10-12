import { test, expect } from "@playwright/test";
import { API } from "./utils/env";
import { waitForApp } from "./utils/waitApp";

test.describe("Pipeline sync buttons", () => {
  test("runs Gmail→Label→Profile with toasts", async ({ page }) => {
    const ping = await page.request.get(`${API}/profile/summary?user_email=leoklemet.pa@gmail.com`);
    test.skip(!ping.ok(), "API not reachable—skipping live pipeline test.");

    await page.goto("/", { waitUntil: "domcontentloaded" });
    await waitForApp(page);
    
    const sync7 = page.getByTestId("btn-sync-7").or(page.getByRole("button", { name: /sync 7/i }));
    await sync7.click();

    await expect(page.getByText(/syncing last 7 days/i)).toBeVisible({ timeout: 15000 });
    await expect(page.getByText(/applying smart labels/i)).toBeVisible({ timeout: 30000 });
    await expect(page.getByText(/updating your profile/i)).toBeVisible({ timeout: 30000 });
    await expect(page.getByText(/sync complete/i)).toBeVisible({ timeout: 30000 });
  });

  test("runs 60-day sync with toasts", async ({ page }) => {
    const ping = await page.request.get(`${API}/profile/summary?user_email=leoklemet.pa@gmail.com`);
    test.skip(!ping.ok(), "API not reachable—skipping live pipeline test.");

    await page.goto("/", { waitUntil: "domcontentloaded" });
    await waitForApp(page);
    
    const sync60 = page.getByTestId("btn-sync-60").or(page.getByRole("button", { name: /sync 60/i }));
    await sync60.click();

    await expect(page.getByText(/syncing last 60 days/i)).toBeVisible({ timeout: 15000 });
    await expect(page.getByText(/sync complete/i)).toBeVisible({ timeout: 60000 });
  });
});
