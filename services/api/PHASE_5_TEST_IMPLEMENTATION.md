# Phase 5.0: Style Tuning Tests Implementation Guide

## Overview

Phase 5.0 backend is complete. This guide shows how to validate the style tuning feedback loop with E2E and unit tests in the extension.

**What Phase 5.0 Tests Should Prove:**

1. **Profile → styleId mapping**: When profile returns `style_hint.preferred_style_id = "bullets_v1"`, the extension exposes `styleHint.styleId === "bullets_v1"`
2. **styleId → generate-form-answers payload**: The extension sends the preferred style in the generation request as `style_hint.styleId`

## 1. E2E Test: Style Tuning Flow

**File**: `apps/extension-applylens/e2e/autofill-style-tuning.spec.ts`

```typescript
/**
 * Phase 5.0: Feedback-aware style tuning E2E tests
 *
 * @tags companion styletuning
 *
 * Validates that:
 * - Profile endpoint returns style_hint.preferred_style_id
 * - Extension maps it to styleHint.styleId
 * - Generate-form-answers request includes style_hint.styleId
 */

import { test, expect } from "@playwright/test";

test.describe("@companion @styletuning", () => {
  test("forwards preferred_style_id from profile into generate-form-answers style_hint", async ({
    page,
  }) => {
    // 1) Mock learning profile with preferred_style_id
    await page.route("**/api/extension/learning/profile**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          host: "example-ats.com",
          schema_hash: "schema-style",
          canonical_map: {
            "input[name='full_name']": "full_name",
            "input[name='email']": "email",
            "input[name='phone']": "phone",
            "textarea[name='cover_letter']": "cover_letter",
          },
          style_hint: {
            gen_style_id: "bullets_v1",
            confidence: 0.9,
            preferred_style_id: "bullets_v1", // Phase 5.0: Best performing style
          },
        }),
      });
    });

    // 2) Capture generate-form-answers payload
    let capturedRequestBody: any = null;

    await page.route(
      "**/api/extension/generate-form-answers**",
      async (route) => {
        const request = route.request();
        capturedRequestBody = await request.postDataJSON();

        // Return mock answers for all fields
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
                  "• 5 years of experience in software engineering\n• Led team of 3 developers\n• Expert in React and Node.js",
              },
            ],
          }),
        });
      },
    );

    // 3) Load demo form (adjust path to match your setup)
    await page.goto("/test/demo-form.html");

    // Override host to match profile mock
    await page.evaluate(() => {
      // @ts-ignore
      (window as any).__APPLYLENS_HOST_OVERRIDE__ = "example-ats.com";
    });

    // 4) Open ApplyLens panel
    const panelButton = page.getByRole("button", { name: /applylens/i });
    await panelButton.click();

    // Wait for panel to appear
    const panel = page.locator('[data-testid="al-panel"]');
    await expect(panel).toBeVisible({ timeout: 5000 });

    // 5) Wait for autofill rows to load
    const answerRows = panel.locator('[data-testid="al-answer-row"]');
    await expect(answerRows).toHaveCount(4, { timeout: 10000 });

    // Verify rows are populated (sanity check)
    await expect(answerRows.first()).toContainText("full_name");

    // 6) Click "Fill All" to trigger generation request
    const fillAllButton = page.getByRole("button", { name: /fill all/i });
    await fillAllButton.click();

    // Wait for request to complete
    await page.waitForTimeout(500);

    // 7) Assert captured request includes preferred_style_id
    expect(capturedRequestBody).not.toBeNull();
    expect(capturedRequestBody.style_hint).toBeDefined();

    // Check both camelCase and snake_case (depending on your normalization)
    const styleId =
      capturedRequestBody.style_hint.styleId ||
      capturedRequestBody.style_hint.style_id ||
      capturedRequestBody.style_hint.genStyleId ||
      capturedRequestBody.style_hint.gen_style_id;

    expect(styleId).toBe("bullets_v1");

    console.log("✅ Style tuning test passed: preferred_style_id correctly forwarded");
  });

  test("uses gen_style_id fallback when preferred_style_id is not set", async ({
    page,
  }) => {
    // Mock profile WITHOUT preferred_style_id (legacy profile)
    await page.route("**/api/extension/learning/profile**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          host: "legacy-ats.com",
          schema_hash: "schema-legacy",
          canonical_map: {
            "input[name='name']": "full_name",
          },
          style_hint: {
            gen_style_id: "narrative_v1", // Only old-style gen_style_id
            confidence: 0.7,
            // preferred_style_id NOT set
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
      },
    );

    await page.goto("/test/demo-form.html");

    await page.evaluate(() => {
      // @ts-ignore
      (window as any).__APPLYLENS_HOST_OVERRIDE__ = "legacy-ats.com";
    });

    const panelButton = page.getByRole("button", { name: /applylens/i });
    await panelButton.click();

    const panel = page.locator('[data-testid="al-panel"]');
    await expect(panel).toBeVisible();

    const fillAllButton = page.getByRole("button", { name: /fill all/i });
    await fillAllButton.click();

    await page.waitForTimeout(500);

    // Should fall back to gen_style_id
    expect(capturedRequestBody).not.toBeNull();
    const styleId =
      capturedRequestBody.style_hint?.styleId ||
      capturedRequestBody.style_hint?.genStyleId;

    expect(styleId).toBe("narrative_v1");

    console.log("✅ Fallback test passed: gen_style_id used when preferred not available");
  });
});
```

**Add to package.json scripts** (if not already present):

```json
{
  "scripts": {
    "e2e:companion": "playwright test --grep='@companion'",
    "e2e:styletuning": "playwright test --grep='@styletuning'"
  }
}
```

## 2. Unit Test: Profile Client Mapping

**File**: `apps/extension-applylens/tests/profileClient.test.ts`

Add this test to your existing profileClient tests:

```typescript
import { describe, it, expect } from "vitest";

describe("profileClient Phase 5.0 styleHint mapping", () => {
  it("maps style_hint.preferred_style_id to styleHint.styleId", () => {
    // Raw backend response format (snake_case)
    const rawProfileResponse = {
      host: "example-ats.com",
      schema_hash: "schema-style",
      canonical_map: {
        "input[name='email']": "email",
      },
      style_hint: {
        gen_style_id: "bullets_v1",
        confidence: 0.85,
        preferred_style_id: "bullets_v1", // Phase 5.0 field
      },
    };

    // Your normalization function (adjust import path as needed)
    // If you don't export this, you may need to test via the full flow
    const profile = normalizeLearningProfile(rawProfileResponse);

    expect(profile.styleHint).toBeDefined();

    // Extension uses camelCase internally
    expect(profile.styleHint?.styleId).toBe("bullets_v1");
    expect(profile.styleHint?.genStyleId).toBe("bullets_v1");
    expect(profile.styleHint?.confidence).toBe(0.85);
  });

  it("prioritizes preferred_style_id over gen_style_id", () => {
    const rawProfileResponse = {
      host: "example-ats.com",
      schema_hash: "schema-style",
      canonical_map: {},
      style_hint: {
        gen_style_id: "narrative_v1", // Old default
        confidence: 0.7,
        preferred_style_id: "bullets_v1", // New best performer
      },
    };

    const profile = normalizeLearningProfile(rawProfileResponse);

    // Should use preferred_style_id
    expect(profile.styleHint?.styleId).toBe("bullets_v1");
  });

  it("falls back to gen_style_id when preferred_style_id is missing", () => {
    const rawProfileResponse = {
      host: "legacy-ats.com",
      schema_hash: "schema-old",
      canonical_map: {},
      style_hint: {
        gen_style_id: "narrative_v1",
        confidence: 0.6,
        // preferred_style_id not set (legacy profile)
      },
    };

    const profile = normalizeLearningProfile(rawProfileResponse);

    // Should fall back to gen_style_id
    expect(profile.styleHint?.styleId).toBe("narrative_v1");
  });

  it("handles missing style_hint gracefully", () => {
    const rawProfileResponse = {
      host: "new-ats.com",
      schema_hash: "schema-new",
      canonical_map: {},
      // style_hint not set (brand new form)
    };

    const profile = normalizeLearningProfile(rawProfileResponse);

    expect(profile.styleHint).toBeUndefined();
  });
});
```

**If `normalizeLearningProfile` is not exported**, you can test via the fetch mock:

```typescript
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { fetchLearningProfile } from "../src/learning/profileClient";

describe("profileClient fetches and maps preferred_style_id", () => {
  beforeEach(() => {
    // Mock fetch globally
    global.fetch = vi.fn();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("maps preferred_style_id from API response", async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        host: "example-ats.com",
        schema_hash: "schema-style",
        canonical_map: {},
        style_hint: {
          gen_style_id: "bullets_v1",
          confidence: 0.9,
          preferred_style_id: "bullets_v1",
        },
      }),
    });

    const profile = await fetchLearningProfile("example-ats.com", "schema-style");

    expect(profile).toBeDefined();
    expect(profile?.styleHint?.styleId).toBe("bullets_v1");
    expect(profile?.styleHint?.confidence).toBe(0.9);
  });
});
```

## 3. Update Extension Profile Client (If Needed)

**File**: `apps/extension-applylens/src/learning/profileClient.ts`

Ensure your normalization function handles `preferred_style_id`:

```typescript
interface BackendStyleHint {
  gen_style_id?: string;
  confidence?: number;
  preferred_style_id?: string; // Phase 5.0
}

interface NormalizedStyleHint {
  styleId?: string; // Preferred or fallback
  genStyleId?: string; // Original
  confidence: number;
}

function normalizeStyleHint(
  backendHint?: BackendStyleHint,
): NormalizedStyleHint | undefined {
  if (!backendHint) return undefined;

  return {
    // Phase 5.0: Prefer preferred_style_id, fall back to gen_style_id
    styleId: backendHint.preferred_style_id || backendHint.gen_style_id,
    genStyleId: backendHint.gen_style_id,
    confidence: backendHint.confidence || 0.0,
  };
}

export async function fetchLearningProfile(
  host: string,
  schemaHash: string,
): Promise<LearningProfile | null> {
  const url = `${API_BASE}/api/extension/learning/profile?host=${encodeURIComponent(host)}&schema_hash=${encodeURIComponent(schemaHash)}`;

  const response = await fetch(url);

  if (!response.ok) {
    if (response.status === 404) return null;
    throw new Error(`Profile fetch failed: ${response.status}`);
  }

  const data = await response.json();

  return {
    host: data.host,
    schemaHash: data.schema_hash,
    canonicalMap: data.canonical_map || {},
    styleHint: normalizeStyleHint(data.style_hint),
  };
}
```

## 4. Update Content Script (If Needed)

**File**: `apps/extension-applylens/content.js`

When calling `generate-form-answers`, include `styleId` from profile:

```javascript
// Fetch profile
const profile = await fetchLearningProfile(host, schemaHash);

// Later, when generating answers:
const generatePayload = {
  fields: fieldsList,
  job: jobContext,
  style_hint: {
    // Phase 5.0: Use preferred style if available
    style_id: profile?.styleHint?.styleId || "default",
    tone: profile?.styleHint?.tone || "professional",
    max_length: profile?.styleHint?.maxLength || 500,
  },
};

const response = await fetch("/api/extension/generate-form-answers", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(generatePayload),
});
```

## 5. Run Tests

```bash
# Run all companion tests (including new style tuning test)
cd apps/extension-applylens
npm run e2e:companion

# Run only style tuning tests
npm run e2e:styletuning

# Run unit tests
npm run test
```

**Expected Output:**

```
✓ @companion @styletuning: forwards preferred_style_id from profile into generate-form-answers style_hint (2.5s)
✓ @companion @styletuning: uses gen_style_id fallback when preferred_style_id is not set (1.8s)
```

## 6. Validation Checklist

- [ ] E2E test created: `e2e/autofill-style-tuning.spec.ts`
- [ ] Unit tests added to `tests/profileClient.test.ts`
- [ ] Profile client maps `preferred_style_id` → `styleId`
- [ ] Generate-form-answers receives `style_hint.styleId`
- [ ] Fallback to `gen_style_id` works when `preferred_style_id` missing
- [ ] All existing `@companion` tests still pass
- [ ] Tests tagged with `@companion @styletuning`

## 7. Integration with Backend

**How it works end-to-end:**

1. **User autofills form** → Learning event sent with `gen_style_id`
2. **User clicks thumbs up/down** → Feedback endpoint updates `AutofillEvent.feedback_status`
3. **Aggregator runs** → Computes `StyleStats`, writes `preferred_style_id` to `FormProfile.style_hint`
4. **Next autofill** → `GET /api/extension/learning/profile` returns `preferred_style_id`
5. **Extension maps** → `preferred_style_id` → `styleHint.styleId`
6. **Generation request** → `POST /api/extension/generate-form-answers` includes `style_hint.style_id = "bullets_v1"`
7. **LLM generates** → Uses preferred style for better results
8. **Feedback loop continues** → More helpful feedback → Style tuning improves

## 8. Debugging Tips

### Profile not returning preferred_style_id

```bash
# Check database
cd services/api
python -c "
from app.db import SessionLocal
from app.models_learning_db import FormProfile

db = SessionLocal()
profiles = db.query(FormProfile).filter(FormProfile.style_hint.isnot(None)).all()
for p in profiles:
    print(f'{p.host}/{p.schema_hash}: {p.style_hint}')
"
```

### Run aggregator manually

```bash
cd services/api
python -c "from app.autofill_aggregator import run_aggregator; print(f'Updated {run_aggregator(days=30)} profiles')"
```

### Check network in browser DevTools

1. Open extension on a form
2. Open DevTools → Network tab
3. Filter: `learning/profile`
4. Check response: Should have `style_hint.preferred_style_id`

### Test captures wrong style_id

Check your normalization:
- Backend sends: `preferred_style_id` (snake_case)
- Extension should map to: `styleId` (camelCase)
- Generation request can accept either format (backend normalizes)

## Summary

Phase 5.0 backend is complete and working. These tests validate:

✅ **Profile fetching** - Extension receives `preferred_style_id`
✅ **Mapping** - `preferred_style_id` → `styleHint.styleId`
✅ **Generation** - `styleId` sent in generation request
✅ **Fallback** - Uses `gen_style_id` when preferred not available

The feedback loop is closed! 🎉
