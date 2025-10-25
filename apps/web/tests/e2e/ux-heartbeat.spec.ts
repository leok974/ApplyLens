import { test, expect } from "@playwright/test";
import { installProdReadOnlyGuard } from "../utils/prodGuard";

test.describe("UX Heartbeat", () => {
  test("@prodSafe heartbeat endpoint is CSRF-exempt and accepts payload", async ({ page, request }) => {
    await installProdReadOnlyGuard(page);

    // Call heartbeat endpoint without CSRF token
    const res = await request.post("/api/ux/heartbeat", {
      data: {
        page: "/chat",
        ts: Date.now(),
        meta: { test: true }
      }
    });

    // Should return 200 OK (not 403 CSRF error)
    expect(res.status()).toBe(200);

    // Should return ok: true
    const body = await res.json();
    expect(body).toEqual({ ok: true });
  });

  test("@prodSafe heartbeat endpoint accepts minimal payload", async ({ page, request }) => {
    await installProdReadOnlyGuard(page);

    // Test with minimal required fields
    const res = await request.post("/api/ux/heartbeat", {
      data: {
        page: "/inbox",
        ts: Date.now()
      }
    });

    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body.ok).toBe(true);
  });

  test("@prodSafe heartbeat endpoint accepts meta field", async ({ page, request }) => {
    await installProdReadOnlyGuard(page);

    // Test with meta object
    const res = await request.post("/api/ux/heartbeat", {
      data: {
        page: "/search",
        ts: Date.now(),
        meta: {
          query: "test",
          filters: ["label:interview"],
          viewport: { width: 1920, height: 1080 }
        }
      }
    });

    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body.ok).toBe(true);
  });

  test("@prodSafe heartbeat endpoint validates required fields", async ({ page, request }) => {
    await installProdReadOnlyGuard(page);

    // Test with missing required field (page)
    const res = await request.post("/api/ux/heartbeat", {
      data: {
        ts: Date.now()
      }
    });

    // Should return 422 Unprocessable Entity for validation error
    expect(res.status()).toBe(422);
  });
});
