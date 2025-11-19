/**
 * Playwright global setup for E2E tests with authentication
 *
 * Programmatically creates an authenticated session before tests run.
 * Uses the test-only /api/auth/e2e/login endpoint.
 */

import { chromium, FullConfig } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

async function globalSetup(config: FullConfig) {
  const baseURL = process.env.E2E_BASE_URL || 'https://applylens.app';
  const authPath = process.env.E2E_AUTH_STATE || 'tests/auth/prod.json';
  const secret = process.env.E2E_SHARED_SECRET;

  console.log('🔧 E2E Global Setup');
  console.log(`   Base URL: ${baseURL}`);
  console.log(`   Auth state path: ${authPath}`);

  // Skip auth setup if secret not provided
  if (!secret) {
    console.warn('⚠️  E2E_SHARED_SECRET not set; skipping auth setup.');
    console.warn('   Tests requiring auth will be skipped.');
    return;
  }

  console.log('🔐 Creating authenticated session...');

  const browser = await chromium.launch();
  const context = await browser.newContext({
    baseURL,
  });
  const page = await context.newPage();

  try {
    // Hit the test-only login endpoint
    const loginUrl = `${baseURL}/api/auth/e2e/login`;
    console.log(`   POST ${loginUrl}`);

    const response = await page.request.post(loginUrl, {
      headers: {
        'X-E2E-Secret': secret,
      },
    });

    if (!response.ok()) {
      const body = await response.text();
      throw new Error(
        `E2E login failed: ${response.status()} ${response.statusText()}\n${body}`
      );
    }

    const data = await response.json();
    console.log(`   ✓ Logged in as: ${data.user}`);

    // Navigate to /chat to ensure the session works
    await page.goto(`${baseURL}/chat`, { waitUntil: 'networkidle' });
    console.log('   ✓ Verified session at /chat');

    // Ensure directory exists
    const authDir = path.dirname(authPath);
    if (!fs.existsSync(authDir)) {
      fs.mkdirSync(authDir, { recursive: true });
    }

    // Save storage state for all tests to use
    await context.storageState({ path: authPath });
    console.log(`   ✓ Saved auth state to ${authPath}`);

  } catch (error) {
    console.error('❌ E2E auth setup failed:', error);
    throw error;
  } finally {
    await browser.close();
  }

  console.log('✅ E2E global setup complete\n');
}

export default globalSetup;
