import { Page } from "@playwright/test";

export async function stubApi(page: Page) {
  // Gmail status
  await page.route("**/api/gmail/status", async route => {
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ connected: true, email: "leoklemet.pa@gmail.com" }),
    });
  });

  // Inbox list (minimal fields used by UI)
  await page.route("**/api/inbox**", async route => {
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        total: 3,
        hits: [
          {
            id: "msg-1",
            thread_id: "thr-1",
            subject: "Re: Application confirmation",
            from_name: "jobs@example.com",
            from_email: "jobs@example.com",
            snippet: "Interview scheduled",
            received_at: "2025-10-11T19:55:00Z",
            labels: ["interview", "inbox"],
          },
          {
            id: "msg-2",
            thread_id: "thr-2",
            subject: "Application confirmation",
            from_name: "jobs@example.com",
            from_email: "jobs@example.com",
            snippet: "Thank you for applying",
            received_at: "2025-10-11T18:55:00Z",
            labels: ["inbox"],
          },
          {
            id: "msg-3",
            thread_id: "thr-3",
            subject: "Interview for AI Engineer",
            from_name: "hr@acme.com",
            from_email: "hr@acme.com",
            snippet: "We'd like to schedule an interview",
            received_at: "2025-10-11T17:55:00Z",
            labels: ["interview", "inbox"],
          },
        ],
      }),
    });
  });

  // Email by id
  await page.route("**/api/emails/msg-1", async route => {
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: "msg-1",
        thread_id: "thr-1",
        subject: "Re: Application confirmation",
        from_name: "jobs@example.com",
        from_email: "jobs@example.com",
        received_at: "2025-10-11T19:55:00Z",
        body_text: "Interview scheduled\n\nPlease reply with availability.",
        headers: { "list-unsubscribe": "<mailto:unsub@example.com>" },
      }),
    });
  });

  // Thread for msg-1
  await page.route("**/api/threads/thr-1?**", async route => {
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        messages: [
          {
            id: "msg-1",
            subject: "Re: Application confirmation",
            from_name: "jobs@example.com",
            from_email: "jobs@example.com",
            received_at: "2025-10-11T19:55:00Z",
            snippet: "Interview scheduled",
          },
          {
            id: "msg-1b",
            subject: "Application confirmation",
            from_name: "me@example.com",
            from_email: "me@example.com",
            received_at: "2025-10-11T19:20:00Z",
            snippet: "Thanks, sounds good.",
          },
        ],
      }),
    });
  });

  // Search endpoint (BM25 result set)
  await page.route("**/api/search**", async route => {
    const url = new URL(route.request().url());
    const q = url.searchParams.get("q") ?? "";
    const make = (id: string, subject: string, snippet: string) => ({
      id,
      thread_id: `thr-${id}`,
      subject,
      snippet,
      from_name: "search@example.com",
      from_email: "search@example.com",
      received_at: "2025-10-11T15:00:00Z",
      labels: ["inbox"],
    });
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        total: 2,
        hits: [
          make("s-1", `Found: ${q}`, "snippet one"),
          make("s-2", `Result for ${q}`, "snippet two"),
        ],
      }),
    });
  });

  // Applications tracker list
  await page.route("**/api/applications**", async route => {
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        rows: [
          {
            id: "app-1",
            company: "Acme",
            role: "AI Engineer",
            status: "Interview",
            source: "Greenhouse",
            applied_date: "2025-10-01",
            updated_at: "2025-10-10T10:00:00Z",
          },
          {
            id: "app-2",
            company: "Example Inc",
            role: "Software Engineer",
            status: "Applied",
            source: "Lever",
            applied_date: "2025-10-05",
            updated_at: "2025-10-09T11:00:00Z",
          },
        ],
        total: 2,
      }),
    });
  });

  // Any unknown API: default 200 empty
  await page.route("**/api/**", route => {
    route.fulfill({ status: 200, contentType: "application/json", body: "{}" });
  });
}
