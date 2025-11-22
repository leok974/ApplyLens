/**
 * Script to save Chrome cookies to Playwright storage state format
 *
 * Usage:
 * 1. Open Chrome DevTools (F12) on https://applylens.app
 * 2. Go to Console tab
 * 3. Paste this entire script and press Enter
 * 4. Copy the output JSON
 * 5. Save it to apps/web/tests/auth/prod.json
 */

(async function exportCookies() {
  console.log('Extracting cookies for applylens.app...\n');

  // Get all cookies for the current domain
  const cookies = await cookieStore.getAll();

  // Format cookies in Playwright's storage state format
  const playwrightCookies = cookies.map(cookie => ({
    name: cookie.name,
    value: cookie.value,
    domain: cookie.domain || '.applylens.app',
    path: cookie.path || '/',
    expires: cookie.expires || -1,
    httpOnly: cookie.httpOnly || false,
    secure: cookie.secure || false,
    sameSite: cookie.sameSite || 'Lax'
  }));

  const storageState = {
    cookies: playwrightCookies,
    origins: [
      {
        origin: 'https://applylens.app',
        localStorage: []
      }
    ]
  };

  console.log('Copy this JSON and save to apps/web/tests/auth/prod.json:\n');
  console.log(JSON.stringify(storageState, null, 2));

  // Also copy to clipboard if available
  try {
    await navigator.clipboard.writeText(JSON.stringify(storageState, null, 2));
    console.log('\n✓ JSON copied to clipboard!');
  } catch (e) {
    console.log('\n⚠ Could not copy to clipboard, please copy manually from above');
  }
})();
