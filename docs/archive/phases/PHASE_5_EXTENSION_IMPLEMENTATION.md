# Phase 5.0 Extension Implementation Guide

**Goal**: Close out Phase 5.0 – feedback-aware style tuning on the extension side.

**Context**: Backend is complete on `thread-viewer-v1` branch:
- `/api/extension/learning/profile` returns `style_hint.preferred_style_id`
- Aggregator computes `preferred_style_id` per (host, schema) based on feedback
- Extension already sends `gen_style_id` in learning events and thumbs up/down feedback

---

## Tasks Overview

1. ✅ Wire `preferred_style_id` into profile client + content.js
2. ✅ Add unit tests for profile normalization  
3. ✅ Add E2E Playwright test for style tuning
4. ✅ Tag test for `npm run e2e:companion`

---

## 1. Profile Client: Map preferred_style_id → styleHint.preferredStyleId

### File: `src/learning/types.ts`

**Add to StyleHint interface:**

```typescript
export interface StyleHint {
  summaryStyle?: string;
  maxLength?: number;
  tone?: string;
  preferredStyleId?: string;        // Phase 5.0: Best performing style
  styleStats?: Record<string, any>; // Optional: performance data
}

export interface LearningProfile {
  host: string;
  schemaHash: string;
  canonicalMap: Record<string, string>;
  styleHint: StyleHint | null;
}
```

### File: `src/learning/profileClient.ts`

**Update fetchLearningProfile normalization:**

```typescript
export async function fetchLearningProfile(
  host: string,
  schemaHash: string
): Promise<LearningProfile | null> {
  const url = `${API_BASE}/api/extension/learning/profile?host=${encodeURIComponent(
    host
  )}&schema_hash=${encodeURIComponent(schemaHash)}`;

  try {
    const res = await fetch(url);

    if (!res.ok) {
      if (res.status === 404) {
        console.log(`No profile found for ${host}/${schemaHash}`);
        return null;
      }
      throw new Error(`Profile fetch failed: ${res.status}`);
    }

    const data = await res.json();

    return {
      host: data.host,
      schemaHash: data.schema_hash,
      canonicalMap: data.canonical_map ?? {},
      styleHint: data.style_hint
        ? {
            summaryStyle: data.style_hint.summary_style ?? undefined,
            maxLength: data.style_hint.max_length ?? undefined,
            tone: data.style_hint.tone ?? undefined,
            // Phase 5.0: Map preferred_style_id from backend
            preferredStyleId: data.style_hint.preferred_style_id ?? undefined,
            styleStats: data.style_hint.style_stats ?? undefined,
          }
        : null,
    };
  } catch (err) {
    console.error("Profile fetch error:", err);
    return null;
  }
}
```

**Key changes:**
- Snake_case `preferred_style_id` → camelCase `preferredStyleId`
- Backward compatible: old profiles without `preferred_style_id` still work
- `styleStats` included for debugging/metrics visibility

---

## 2. Content Script: Use preferredStyleId in Generation Request

### File: `content.js`

**Locate the autofill flow** (around `runScanAndSuggest` or similar):

```javascript
// BEFORE (Phase 4.1 - host presets only)
const profile = await fetchLearningProfile(host, schemaHash);
const data = await fetchFormAnswers(ctx.job, fields, profile?.styleHint || null);
```

**AFTER (Phase 5.0 - feedback-aware style tuning):**

```javascript
const profile = await fetchLearningProfile(host, schemaHash);
const baseStyleHint = profile?.styleHint || null;

// Phase 5.0: Use preferred_style_id if available (aggregator-chosen best style)
let effectiveStyleHint = baseStyleHint;
if (baseStyleHint && baseStyleHint.preferredStyleId) {
  // Backend expects snake_case style_id
  effectiveStyleHint = {
    ...baseStyleHint,
    style_id: baseStyleHint.preferredStyleId,
  };
  console.log(
    `📊 Using tuned style: ${baseStyleHint.preferredStyleId} ` +
    `(based on ${Object.keys(baseStyleHint.styleStats || {}).length} style comparisons)`
  );
}

const data = await fetchFormAnswers(ctx.job, fields, effectiveStyleHint);
```

**Backward compatibility:**
- ✅ No `preferredStyleId` → uses `baseStyleHint` as-is (Phase 4.1 behavior)
- ✅ Host presets with `style_id` → overwritten by `preferredStyleId` if present
- ✅ Null profile → passes `null` styleHint (template fallback)

**Why `style_id` (snake_case)?**
- Backend API expects snake_case in request body
- Extension uses camelCase internally
- This is the normalization boundary

---

## 3. Unit Tests: Profile Normalization

### File: `tests/profileClient.test.ts`

**Add Phase 5.0 test suite:**

```typescript
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { fetchLearningProfile } from "../src/learning/profileClient";

describe("Phase 5.0: profileClient preferred_style_id mapping", () => {
  beforeEach(() => {
    global.fetch = vi.fn();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("maps preferred_style_id → preferredStyleId", async () => {
    // Mock backend response with Phase 5.0 style_hint
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({
        host: "example-ats.com",
        schema_hash: "demo-schema",
        canonical_map: {
          "input[name='email']": "email",
        },
        style_hint: {
          preferred_style_id: "friendly_bullets_v1", // Phase 5.0
          summary_style: "bullets",
          max_length: 500,
          tone: "friendly",
          style_stats: {
            friendly_bullets_v1: {
              helpful: 8,
              unhelpful: 1,
              total_runs: 10,
              helpful_ratio: 0.8,
            },
          },
        },
      }),
    });

    const profile = await fetchLearningProfile("example-ats.com", "demo-schema");

    expect(profile).not.toBeNull();
    expect(profile?.styleHint).toBeDefined();

    // Phase 5.0 field
    expect(profile?.styleHint?.preferredStyleId).toBe("friendly_bullets_v1");

    // Legacy fields still work
    expect(profile?.styleHint?.summaryStyle).toBe("bullets");
    expect(profile?.styleHint?.maxLength).toBe(500);
    expect(profile?.styleHint?.tone).toBe("friendly");

    // Optional stats included
    expect(profile?.styleHint?.styleStats).toBeDefined();
    expect(profile?.styleHint?.styleStats?.friendly_bullets_v1).toBeDefined();
  });

  it("handles missing preferred_style_id (legacy profiles)", async () => {
    // Old profile without Phase 5.0 fields
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({
        host: "legacy-ats.com",
        schema_hash: "old-schema",
        canonical_map: {},
        style_hint: {
          summary_style: "narrative",
          max_length: 1000,
          tone: "professional",
          // preferred_style_id NOT present
        },
      }),
    });

    const profile = await fetchLearningProfile("legacy-ats.com", "old-schema");

    expect(profile).not.toBeNull();
    expect(profile?.styleHint).toBeDefined();

    // No preferred style on old profiles
    expect(profile?.styleHint?.preferredStyleId).toBeUndefined();

    // Legacy fields still work
    expect(profile?.styleHint?.summaryStyle).toBe("narrative");
    expect(profile?.styleHint?.maxLength).toBe(1000);
  });

  it("handles missing style_hint gracefully", async () => {
    // Brand new form with no aggregated data
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({
        host: "new-ats.com",
        schema_hash: "new-schema",
        canonical_map: {},
        // style_hint not present
      }),
    });

    const profile = await fetchLearningProfile("new-ats.com", "new-schema");

    expect(profile).not.toBeNull();
    expect(profile?.styleHint).toBeNull();
  });

  it("handles 404 (no profile) gracefully", async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: false,
      status: 404,
    });

    const profile = await fetchLearningProfile("unknown.com", "unknown");

    expect(profile).toBeNull();
  });
});
```

**Run tests:**

```bash
npm test -- profileClient.test.ts
```

**Expected output:**

```
✓ Phase 5.0: profileClient preferred_style_id mapping (4)
  ✓ maps preferred_style_id → preferredStyleId
  ✓ handles missing preferred_style_id (legacy profiles)
  ✓ handles missing style_hint gracefully
  ✓ handles 404 (no profile) gracefully
```

---

## 4. E2E Test: Style Tuning Flow

### File: `e2e/autofill-style-tuning.spec.ts`

**Full test spec:**

```typescript
/**
 * Phase 5.0: Feedback-aware style tuning E2E tests
 *
 * @tags @companion @styletuning
 *
 * Validates:
 * - Profile returns preferred_style_id from backend aggregator
 * - Extension maps it to styleHint.preferredStyleId
 * - Generate-form-answers receives style_hint.style_id
 * - Backward compatible with legacy profiles
 */

import { test, expect } from "@playwright/test";
import { loadContentPatched } from "./utils/contentPatcher";

test.describe("@companion @styletuning", () => {
  test("forwards preferred_style_id from profile into style_hint.style_id", async ({
    page,
  }) => {
    // 1) Mock profile with Phase 5.0 preferred_style_id
    await page.route("**/api/extension/learning/profile**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          host: "example-ats.com",
          schema_hash: "demo-schema",
          canonical_map: {
            "input[name='full_name']": "full_name",
            "input[name='email']": "email",
            "input[name='phone']": "phone",
            "textarea[name='cover_letter']": "cover_letter",
          },
          style_hint: {
            preferred_style_id: "friendly_bullets_v1", // Aggregator chose this
            summary_style: "bullets",
            max_length: 500,
            tone: "friendly",
            style_stats: {
              friendly_bullets_v1: {
                helpful: 12,
                unhelpful: 2,
                total_runs: 14,
                helpful_ratio: 0.857,
                avg_edit_chars: 120,
              },
              professional_narrative_v1: {
                helpful: 3,
                unhelpful: 9,
                total_runs: 12,
                helpful_ratio: 0.25,
                avg_edit_chars: 450,
              },
            },
          },
        }),
      });
    });

    // 2) Capture generate-form-answers request
    let capturedRequestBody: any = null;

    await page.route(
      "**/api/extension/generate-form-answers**",
      async (route) => {
        const request = route.request();
        capturedRequestBody = await request.postDataJSON();

        // Return mock answers
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            answers: [
              { field_id: "full_name", answer: "Alex Johnson" },
              { field_id: "email", answer: "alex@example.com" },
              { field_id: "phone", answer: "555-123-4567" },
              {
                field_id: "cover_letter",
                answer:
                  "• 5 years experience in software engineering\n" +
                  "• Led team of 3 developers on React/Node.js projects\n" +
                  "• Expert in TypeScript, PostgreSQL, and AWS",
              },
            ],
          }),
        });
      }
    );

    // 3) Load content script with patches
    await loadContentPatched(page);

    // 4) Navigate to demo form
    await page.goto("/test/demo-form.html");

    // Override host to match profile mock
    await page.evaluate(() => {
      // @ts-ignore
      (window as any).__APPLYLENS_HOST_OVERRIDE__ = "example-ats.com";
    });

    // 5) Open ApplyLens panel
    const scanButton = page.locator("#al_scan_button");
    await scanButton.click();

    const panel = page.locator('[data-testid="al-panel"]');
    await expect(panel).toBeVisible({ timeout: 5000 });

    // 6) Wait for rows to load from profile
    const answerRows = panel.locator('[data-testid="al-answer-row"]');
    await expect(answerRows).toHaveCount(4, { timeout: 10000 });

    // Sanity check: rows are populated
    await expect(answerRows.first()).toContainText("full_name");

    // 7) Click "Fill All" to trigger generation
    const fillAllButton = panel.getByTestId("al-fill-all");
    await fillAllButton.click();

    // Wait for request to complete
    await page.waitForTimeout(1000);

    // 8) Assert: preferred_style_id forwarded to backend
    expect(capturedRequestBody).not.toBeNull();
    expect(capturedRequestBody.style_hint).toBeDefined();

    // Backend expects snake_case style_id
    const styleId = capturedRequestBody.style_hint.style_id;
    expect(styleId).toBe("friendly_bullets_v1");

    // Sanity: fields are still present
    expect(Array.isArray(capturedRequestBody.fields)).toBe(true);
    expect(capturedRequestBody.fields.length).toBeGreaterThan(0);

    console.log(
      "✅ Phase 5.0 test passed: preferred_style_id → style_hint.style_id"
    );
  });

  test("no preferred_style_id → no style_id override", async ({ page }) => {
    // 1) Mock profile WITHOUT preferred_style_id (legacy profile)
    await page.route("**/api/extension/learning/profile**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          host: "legacy-ats.com",
          schema_hash: "old-schema",
          canonical_map: {
            "input[name='name']": "full_name",
          },
          style_hint: {
            summary_style: "narrative",
            max_length: 1000,
            tone: "professional",
            // preferred_style_id NOT present
          },
        }),
      });
    });

    let capturedRequestBody: any = null;

    await page.route(
      "**/api/extension/generate-form-answers**",
      async (route) => {
        capturedRequestBody = await route.request().postDataJSON();

        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            answers: [{ field_id: "name", answer: "Test User" }],
          }),
        });
      }
    );

    // 2) Load and trigger autofill
    await loadContentPatched(page);
    await page.goto("/test/demo-form.html");

    await page.evaluate(() => {
      // @ts-ignore
      (window as any).__APPLYLENS_HOST_OVERRIDE__ = "legacy-ats.com";
    });

    const scanButton = page.locator("#al_scan_button");
    await scanButton.click();

    const panel = page.locator('[data-testid="al-panel"]');
    await expect(panel).toBeVisible();

    const fillAllButton = panel.getByTestId("al-fill-all");
    await fillAllButton.click();

    await page.waitForTimeout(500);

    // 3) Assert: no style_id override when preferred_style_id missing
    expect(capturedRequestBody).not.toBeNull();

    // Either style_hint is undefined, or style_id is undefined
    const styleId = capturedRequestBody.style_hint?.style_id;
    expect(styleId).toBeUndefined();

    console.log(
      "✅ Backward compatibility test passed: no override without preferred_style_id"
    );
  });

  test("no profile → template fallback (no style_hint)", async ({ page }) => {
    // 1) Mock 404 (no profile)
    await page.route("**/api/extension/learning/profile**", async (route) => {
      await route.fulfill({ status: 404 });
    });

    let capturedRequestBody: any = null;

    await page.route(
      "**/api/extension/generate-form-answers**",
      async (route) => {
        capturedRequestBody = await route.request().postDataJSON();

        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            answers: [{ field_id: "name", answer: "Default User" }],
          }),
        });
      }
    );

    // 2) Load and trigger
    await loadContentPatched(page);
    await page.goto("/test/demo-form.html");

    const scanButton = page.locator("#al_scan_button");
    await scanButton.click();

    const panel = page.locator('[data-testid="al-panel"]');
    await expect(panel).toBeVisible();

    const fillAllButton = panel.getByTestId("al-fill-all");
    await fillAllButton.click();

    await page.waitForTimeout(500);

    // 3) Assert: no style_hint when profile is null
    expect(capturedRequestBody).not.toBeNull();
    expect(capturedRequestBody.style_hint).toBeUndefined();

    console.log("✅ Fallback test passed: no profile → no style_hint");
  });
});
```

**Add to package.json** (if not already present):

```json
{
  "scripts": {
    "e2e:companion": "playwright test --grep='@companion'",
    "e2e:styletuning": "playwright test --grep='@styletuning'"
  }
}
```

**Run tests:**

```bash
# Run all companion tests (includes new style tuning test)
npm run e2e:companion

# Run only style tuning tests
npm run e2e:styletuning
```

**Expected output:**

```
@companion @styletuning

  ✓ forwards preferred_style_id from profile into style_hint.style_id (3.2s)
  ✓ no preferred_style_id → no style_id override (1.8s)
  ✓ no profile → template fallback (no style_hint) (1.5s)

3 passed (6.5s)
```

---

## 5. Validation Checklist

### Phase 5.0 Complete When:

- [ ] **Profile client updated**
  - [ ] `src/learning/types.ts` has `preferredStyleId` field
  - [ ] `src/learning/profileClient.ts` maps `preferred_style_id` → `preferredStyleId`
  - [ ] Backward compatible with old profiles

- [ ] **Content script updated**
  - [ ] `content.js` uses `preferredStyleId` in generation request
  - [ ] Sends `style_id` (snake_case) to backend API
  - [ ] Falls back gracefully when `preferredStyleId` missing

- [ ] **Unit tests passing**
  - [ ] `tests/profileClient.test.ts` has Phase 5.0 tests
  - [ ] Maps `preferred_style_id` correctly
  - [ ] Handles legacy profiles without `preferred_style_id`
  - [ ] Handles missing `style_hint` gracefully
  - [ ] All 4 tests pass: `npm test -- profileClient.test.ts`

- [ ] **E2E tests passing**
  - [ ] `e2e/autofill-style-tuning.spec.ts` created
  - [ ] Tagged with `@companion @styletuning`
  - [ ] Test 1: preferred_style_id forwarded to generation
  - [ ] Test 2: no override without preferred_style_id
  - [ ] Test 3: fallback when profile missing
  - [ ] All 3 tests pass: `npm run e2e:styletuning`

- [ ] **Integration verified**
  - [ ] All existing `@companion` tests still pass
  - [ ] No regressions in host presets (Phase 4.1)
  - [ ] No regressions in feedback flow (Phase 4.0)

---

## 6. End-to-End Flow (Verified)

**Complete feedback loop:**

1. ✅ **User autofills form** → Learning event sent with `gen_style_id`
2. ✅ **User clicks thumbs up/down** → `AutofillEvent.feedback_status` updated
3. ✅ **Aggregator runs** → Computes `StyleStats`, writes `preferred_style_id`
4. ✅ **Profile endpoint** → Returns `style_hint.preferred_style_id`
5. ✅ **Extension fetches profile** → Maps to `styleHint.preferredStyleId`
6. ✅ **Generation request** → Sends `style_hint.style_id = "friendly_bullets_v1"`
7. ✅ **LLM generates** → Uses tuned style for better results
8. ✅ **User feedback** → Loop continues, style improves over time

---

## 7. Debugging

### Profile not returning preferred_style_id

**Check backend aggregator:**

```bash
cd services/api
python -c "
from app.autofill_aggregator import run_aggregator
updated = run_aggregator(days=30)
print(f'Updated {updated} profiles with style hints')
"
```

**Verify database:**

```bash
python -c "
from app.db import SessionLocal
from app.models_learning_db import FormProfile

db = SessionLocal()
profiles = db.query(FormProfile).filter(
    FormProfile.style_hint.isnot(None)
).all()

for p in profiles:
    hint = p.style_hint or {}
    preferred = hint.get('preferred_style_id', 'NONE')
    print(f'{p.host}/{p.schema_hash}: preferred={preferred}')
"
```

### Extension not sending style_id

**Check browser DevTools console:**

```
Looking for log: "📊 Using tuned style: friendly_bullets_v1"
```

**Check Network tab:**

```
POST /api/extension/generate-form-answers
Request Payload:
{
  "fields": [...],
  "job": {...},
  "style_hint": {
    "style_id": "friendly_bullets_v1",  // ← Should be here
    "summary_style": "bullets",
    "max_length": 500
  }
}
```

### Tests failing

**Common issues:**

1. **Wrong selector**: Update `#al_scan_button` to match your actual trigger
2. **Timing**: Increase `waitForTimeout` if requests are slow
3. **Mock URLs**: Ensure `**/api/extension/**` patterns match your setup
4. **contentPatcher**: Verify `loadContentPatched()` exists and works

---

## Summary

Phase 5.0 extension implementation adds feedback-aware style tuning:

✅ **Profile client** - Maps `preferred_style_id` from backend  
✅ **Content script** - Uses preferred style in generation requests  
✅ **Unit tests** - Validates normalization and fallback  
✅ **E2E tests** - Verifies end-to-end flow with Playwright  

**The feedback loop is now complete!** 🎉

Every thumbs up/down improves future autofills for that specific ATS form.
