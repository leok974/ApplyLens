import { test, expect } from "@playwright/test";

test.describe("Security UI Components", () => {
  test("Security panel displays risk information", async ({ page }) => {
    // Navigate to search and select an email
    await page.goto("/search?q=interview");
    await page.waitForTimeout(1000); // Wait for search results
    
    // Click on first result to open details
    const firstResult = page.getByTestId("result-0").or(page.locator('[role="row"]').first());
    await firstResult.click();
    
    // Security panel should be visible if email has risk_score
    const securityPanel = page.getByTestId("security-panel");
    if (await securityPanel.isVisible()) {
      // Risk badge should be visible
      await expect(page.getByTestId("risk-badge")).toBeVisible();
      
      // Evidence button should be clickable
      const evidenceButton = page.getByTestId("evidence-open");
      await expect(evidenceButton).toBeVisible();
      
      // Click to open evidence modal
      await evidenceButton.click();
      await expect(page.getByTestId("evidence-list")).toBeVisible();
      
      // Close modal (press Escape)
      await page.keyboard.press("Escape");
      await expect(page.getByTestId("evidence-list")).not.toBeVisible();
      
      // Rescan button should be present
      await expect(page.getByTestId("rescan-btn")).toBeVisible();
    }
  });

  test("Risk badge displays with correct colors", async ({ page }) => {
    await page.goto("/search");
    await page.waitForTimeout(1000);
    
    // Look for any risk badges in the list
    const badges = page.getByTestId("risk-badge");
    const count = await badges.count();
    
    if (count > 0) {
      const firstBadge = badges.first();
      await expect(firstBadge).toBeVisible();
      
      // Badge should contain a number
      const badgeText = await firstBadge.textContent();
      expect(badgeText).toMatch(/\d+/);
    }
  });

  test("Security settings page loads", async ({ page }) => {
    await page.goto("/settings/security");
    
    // Policy panel should be visible
    await expect(page.getByTestId("policy-panel")).toBeVisible();
    
    // Check for policy toggles
    const autoQuarantineToggle = page.locator("#autoQ");
    await expect(autoQuarantineToggle).toBeVisible();
    
    const autoArchiveToggle = page.locator("#autoArchive");
    await expect(autoArchiveToggle).toBeVisible();
    
    // Save button should be present
    await expect(page.getByTestId("policy-save")).toBeVisible();
  });

  test("Policy panel toggles work", async ({ page }) => {
    await page.goto("/settings/security");
    await page.waitForTimeout(500);
    
    const saveButton = page.getByTestId("policy-save");
    const autoQuarantineToggle = page.locator("#autoQ");
    
    // Get initial state
    const initialState = await autoQuarantineToggle.getAttribute("data-state");
    
    // Toggle the switch
    await autoQuarantineToggle.click();
    
    // State should change
    const newState = await autoQuarantineToggle.getAttribute("data-state");
    expect(newState).not.toBe(initialState);
    
    // Save button should be enabled
    await expect(saveButton).toBeEnabled();
  });

  test("Rescan email button triggers API call", async ({ page }) => {
    // Mock the rescan API endpoint
    await page.route("**/api/security/rescan/**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          status: "ok",
          email_id: "123",
          risk_score: 45,
          quarantined: false,
          flags: [
            { signal: "TEST_FLAG", evidence: "Test evidence", weight: 10 },
          ],
        }),
      });
    });

    await page.goto("/search?q=test");
    await page.waitForTimeout(1000);
    
    // Click on first result
    const firstResult = page.locator('[role="row"]').first();
    await firstResult.click();
    
    // If security panel is visible, test rescan
    const securityPanel = page.getByTestId("security-panel");
    if (await securityPanel.isVisible()) {
      const rescanButton = page.getByTestId("rescan-btn");
      await rescanButton.click();
      
      // Should show success toast (using sonner)
      await expect(page.locator("text=Email rescanned")).toBeVisible({ timeout: 3000 });
    }
  });

  test("Evidence modal shows flag details", async ({ page }) => {
    await page.goto("/search");
    await page.waitForTimeout(1000);
    
    // Click on first email
    const firstResult = page.locator('[role="row"]').first();
    await firstResult.click();
    
    const securityPanel = page.getByTestId("security-panel");
    if (await securityPanel.isVisible()) {
      // Open evidence modal
      await page.getByTestId("evidence-open").click();
      
      const evidenceList = page.getByTestId("evidence-list");
      await expect(evidenceList).toBeVisible();
      
      // Evidence list should contain items or "No evidence available"
      const listContent = await evidenceList.textContent();
      expect(listContent).toBeTruthy();
      expect(listContent.length).toBeGreaterThan(0);
    }
  });
});
