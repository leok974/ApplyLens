import { test, expect } from "@playwright/test";
import { API } from "./utils/env";

test.describe("Pipeline sync buttons", () => {
  test("runs Gmail→Label→Profile with toasts", async ({ page }) => {
    await page.goto("/");

    // ensure API is reachable (skip test gracefully if not)
    try {
      const pong = await page.request.get(`${API}/profile/summary?user_email=leoklemet.pa@gmail.com`);
      if (!pong.ok()) {
        test.skip(true, "API not reachable—skipping live pipeline test.");
      }
    } catch {
      test.skip(true, "API not reachable—skipping live pipeline test.");
    }

    const sync7 = page.getByTestId("btn-sync-7").or(page.getByRole("button", { name: /sync 7/i }));
    await sync7.click();

    // Wait for toasts to appear in sequence
    await expect(page.getByText(/syncing last 7 days/i)).toBeVisible({ timeout: 15000 });
    await expect(page.getByText(/applying smart labels/i)).toBeVisible({ timeout: 30000 });
    await expect(page.getByText(/updating your profile/i)).toBeVisible({ timeout: 30000 });
    await expect(page.getByText(/sync complete/i)).toBeVisible({ timeout: 30000 });
  });

  test("runs 60-day sync with toasts", async ({ page }) => {
    await page.goto("/");

    // ensure API is reachable
    try {
      const pong = await page.request.get(`${API}/profile/summary?user_email=leoklemet.pa@gmail.com`);
      if (!pong.ok()) {
        test.skip(true, "API not reachable—skipping live pipeline test.");
      }
    } catch {
      test.skip(true, "API not reachable—skipping live pipeline test.");
    }

    const sync60 = page.getByTestId("btn-sync-60").or(page.getByRole("button", { name: /sync 60/i }));
    await sync60.click();

    // Wait for completion toast
    await expect(page.getByText(/syncing last 60 days/i)).toBeVisible({ timeout: 15000 });
    await expect(page.getByText(/sync complete/i)).toBeVisible({ timeout: 60000 });
  });
});
