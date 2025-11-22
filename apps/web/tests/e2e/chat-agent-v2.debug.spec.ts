/**
 * Debug test for Agent V2 production smoke testing
 */
import { test, expect } from '@playwright/test';

const BASE_URL = process.env.E2E_BASE_URL || 'http://localhost:5173';

test.describe('@debug Agent V2 debug', () => {
  test('check chat interface elements', async ({ page }) => {
    await page.goto('/chat');

    // Log the URL
    console.log('Current URL:', page.url());

    // Wait for container
    const container = page.getByTestId('agent-mail-chat');
    await container.waitFor({ state: 'visible', timeout: 10000 });
    console.log('✓ Container found');

    // Check for input
    const input = page.getByTestId('chat-input');
    await expect(input).toBeVisible();
    console.log('✓ Input visible');

    const isEnabled = await input.isEnabled();
    console.log('Input enabled:', isEnabled);

    // Fill input
    await input.fill('show suspicious emails');
    console.log('✓ Input filled');

    // Check button
    const sendButton = page.getByTestId('chat-send');
    await expect(sendButton).toBeVisible();
    console.log('✓ Button visible');

    const buttonEnabled = await sendButton.isEnabled();
    console.log('Button enabled:', buttonEnabled);

    // Get button text
    const buttonText = await sendButton.textContent();
    console.log('Button text:', buttonText);

    // Try to click
    console.log('Attempting click...');
    await sendButton.click({ timeout: 5000 });
    console.log('✓ Click executed');

    // Wait a bit and check network
    await page.waitForTimeout(2000);

    // Check if any network requests were made
    const requests = [];
    page.on('request', request => {
      if (request.url().includes('/agent')) {
        console.log('Agent request:', request.url(), request.method());
        requests.push(request.url());
      }
    });

    // Take a screenshot
    await page.screenshot({ path: 'test-results/debug-after-click.png', fullPage: true });
    console.log('✓ Screenshot saved');
  });
});
