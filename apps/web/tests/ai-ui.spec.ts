import { test, expect } from '@playwright/test';

test.describe('Phase 4 AI Features', () => {
  
  test('summary card renders and triggers', async ({ page }) => {
    await page.route('/api/ai/summarize', (route) => 
      route.fulfill({ 
        json: { 
          bullets: ['One', 'Two', 'Three', 'Four', 'Five'], 
          citations: [
            { snippet: 'First reference', message_id: 'msg1', offset: 10 }
          ] 
        } 
      })
    );
    
    await page.goto('/demo-ai');
    await page.getByRole('button', { name: 'Summarize' }).click();
    await expect(page.getByTestId('summary-card')).toContainText('One');
    await expect(page.getByTestId('summary-citations')).toBeVisible();
  });

  test('risk popover shows 3 signals', async ({ page }) => {
    await page.route(/\/api\/security\/risk-top3.*/, (route) => 
      route.fulfill({ 
        json: { 
          score: 87, 
          signals: [
            { id: 'auth', label: 'SPF/DKIM fail', explain: 'Sender failed authentication' },
            { id: 'new_domain', label: 'New domain', explain: 'First seen in 30d' },
            { id: 'url_mismatch', label: 'Suspicious link', explain: 'Visible vs target mismatch' },
          ] 
        } 
      })
    );
    
    await page.goto('/demo-ai');
    await page.getByTestId('risk-badge').click();
    await expect(page.getByTestId('risk-popover')).toContainText('SPF/DKIM');
    await expect(page.getByTestId('risk-popover')).toContainText('New domain');
    await expect(page.getByTestId('risk-popover')).toContainText('Suspicious link');
  });

  test('rag results show highlights', async ({ page }) => {
    await page.route('/api/rag/query', (route) => 
      route.fulfill({ 
        json: { 
          hits: [
            { 
              thread_id: 't1', 
              sender: 'Bianca', 
              date: '2025-10-15', 
              why: 'semantic+bm25', 
              highlights: ['Interview at 2pm', 'Bring portfolio'] 
            }
          ] 
        } 
      })
    );
    
    await page.goto('/demo-ai');
    await page.getByPlaceholder('Ask your inbox…').fill('interview from Bianca');
    await page.getByRole('button', { name: 'Ask' }).click();
    await expect(page.getByTestId('rag-results')).toContainText('Interview at 2pm');
    await expect(page.getByTestId('rag-results')).toContainText('Bianca');
  });

  test('ai health endpoint accessible', async ({ page }) => {
    await page.route('/api/ai/health', (route) => 
      route.fulfill({ 
        json: { 
          ollama: 'available', 
          features: { summarize: true } 
        } 
      })
    );
    
    const response = await page.request.get('/api/ai/health');
    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    expect(data.ollama).toBe('available');
  });

  test('summary handles error gracefully', async ({ page }) => {
    await page.route('/api/ai/summarize', (route) => 
      route.fulfill({ status: 404, json: { detail: 'Thread not found' } })
    );
    
    await page.goto('/demo-ai');
    await page.getByRole('button', { name: 'Summarize' }).click();
    await expect(page.getByTestId('summary-card')).toContainText('Unable to summarize');
  });

  test('risk badge displays correct color', async ({ page }) => {
    await page.route(/\/api\/security\/risk-top3.*/, (route) => 
      route.fulfill({ json: { score: 85, signals: [] } })
    );
    
    await page.goto('/demo-ai');
    const badge = page.getByTestId('risk-badge');
    await badge.click();
    
    // High risk (>80) should be red
    await expect(badge).toHaveClass(/bg-red-500/);
  });

  test('rag search with enter key', async ({ page }) => {
    await page.route('/api/rag/query', (route) => 
      route.fulfill({ json: { hits: [{ thread_id: 't1', sender: 'Test' }] } })
    );
    
    await page.goto('/demo-ai');
    const input = page.getByPlaceholder('Ask your inbox…');
    await input.fill('test query');
    await input.press('Enter');
    await expect(page.getByTestId('rag-results')).toContainText('Test');
  });
});
