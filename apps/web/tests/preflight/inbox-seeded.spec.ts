// Preflight check: Verify inbox has seeded data before running tests
import { test, expect } from '@playwright/test';

const API_BASE = process.env.E2E_API || 'http://127.0.0.1:8888/api';

test('preflight: inbox seeded with data', async ({ request }) => {
  console.log('   🔍 Checking if inbox has seeded data...');

  const res = await request.get(`${API_BASE}/actions/tray?limit=1`);
  expect(res.ok(), `API /actions/tray returned ${res.status()}`).toBeTruthy();

  const json = await res.json();
  const itemCount = json?.items?.length ?? 0;

  console.log(`   → Found ${itemCount} items in inbox`);
  expect(itemCount, 'Inbox should have at least 1 seeded item').toBeGreaterThan(0);

  console.log('   ✅ Preflight check passed - inbox has data');
});
