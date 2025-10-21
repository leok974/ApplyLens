import { test, expect } from '@playwright/test';

test.describe('Profile Metrics (Warehouse)', () => {
  test.beforeEach(async ({ page }) => {
    // Set environment variable to enable warehouse metrics
    await page.addInitScript(() => {
      // @ts-ignore
      window.import = {
        meta: {
          env: {
            VITE_USE_WAREHOUSE: '1'
          }
        }
      };
    });
  });

  test('should not display ProfileMetrics when feature disabled', async ({ page }) => {
    // Override to disable feature
    await page.addInitScript(() => {
      // @ts-ignore
      window.import = {
        meta: {
          env: {
            VITE_USE_WAREHOUSE: ''
          }
        }
      };
    });

    await page.goto('/web/settings');
    
    // Should not see warehouse metrics section
    await expect(page.locator('text=Inbox Analytics')).not.toBeVisible();
    await expect(page.locator('text=Powered by BigQuery')).not.toBeVisible();
  });

  test('should display ProfileMetrics when feature enabled', async ({ page, context }) => {
    // Mock warehouse API responses
    await context.route('**/api/warehouse/profile/activity-daily*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          {
            day: '2025-10-17',
            messages_count: 35,
            unique_senders: 12,
            avg_size_kb: 45.2,
            total_size_mb: 1.5
          },
          {
            day: '2025-10-18',
            messages_count: 28,
            unique_senders: 10,
            avg_size_kb: 42.1,
            total_size_mb: 1.2
          }
        ])
      });
    });

    await context.route('**/api/warehouse/profile/top-senders*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          {
            from_email: 'jobs@linkedin.com',
            messages_30d: 42,
            total_size_mb: 1.5
          },
          {
            from_email: 'noreply@github.com',
            messages_30d: 35,
            total_size_mb: 0.8
          }
        ])
      });
    });

    await context.route('**/api/warehouse/profile/categories-30d*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          {
            category: 'promotions',
            messages_30d: 150,
            pct_of_total: 45.5
          },
          {
            category: 'primary',
            messages_30d: 120,
            pct_of_total: 36.4
          }
        ])
      });
    });

    await page.goto('/web/settings');
    
    // Should see warehouse metrics section
    await expect(page.locator('text=Inbox Analytics (Last 14 Days)')).toBeVisible();
    await expect(page.locator('text=Powered by BigQuery')).toBeVisible();
    
    // Should see activity card
    await expect(page.locator('text=Inbox Activity')).toBeVisible();
    await expect(page.locator('text=63')).toBeVisible(); // Total messages
    
    // Should see top senders card
    await expect(page.locator('text=Top Senders (30d)')).toBeVisible();
    await expect(page.locator('text=jobs')).toBeVisible(); // Truncated email
    await expect(page.locator('text=42 emails')).toBeVisible();
    
    // Should see categories card
    await expect(page.locator('text=Categories (30d)')).toBeVisible();
    await expect(page.locator('text=promotions')).toBeVisible();
    await expect(page.locator('text=45.5%')).toBeVisible();
  });

  test('should show error state when API fails', async ({ page, context }) => {
    // Mock API failure
    await context.route('**/api/warehouse/profile/**', async (route) => {
      await route.fulfill({
        status: 412,
        contentType: 'application/json',
        body: JSON.stringify({
          detail: 'Warehouse disabled. Set USE_WAREHOUSE=1 to enable BigQuery metrics.'
        })
      });
    });

    await page.goto('/web/settings');
    
    // Should see error message
    await expect(page.locator('text=Warehouse Metrics Unavailable')).toBeVisible();
    await expect(page.locator('text=Ensure USE_WAREHOUSE=1')).toBeVisible();
  });

  test('should show loading state initially', async ({ page, context }) => {
    // Add delay to API responses
    await context.route('**/api/warehouse/profile/**', async (route) => {
      await new Promise(resolve => setTimeout(resolve, 1000));
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([])
      });
    });

    await page.goto('/web/settings');
    
    // Should see loading skeleton
    await expect(page.locator('.animate-pulse')).toBeVisible();
  });
});
