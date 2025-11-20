import { request, FullConfig } from '@playwright/test';

export default async function globalSetup(config: FullConfig) {
  const base = process.env.E2E_BASE_URL ?? 'http://127.0.0.1:8888';
  const api  = process.env.E2E_API      ?? `${base}/api`;
  const seed = Number(process.env.SEED_COUNT ?? '20');
  const smoke = (process.env.USE_SMOKE_SETUP ?? 'false') === 'true';
  const authStatePath = process.env.E2E_AUTH_STATE;

  console.log('🔧 E2E Global Setup');
  console.log('   Base URL:', base);
  console.log('   Auth state path:', authStatePath || '(will create new)');

  // If E2E_AUTH_STATE is provided, skip auth setup (use existing cookies)
  if (authStatePath) {
    console.log('✅  Using existing auth state; skipping auth setup.');
    console.log('   Tests will use cookies from:', authStatePath);
    return;
  }

  console.log('');

  const ctx = await request.newContext({
    baseURL: base,  // Use base URL, not api, since routes don't have /api prefix
    extraHTTPHeaders: { 'Accept': 'application/json' }
  });

  // 1) CSRF cookie
  console.log('   📝 Getting CSRF token...');
  const csrfResp = await ctx.get('/auth/csrf');
  if (!csrfResp.ok()) {
    throw new Error(`CSRF endpoint failed: ${csrfResp.status()}`);
  }

  // Get the storage state to extract CSRF cookie
  const storage = await ctx.storageState();
  const csrfCookie = storage.cookies.find(c => c.name === 'csrf_token');
  if (!csrfCookie) {
    throw new Error('CSRF cookie not set by server');
  }
  console.log('   ✓ CSRF token obtained:', csrfCookie.value.substring(0, 20) + '...');

  // 2) Demo session (guarantees JSON from /auth/me per your fixes)
  console.log('   📝 Starting demo authentication...');
  const res = await ctx.post('/auth/demo/start', {
    headers: { 'X-CSRF-Token': csrfCookie.value }
  });
  if (!res.ok()) {
    const errorText = await res.text().catch(() => 'unknown');
    throw new Error(`demo/start failed: ${res.status()} - ${errorText}`);
  }
  console.log('   ✓ Demo authentication successful');

  // 3) Optional seed (idempotent in dev)
  if (smoke) {
    console.log(`   🌱 Seeding ${seed} threads...`);
    const r = await ctx.get(`/dev/seed-threads-simple?count=${seed}`);
    if (!r.ok()) {
      console.warn(`   ⚠ Seed failed: ${r.status()} - continuing anyway`);
    } else {
      console.log(`   ✓ Seeded ${seed} threads successfully`);
    }
  }

  // 4) Persist session storage for UI tests
  //    We fetch /auth/me to ensure cookies are set, then save state.
  await ctx.get('/auth/me');
  await ctx.storageState({ path: 'tests/.auth/storageState.json' });
  await ctx.dispose();

  console.log('   ✓ Storage state saved');
  console.log('✅ Global setup complete\n');
}
