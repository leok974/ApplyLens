// apps/web/tests/global.setup.ts
import { test as setup, request, expect } from '@playwright/test';
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const STORAGE = path.resolve(__dirname, '.auth', 'storageState.json');

export default async () => {
  const apiBase = (process.env.E2E_API || 'http://127.0.0.1:8000').replace(/\/$/, '');
  console.log(`🔧 Global setup starting - API: ${apiBase}`);

  // Create request context - note: we don't use baseURL since it doesn't work well with paths
  const ctx = await request.newContext({
    extraHTTPHeaders: {
      'Accept': 'application/json'
    }
  });

  // Skip authentication if USE_SMOKE_SETUP is false (production/read-only tests)
  if (process.env.USE_SMOKE_SETUP !== 'true') {
    console.log('   ⊘ Skipping authentication (USE_SMOKE_SETUP=false)');
    await fs.mkdir(path.dirname(STORAGE), { recursive: true });
    await ctx.storageState({ path: STORAGE });
    await ctx.dispose();
    console.log('✅ Global setup complete (no auth)\n');
    return;
  }

  // 1) Get CSRF token first (required for demo auth)
  // Note: Use full URLs instead of relative paths since baseURL with path segments doesn't work reliably
  console.log('   📝 Getting CSRF token...');
  const csrfUrl = `${apiBase}/auth/csrf`;
  console.log(`   → GET ${csrfUrl}`);
  const csrfResp = await ctx.get(csrfUrl);

  // Debug: log response details
  console.log(`   → Response status: ${csrfResp.status()}`);
  console.log(`   → Content-Type: ${csrfResp.headers()['content-type']}`);

  expect(csrfResp.ok()).toBeTruthy();

  // Extract CSRF token from Set-Cookie header
  const allHeaders = csrfResp.headersArray();
  const setCookieHeaders = allHeaders.filter(h => h.name.toLowerCase() === 'set-cookie');
  console.log(`   → Found ${setCookieHeaders.length} Set-Cookie headers`);

  let csrf = '';
  // Note: The API sends multiple Set-Cookie headers with csrf_token.
  // We need to use the LAST one since that's what ends up in the cookie jar.
  for (const header of setCookieHeaders) {
    const match = header.value.match(/csrf_token=([^;]+)/);
    if (match) {
      csrf = match[1];  // Keep updating, so we end up with the last one
    }
  }

  if (csrf) {
    console.log(`   ✓ CSRF token extracted: ${csrf.substring(0, 20)}...`);
  }

  if (!csrf) {
    console.error('   ❌ No CSRF token found in Set-Cookie headers');
    console.error('   Set-Cookie headers:', setCookieHeaders.map(h => h.value));
    throw new Error('Failed to get CSRF token');
  }

  // Debug: Check what cookies are stored in the context
  const cookies = await ctx.storageState();
  console.log(`   → Context has ${cookies.cookies.length} cookies stored`);
  cookies.cookies.forEach(c => console.log(`     - ${c.name} = ${c.value.substring(0, 20)}...`));

  // 2) Start demo auth (sets session cookies)
  console.log('   📝 Starting demo authentication...');
  const demoUrl = `${apiBase}/auth/demo/start`;
  console.log(`   → POST ${demoUrl}`);
  const demo = await ctx.post(demoUrl, {
    headers: { 'X-CSRF-Token': csrf },
    data: {}
  });

  if (!demo.ok()) {
    const body = await demo.text();
    console.error(`   ❌ Demo auth failed: ${demo.status()} - ${body}`);
    console.error(`   URL: ${demo.url()}`);
    throw new Error(`Demo auth failed: ${demo.status()}`);
  }
  console.log('   ✓ Demo authentication successful');

  // 3) Seed (only if we're asked to)
  const seedCount = Number(process.env.SEED_COUNT ?? 40);
  console.log(`   🌱 Seeding ${seedCount} threads...`);

  // Note: The dev router has prefix="/api/dev", so the full path is /api/api/dev/...
  // because we're already proxying through /api in Nginx
  const seedUrl = `${apiBase}/api/dev/seed-threads-simple`;
  const res = await ctx.post(seedUrl, {
    headers: { 'X-CSRF-Token': csrf },
    data: { count: seedCount }
  });

  if (!res.ok()) {
    const errorText = await res.text();
    throw new Error(`Seeding failed: ${res.status()} ${errorText}`);
  }

  const result = await res.json();
  console.log(`   ✓ Seeded ${result.count} threads successfully`);

  // 4) Persist cookies to storage state for tests
  await fs.mkdir(path.dirname(STORAGE), { recursive: true });
  await ctx.storageState({ path: STORAGE });
  await ctx.dispose();

  console.log('   ✓ Storage state saved');
  console.log('✅ Global setup complete\n');
};
