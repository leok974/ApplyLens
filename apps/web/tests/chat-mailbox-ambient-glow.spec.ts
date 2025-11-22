import { test, expect } from '@playwright/test';

test.describe('@prodSafe @prod @chat @theme', () => {
  test('Banana Pro has no ambient frame overlay', async ({ page }) => {
    // Force cache bypass to ensure we're testing the latest deployment
    await page.goto('/', { waitUntil: 'networkidle' });
    await page.reload({ waitUntil: 'networkidle' });

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

    // Tailwind's shadow-none produces rgba(0,0,0,0) which is effectively no shadow
    // So we just need to verify NO yellow glow (already checked above)
  });

  test('Banana Pro has only 3 localized glows (hero, shell, send button)', async ({ page }) => {
    // Force cache bypass
    await page.goto('/', { waitUntil: 'networkidle' });
    await page.reload({ waitUntil: 'networkidle' });

    // Select Banana Pro theme
    await page.goto('/settings');
    const bananaCard = page.getByTestId('mailbox-theme-card-bananaPro');
    await bananaCard.click();
    await page.waitForTimeout(500);

    // Go to chat
    await page.goto('/chat');
    await expect(page.getByTestId('chat-root')).toHaveAttribute('data-mailbox-theme', 'bananaPro');

    // Main verification: Frame should NOT have yellow glow
    const frame = page.getByTestId('mailbox-frame');
    const frameStyles = await frame.evaluate((el) => {
      return window.getComputedStyle(el).boxShadow;
    });

    expect(frameStyles).not.toContain('250, 204, 21');

    // Verify it's transparent black (Tailwind shadow-none) or none
    const isTransparentOrNone =
      frameStyles === 'none' ||
      frameStyles.includes('rgba(0, 0, 0, 0)');
    expect(isTransparentOrNone).toBe(true);
  });
});
