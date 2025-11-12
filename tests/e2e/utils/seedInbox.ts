/**
 * Helper to seed inbox threads for E2E tests.
 * Calls the dev-only /api/dev/seed-threads endpoint.
 * Safe to no-op in production (when PROD=1 env var is set).
 */

import { APIRequestContext, expect } from "@playwright/test";

export interface MockThread {
  thread_id: string;
  subject: string;
  from_addr: string;
  risk_level: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  summary_headline: string;
  summary_details: string[];
}

/**
 * Call the dev seed route to ensure /inbox has rows.
 * Safe to no-op/soft-fail in prod (PROD=1).
 */
export async function seedInboxThreads(request: APIRequestContext) {
  if (process.env.PROD === "1") {
    // Don't try to seed prod ever.
    console.log("[SEED] Skipping seed in production environment");
    return;
  }

  // Get API base URL from environment or default to localhost:8003
  const apiBase = process.env.API_BASE_URL || "http://localhost:8003";

  const mockThreads: MockThread[] = [
    {
      thread_id: "test-thread-1",
      subject: "Interview invite: Backend Engineer",
      from_addr: "recruiter@example.com",
      risk_level: "LOW",
      summary_headline: "Recruiter asking to schedule a call",
      summary_details: [
        "They want to schedule an interview",
        "Mentions salary range",
        "Waiting on your availability",
      ],
    },
    {
      thread_id: "test-thread-2",
      subject: "Offer details - Please review",
      from_addr: "hr@examplecorp.com",
      risk_level: "LOW",
      summary_headline: "Offer package attached",
      summary_details: [
        "They sent comp breakdown",
        "They request signature by Friday",
        "They need ID docs",
      ],
    },
    {
      thread_id: "test-thread-3",
      subject: "Follow-up: Your application status",
      from_addr: "hiring@techstartup.io",
      risk_level: "MEDIUM",
      summary_headline: "Application status update",
      summary_details: [
        "Moving to next round",
        "Technical assessment scheduled",
        "Deadline is end of week",
      ],
    },
  ];

  try {
    // Import request from playwright/test to create a new context
    const { request: playwrightRequest } = await import("@playwright/test");

    // Get the storage state (cookies) from the existing request context
    const storageState = await request.storageState();

    console.log(`[SEED] Creating API context with base URL: ${apiBase}`);
    console.log(`[SEED] Storage state has ${storageState.cookies.length} cookies`);

    // Create a new request context pointing to the API server
    const apiContext = await playwrightRequest.newContext({
      baseURL: apiBase,
      storageState: storageState
    });

    console.log(`[SEED] Posting to /api/dev/seed-threads with ${mockThreads.length} threads`);
    const resp = await apiContext.post("/api/dev/seed-threads", {
      data: mockThreads,
    });

    console.log(`[SEED] Response status: ${resp.status()}`);

    // If dev routes are off (403) or not found (404), that's okay in prod CI
    // we just won't get rows and tests will be skipped.
    if (resp.status() === 403) {
      console.log("[SEED] Dev routes disabled (ALLOW_DEV_ROUTES != 1)");
      await apiContext.dispose();
      return;
    }

    if (resp.status() === 404) {
      console.log("[SEED] Dev seed endpoint not found");
      await apiContext.dispose();
      return;
    }

    // Otherwise, expect success
    expect(resp.ok(), `Expected seed request to succeed, got ${resp.status()}`).toBeTruthy();
    const body = await resp.json();
    expect(body.ok).toBeTruthy();
    expect(body.count).toBeGreaterThan(0);

    console.log(`[SEED] Successfully seeded ${body.count} threads`);
    await apiContext.dispose();
  } catch (error) {
    console.error("[SEED] Error seeding inbox:", error);
    // Don't fail the test - just log the error
    // Tests may still pass if real data exists
  }
}
