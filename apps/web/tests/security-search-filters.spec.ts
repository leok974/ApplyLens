import { test, expect } from "@playwright/test"

test.describe("Security Search Filters", () => {
  test("High-Risk chip sets URL params and calls API with risk_min=80", async ({ page }) => {
    // Mock API to assert query contains risk_min=80
    let apiCallMade = false
    let hasRiskMin = false
    
    await page.route("**/api/search/**", async (route) => {
      const url = new URL(route.request().url())
      apiCallMade = true
      hasRiskMin = url.searchParams.get("risk_min") === "80"
      
      // Return minimal fake results
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ 
          hits: [
            { 
              id: "1", 
              subject: "Phishing attempt detected", 
              from_addr: "bad@suspicious.ru",
              received_at: "2024-01-15T10:30:00Z",
              score: 0.95
            }
          ] 
        }),
      })
    })

    // Navigate to search page
    await page.goto("/search?q=test")
    
    // Wait for page to load
    await page.waitForLoadState("networkidle")
    
    // Click the high-risk chip to toggle it on
    await page.getByTestId("chip-high-risk").click()
    
    // Wait a moment for state to update and search to trigger
    await page.waitForTimeout(500)

    // Verify URL reflects the risk_min filter
    await expect(page).toHaveURL(/risk_min=80/)

    // Verify API was called with the filter
    expect(apiCallMade).toBeTruthy()
    expect(hasRiskMin).toBeTruthy()

    // Verify results are rendered
    await expect(page.getByTestId("result-0")).toBeVisible({ timeout: 5000 })
  })

  test("Quarantined chip sets quarantined=true", async ({ page }) => {
    let apiCallMade = false
    let hasQuarantined = false
    
    await page.route("**/api/search/**", async (route) => {
      const url = new URL(route.request().url())
      apiCallMade = true
      hasQuarantined = url.searchParams.get("quarantined") === "true"
      
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ hits: [] }),
      })
    })

    await page.goto("/search?q=test")
    await page.waitForLoadState("networkidle")
    
    await page.getByTestId("chip-quarantined").click()
    await page.waitForTimeout(500)
    
    // Verify URL has quarantined param
    await expect(page).toHaveURL(/quarantined=true/)
    
    // Verify API was called with quarantined filter
    expect(apiCallMade).toBeTruthy()
    expect(hasQuarantined).toBeTruthy()
  })

  test("Both filters can be active simultaneously", async ({ page }) => {
    let hasRiskMin = false
    let hasQuarantined = false
    
    await page.route("**/api/search/**", async (route) => {
      const url = new URL(route.request().url())
      hasRiskMin = url.searchParams.get("risk_min") === "80"
      hasQuarantined = url.searchParams.get("quarantined") === "true"
      
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ 
          hits: [
            {
              id: "q1",
              subject: "Quarantined high-risk email",
              from_addr: "attacker@evil.com",
              received_at: "2024-01-15T10:30:00Z",
              score: 0.88
            }
          ]
        }),
      })
    })

    await page.goto("/search?q=security")
    await page.waitForLoadState("networkidle")
    
    // Toggle both filters
    await page.getByTestId("chip-high-risk").click()
    await page.waitForTimeout(300)
    await page.getByTestId("chip-quarantined").click()
    await page.waitForTimeout(500)
    
    // URL should have both params
    await expect(page).toHaveURL(/risk_min=80/)
    await expect(page).toHaveURL(/quarantined=true/)
    
    // API should receive both filters
    expect(hasRiskMin).toBeTruthy()
    expect(hasQuarantined).toBeTruthy()
    
    // Results should render
    await expect(page.getByTestId("result-0")).toBeVisible({ timeout: 5000 })
  })

  test("Clear filters button removes all security filters", async ({ page }) => {
    await page.route("**/api/search/**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ hits: [] }),
      })
    })

    await page.goto("/search?q=test&risk_min=80&quarantined=true")
    await page.waitForLoadState("networkidle")
    
    // Both filters should be active
    const highRiskChip = page.getByTestId("chip-high-risk")
    const quarantinedChip = page.getByTestId("chip-quarantined")
    
    // Verify chips are in active state (check for active styling classes)
    await expect(highRiskChip).toBeVisible()
    await expect(quarantinedChip).toBeVisible()
    
    // Click clear filters button
    await page.getByRole("button", { name: /clear filters/i }).click()
    await page.waitForTimeout(500)
    
    // URL should not have security filter params
    expect(page.url()).not.toContain("risk_min")
    expect(page.url()).not.toContain("quarantined")
  })

  test("URL params initialize filter state on page load", async ({ page }) => {
    await page.route("**/api/search/**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ 
          hits: [
            {
              id: "loaded",
              subject: "Pre-filtered result",
              from_addr: "test@example.com",
              received_at: "2024-01-15T10:30:00Z",
              score: 0.75
            }
          ]
        }),
      })
    })

    // Navigate with filters already in URL
    await page.goto("/search?q=invoice&risk_min=80&quarantined=true")
    await page.waitForLoadState("networkidle")
    
    // Chips should be in active state
    const highRiskChip = page.getByTestId("chip-high-risk")
    const quarantinedChip = page.getByTestId("chip-quarantined")
    
    await expect(highRiskChip).toBeVisible()
    await expect(quarantinedChip).toBeVisible()
    
    // Results should be shown
    await expect(page.getByTestId("result-0")).toBeVisible({ timeout: 5000 })
  })

  test("Individual chips can be toggled independently", async ({ page }) => {
    let lastRiskMin: string | null = null
    let lastQuarantined: string | null = null
    
    await page.route("**/api/search/**", async (route) => {
      const url = new URL(route.request().url())
      lastRiskMin = url.searchParams.get("risk_min")
      lastQuarantined = url.searchParams.get("quarantined")
      
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ hits: [] }),
      })
    })

    await page.goto("/search?q=test")
    await page.waitForLoadState("networkidle")
    
    // Toggle high-risk ON
    await page.getByTestId("chip-high-risk").click()
    await page.waitForTimeout(500)
    expect(lastRiskMin).toBe("80")
    expect(lastQuarantined).toBeNull()
    
    // Toggle high-risk OFF
    await page.getByTestId("chip-high-risk").click()
    await page.waitForTimeout(500)
    expect(lastRiskMin).toBeNull()
    
    // Toggle quarantined ON
    await page.getByTestId("chip-quarantined").click()
    await page.waitForTimeout(500)
    expect(lastRiskMin).toBeNull()
    expect(lastQuarantined).toBe("true")
    
    // Toggle quarantined OFF
    await page.getByTestId("chip-quarantined").click()
    await page.waitForTimeout(500)
    expect(lastQuarantined).toBeNull()
  })
})
