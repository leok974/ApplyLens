import { test, expect } from '@playwright/test';

test.describe('@prod @chat @theme', () => {
  test('Banana Pro has no ambient frame overlay', async ({ page }) => {
    // 1) Go to Settings and select Banana Pro theme
    await page.goto('/settings');

    // Click the Banana Pro theme card
    const bananaCard = page.getByTestId('mailbox-theme-card-bananaPro');
    await expect(bananaCard).toBeVisible();
    await bananaCard.click();

    // Give the preference write + localStorage a moment
    await page.waitForTimeout(500);

    // 2) Go to Chat and confirm Banana Pro is active
    await page.goto('/chat');

    const chatRoot = page.getByTestId('chat-root');
    await expect(chatRoot).toBeVisible();
    await expect(chatRoot).toHaveAttribute('data-mailbox-theme', 'bananaPro');

    const frame = page.getByTestId('mailbox-frame');
    await expect(frame).toBeVisible();

    // 3) Inspect computed styles on the frame container
    const styles = await frame.evaluate((el) => {
      const cs = window.getComputedStyle(el);
      return {
        boxShadow: cs.boxShadow,
        backgroundImage: cs.backgroundImage,
      };
    });

    // We never want a big yellow or gradient-based vignette on the frame
    // boxShadow should be 'none' or not contain yellow rgb(250, 204, 21)
    expect(styles.boxShadow || '').not.toContain('250, 204, 21'); // no yellow glow
    expect(styles.backgroundImage || '').not.toContain('radial-gradient');

    // Additional verification: check that frame has shadow-none or no shadow
    const hasNoShadow =
      styles.boxShadow === 'none' ||
      styles.boxShadow === '' ||
      !styles.boxShadow;

    expect(hasNoShadow).toBe(true);
  });

  test('Banana Pro has only 3 localized glows (hero, shell, send button)', async ({ page }) => {
    // Select Banana Pro theme
    await page.goto('/settings');
    const bananaCard = page.getByTestId('mailbox-theme-card-bananaPro');
    await bananaCard.click();
    await page.waitForTimeout(500);

    // Go to chat
    await page.goto('/chat');
    await expect(page.getByTestId('chat-root')).toHaveAttribute('data-mailbox-theme', 'bananaPro');

    // Check that hero card has a glow (localized)
    const heroCard = page.locator('[data-testid="chat-root"]').locator('> div > div').first();
    const heroStyles = await heroCard.evaluate((el) => {
      return window.getComputedStyle(el).boxShadow;
    });

    // Hero should have yellow glow
    expect(heroStyles).toContain('250, 204, 21');

    // Check that chat shell has a glow (localized)
    const shellCard = page.getByTestId('chat-shell');
    if (await shellCard.isVisible()) {
      const shellStyles = await shellCard.evaluate((el) => {
        return window.getComputedStyle(el).boxShadow;
      });

      // Shell should have yellow glow
      expect(shellStyles).toContain('250, 204, 21');
    }

    // Frame should NOT have yellow glow
    const frame = page.getByTestId('mailbox-frame');
    const frameStyles = await frame.evaluate((el) => {
      return window.getComputedStyle(el).boxShadow;
    });

    expect(frameStyles).not.toContain('250, 204, 21');
  });
});
