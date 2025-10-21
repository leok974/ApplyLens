# Email Risk Banner E2E Tests

End-to-end tests for the v3.1 multi-signal phishing detection system, covering API contract validation and UI behavior.

## Test Coverage

### API Tests
- ✅ **Risk advice endpoint** - Returns suspicious=true with score ≥40 for high-risk emails
- ✅ **Explanation contract** - Includes domain mismatch and other v3.1 signals
- ✅ **Feedback endpoint (scam)** - Accepts "scam" verdict and returns email_id
- ✅ **Feedback endpoint (legit)** - Accepts "legit" verdict and returns email_id

### UI Tests
- ✅ **Risk banner visibility** - Red banner appears for suspicious emails
- ✅ **Risk score display** - Score shown in banner header
- ✅ **Explanations list** - "Why it's flagged" section with multiple reasons
- ✅ **Actions list** - "What you should do" recommendations
- ✅ **Verify checks** - "Verify with sender" checklist
- ✅ **Mark as Scam button** - Button visible and clickable
- ✅ **Mark Legit button** - Button visible and clickable
- ✅ **Deep-link support** - Opens email via `?open=<id>` query parameter

## Test Fixture

The test seeds **tc1-brand-mismatch** email that triggers multiple v3.1 signals:
- Brand mention: "Prometric" in body, but domain is `careers-finetunelearning.com`
- SPF neutral + DMARC none
- Reply-To domain mismatch
- Risky phrases: "mini home office"
- PII request: "name, phone, location"

Expected: `suspicious=true`, score 80-105+

## Prerequisites

### 1. Install Playwright

```bash
cd apps/web
npx playwright install --with-deps
```

### 2. Deploy v3.1 Pipeline

Ensure Elasticsearch has the v3.1 pipeline with all 5 processors:

```bash
export ES_URL="http://localhost:9200"
bash scripts/deploy_email_risk_v31.sh
```

### 3. Start Services

```bash
# Terminal 1: API server
cd services/api
uvicorn app.main:app --reload --port 8000

# Terminal 2: Web dev server
cd apps/web
npm run dev
```

## Running Tests

### Quick Start

```bash
cd apps/web

# Run all E2E tests (headless)
npm run e2e

# Run only email risk banner tests
npx playwright test tests/e2e/email-risk-banner.spec.ts

# Run with browser visible (headed mode)
npx playwright test tests/e2e/email-risk-banner.spec.ts --headed

# Run with Playwright UI (interactive)
npx playwright test tests/e2e/email-risk-banner.spec.ts --ui

# Debug mode (step through)
npx playwright test tests/e2e/email-risk-banner.spec.ts --debug
```

### Environment Variables

Customize test targets via environment variables:

```bash
# Use different Elasticsearch instance
ES_URL="http://staging-es:9200" npm run e2e

# Test against different API/web servers
API_BASE="http://localhost:8001" \
WEB_BASE="http://localhost:3000" \
npm run e2e

# Use custom test index
ES_INDEX="gmail_emails-test" npm run e2e

# Use custom pipeline
ES_PIPELINE="applylens_emails_v3_staging" npm run e2e
```

### Full Environment Example

```bash
export ES_URL="http://localhost:9200"
export API_BASE="http://localhost:8000"
export WEB_BASE="http://localhost:5175"
export ES_INDEX="gmail_emails-999999"
export ES_PIPELINE="applylens_emails_v3"

cd apps/web
npm run e2e
```

## Test Structure

```typescript
test.describe("Email Risk Advice (API + UI)", () => {
  // Seeds tc1-brand-mismatch email into Elasticsearch
  test.beforeAll(async ({ playwright }) => {
    // Bulk index via pipeline to trigger v3.1 signal detection
  });

  // API contract validation
  test("API returns suspicious=true with explanations for tc1", async ({ request }) => {
    // GET /emails/tc1-brand-mismatch/risk-advice
    // Asserts: suspicious=true, score ≥40, explanations present
  });

  // UI behavior validation
  test("UI shows red banner with reasons and actions", async ({ page }) => {
    // Deep-link open: /inbox?open=tc1-brand-mismatch
    // Asserts: banner visible, score displayed, lists populated, buttons work
  });

  // Feedback endpoint validation
  test("Feedback endpoint accepts scam verdict", async ({ request }) => {
    // POST /emails/{id}/risk-feedback with verdict: "scam"
    // Asserts: 200 OK, email_id returned
  });

  test("Feedback endpoint accepts legit verdict", async ({ request }) => {
    // POST /emails/{id}/risk-feedback with verdict: "legit"
    // Asserts: 200 OK, email_id returned
  });
});
```

## UI Implementation Notes

### Query Parameter Hook

The test uses `?open=<id>` to deep-link to specific emails. Implementation in `EmailDetailsPanel.tsx`:

```tsx
React.useEffect(() => {
  if (!onOpenEmail) return;
  const params = new URLSearchParams(window.location.search);
  const openId = params.get("open");
  if (openId) {
    onOpenEmail(openId);
    // Clean URL after opening
    const url = new URL(window.location.href);
    url.searchParams.delete("open");
    window.history.replaceState({}, "", url);
  }
}, [onOpenEmail]);
```

### Test IDs in EmailRiskBanner

```tsx
<Card data-testid="risk-banner">
  <span data-testid="risk-score">Score: {score}</span>
  <ul data-testid="risk-explanations">
    {explanations.map(...)}
  </ul>
  <ul data-testid="risk-actions">
    {actions.map(...)}
  </ul>
  <ul data-testid="risk-checks">
    {checks.map(...)}
  </ul>
  <Button data-testid="btn-mark-scam">Mark as Scam</Button>
  <Button data-testid="btn-mark-legit">Mark Legit</Button>
</Card>
```

## Troubleshooting

### Test Fails: "Cannot connect to Elasticsearch"

Ensure Elasticsearch is running and accessible:

```bash
curl http://localhost:9200
```

Start Elasticsearch if needed:

```bash
docker run -d --name es01 \
  -p 9200:9200 \
  -e "discovery.type=single-node" \
  -e "xpack.security.enabled=false" \
  docker.elastic.co/elasticsearch/elasticsearch:8.11.0
```

### Test Fails: "Pipeline not found"

Upload the v3.1 pipeline:

```bash
export ES_URL="http://localhost:9200"
bash scripts/deploy_email_risk_v31.sh
```

Or manually:

```bash
curl -X PUT "http://localhost:9200/_ingest/pipeline/applylens_emails_v3" \
  -H 'Content-Type: application/json' \
  --data-binary @infra/elasticsearch/pipelines/emails_v3.json
```

### Test Fails: "risk-banner not visible"

1. Check API is returning risk advice:
```bash
curl "http://localhost:8000/emails/tc1-brand-mismatch/risk-advice"
```

2. Verify email exists in index:
```bash
curl "http://localhost:9200/gmail_emails-999999/_doc/tc1-brand-mismatch"
```

3. Check pipeline scored it correctly:
```bash
curl "http://localhost:9200/gmail_emails-999999/_search?q=_id:tc1-brand-mismatch&pretty" | jq '._source.suspicion_score'
```

### Test Fails: "Timeout waiting for element"

Increase timeout in test:

```typescript
await expect(banner).toBeVisible({ timeout: 15000 }); // 15 seconds
```

### Test Fails: "explanations list has 0 items"

Check if details are collapsed. Test auto-expands them:

```typescript
const expandButton = page.getByRole("button", { name: /why we flagged/i });
if (await expandButton.isVisible()) {
  await expandButton.click();
}
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: E2E Tests

on: [push, pull_request]

jobs:
  e2e:
    runs-on: ubuntu-latest
    services:
      elasticsearch:
        image: docker.elastic.co/elasticsearch/elasticsearch:8.11.0
        ports:
          - 9200:9200
        env:
          discovery.type: single-node
          xpack.security.enabled: false

    steps:
      - uses: actions/checkout@v4

      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: 20

      - name: Install dependencies
        run: |
          cd apps/web
          npm install
          npx playwright install --with-deps

      - name: Deploy pipeline
        run: |
          ES_URL=http://localhost:9200 bash scripts/deploy_email_risk_v31.sh

      - name: Start API
        run: |
          cd services/api
          pip install -r requirements.txt
          uvicorn app.main:app --port 8000 &

      - name: Run E2E tests
        run: |
          cd apps/web
          ES_URL=http://localhost:9200 \
          API_BASE=http://localhost:8000 \
          WEB_BASE=http://localhost:5175 \
          npm run e2e

      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: playwright-results
          path: apps/web/test-results/
```

## Future Enhancements

### Additional Test Cases

1. **tc2-replyto-mismatch** - Reply-To domain differs from From
2. **tc3-spf-dmarc-fail** - SPF/DKIM/DMARC all fail
3. **tc4-shortener-anchor** - URL shorteners + anchor mismatch
4. **tc5-risky-attachments** - .exe/.docm/.zip attachments
5. **tc6-young-domain** - Newly-registered domain (with enrichment)
6. **tc7-ok-control** - Clean email (should NOT flag)

### Feedback Flow Tests

```typescript
test("Mark as Scam updates UI and ES", async ({ page, request }) => {
  await page.goto(`${WEB_BASE}/inbox?open=tc1-brand-mismatch`);
  await page.getByTestId("btn-mark-scam").click();

  // Toast/snackbar appears
  await expect(page.getByText(/feedback saved/i)).toBeVisible();

  // Verify ES updated
  const res = await request.get(
    `${ES_URL}/gmail_emails-999999/_doc/tc1-brand-mismatch`
  );
  const doc = await res.json();
  expect(doc._source.user_confirmed_scam).toBeTruthy();
  expect(doc._source.user_feedback_verdict).toBe("scam");
});
```

### Prometheus Metrics Tests

```typescript
test("Feedback increments Prometheus counter", async ({ request }) => {
  // Call feedback endpoint
  await request.post(
    `${API_BASE}/emails/tc1-brand-mismatch/risk-feedback`,
    { data: { verdict: "scam" } }
  );

  // Check Prometheus metrics
  const metrics = await request.get(`${API_BASE}/metrics`);
  const text = await metrics.text();
  expect(text).toContain('applylens_email_risk_feedback_total{verdict="scam"}');
});
```

## References

- [Playwright Docs](https://playwright.dev/docs/intro)
- [Email Risk Detection v3.1 Summary](../../../docs/EMAIL_RISK_V3.1_SUMMARY.md)
- [Test Email Generator](../../../docs/TEST_EMAIL_GENERATOR.md)
- [Pipeline Configuration](../../../infra/elasticsearch/pipelines/emails_v3.json)
