// apps/web/tests/smoke/inbox-has-data.spec.ts
import { test, expect } from '@playwright/test';

const BASE = process.env.E2E_BASE_URL ?? 'http://127.0.0.1:8000';
const API_BASE = process.env.E2E_API ?? BASE;  // Use E2E_API if set, otherwise fall back to BASE

test.describe('Smoke: API Health (No Auth Required)', () => {
  test('healthz endpoint returns ok', async ({ request }) => {
    const res = await request.get(`${API_BASE}/healthz`, { failOnStatusCode: false });
    expect(res.ok()).toBeTruthy();
    const json = await res.json();
    expect(json.status).toBe('ok');
    console.log('✓ Liveness check passed');
  });

  test('ready endpoint returns status', async ({ request }) => {
    const res = await request.get(`${API_BASE}/ready`, { failOnStatusCode: false });
    expect(res.ok()).toBeTruthy();
    const json = await res.json();
    expect(json).toHaveProperty('status');
    expect(json.status).toBe('ready');
    console.log(`✓ Readiness check: status=${json.status}, db=${json.db}, es=${json.es}`);
  });
});
