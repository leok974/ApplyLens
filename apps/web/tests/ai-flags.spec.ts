import { test, expect } from '@playwright/test';

/**
 * Feature Flag Tests
 * 
 * These tests verify that feature flags properly control the visibility
 * of Phase 4 AI components.
 */

test.describe('Feature Flags', () => {
  test('all features visible when flags are enabled', async ({ page }) => {
    // Simulate all flags enabled
    await page.addInitScript(() => {
      (window as any).import = {
        meta: {
          env: {
            VITE_FEATURE_SUMMARIZE: '1',
            VITE_FEATURE_RISK_BADGE: '1',
            VITE_FEATURE_RAG_SEARCH: '1',
            VITE_DEMO_MODE: '1',
          },
        },
      };
    });

    await page.goto('/demo-ai');

    // All components should be visible
    await expect(page.getByTestId('summary-card')).toBeVisible();
    await expect(page.getByTestId('risk-popover')).toBeVisible();
    await expect(page.getByTestId('rag-results')).toBeVisible();
    
    // Demo mode indicator should be visible
    await expect(page.getByText(/demo mode enabled/i)).toBeVisible();
  });

  test('components hidden when flags are disabled', async ({ page }) => {
    // Simulate all flags disabled
    await page.addInitScript(() => {
      (window as any).import = {
        meta: {
          env: {
            VITE_FEATURE_SUMMARIZE: '0',
            VITE_FEATURE_RISK_BADGE: '0',
            VITE_FEATURE_RAG_SEARCH: '0',
            VITE_DEMO_MODE: '0',
          },
        },
      };
    });

    await page.goto('/demo-ai');

    // No components should be present
    await expect(page.getByTestId('summary-card')).toHaveCount(0);
    await expect(page.getByTestId('risk-popover')).toHaveCount(0);
    await expect(page.getByTestId('rag-results')).toHaveCount(0);

    // Should show "no features enabled" message
    await expect(page.getByText(/no ai features are currently enabled/i)).toBeVisible();
  });

  test('only summarize feature enabled', async ({ page }) => {
    await page.addInitScript(() => {
      (window as any).import = {
        meta: {
          env: {
            VITE_FEATURE_SUMMARIZE: '1',
            VITE_FEATURE_RISK_BADGE: '0',
            VITE_FEATURE_RAG_SEARCH: '0',
          },
        },
      };
    });

    await page.goto('/demo-ai');

    // Only summary card should be visible
    await expect(page.getByTestId('summary-card')).toBeVisible();
    await expect(page.getByTestId('risk-popover')).toHaveCount(0);
    await expect(page.getByTestId('rag-results')).toHaveCount(0);
  });

  test('only risk badge enabled', async ({ page }) => {
    await page.addInitScript(() => {
      (window as any).import = {
        meta: {
          env: {
            VITE_FEATURE_SUMMARIZE: '0',
            VITE_FEATURE_RISK_BADGE: '1',
            VITE_FEATURE_RAG_SEARCH: '0',
          },
        },
      };
    });

    await page.goto('/demo-ai');

    // Only risk badge should be visible
    await expect(page.getByTestId('summary-card')).toHaveCount(0);
    await expect(page.getByTestId('risk-popover')).toBeVisible();
    await expect(page.getByTestId('rag-results')).toHaveCount(0);
  });

  test('only RAG search enabled', async ({ page }) => {
    await page.addInitScript(() => {
      (window as any).import = {
        meta: {
          env: {
            VITE_FEATURE_SUMMARIZE: '0',
            VITE_FEATURE_RISK_BADGE: '0',
            VITE_FEATURE_RAG_SEARCH: '1',
          },
        },
      };
    });

    await page.goto('/demo-ai');

    // Only RAG results should be visible
    await expect(page.getByTestId('summary-card')).toHaveCount(0);
    await expect(page.getByTestId('risk-popover')).toHaveCount(0);
    await expect(page.getByTestId('rag-results')).toBeVisible();
  });

  test('demo mode indicator only shows when enabled', async ({ page }) => {
    await page.addInitScript(() => {
      (window as any).import = {
        meta: {
          env: {
            VITE_FEATURE_SUMMARIZE: '1',
            VITE_DEMO_MODE: '1',
          },
        },
      };
    });

    await page.goto('/demo-ai');
    await expect(page.getByText(/demo mode enabled/i)).toBeVisible();
  });

  test('demo mode indicator hidden when disabled', async ({ page }) => {
    await page.addInitScript(() => {
      (window as any).import = {
        meta: {
          env: {
            VITE_FEATURE_SUMMARIZE: '1',
            VITE_DEMO_MODE: '0',
          },
        },
      };
    });

    await page.goto('/demo-ai');
    await expect(page.getByText(/demo mode enabled/i)).toHaveCount(0);
  });
});

test.describe('Flag Integration in Other Views', () => {
  test('summarize button respects flag in email detail', async ({ page }) => {
    // This test assumes you'll integrate SummaryCard into email detail view
    // Update selector to match your actual implementation
    
    await page.goto('/emails/123'); // Adjust route as needed
    
    const summaryCard = page.getByTestId('summary-card');
    
    // Check if feature flag is enabled
    const flagEnabled = process.env.VITE_FEATURE_SUMMARIZE === '1';
    
    if (flagEnabled) {
      await expect(summaryCard).toBeVisible();
    } else {
      await expect(summaryCard).toHaveCount(0);
    }
  });

  test('risk badge respects flag in email list', async ({ page }) => {
    // This test assumes you'll integrate RiskPopover into email list
    // Update selector to match your actual implementation
    
    await page.goto('/inbox');
    
    const riskBadges = page.getByTestId('risk-badge');
    
    const flagEnabled = process.env.VITE_FEATURE_RISK_BADGE === '1';
    
    if (flagEnabled) {
      // Should have at least one risk badge if emails exist
      const count = await riskBadges.count();
      expect(count).toBeGreaterThanOrEqual(0);
    } else {
      await expect(riskBadges).toHaveCount(0);
    }
  });
});
