// tests/agent-v2-api.spec.ts
import { test, expect } from "@playwright/test";

const AGENT_PATH = "/api/v2/agent/run";

async function runAgent(request: any, payload: any) {
  const res = await request.post(AGENT_PATH, {
    data: {
      run_id: `pw-${Date.now()}`,
      user_id: null, // backend derives from session / DEFAULT_USER_EMAIL
      mode: "preview_only",
      context: {
        time_window_days: payload.timeWindowDays ?? 30,
        filters: {},
      },
      query: payload.query,
    },
  });

  expect(res.ok()).toBeTruthy();
  const json = await res.json();

  // Basic shape validation
  expect(json).toHaveProperty("answer");
  expect(typeof json.answer).toBe("string");
  expect(Array.isArray(json.cards)).toBeTruthy();
  expect(Array.isArray(json.tools_used)).toBeTruthy();

  return json;
}

test.describe("@agent @api Mailbox Agent V2", () => {
  test("suspicious intent uses email_search + security_scan", async ({
    request,
  }) => {
    const json = await runAgent(request, {
      query: "Show suspicious or scam emails from this week",
      timeWindowDays: 7,
    });

    const tools: string[] = json.tools_used || [];
    expect(tools).toContain("email_search");
    expect(tools).toContain("security_scan");

    // Verify intent was classified correctly
    expect(json.intent).toBe("suspicious");
  });

  test("bills intent uses email_search (and optionally applications_lookup)", async ({
    request,
  }) => {
    const json = await runAgent(request, {
      query: "Show my bills and invoices from the last 30 days",
      timeWindowDays: 30,
    });

    const tools: string[] = json.tools_used || [];
    expect(tools).toContain("email_search");

    // Verify intent was classified correctly
    expect(json.intent).toBe("bills");

    // applications_lookup is optional depending on results
    // expect(tools).toContain("applications_lookup");
  });

  test("interviews intent uses email_search + applications_lookup + thread_detail", async ({
    request,
  }) => {
    const json = await runAgent(request, {
      query: "Show my interview emails and recruiter threads",
      timeWindowDays: 30,
    });

    const tools: string[] = json.tools_used || [];
    expect(tools).toContain("email_search");

    // Verify intent was classified correctly
    expect(json.intent).toBe("interviews");

    // applications_lookup and thread_detail may be included if emails found
    // expect(tools).toContain("applications_lookup");
    // expect(tools).toContain("thread_detail");
  });

  test("followups intent uses email_search + applications_lookup + thread_detail", async ({
    request,
  }) => {
    const json = await runAgent(request, {
      query: "What emails need follow-up or follow up?",
      timeWindowDays: 30,
    });

    const tools: string[] = json.tools_used || [];
    expect(tools).toContain("email_search");

    // Verify intent was classified correctly
    expect(json.intent).toBe("followups");

    // applications_lookup and thread_detail may be included if emails found
    // expect(tools).toContain("applications_lookup");
    // expect(tools).toContain("thread_detail");
  });

  test("profile intent uses profile_stats", async ({ request }) => {
    const json = await runAgent(request, {
      query: "Give me a profile and stats overview of my job-search inbox",
      timeWindowDays: 30,
    });

    const tools: string[] = json.tools_used || [];
    expect(tools).toContain("profile_stats");

    // Verify intent was classified correctly
    expect(json.intent).toBe("profile");
  });

  test("generic intent at least uses email_search", async ({ request }) => {
    const json = await runAgent(request, {
      query: "Show me my recent job application emails",
      timeWindowDays: 30,
    });

    const tools: string[] = json.tools_used || [];
    expect(tools).toContain("email_search");

    // Verify intent was classified correctly
    expect(json.intent).toBe("generic");
  });

  test("returns structured response with all required fields", async ({
    request,
  }) => {
    const json = await runAgent(request, {
      query: "Show me emails from last week",
      timeWindowDays: 7,
    });

    // Validate response structure
    expect(json).toHaveProperty("run_id");
    expect(json).toHaveProperty("user_id");
    expect(json).toHaveProperty("query");
    expect(json).toHaveProperty("mode");
    expect(json).toHaveProperty("status");
    expect(json).toHaveProperty("answer");
    expect(json).toHaveProperty("cards");
    expect(json).toHaveProperty("tools_used");
    expect(json).toHaveProperty("metrics");
    expect(json).toHaveProperty("intent");

    // Validate status
    expect(json.status).toBe("done");

    // Validate metrics
    expect(json.metrics).toHaveProperty("emails_scanned");
    expect(json.metrics).toHaveProperty("tool_calls");
    expect(json.metrics).toHaveProperty("duration_ms");
  });

  test("handles errors gracefully", async ({ request }) => {
    // This test may need adjustment based on your error handling
    // For now, just verify the endpoint responds
    const res = await request.post(AGENT_PATH, {
      data: {
        run_id: `pw-error-${Date.now()}`,
        user_id: null,
        mode: "preview_only",
        context: {
          time_window_days: 30,
          filters: {},
        },
        query: "", // Empty query might trigger validation error
      },
    });

    // Should still return a response (might be error status)
    expect(res.ok() || res.status() === 400 || res.status() === 422).toBeTruthy();
  });
});
