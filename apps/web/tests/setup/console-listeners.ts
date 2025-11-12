/**
 * Console and error listener fixture for Playwright tests
 *
 * Captures browser console messages and page errors to help debug
 * crashes and JavaScript errors that cause tests to fail.
 *
 * Usage:
 *   import { test, expect } from '../setup/console-listeners';
 *
 *   test('my test', async ({ page }) => {
 *     // Console logs and errors will be captured automatically
 *   });
 */
import { test as base } from '@playwright/test';

export const test = base.extend({
  page: async ({ page }, use) => {
    // Capture console messages
    page.on('console', (msg) => {
      const type = msg.type();
      const text = msg.text();

      // Prefix with color for visibility
      const prefix = type === 'error' ? '🔴' :
                     type === 'warning' ? '🟡' :
                     type === 'info' ? '🔵' : '⚪';

      // eslint-disable-next-line no-console
      console.log(`${prefix} [console.${type}]`, text);
    });

    // Capture page errors (unhandled exceptions)
    page.on('pageerror', (err) => {
      // eslint-disable-next-line no-console
      console.error('💥 [pageerror]', err.message);
      // eslint-disable-next-line no-console
      console.error('Stack:', err.stack);
    });

    // Capture crashes
    page.on('crash', () => {
      // eslint-disable-next-line no-console
      console.error('💀 [crash] Page crashed!');
    });

    await use(page);
  },
});

export { expect } from '@playwright/test';
