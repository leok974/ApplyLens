# Phase 3: Companion UX & LLM Generation

**Status**: Planning
**Date**: November 2025
**Prerequisites**: Phase 2.1 complete (learning loop, profile aggregation)

---

## Overview

Phase 3 enhances the ApplyLens Companion extension with a rich answer UX and real LLM-powered generation. This phase is split into two sub-phases:

- **Phase 3.0**: Rich Answer UX in the panel (per-field controls, confidence hints, manual editing)
- **Phase 3.1**: Real LLM Generation & Guardrails (OpenAI/Ollama integration, safety filters)

Both phases build on the existing learning loop from Phase 2.1, using learned mappings and profile data to generate high-quality, ATS-friendly application answers.

---

## Phase 3.0 – Rich Answer UX in the Panel

### Goals

1. **Per-field controls**: Allow users to accept/reject individual suggestions
2. **Inline editing**: Let users modify suggested text directly in the panel
3. **Confidence indicators**: Show visual hints for field mapping confidence
4. **Source tracking**: Distinguish between profile-based, heuristic, and manually edited answers

### Data Model for Answer Row

Create an extension-side TypeScript interface for per-field answer rows:

**File**: `apps/extension-applylens/src/types/answers.ts`

```typescript
/**
 * Represents a single field's suggested answer in the panel.
 * Used for rendering UI controls and tracking user edits.
 */
export interface FieldAnswerRow {
  /** CSS selector for the target field (e.g. "input[name='q1']") */
  selector: string;

  /** Semantic key from learning profile (e.g. "first_name") */
  semanticKey: string;

  /** User-facing label for the field */
  label: string;

  /** Generated or suggested text answer */
  suggestedText: string;

  /** Whether this field will be applied on "Fill All" */
  accepted: boolean;

  /** Mapping confidence level */
  confidence?: "low" | "medium" | "high";

  /** Source of the suggestion */
  source?: "profile" | "heuristic" | "manual";
}
```

This interface maps from your backend `/generate-form-answers` payload to in-memory rows for the panel.

### UX Changes in content.js

#### Current State (Phase 2.1)

Your extension currently:
- Scans form fields
- Fetches learning profile
- Merges server + local mappings
- Renders a panel with "Fill All" button

#### New Behavior (Phase 3.0)

The panel will now render **one row per field** with:
- Checkbox (accept/reject)
- Inline `<textarea>` for editing
- Confidence badge (low/medium/high)

#### Implementation Pattern

**Step 1**: Create helper to convert backend payload to rows

**File**: `apps/extension-applylens/src/answers/rows.ts`

```typescript
import type { FieldAnswerRow } from "../types/answers";

interface BackendAnswersPayload {
  answers: Record<string, string>;
  fields: Array<{
    selector: string;
    semantic_key: string;
    label: string;
    confidence?: string;
  }>;
}

/**
 * Converts backend answers payload into per-field rows for panel rendering.
 */
export function toFieldRows(payload: BackendAnswersPayload): FieldAnswerRow[] {
  const { answers, fields } = payload;

  return fields.map(field => ({
    selector: field.selector,
    semanticKey: field.semantic_key,
    label: field.label,
    suggestedText: answers[field.semantic_key] || "",
    accepted: true, // Default: all fields accepted
    confidence: field.confidence as FieldAnswerRow["confidence"],
    source: answers[field.semantic_key] ? "profile" : "heuristic",
  }));
}
```

**Step 2**: Update panel rendering logic

**File**: `apps/extension-applylens/content.js` (or `src/content/panel.ts` if using TypeScript)

```javascript
import { toFieldRows } from "./answers/rows"; // Adjust path as needed

/**
 * Renders answer rows in the panel with per-field controls.
 * @param {HTMLElement} panel - The panel container
 * @param {Object} answersPayload - Backend response from /generate-form-answers
 */
function renderAnswers(panel, answersPayload) {
  const rows = toFieldRows(answersPayload);
  const tbody = panel.querySelector("#al_answers_body");
  tbody.innerHTML = "";

  for (const row of rows) {
    const tr = document.createElement("tr");
    tr.dataset.selector = row.selector;
    tr.className = "al-answer-row";

    // Column 1: Field Label
    const labelTd = document.createElement("td");
    labelTd.textContent = row.label;
    labelTd.className = "al-field-label";

    // Column 2: Editable Text
    const textTd = document.createElement("td");
    const textarea = document.createElement("textarea");
    textarea.value = row.suggestedText;
    textarea.rows = 3;
    textarea.className = "al-answer-input";
    textarea.addEventListener("input", () => {
      row.suggestedText = textarea.value;
      row.source = "manual"; // Mark as manually edited
    });
    textTd.appendChild(textarea);

    // Column 3: Controls (Checkbox + Confidence Badge)
    const controlsTd = document.createElement("td");
    controlsTd.className = "al-controls";

    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.checked = row.accepted;
    checkbox.className = "al-accept-checkbox";
    checkbox.addEventListener("change", () => {
      row.accepted = checkbox.checked;
      tr.classList.toggle("al-rejected", !checkbox.checked);
    });

    const badge = document.createElement("span");
    badge.textContent = row.confidence || "unknown";
    badge.className = `al-badge al-badge-${row.confidence || "unknown"}`;

    controlsTd.appendChild(checkbox);
    controlsTd.appendChild(badge);

    tr.appendChild(labelTd);
    tr.appendChild(textTd);
    tr.appendChild(controlsTd);

    tbody.appendChild(tr);
  }

  // Update Fill All button behavior
  const fillAllBtn = panel.querySelector("#al_fill_all");
  fillAllBtn.onclick = async () => {
    let appliedCount = 0;

    for (const row of rows) {
      if (!row.accepted) continue; // Skip rejected fields

      const applied = applyAnswerToField(row.selector, row.suggestedText);
      if (applied) appliedCount++;
    }

    console.log(`✅ Applied ${appliedCount}/${rows.length} answers`);

    // Track completion metrics
    await trackAutofillCompletion({
      host: window.location.host,
      schemaHash: computeSchemaHash(document),
      totalFields: rows.length,
      appliedFields: appliedCount,
      manualEdits: rows.filter(r => r.source === "manual").length,
    });
  };
}

/**
 * Applies answer text to the target field in the DOM.
 * @param {string} selector - CSS selector for the field
 * @param {string} text - Answer text to fill
 * @returns {boolean} - True if field was found and filled
 */
function applyAnswerToField(selector, text) {
  const field = document.querySelector(selector);
  if (!field) {
    console.warn(`⚠️ Field not found: ${selector}`);
    return false;
  }

  field.value = text;
  field.dispatchEvent(new Event("input", { bubbles: true }));
  field.dispatchEvent(new Event("change", { bubbles: true }));

  return true;
}
```

**Step 3**: Add minimal CSS for the panel

**File**: `apps/extension-applylens/content.css`

```css
/* Answer row styles */
.al-answer-row {
  border-bottom: 1px solid #e5e7eb;
}

.al-answer-row.al-rejected {
  opacity: 0.5;
  background-color: #fef2f2;
}

.al-field-label {
  font-weight: 500;
  padding: 8px;
  min-width: 120px;
}

.al-answer-input {
  width: 100%;
  padding: 6px;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-family: inherit;
  resize: vertical;
}

.al-controls {
  white-space: nowrap;
  padding: 8px;
}

.al-accept-checkbox {
  margin-right: 8px;
}

.al-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
}

.al-badge-high {
  background-color: #d1fae5;
  color: #065f46;
}

.al-badge-medium {
  background-color: #fef3c7;
  color: #92400e;
}

.al-badge-low {
  background-color: #fee2e2;
  color: #991b1b;
}

.al-badge-unknown {
  background-color: #e5e7eb;
  color: #6b7280;
}
```

### Extension-Side Tests

#### Vitest Unit Test for Row Conversion

**File**: `apps/extension-applylens/tests/answersRows.test.ts`

```typescript
import { describe, it, expect } from "vitest";
import { toFieldRows } from "../src/answers/rows";

describe("toFieldRows", () => {
  it("maps backend answers into field rows with defaults", () => {
    const payload = {
      answers: {
        first_name: "Testy",
        last_name: "McTest",
      },
      fields: [
        { selector: "input[name='q1']", semantic_key: "first_name", label: "First name" },
        { selector: "input[name='q2']", semantic_key: "last_name", label: "Last name" },
      ],
    };

    const rows = toFieldRows(payload);

    expect(rows).toHaveLength(2);
    expect(rows[0]).toMatchObject({
      selector: "input[name='q1']",
      semanticKey: "first_name",
      label: "First name",
      suggestedText: "Testy",
      accepted: true,
    });
    expect(rows[1]).toMatchObject({
      selector: "input[name='q2']",
      semanticKey: "last_name",
      label: "Last name",
      suggestedText: "McTest",
      accepted: true,
    });
  });

  it("defaults to empty string if answer not found", () => {
    const payload = {
      answers: {},
      fields: [
        { selector: "input[name='q1']", semantic_key: "first_name", label: "First name" },
      ],
    };

    const rows = toFieldRows(payload);

    expect(rows[0].suggestedText).toBe("");
    expect(rows[0].source).toBe("heuristic");
  });

  it("preserves confidence level from backend", () => {
    const payload = {
      answers: { email: "test@example.com" },
      fields: [
        { selector: "input[name='email']", semantic_key: "email", label: "Email", confidence: "high" },
      ],
    };

    const rows = toFieldRows(payload);

    expect(rows[0].confidence).toBe("high");
  });
});
```

#### E2E Test for Panel UX

**File**: `apps/extension-applylens/e2e/autofill-ux-panel.spec.ts`

Tag: `@companion @ux`

```typescript
import { test, expect } from "@playwright/test";

test.describe("Autofill Panel UX @companion @ux", () => {
  test.beforeEach(async ({ page }) => {
    // Mock backend endpoints
    await page.route("**/api/extension/learning/profile*", route =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          host: "test.com",
          schema_hash: "abc123",
          canonical_map: {
            "input[name='firstName']": "first_name",
            "input[name='lastName']": "last_name",
          },
        }),
      })
    );

    await page.route("**/api/extension/generate-form-answers", route =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          answers: {
            first_name: "Test",
            last_name: "User",
          },
          fields: [
            { selector: "input[name='firstName']", semantic_key: "first_name", label: "First Name", confidence: "high" },
            { selector: "input[name='lastName']", semantic_key: "last_name", label: "Last Name", confidence: "medium" },
          ],
        }),
      })
    );

    await page.route("**/api/profile/me", route =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ email: "test@example.com" }),
      })
    );

    // Navigate to test form
    await page.goto("http://localhost:4173/test/demo-form.html");
  });

  test("renders answer rows with controls", async ({ page }) => {
    // Trigger autofill panel
    await page.click('[data-testid="applylens-trigger"]');

    // Wait for panel to appear
    await page.waitForSelector("#al_answers_body");

    // Check rows rendered
    const rows = await page.locator(".al-answer-row").count();
    expect(rows).toBeGreaterThan(0);

    // Verify first row has all elements
    const firstRow = page.locator(".al-answer-row").first();
    await expect(firstRow.locator(".al-field-label")).toBeVisible();
    await expect(firstRow.locator(".al-answer-input")).toBeVisible();
    await expect(firstRow.locator(".al-accept-checkbox")).toBeVisible();
    await expect(firstRow.locator(".al-badge")).toBeVisible();
  });

  test("unchecking field excludes it from Fill All", async ({ page }) => {
    await page.click('[data-testid="applylens-trigger"]');
    await page.waitForSelector("#al_answers_body");

    // Uncheck first field
    const firstCheckbox = page.locator(".al-accept-checkbox").first();
    await firstCheckbox.uncheck();

    // Click Fill All
    await page.click("#al_fill_all");

    // First input should remain empty (rejected)
    const firstInput = page.locator("input[name='firstName']");
    await expect(firstInput).toHaveValue("");

    // Second input should be filled (accepted)
    const secondInput = page.locator("input[name='lastName']");
    await expect(secondInput).toHaveValue("User");
  });

  test("editing text in panel uses edited value on Fill All", async ({ page }) => {
    await page.click('[data-testid="applylens-trigger"]');
    await page.waitForSelector("#al_answers_body");

    // Edit first field's suggested text
    const firstTextarea = page.locator(".al-answer-input").first();
    await firstTextarea.clear();
    await firstTextarea.fill("CustomName");

    // Click Fill All
    await page.click("#al_fill_all");

    // Input should have edited value
    const firstInput = page.locator("input[name='firstName']");
    await expect(firstInput).toHaveValue("CustomName");
  });

  test("confidence badges display correctly", async ({ page }) => {
    await page.click('[data-testid="applylens-trigger"]');
    await page.waitForSelector("#al_answers_body");

    // Check first row has "high" badge
    const firstBadge = page.locator(".al-answer-row").first().locator(".al-badge");
    await expect(firstBadge).toHaveText("high");
    await expect(firstBadge).toHaveClass(/al-badge-high/);

    // Check second row has "medium" badge
    const secondBadge = page.locator(".al-answer-row").nth(1).locator(".al-badge");
    await expect(secondBadge).toHaveText("medium");
    await expect(secondBadge).toHaveClass(/al-badge-medium/);
  });
});
```

Run with:
```bash
cd apps/extension-applylens
npx playwright test e2e/autofill-ux-panel.spec.ts --grep "@companion @ux"
```

### Summary: Phase 3.0 Deliverables

- ✅ TypeScript interface for `FieldAnswerRow`
- ✅ Helper function `toFieldRows()` to convert backend payload
- ✅ Updated panel rendering with per-field controls
- ✅ CSS styling for confidence badges and row states
- ✅ Vitest unit tests for row conversion logic
- ✅ Playwright E2E tests for panel interactions

---

## Phase 3.1 – Real LLM Generation & Guardrails

### Goals

1. **LLM Integration**: Connect to OpenAI/Ollama for high-quality answer generation
2. **Safety Guardrails**: Prevent hallucinated employment, URLs, excessive length
3. **ATS Compatibility**: Ensure generated text meets applicant tracking system requirements
4. **Graceful Fallback**: Use template-based generation when LLM is disabled/unavailable

### Backend Changes

#### LLM Client Abstraction

Create a dedicated module for LLM calls that supports multiple providers and graceful degradation.

**File**: `services/api/app/llm/companion_client.py`

```python
"""
LLM client for ApplyLens Companion extension.
Supports OpenAI, Ollama, and template-based fallback.
"""
from typing import List, Dict, Any, Optional
import os
import logging

logger = logging.getLogger(__name__)

# Environment configuration
LLM_ENABLED = os.getenv("COMPANION_LLM_ENABLED", "0") == "1"
LLM_PROVIDER = os.getenv("COMPANION_LLM_PROVIDER", "openai")  # "openai" | "ollama"
LLM_MODEL = os.getenv("COMPANION_LLM_MODEL", "gpt-4o-mini")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

class CompanionLLMError(Exception):
    """Raised when LLM generation fails."""
    pass


def generate_form_answers_llm(
    fields: List[Dict[str, Any]],
    profile: Dict[str, Any],
    job_context: Optional[Dict[str, Any]] = None,
    style: Optional[Dict[str, Any]] = None,
) -> Dict[str, str]:
    """
    Generate form answers using LLM or template fallback.

    Args:
        fields: List of field descriptors with selector, semantic_key, label
        profile: User profile data (from /api/profile/me)
        job_context: Optional job posting details
        style: Optional generation style preferences

    Returns:
        Dict mapping semantic_key to generated answer text

    Raises:
        CompanionLLMError: If LLM call fails and fallback is disabled
    """
    if not LLM_ENABLED:
        logger.info("LLM disabled, using template fallback")
        return _generate_template_answers(fields, profile)

    try:
        prompt = _build_form_prompt(fields, profile, job_context, style)

        if LLM_PROVIDER == "openai":
            raw_response = _call_openai(prompt)
        elif LLM_PROVIDER == "ollama":
            raw_response = _call_ollama(prompt)
        else:
            raise CompanionLLMError(f"Unknown LLM provider: {LLM_PROVIDER}")

        answers = _parse_llm_output(raw_response, fields)
        logger.info(f"Generated {len(answers)} answers via {LLM_PROVIDER}")
        return answers

    except Exception as exc:
        logger.error(f"LLM generation failed: {exc}", exc_info=True)
        # Fallback to templates on error
        return _generate_template_answers(fields, profile)


def _build_form_prompt(
    fields: List[Dict[str, Any]],
    profile: Dict[str, Any],
    job_context: Optional[Dict[str, Any]],
    style: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Build structured prompt for LLM.

    Returns a dict that will be converted to JSON for the LLM.
    """
    system_prompt = """You are an expert job application assistant. Generate ATS-friendly answers for application form fields.

CRITICAL RULES:
1. Never fabricate employment history or education
2. Never include URLs or links
3. Keep answers concise and relevant to the field
4. Use professional, error-free language
5. Match the tone indicated by the generation style
6. Only use information from the provided profile

For each field, return ONLY the answer text, no explanations."""

    field_descriptions = [
        {
            "semantic_key": f["semantic_key"],
            "label": f.get("label", f["semantic_key"]),
            "type": f.get("type", "text"),
        }
        for f in fields
    ]

    user_prompt = {
        "task": "Generate answers for these application form fields",
        "fields": field_descriptions,
        "profile": {
            "first_name": profile.get("first_name"),
            "last_name": profile.get("last_name"),
            "email": profile.get("email"),
            "phone": profile.get("phone"),
            "summary": profile.get("summary"),
            "skills": profile.get("skills", []),
            # Don't include full employment history to avoid hallucination
        },
        "job_context": job_context or {},
        "style": style or {"tone": "professional", "length": "concise"},
    }

    return {
        "system": system_prompt,
        "user": user_prompt,
    }


def _call_openai(prompt: Dict[str, Any]) -> str:
    """Call OpenAI API."""
    try:
        import openai

        client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": prompt["system"]},
                {"role": "user", "content": str(prompt["user"])},
            ],
            temperature=0.7,
            max_tokens=1500,
        )

        return response.choices[0].message.content

    except Exception as exc:
        raise CompanionLLMError(f"OpenAI call failed: {exc}") from exc


def _call_ollama(prompt: Dict[str, Any]) -> str:
    """Call Ollama API."""
    try:
        import requests

        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={
                "model": LLM_MODEL,
                "prompt": f"{prompt['system']}\n\n{prompt['user']}",
                "stream": False,
            },
            timeout=30,
        )
        response.raise_for_status()

        return response.json()["response"]

    except Exception as exc:
        raise CompanionLLMError(f"Ollama call failed: {exc}") from exc


def _parse_llm_output(raw: str, fields: List[Dict[str, Any]]) -> Dict[str, str]:
    """
    Parse LLM response into semantic_key -> answer mapping.

    Expected format: JSON object with semantic keys or structured text.
    """
    import json
    import re

    # Try to extract JSON from response
    json_match = re.search(r'\{[\s\S]*\}', raw)
    if json_match:
        try:
            parsed = json.loads(json_match.group(0))
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

    # Fallback: look for key-value pairs
    answers = {}
    for field in fields:
        key = field["semantic_key"]
        # Look for "key: value" pattern
        pattern = rf'{key}\s*:\s*(.+?)(?:\n|$)'
        match = re.search(pattern, raw, re.IGNORECASE)
        if match:
            answers[key] = match.group(1).strip()

    return answers


def _generate_template_answers(
    fields: List[Dict[str, Any]],
    profile: Dict[str, Any],
) -> Dict[str, str]:
    """
    Simple template-based fallback when LLM is unavailable.
    """
    answers = {}

    for field in fields:
        key = field["semantic_key"]

        # Direct profile mapping
        if key in profile and profile[key]:
            answers[key] = str(profile[key])
            continue

        # Common field templates
        if key == "summary":
            answers[key] = profile.get("summary", "Experienced professional seeking new opportunities.")
        elif key == "cover_letter":
            answers[key] = f"Dear Hiring Manager,\n\nI am interested in this position. {profile.get('summary', '')}\n\nThank you for your consideration."
        elif key in ("why_interested", "motivation"):
            answers[key] = "I am excited about this opportunity and believe my skills align well with your needs."
        else:
            # Generic fallback
            answers[key] = profile.get(key, "")

    return answers
```

#### Guardrails Module

Create safety filters to sanitize LLM output.

**File**: `services/api/app/llm/companion_guardrails.py`

```python
"""
Safety guardrails for LLM-generated application answers.
"""
import re
from typing import Dict

# Configuration
MAX_FIELD_CHARS = 2000
MAX_SUMMARY_CHARS = 500

# Forbidden phrases that might indicate hallucination
FORBIDDEN_PHRASES = [
    "I worked at",
    "I was employed at",
    "I currently work at",
    "My experience at",
    "During my time at",
    # Add more as needed
]

# URL patterns to strip
URL_PATTERN = re.compile(r'https?://\S+')
EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')


def sanitize_answer(text: str, field_type: str = "text") -> str:
    """
    Apply safety guardrails to a single answer.

    Args:
        text: Raw answer text from LLM
        field_type: Field semantic type (e.g. "summary", "first_name")

    Returns:
        Sanitized answer text
    """
    if text is None:
        return ""

    text = text.strip()

    # 1. Length limits
    max_len = MAX_SUMMARY_CHARS if field_type == "summary" else MAX_FIELD_CHARS
    if len(text) > max_len:
        # Trim at word boundary
        text = text[:max_len].rsplit(" ", 1)[0] + "..."

    # 2. Strip URLs (most ATS forms reject them)
    text = URL_PATTERN.sub("", text)

    # 3. Strip email addresses if not an email field
    if field_type != "email":
        text = EMAIL_PATTERN.sub("", text)

    # 4. Remove forbidden phrases (hallucination indicators)
    for phrase in FORBIDDEN_PHRASES:
        if phrase.lower() in text.lower():
            # Remove the phrase and surrounding sentence
            text = re.sub(
                rf'[^.!?]*{re.escape(phrase)}[^.!?]*[.!?]',
                '',
                text,
                flags=re.IGNORECASE
            )

    # 5. Clean up whitespace
    text = re.sub(r'\s+', ' ', text).strip()

    return text


def sanitize_answers(answers: Dict[str, str]) -> Dict[str, str]:
    """
    Apply guardrails to all answers in a dict.

    Args:
        answers: Dict mapping semantic_key to answer text

    Returns:
        Sanitized answers dict
    """
    return {
        key: sanitize_answer(value, field_type=key)
        for key, value in answers.items()
    }


def validate_answers(
    answers: Dict[str, str],
    required_fields: list[str],
) -> tuple[bool, list[str]]:
    """
    Validate that all required fields have non-empty answers.

    Args:
        answers: Generated answers dict
        required_fields: List of semantic keys that must have values

    Returns:
        Tuple of (is_valid, list_of_missing_fields)
    """
    missing = [
        field for field in required_fields
        if not answers.get(field, "").strip()
    ]

    return len(missing) == 0, missing
```

#### Wire into Extension Endpoint

Update the `/api/extension/generate-form-answers` endpoint to use the new LLM client.

**File**: `services/api/app/routers/extension_endpoints.py` (or wherever this endpoint lives)

```python
from fastapi import APIRouter, Depends, HTTPException
from app.auth import get_current_user
from app.models import User
from app.llm.companion_client import generate_form_answers_llm, CompanionLLMError
from app.llm.companion_guardrails import sanitize_answers, validate_answers
from app.schemas import FormAnswersRequest, FormAnswersResponse
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/api/extension/generate-form-answers", response_model=FormAnswersResponse)
async def generate_form_answers_endpoint(
    req: FormAnswersRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Generate form answers using LLM + guardrails.

    Phase 3.1: Now uses real LLM instead of static templates.
    """
    try:
        # 1. Gather user profile context
        profile = await _get_profile_for_user(current_user)

        # 2. Optional: Extract job context from request
        job_ctx = await _maybe_get_job_context(req)

        # 3. Optional: Get style hint from learning profile
        style = await _get_style_hint(req.host, req.schema_hash)

        # 4. Generate answers via LLM
        raw_answers = generate_form_answers_llm(
            fields=[f.model_dump() for f in req.fields],
            profile=profile,
            job_context=job_ctx,
            style=style,
        )

        # 5. Apply safety guardrails
        safe_answers = sanitize_answers(raw_answers)

        # 6. Validate required fields
        required = [f.semantic_key for f in req.fields if f.required]
        is_valid, missing = validate_answers(safe_answers, required)

        if not is_valid:
            logger.warning(f"Missing required fields: {missing}")
            # Could return partial answers or raise error

        logger.info(f"Generated {len(safe_answers)} answers for {current_user.email}")

        return FormAnswersResponse(
            answers=safe_answers,
            fields=[
                {
                    "selector": f.selector,
                    "semantic_key": f.semantic_key,
                    "label": f.label,
                    "confidence": _compute_confidence(f, safe_answers),
                }
                for f in req.fields
            ],
        )

    except CompanionLLMError as exc:
        logger.error(f"LLM generation failed: {exc}")
        raise HTTPException(status_code=500, detail="Answer generation unavailable")


async def _get_profile_for_user(user: User) -> dict:
    """Fetch user profile data (reuse existing /api/profile/me logic)."""
    # TODO: Import and call your existing profile service
    return {
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        # ... other fields
    }


async def _maybe_get_job_context(req: FormAnswersRequest) -> dict | None:
    """Extract job posting details if available."""
    # Could parse from req.job_url or req.job_description if provided
    return None


async def _get_style_hint(host: str, schema_hash: str) -> dict | None:
    """Get generation style from learning profile."""
    # TODO: Query form_profiles table for style_hint
    return None


def _compute_confidence(field, answers: dict) -> str:
    """Compute confidence level for field mapping."""
    if field.semantic_key not in answers or not answers[field.semantic_key]:
        return "low"

    # Could use learning profile stats here
    return "medium"
```

### Backend Tests (Pytest)

**File**: `services/api/tests/test_companion_generation.py`

```python
import pytest
from app.llm.companion_guardrails import sanitize_answer, sanitize_answers, validate_answers


def test_sanitize_answer_trims_long_text():
    """Ensure answers respect length limits."""
    long_text = "A" * 3000
    result = sanitize_answer(long_text, field_type="summary")

    assert len(result) <= 503  # MAX_SUMMARY_CHARS + "..."
    assert result.endswith("...")


def test_sanitize_answer_strips_urls():
    """URLs should be removed from answers."""
    text = "Check my portfolio at https://example.com for more info"
    result = sanitize_answer(text)

    assert "http" not in result
    assert "example.com" not in result
    assert "Check my portfolio" in result


def test_sanitize_answer_removes_forbidden_phrases():
    """Forbidden phrases indicating hallucination should be removed."""
    text = "I worked at FakeCorp doing AI engineering. I have 5 years of experience."
    result = sanitize_answer(text)

    assert "I worked at" not in result
    assert "FakeCorp" not in result  # Whole sentence removed
    assert "I have 5 years of experience" in result


def test_sanitize_answers_applies_to_all_fields():
    """Guardrails should apply to entire answers dict."""
    answers = {
        "summary": "Experienced engineer. I worked at BadCo last year.",
        "email": "test@example.com",
        "website": "Visit https://mysite.com",
    }

    result = sanitize_answers(answers)

    assert "I worked at" not in result["summary"]
    assert "BadCo" not in result["summary"]
    assert result["email"] == "test@example.com"  # Email preserved
    assert "https://" not in result["website"]


def test_validate_answers_checks_required_fields():
    """Validation should detect missing required fields."""
    answers = {
        "first_name": "John",
        "last_name": "",
        "email": "john@example.com",
    }

    is_valid, missing = validate_answers(answers, required_fields=["first_name", "last_name", "email"])

    assert not is_valid
    assert "last_name" in missing
    assert "first_name" not in missing


@pytest.mark.asyncio
async def test_generate_form_answers_endpoint_uses_guardrails(async_client, test_user, monkeypatch):
    """Integration test: endpoint applies guardrails to LLM output."""
    from app.routers.extension_endpoints import generate_form_answers_endpoint
    from app.llm.companion_client import generate_form_answers_llm

    # Mock LLM to return dangerous content
    def mock_llm(*args, **kwargs):
        return {
            "summary": "I worked at FakeCorp. Check https://fake.com",
            "first_name": "Test",
        }

    monkeypatch.setattr("app.routers.extension_endpoints.generate_form_answers_llm", mock_llm)

    # Make request
    response = await async_client.post(
        "/api/extension/generate-form-answers",
        json={
            "host": "test.com",
            "schema_hash": "abc123",
            "fields": [
                {"selector": "input[name='summary']", "semantic_key": "summary", "label": "Summary"},
                {"selector": "input[name='fname']", "semantic_key": "first_name", "label": "First Name"},
            ],
        },
        headers={"Authorization": f"Bearer {test_user.token}"},
    )

    assert response.status_code == 200
    data = response.json()

    # Verify guardrails applied
    assert "I worked at" not in data["answers"]["summary"]
    assert "FakeCorp" not in data["answers"]["summary"]
    assert "https://" not in data["answers"]["summary"]
    assert data["answers"]["first_name"] == "Test"  # Safe field unchanged
```

Run tests:
```bash
cd services/api
python -m pytest tests/test_companion_generation.py -v
```

### Extension E2E Test for Generation

Create a new E2E test that verifies LLM-generated content is sanitized.

**File**: `apps/extension-applylens/e2e/autofill-generation.spec.ts`

Tag: `@companion @generation`

```typescript
import { test, expect } from "@playwright/test";

test.describe("Autofill Generation with Guardrails @companion @generation", () => {
  test.beforeEach(async ({ page }) => {
    // Mock profile endpoint
    await page.route("**/api/profile/me", route =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          email: "test@example.com",
          first_name: "Test",
          last_name: "User",
        }),
      })
    );

    // Mock learning profile
    await page.route("**/api/extension/learning/profile*", route =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          host: "test.com",
          schema_hash: "abc123",
          canonical_map: {
            "input[name='summary']": "summary",
            "input[name='motivation']": "why_interested",
          },
        }),
      })
    );
  });

  test("strips URLs from generated answers", async ({ page }) => {
    // Mock generate-form-answers to return dangerous content with URLs
    await page.route("**/api/extension/generate-form-answers", route =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          answers: {
            summary: "Experienced engineer. Check my portfolio at https://dangerous.com for samples.",
            motivation: "I want to work here. Visit https://spam.link for details.",
          },
          fields: [
            { selector: "input[name='summary']", semantic_key: "summary", label: "Summary" },
            { selector: "input[name='motivation']", semantic_key: "why_interested", label: "Why interested?" },
          ],
        }),
      })
    );

    await page.goto("http://localhost:4173/test/demo-form.html");

    // Trigger autofill
    await page.click('[data-testid="applylens-trigger"]');
    await page.waitForSelector("#al_answers_body");

    // Check that URLs are NOT in the textarea values
    const summaryTextarea = page.locator(".al-answer-row").first().locator(".al-answer-input");
    const summaryValue = await summaryTextarea.inputValue();

    expect(summaryValue).not.toContain("https://");
    expect(summaryValue).not.toContain("dangerous.com");
    expect(summaryValue).toContain("Experienced engineer"); // Safe part preserved

    const motivationTextarea = page.locator(".al-answer-row").nth(1).locator(".al-answer-input");
    const motivationValue = await motivationTextarea.inputValue();

    expect(motivationValue).not.toContain("https://");
    expect(motivationValue).not.toContain("spam.link");
  });

  test("removes forbidden phrases from answers", async ({ page }) => {
    // Mock generate-form-answers to return hallucinated employment
    await page.route("**/api/extension/generate-form-answers", route =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          answers: {
            summary: "I worked at FakeCorp as a senior engineer. I was employed at BigTech for 3 years doing AI research.",
            motivation: "I have relevant experience and want to contribute.",
          },
          fields: [
            { selector: "input[name='summary']", semantic_key: "summary", label: "Summary" },
            { selector: "input[name='motivation']", semantic_key: "why_interested", label: "Motivation" },
          ],
        }),
      })
    );

    await page.goto("http://localhost:4173/test/demo-form.html");
    await page.click('[data-testid="applylens-trigger"]');
    await page.waitForSelector("#al_answers_body");

    // Check that forbidden phrases are removed
    const summaryTextarea = page.locator(".al-answer-row").first().locator(".al-answer-input");
    const summaryValue = await summaryTextarea.inputValue();

    expect(summaryValue).not.toContain("I worked at");
    expect(summaryValue).not.toContain("I was employed at");
    expect(summaryValue).not.toContain("FakeCorp");
    expect(summaryValue).not.toContain("BigTech");

    // Safe answer should be unaffected
    const motivationTextarea = page.locator(".al-answer-row").nth(1).locator(".al-answer-input");
    const motivationValue = await motivationTextarea.inputValue();

    expect(motivationValue).toContain("I have relevant experience");
  });

  test("applies both URL and phrase guardrails together", async ({ page }) => {
    // Mock with multiple violations
    await page.route("**/api/extension/generate-form-answers", route =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          answers: {
            summary: "I worked at EvilCorp https://evil.com doing bad things. I am a great candidate!",
          },
          fields: [
            { selector: "input[name='summary']", semantic_key: "summary", label: "Summary" },
          ],
        }),
      })
    );

    await page.goto("http://localhost:4173/test/demo-form.html");
    await page.click('[data-testid="applylens-trigger"]');
    await page.waitForSelector("#al_answers_body");

    const summaryTextarea = page.locator(".al-answer-row").first().locator(".al-answer-input");
    const summaryValue = await summaryTextarea.inputValue();

    // Both guardrails applied
    expect(summaryValue).not.toContain("I worked at");
    expect(summaryValue).not.toContain("https://");
    expect(summaryValue).not.toContain("EvilCorp");
    expect(summaryValue).not.toContain("evil.com");

    // Safe content preserved
    expect(summaryValue).toContain("I am a great candidate");
  });

  test("handles excessively long answers by truncating", async ({ page }) => {
    const veryLongText = "A".repeat(3000); // Exceeds MAX_FIELD_CHARS

    await page.route("**/api/extension/generate-form-answers", route =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          answers: {
            summary: veryLongText,
          },
          fields: [
            { selector: "input[name='summary']", semantic_key: "summary", label: "Summary" },
          ],
        }),
      })
    );

    await page.goto("http://localhost:4173/test/demo-form.html");
    await page.click('[data-testid="applylens-trigger"]');
    await page.waitForSelector("#al_answers_body");

    const summaryTextarea = page.locator(".al-answer-row").first().locator(".al-answer-input");
    const summaryValue = await summaryTextarea.inputValue();

    // Should be truncated
    expect(summaryValue.length).toBeLessThan(3000);
    expect(summaryValue.length).toBeLessThanOrEqual(503); // MAX_SUMMARY_CHARS + "..."
    expect(summaryValue).toMatch(/\.\.\.$/); // Ends with ellipsis
  });
});
```

Run with:
```bash
cd apps/extension-applylens
npx playwright test e2e/autofill-generation.spec.ts --grep "@companion @generation"
```

---

## Rollout Plan & Feature Flags

### Environment Variables

#### Backend (services/api/.env)

```bash
# Phase 3.1 - LLM Generation
COMPANION_LLM_ENABLED=0              # 0=template fallback, 1=real LLM
COMPANION_LLM_PROVIDER=openai        # "openai" | "ollama"
COMPANION_LLM_MODEL=gpt-4o-mini      # Model identifier

# OpenAI configuration
OPENAI_API_KEY=sk-...                # Required if COMPANION_LLM_PROVIDER=openai

# Ollama configuration
OLLAMA_BASE_URL=http://localhost:11434  # Required if COMPANION_LLM_PROVIDER=ollama
```

#### Extension (No Changes Needed)

Extension continues to use existing `API_BASE_URL` configuration. The backend determines whether to use LLM or templates transparently.

### Rollout Stages

#### Stage 1: Panel UX Only (Phase 3.0)

- **Target**: Week 1-2
- **Config**: `COMPANION_LLM_ENABLED=0`
- **Behavior**:
  - Panel shows per-field controls (checkboxes, editing, confidence badges)
  - Backend uses template-based answers
  - No LLM costs
- **Validation**:
  - E2E tests with `@companion @ux` tag pass
  - Users can accept/reject/edit fields
  - Metrics show autofill completion rates

#### Stage 2: LLM in Development (Phase 3.1 - Dev Only)

- **Target**: Week 3
- **Config**:
  - Dev: `COMPANION_LLM_ENABLED=1`, `COMPANION_LLM_PROVIDER=ollama`
  - Prod: `COMPANION_LLM_ENABLED=0`
- **Behavior**:
  - Local Ollama instance generates answers
  - Guardrails applied and logged
  - Monitor for quality issues
- **Validation**:
  - E2E tests with `@companion @generation` tag pass
  - Manual testing on job application forms
  - Check logs for guardrail triggers

#### Stage 3: LLM for Internal Users (Phase 3.1 - Beta)

- **Target**: Week 4-5
- **Config**:
  - Prod: `COMPANION_LLM_ENABLED=1`, `COMPANION_LLM_PROVIDER=openai`
  - Feature flag: Check `user.is_beta_tester` or `user.tenant_id` in allowlist
- **Behavior**:
  - OpenAI API used for beta users only
  - All others get template fallback
  - Monitor costs and quality
- **Code Change** (in `extension_endpoints.py`):
  ```python
  async def generate_form_answers_endpoint(...):
      # Check if user has access to LLM feature
      if not current_user.is_beta_tester:
          logger.info(f"User {current_user.email} not in beta, using templates")
          # Force template mode for this request
          raw_answers = _generate_template_answers(fields, profile)
      else:
          # Use configured LLM
          raw_answers = generate_form_answers_llm(...)
  ```
- **Validation**:
  - Beta users report answer quality
  - Monitor OpenAI API costs via dashboard
  - Collect feedback on guardrail effectiveness

#### Stage 4: General Rollout (Phase 3.1 - Production)

- **Target**: Week 6+
- **Config**:
  - Prod: `COMPANION_LLM_ENABLED=1`
  - All users get LLM generation
- **Behavior**:
  - Full LLM generation for all users
  - Guardrails protect against hallucination
  - Observability tracks quality metrics
- **Validation**:
  - Monitor autofill success rates
  - Track LLM API latency (p50, p95, p99)
  - Watch for cost spikes

---

## Observability Additions

### Backend Metrics (Prometheus)

Add new metrics to `services/api/app/metrics.py`:

```python
from prometheus_client import Counter, Histogram, Gauge

# LLM Generation Metrics
llm_generation_requests = Counter(
    "applylens_llm_generation_requests_total",
    "Total LLM generation requests",
    ["provider", "model", "status"],
)

llm_generation_duration = Histogram(
    "applylens_llm_generation_duration_seconds",
    "LLM generation latency",
    ["provider"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0],
)

llm_guardrail_triggers = Counter(
    "applylens_llm_guardrail_triggers_total",
    "Guardrail violations detected",
    ["guardrail_type"],  # "url", "forbidden_phrase", "length"
)

llm_template_fallbacks = Counter(
    "applylens_llm_template_fallbacks_total",
    "LLM failures resulting in template fallback",
    ["reason"],  # "disabled", "error", "timeout"
)

# Answer Quality Metrics
autofill_field_acceptance = Counter(
    "applylens_autofill_field_acceptance_total",
    "Fields accepted vs rejected by users",
    ["accepted"],  # "true" | "false"
)

autofill_manual_edits = Counter(
    "applylens_autofill_manual_edits_total",
    "Fields manually edited by users",
)
```

### Instrumentation Examples

**In `companion_client.py`**:

```python
from app.metrics import (
    llm_generation_requests,
    llm_generation_duration,
    llm_template_fallbacks,
)
import time

def generate_form_answers_llm(...):
    if not LLM_ENABLED:
        llm_template_fallbacks.labels(reason="disabled").inc()
        return _generate_template_answers(fields, profile)

    start_time = time.time()

    try:
        if LLM_PROVIDER == "openai":
            raw_response = _call_openai(prompt)
        elif LLM_PROVIDER == "ollama":
            raw_response = _call_ollama(prompt)

        duration = time.time() - start_time
        llm_generation_duration.labels(provider=LLM_PROVIDER).observe(duration)
        llm_generation_requests.labels(
            provider=LLM_PROVIDER,
            model=LLM_MODEL,
            status="success"
        ).inc()

        return _parse_llm_output(raw_response, fields)

    except Exception as exc:
        llm_generation_requests.labels(
            provider=LLM_PROVIDER,
            model=LLM_MODEL,
            status="error"
        ).inc()
        llm_template_fallbacks.labels(reason="error").inc()
        return _generate_template_answers(fields, profile)
```

**In `companion_guardrails.py`**:

```python
from app.metrics import llm_guardrail_triggers

def sanitize_answer(text: str, field_type: str = "text") -> str:
    # ... (existing code)

    # Track URL removal
    url_count = len(URL_PATTERN.findall(text))
    if url_count > 0:
        llm_guardrail_triggers.labels(guardrail_type="url").inc(url_count)

    text = URL_PATTERN.sub("", text)

    # Track forbidden phrases
    for phrase in FORBIDDEN_PHRASES:
        if phrase.lower() in text.lower():
            llm_guardrail_triggers.labels(guardrail_type="forbidden_phrase").inc()
            # ... (removal logic)

    # Track length truncation
    if len(text) > max_len:
        llm_guardrail_triggers.labels(guardrail_type="length").inc()
        text = text[:max_len].rsplit(" ", 1)[0] + "..."

    return text
```

### Grafana Dashboard Additions

Add panels to `services/api/dashboards/companion.json`:

```json
{
  "panels": [
    {
      "title": "LLM Generation Rate",
      "targets": [
        {
          "expr": "rate(applylens_llm_generation_requests_total[5m])",
          "legendFormat": "{{provider}} - {{status}}"
        }
      ]
    },
    {
      "title": "LLM Latency (p50, p95, p99)",
      "targets": [
        {
          "expr": "histogram_quantile(0.50, rate(applylens_llm_generation_duration_seconds_bucket[5m]))",
          "legendFormat": "p50"
        },
        {
          "expr": "histogram_quantile(0.95, rate(applylens_llm_generation_duration_seconds_bucket[5m]))",
          "legendFormat": "p95"
        },
        {
          "expr": "histogram_quantile(0.99, rate(applylens_llm_generation_duration_seconds_bucket[5m]))",
          "legendFormat": "p99"
        }
      ]
    },
    {
      "title": "Guardrail Triggers",
      "targets": [
        {
          "expr": "rate(applylens_llm_guardrail_triggers_total[5m])",
          "legendFormat": "{{guardrail_type}}"
        }
      ]
    },
    {
      "title": "Template Fallback Rate",
      "targets": [
        {
          "expr": "rate(applylens_llm_template_fallbacks_total[5m])",
          "legendFormat": "{{reason}}"
        }
      ]
    },
    {
      "title": "Field Acceptance Rate",
      "targets": [
        {
          "expr": "sum(rate(applylens_autofill_field_acceptance_total{accepted=\"true\"}[5m])) / sum(rate(applylens_autofill_field_acceptance_total[5m]))",
          "legendFormat": "Acceptance Rate"
        }
      ]
    }
  ]
}
```

---

## Integration with Phase 2.1

Phase 3 builds directly on the learning loop from Phase 2.1:

### How They Connect

1. **Profile Fetching** (Phase 2.1):
   - Extension calls `GET /api/extension/learning/profile`
   - Gets `canonical_map` and `style_hint`

2. **Answer Generation** (Phase 3.1):
   - Extension calls `POST /api/extension/generate-form-answers`
   - Backend uses `style_hint` from learning profile to tune LLM tone
   - Returns generated answers for each semantic field

3. **Panel Rendering** (Phase 3.0):
   - Extension merges learned mappings with generated answers
   - Displays per-field rows with confidence from learning data
   - User accepts/rejects/edits

4. **Learning Sync** (Phase 2.1):
   - After autofill, extension sends `AutofillEvent` data
   - Includes which fields were accepted/rejected
   - Aggregator improves mappings for future runs

### Shared Data Flow

```
┌─────────────────┐
│  User triggers  │
│   autofill      │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│  Phase 2.1: Fetch Learning Profile      │
│  GET /learning/profile                  │
│  → canonical_map, style_hint            │
└────────┬────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│  Phase 3.1: Generate Answers            │
│  POST /generate-form-answers            │
│  → Use style_hint for LLM tone          │
│  → Apply guardrails                     │
└────────┬────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│  Phase 3.0: Render Panel                │
│  → Show per-field controls              │
│  → Confidence from canonical_map votes  │
│  → User edits/accepts/rejects           │
└────────┬────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│  Phase 2.1: Sync Learning Events        │
│  POST /learning/sync                    │
│  → Track accepts/rejects/edits          │
│  → Aggregator improves future profiles  │
└─────────────────────────────────────────┘
```

---

## Summary

### Phase 3.0 Deliverables

- ✅ `FieldAnswerRow` TypeScript interface
- ✅ Panel rendering with per-field controls (checkbox, textarea, confidence badge)
- ✅ CSS styling for row states and badges
- ✅ Vitest unit tests for row conversion
- ✅ Playwright E2E tests tagged `@companion @ux`

### Phase 3.1 Deliverables

- ✅ LLM client abstraction (`companion_client.py`) supporting OpenAI/Ollama
- ✅ Guardrails module (`companion_guardrails.py`) with URL/phrase/length filters
- ✅ Updated `/generate-form-answers` endpoint
- ✅ Pytest tests for guardrails and endpoint
- ✅ Playwright E2E tests tagged `@companion @generation`
- ✅ Feature flag strategy for staged rollout
- ✅ Prometheus metrics for LLM quality and costs
- ✅ Grafana dashboard panels

### Next Steps

1. **Implement Phase 3.0** - Start with panel UX and template answers
2. **Test with users** - Gather feedback on per-field controls
3. **Enable LLM in dev** - Test Ollama integration locally
4. **Beta test Phase 3.1** - Internal users only with OpenAI
5. **Monitor metrics** - Watch for guardrail triggers and quality issues
6. **General rollout** - Enable LLM for all users once validated

---

## Related Documentation

- **Phase 2.0**: `PHASE_2.0_READY.md` - Initial learning loop implementation
- **Phase 2.1**: `PHASE_2.1_COMPLETE.md` - Profile aggregation and quality guards
- **Content Integration**: `CONTENT_INTEGRATION.md` - Wiring learning into content.js
- **Extension Integration**: `EXTENSION_INTEGRATION.md` - Browser extension architecture

**Phase 3 documentation complete.**
