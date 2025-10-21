import { test, expect } from '@playwright/test';

/**
 * AI Routes Smoke Tests
 * 
 * Quick smoke tests to verify all Phase 4 API routes are accessible.
 * These tests hit real API endpoints to ensure registration is correct.
 */

const API_BASE = process.env.VITE_API_BASE || 'http://localhost:8000';

test.describe('AI Routes Smoke Tests', () => {
  test('AI health endpoint is accessible', async ({ request }) => {
    const response = await request.get(`${API_BASE}/api/ai/health`);
    expect(response.ok()).toBeTruthy();
    
    const data = await response.json();
    expect(data).toHaveProperty('ollama');
    expect(['available', 'unavailable']).toContain(data.ollama);
    expect(data).toHaveProperty('features');
  });

  test('AI summarize endpoint exists', async ({ request }) => {
    const response = await request.post(`${API_BASE}/api/ai/summarize`, {
      data: { thread_id: 'test-thread-123', max_citations: 3 }
    });
    
    // Should not return 404 (route should exist)
    expect(response.status()).not.toBe(404);
    
    // May return 404 for missing thread or 500 if Ollama down, but route exists
    expect([200, 404, 422, 500]).toContain(response.status());
  });

  test('RAG health endpoint is accessible', async ({ request }) => {
    const response = await request.get(`${API_BASE}/rag/health`);
    expect(response.ok()).toBeTruthy();
    
    const data = await response.json();
    expect(data).toHaveProperty('status');
    expect(['ready', 'fallback', 'unavailable']).toContain(data.status);
  });

  test('RAG query endpoint exists', async ({ request }) => {
    const response = await request.post(`${API_BASE}/api/rag/query`, {
      data: { q: 'test query', k: 5 }
    });
    
    // Should not return 404
    expect(response.status()).not.toBe(404);
    
    // May return empty results or error, but route should exist
    expect([200, 422, 500]).toContain(response.status());
  });

  test('Security risk endpoint exists', async ({ request }) => {
    const response = await request.get(
      `${API_BASE}/api/security/risk-top3?message_id=test-msg-123`
    );
    
    // Should not return 404
    expect(response.status()).not.toBe(404);
    
    // May return 404 for missing message, but route exists
    expect([200, 404, 422, 500]).toContain(response.status());
  });

  test('Metrics divergence endpoint is accessible', async ({ request }) => {
    const response = await request.get(`${API_BASE}/api/metrics/divergence-24h`);
    expect(response.ok()).toBeTruthy();
    
    const data = await response.json();
    expect(data).toHaveProperty('status');
    expect(['ok', 'degraded', 'paused']).toContain(data.status);
    
    if (data.status !== 'paused') {
      expect(data).toHaveProperty('divergence_pct');
      expect(data).toHaveProperty('es_count');
      expect(data).toHaveProperty('bq_count');
    }
  });

  test('OpenAPI spec includes Phase 4 routes', async ({ request }) => {
    const response = await request.get(`${API_BASE}/openapi.json`);
    expect(response.ok()).toBeTruthy();
    
    const openapi = await response.json();
    expect(openapi).toHaveProperty('paths');
    
    const paths = openapi.paths;
    const phase4Paths = [
      '/api/ai/health',
      '/api/ai/summarize',
      '/rag/health',
      '/api/rag/query',
    ];
    
    for (const path of phase4Paths) {
      expect(paths).toHaveProperty(path);
    }
  });
});

test.describe('Phase 4 Routes Count', () => {
  test('verify expected number of Phase 4 routes', async ({ request }) => {
    const response = await request.get(`${API_BASE}/openapi.json`);
    const openapi = await response.json();
    
    const phase4Paths = [
      '/api/ai/health',
      '/api/ai/summarize',
      '/rag/health',
      '/api/rag/query',
      '/api/security/risk-top3',
      '/api/metrics/divergence-24h',
      '/api/metrics/activity-daily',
      '/api/metrics/top-senders-30d',
      '/api/metrics/categories-30d',
    ];
    
    let foundCount = 0;
    for (const path of phase4Paths) {
      if (openapi.paths[path]) {
        foundCount++;
      }
    }
    
    console.log(`Found ${foundCount}/${phase4Paths.length} Phase 4 routes`);
    expect(foundCount).toBeGreaterThanOrEqual(6); // At minimum, core AI routes
  });
});

test.describe('Error Handling', () => {
  test('AI summarize returns proper error for missing thread_id', async ({ request }) => {
    const response = await request.post(`${API_BASE}/api/ai/summarize`, {
      data: {}
    });
    
    expect([400, 422]).toContain(response.status());
  });

  test('RAG query returns proper error for missing query', async ({ request }) => {
    const response = await request.post(`${API_BASE}/api/rag/query`, {
      data: {}
    });
    
    expect([400, 422]).toContain(response.status());
  });

  test('Security risk endpoint handles missing message_id', async ({ request }) => {
    const response = await request.get(`${API_BASE}/api/security/risk-top3`);
    
    // Should require message_id
    expect([400, 422]).toContain(response.status());
  });
});

test.describe('Divergence States', () => {
  test('divergence endpoint returns valid status', async ({ request }) => {
    const response = await request.get(`${API_BASE}/api/metrics/divergence-24h`);
    expect(response.ok()).toBeTruthy();
    
    const data = await response.json();
    
    // Check status thresholds
    if (data.status === 'ok') {
      expect(data.divergence_pct).toBeLessThan(2.0);
    } else if (data.status === 'degraded') {
      expect(data.divergence_pct).toBeGreaterThanOrEqual(2.0);
      expect(data.divergence_pct).toBeLessThanOrEqual(5.0);
    }
    // paused may not have divergence_pct
  });
});
