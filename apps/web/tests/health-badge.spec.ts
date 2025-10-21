import { test, expect, Page } from '@playwright/test';

const DIVERGENCE_ENDPOINT = '/api/metrics/divergence-24h';

/**
 * Helper to mock divergence API endpoint
 */
async function mockDivergenceState(
  page: Page,
  payload: any,
  statusCode: number = 200
) {
  await page.route(DIVERGENCE_ENDPOINT, async (route) => {
    await route.fulfill({
      status: statusCode,
      contentType: 'application/json',
      body: JSON.stringify(payload),
    });
  });
}

test.describe('HealthBadge Component', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to a page that includes the HealthBadge (e.g., dashboard)
    // Adjust the route based on your app structure
  });

  test('displays green badge for healthy state (<2% divergence)', async ({ page }) => {
    await mockDivergenceState(page, {
      divergence_pct: 0.011,
      status: 'ok',
      es_count: 10050,
      bq_count: 10000,
      slo_met: true,
      message: 'Divergence: 1.10% (within SLO)',
    });

    await page.goto('/');

    // Wait for badge to appear
    const badge = page.getByText('Warehouse OK');
    await expect(badge).toBeVisible();

    // Verify green styling
    const badgeElement = page.locator('[title*="Healthy"]');
    await expect(badgeElement).toBeVisible();
  });

  test('displays yellow badge for degraded state (2-5% divergence)', async ({ page }) => {
    await mockDivergenceState(page, {
      divergence_pct: 0.035,
      status: 'degraded',
      es_count: 10350,
      bq_count: 10000,
      slo_met: false,
      message: 'Divergence: 3.50% (exceeds SLO)',
    });

    await page.goto('/');

    const badge = page.getByText('Degraded');
    await expect(badge).toBeVisible();

    // Verify tooltip shows divergence percentage
    const badgeElement = page.locator('[title*="3.5%"]');
    await expect(badgeElement).toBeVisible();
  });

  test('displays grey badge for paused state (warehouse offline)', async ({ page }) => {
    await mockDivergenceState(
      page,
      {
        detail: 'Warehouse disabled. Set USE_WAREHOUSE=1 to enable BigQuery metrics.',
      },
      412
    );

    await page.goto('/');

    const badge = page.getByText('Paused');
    await expect(badge).toBeVisible();

    // Verify tooltip
    const badgeElement = page.locator('[title*="offline"]');
    await expect(badgeElement).toBeVisible();
  });

  test('shows loading state initially', async ({ page }) => {
    // Delay the response to see loading state
    await page.route(DIVERGENCE_ENDPOINT, async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 500));
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          divergence_pct: 0.011,
          status: 'ok',
          slo_met: true,
        }),
      });
    });

    await page.goto('/');

    // Should show loading state
    const loadingBadge = page.getByText('Checking...');
    await expect(loadingBadge).toBeVisible();

    // Then should show OK state
    await expect(page.getByText('Warehouse OK')).toBeVisible({ timeout: 2000 });
  });

  test('auto-refreshes every 60 seconds', async ({ page }) => {
    let callCount = 0;

    await page.route(DIVERGENCE_ENDPOINT, async (route) => {
      callCount++;
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          divergence_pct: 0.011,
          status: 'ok',
          slo_met: true,
        }),
      });
    });

    await page.goto('/');

    // Wait for initial load
    await expect(page.getByText('Warehouse OK')).toBeVisible();
    const initialCallCount = callCount;

    // Wait 61 seconds (to account for any timing variations)
    await page.waitForTimeout(61000);

    // Should have made at least one more call
    expect(callCount).toBeGreaterThan(initialCallCount);
  });

  test('displays divergence percentage in badge', async ({ page }) => {
    await mockDivergenceState(page, {
      divergence_pct: 1.5,
      status: 'ok',
      slo_met: true,
    });

    await page.goto('/');

    // Badge should show percentage
    await expect(page.getByText(/1\.5%/)).toBeVisible();
  });

  test('handles network error gracefully', async ({ page }) => {
    await page.route(DIVERGENCE_ENDPOINT, async (route) => {
      await route.abort('failed');
    });

    await page.goto('/');

    // Should show paused state
    const badge = page.getByText('Paused');
    await expect(badge).toBeVisible();
  });
});

test.describe('ProfileMetrics Fallback Mode', () => {
  test('hides charts and shows fallback card when warehouse disabled', async ({ page }) => {
    // Mock 412 response for all warehouse endpoints
    await page.route('**/api/warehouse/profile/**', async (route) => {
      await route.fulfill({
        status: 412,
        contentType: 'application/json',
        body: JSON.stringify({
          detail: 'Warehouse disabled. Set USE_WAREHOUSE=1 to enable BigQuery metrics.',
        }),
      });
    });

    await page.goto('/profile'); // Adjust route as needed

    // Should show fallback card
    const fallbackCard = page.getByText(/Demo Mode/i);
    await expect(fallbackCard).toBeVisible();

    // Should show friendly message
    const message = page.getByText(/offline/i);
    await expect(message).toBeVisible();

    // Should NOT show error styling (blue, not red)
    const card = page.locator('[class*="bg-blue"]');
    await expect(card).toBeVisible();

    // Should NOT show red error card
    const errorCard = page.locator('[class*="border-destructive"]');
    await expect(errorCard).not.toBeVisible();
  });

  test('shows metrics cards when warehouse is enabled', async ({ page }) => {
    // Mock successful responses
    await page.route('**/api/warehouse/profile/divergence-24h', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ divergence_pct: 0.011, status: 'ok' }),
      });
    });

    await page.route('**/api/warehouse/profile/activity-daily**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          { day: '2025-10-19', messages_count: 150, unique_senders: 50 },
        ]),
      });
    });

    await page.route('**/api/warehouse/profile/top-senders**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          { from_email: 'sender@example.com', messages_30d: 100, total_size_mb: 5.2 },
        ]),
      });
    });

    await page.route('**/api/warehouse/profile/categories-30d**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          { category: 'work', messages_30d: 200, pct_of_total: 45.5 },
        ]),
      });
    });

    await page.goto('/profile'); // Adjust route as needed

    // Should show 3 metric cards
    await expect(page.getByText('Inbox Activity')).toBeVisible();
    await expect(page.getByText('Top Senders')).toBeVisible();
    await expect(page.getByText('Categories')).toBeVisible();

    // Should NOT show fallback card
    const fallbackCard = page.getByText(/Demo Mode/i);
    await expect(fallbackCard).not.toBeVisible();
  });

  test('transitions from healthy to paused state', async ({ page }) => {
    let warehouseEnabled = true;

    await page.route('**/api/warehouse/profile/**', async (route) => {
      if (warehouseEnabled) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ divergence_pct: 0.011, status: 'ok' }),
        });
      } else {
        await route.fulfill({
          status: 412,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Warehouse disabled' }),
        });
      }
    });

    await page.goto('/profile');

    // Initially shows metrics
    await expect(page.getByText('Inbox Activity')).toBeVisible();

    // Simulate warehouse going offline
    warehouseEnabled = false;

    // Reload page
    await page.reload();

    // Should now show fallback card
    await expect(page.getByText(/Demo Mode/i)).toBeVisible();
  });
});

test.describe('Integration: HealthBadge + ProfileMetrics', () => {
  test('badge and metrics cards sync correctly', async ({ page }) => {
    await page.route('**/api/warehouse/profile/divergence-24h', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ divergence_pct: 0.011, status: 'ok' }),
      });
    });

    await page.route('**/api/warehouse/profile/activity-daily**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([{ day: '2025-10-19', messages_count: 150 }]),
      });
    });

    await page.goto('/profile');

    // Badge should be green
    await expect(page.getByText('Warehouse OK')).toBeVisible();

    // Metrics should be visible
    await expect(page.getByText('Inbox Activity')).toBeVisible();
  });

  test('badge paused and fallback card both show when warehouse offline', async ({ page }) => {
    await page.route('**/api/warehouse/profile/**', async (route) => {
      await route.fulfill({
        status: 412,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Warehouse disabled' }),
      });
    });

    await page.goto('/profile');

    // Badge should be grey
    await expect(page.getByText('Paused')).toBeVisible();

    // Fallback card should be visible
    await expect(page.getByText(/Demo Mode/i)).toBeVisible();
  });
});
