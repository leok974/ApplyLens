import { test, expect } from "@playwright/test";

const BASE_URL = process.env.BASE_URL ?? "https://applylens.app";

test.describe("prod health + version", () => {
  test("healthz via /api and version card load", async ({ page }) => {
    // 1) Hit /api/healthz directly
    const res = await page.request.get(`${BASE_URL}/api/healthz`);
    expect(res.ok()).toBeTruthy();
    const json = await res.json();
    expect(json.status ?? json.ok ?? "ok").toBeTruthy();

    // 2) Check that settings → About shows a version card
    await page.goto(`${BASE_URL}/settings`, { waitUntil: "load" });
    await page.getByTestId("version-card").waitFor();

    const text = await page.getByTestId("version-card").innerText();
    expect(text).toContain("0.5.2");
  });

  test("API version endpoint returns correct metadata", async ({ page }) => {
    // Test API subdomain version endpoint
    const apiRes = await page.request.get(`https://api.applylens.app/version`);
    expect(apiRes.ok()).toBeTruthy();

    const apiJson = await apiRes.json();
    expect(apiJson.version).toBe("0.5.2");
    expect(apiJson.commit_sha).toBe("912a6b8");
    expect(apiJson.env).toBe("production");
    expect(apiJson.build_time).toBe("2025-11-18T21:07:37Z");

    // Test main domain API proxy version endpoint
    const proxyRes = await page.request.get(`${BASE_URL}/api/version`);
    expect(proxyRes.ok()).toBeTruthy();

    const proxyJson = await proxyRes.json();
    expect(proxyJson.version).toBe("0.5.2");
    expect(proxyJson.commit_sha).toBe("912a6b8");
    expect(proxyJson.env).toBe("production");
  });

  test("nginx proxy routes API requests correctly", async ({ page }) => {
    // Verify that /api/ routes work through nginx proxy
    const healthRes = await page.request.get(`${BASE_URL}/api/healthz`);
    expect(healthRes.ok()).toBeTruthy();

    const versionRes = await page.request.get(`${BASE_URL}/api/version`);
    expect(versionRes.ok()).toBeTruthy();

    // Both should return JSON, not HTML
    expect(healthRes.headers()["content-type"]).toContain("application/json");
    expect(versionRes.headers()["content-type"]).toContain("application/json");
  });
});
