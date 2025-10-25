import { request } from "@playwright/test";
import * as fs from "node:fs";

const BASE = process.env.PW_BASE_URL ?? "http://localhost:5175";
const STATE = "tests/.auth/demo.json";

export default async () => {
  // Skip auth setup if explicitly disabled (useful for CI without backend)
  if (process.env.SKIP_AUTH === "1") {
    console.log("⏭️  Skipping auth setup (SKIP_AUTH=1)");
    fs.mkdirSync("tests/.auth", { recursive: true });
    fs.writeFileSync(STATE, JSON.stringify({ cookies: [], origins: [] }));
    return;
  }

  console.log("🔐 Setting up demo authentication...");
  const ctx = await request.newContext({ baseURL: BASE });

  try {
    // 1) GET CSRF cookie (same-origin via Vite proxy)
    console.log("   Fetching CSRF token from /api/auth2/google/csrf");
    const csrfRes = await ctx.get("/api/auth2/google/csrf");
    if (!csrfRes.ok()) {
      throw new Error(`CSRF endpoint failed: ${csrfRes.status()} ${await csrfRes.text()}`);
    }

    // Extract CSRF token from cookie (assuming cookie name 'csrf_token')
    const cookies = await ctx.storageState();
    const csrfCookie = cookies.cookies.find(c => c.name === "csrf_token");
    const token = csrfCookie?.value ?? "";

    if (!token) {
      console.warn("⚠️  No CSRF token found in cookies. Proceeding without it.");
    } else {
      console.log("   ✓ CSRF token obtained");
    }

    // 2) POST demo auth with CSRF header
    console.log("   Starting demo session at /api/auth/demo/start");
    const login = await ctx.post("/api/auth/demo/start", {
      headers: {
        "X-CSRF-Token": token,
        "Content-Type": "application/json"
      },
      data: {} // Demo endpoint may not need a body
    });

    if (!login.ok()) {
      const errorText = await login.text();
      throw new Error(`Demo auth failed: ${login.status()} ${errorText}`);
    }

    console.log("   ✓ Demo authentication successful");

    // 3) Save storage state for all tests
    const state = await ctx.storageState();
    fs.mkdirSync("tests/.auth", { recursive: true });
    fs.writeFileSync(STATE, JSON.stringify(state, null, 2));

    console.log(`✅ Auth setup complete! Saved to ${STATE}`);
    console.log(`   Cookies: ${state.cookies.length}`);

  } catch (error) {
    console.error("❌ Auth setup failed:", error);
    throw error;
  } finally {
    await ctx.dispose();
  }
};
