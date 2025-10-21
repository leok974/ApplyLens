import { test, expect, request } from "@playwright/test";

const ES_URL = process.env.ES_URL || "http://localhost:9200";
const API_BASE = process.env.API_BASE || "http://localhost:8000";
const WEB_BASE = process.env.WEB_BASE || "http://localhost:5175";
const TEST_INDEX = process.env.ES_INDEX || "gmail_emails-999999";
const PIPELINE = process.env.ES_PIPELINE || "applylens_emails_v3";

// Minimally seed one high-risk email (tc1_brand_mismatch)
async function seedTestDoc(api: any) {
  // ensure index exists (dev settings)
  await api.put(`${ES_URL}/${TEST_INDEX}`, {
    data: { settings: { number_of_shards: 1, number_of_replicas: 0 } },
    failOnStatusCode: false, // ok if it already exists
  });

  const doc = {
    subject: "You're Invited: Software Developer Interview",
    from: "Terell Johnson <remotetech@careers-finetunelearning.com>",
    reply_to: "interview@careers-finetunelearning.com",
    headers_authentication_results:
      "mx.google.com; spf=neutral; dkim=pass header.d=careers-finetunelearning.com; dmarc=none",
    headers_received_spf:
      "neutral (google.com: 203.0.113.8 is neither permitted nor denied)",
    body_text:
      "Thanks for your interest in Prometric / Finetune. A mini home office will be arranged. Please reply with your name, phone, location. Executive team assigns projects. Work from anywhere. Flexible hours.",
    body_html:
      "<p>Thanks for your interest in <b>Prometric</b> / <b>Finetune</b>. A <i>mini home office</i> will be arranged. Please reply with your name, phone, location.</p>",
    attachments: [],
    received_at: new Date().toISOString(),
    labels_norm: [],
  };

  // bulk index via pipeline to trigger v3 logic
  const ndjson =
    JSON.stringify({ index: { _index: TEST_INDEX, _id: "tc1-brand-mismatch" } }) +
    "\n" +
    JSON.stringify(doc) +
    "\n";

  const res = await api.post(
    `${ES_URL}/_bulk?pipeline=${encodeURIComponent(PIPELINE)}`,
    {
      data: ndjson,
      headers: { "Content-Type": "application/x-ndjson" },
    }
  );
  expect(res.ok()).toBeTruthy();
  const body = await res.json();
  expect(body.errors ?? false).toBeFalsy();
}

test.describe("Email Risk Advice (API + UI)", () => {
  test.beforeAll(async ({ playwright }) => {
    const api = await request.newContext();
    await seedTestDoc(api);
    // Brief wait for indexing
    await new Promise((resolve) => setTimeout(resolve, 1000));
  });

  test("API returns suspicious=true with explanations for tc1", async ({
    request,
  }) => {
    // The API reads from alias/index your backend is configured with.
    // If your API expects the email to exist there, add a nightly alias or reindex in your env.
    const res = await request.get(
      `${API_BASE}/emails/tc1-brand-mismatch/risk-advice`
    );
    expect(res.ok()).toBeTruthy();

    const json = await res.json();
    expect(json).toHaveProperty("suspicious");
    expect(json.suspicious).toBeTruthy();
    expect(json).toHaveProperty("suspicion_score");
    expect(json.suspicion_score).toBeGreaterThanOrEqual(40);
    expect(Array.isArray(json.explanations)).toBeTruthy();
    expect(json.explanations.length).toBeGreaterThan(0);

    // common reasons for this fixture
    const reasons = json.explanations.join(" | ").toLowerCase();
    expect(
      reasons.includes("domain") || reasons.includes("non-canonical")
    ).toBeTruthy();
  });

  test("UI shows red banner with reasons and actions", async ({ page }) => {
    // Deep-link open (requires tiny hook in the UI: ?open=<id>)
    await page.goto(`${WEB_BASE}/inbox?open=tc1-brand-mismatch`, {
      waitUntil: "networkidle",
    });

    const banner = page.getByTestId("risk-banner");
    await expect(banner).toBeVisible({ timeout: 10000 });

    // Score present
    await expect(page.getByTestId("risk-score")).toBeVisible();

    // Expand details if collapsed
    const expandButton = page.getByRole("button", { name: /why we flagged/i });
    if (await expandButton.isVisible()) {
      await expandButton.click();
    }

    // Reasons present
    const reasons = page.getByTestId("risk-explanations");
    await expect(reasons).toBeVisible();
    const reasonItems = reasons.locator("li");
    expect(await reasonItems.count()).toBeGreaterThan(0);

    // Actions present
    await expect(page.getByTestId("risk-actions")).toBeVisible();
    await expect(page.getByTestId("risk-checks")).toBeVisible();

    // Buttons work (we don't assert ES change here, only UI click flow)
    await expect(page.getByTestId("btn-mark-scam")).toBeVisible();
    await expect(page.getByTestId("btn-mark-legit")).toBeVisible();
  });

  test("Feedback endpoint accepts scam verdict", async ({ request }) => {
    const res = await request.post(
      `${API_BASE}/emails/tc1-brand-mismatch/risk-feedback`,
      {
        data: { verdict: "scam" },
        headers: { "Content-Type": "application/json" },
      }
    );
    expect(res.ok()).toBeTruthy();

    const json = await res.json();
    expect(json).toHaveProperty("email_id");
    expect(json.email_id).toBe("tc1-brand-mismatch");
  });

  test("Feedback endpoint accepts legit verdict", async ({ request }) => {
    const res = await request.post(
      `${API_BASE}/emails/tc1-brand-mismatch/risk-feedback`,
      {
        data: { verdict: "legit" },
        headers: { "Content-Type": "application/json" },
      }
    );
    expect(res.ok()).toBeTruthy();

    const json = await res.json();
    expect(json).toHaveProperty("email_id");
    expect(json.email_id).toBe("tc1-brand-mismatch");
  });
});
