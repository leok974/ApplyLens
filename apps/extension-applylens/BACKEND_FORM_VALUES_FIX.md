# Backend Fix: Generate Form-Ready Values (Not Placeholder Text)

## Problem

The LLM is currently generating placeholder/debug text instead of actual form values:

```json
{
  "email": "Answer for 'Email*' based on AI Engineer and my projects...",
  "phone": "Answer for 'Phone' based on AI Engineer and my projects...",
  "years_experience": "Answer for 'How many years...' based on AI Engineer..."
}
```

This is because the prompt is in "explain mode" not "fill form mode".

## Solution

Update the `/api/extension/generate-form-answers` endpoint to:

1. **Pre-fill profile fields** from user profile (don't ask LLM)
2. **Update LLM prompt** to generate form-ready values only
3. **Return clean values** suitable for direct form insertion

---

## 1. Pre-fill Profile Fields (Deterministic)

Before calling the LLM, extract profile fields directly:

```python
# In /api/extension/generate-form-answers handler

answers = {}

# Profile fields that should NEVER go through LLM
PROFILE_FIELDS = {
    "first_name", "last_name", "email", "phone", "linkedin",
    "github", "portfolio", "website", "location"
}

# Pre-fill from profile
for field in request_data["fields"]:
    canonical = field.get("canonical") or field.get("field_id")

    if canonical in PROFILE_FIELDS:
        # Get directly from profile
        value = profile.get(canonical)
        if value:
            answers[canonical] = value

# Only send non-profile fields to LLM
fields_for_llm = [
    f for f in request_data["fields"]
    if (f.get("canonical") or f.get("field_id")) not in answers
]
```

---

## 2. Update LLM System Prompt

Replace the current system message with:

```text
You are ApplyLens Companion, an AI assistant that helps job seekers fill out online application forms.

You are given:
- "job_meta": job title, company, location, description
- "profile": candidate's information (name, email, skills, experience, projects, etc.)
- "fields": list of form fields to fill, each with:
  - "canonical": normalized field type (years_experience, cover_letter, headline, etc.)
  - "label": exact label shown on the page
  - "input_type": textarea, text, select, number, etc.

Your job is to produce **form-ready values**, NOT explanations or descriptions.

RULES:
1. For numeric fields (years_experience, salary, etc.):
   - Return ONLY a number: "3" or "5.5", never a sentence

2. For short text fields (headline, job_title, city):
   - Return a short phrase suitable for that input
   - Example: "AI/ML Engineer" NOT "Answer for headline based on..."

3. For longer fields (cover_letter, motivation, free text):
   - Write 2-5 sentences maximum
   - Be specific and grounded in profile + job_meta
   - Use concrete examples from profile.projects or profile.experience

4. NEVER include:
   - Phrases like "Answer for...", "Based on...", "This should be..."
   - Meta-commentary about the question
   - Mentions of "ApplyLens" in the answer text

5. If you cannot provide a good answer:
   - Return an empty string "" rather than placeholder text

You MUST respond with ONLY a JSON object:
{"answers": {"<canonical>": "<value>", ...}}

Nothing else. No markdown. No explanation.
```

---

## 3. Update User Message Format

Structure the request to the LLM as:

```json
{
  "job_meta": {
    "title": "AI Engineer",
    "company": "SAF AI Centre",
    "location": "Singapore",
    "description": "<full job description text>"
  },
  "profile": {
    "first_name": "Leo",
    "last_name": "Klemet",
    "headline": "AI/ML Engineer & full-stack builder",
    "location": "Singapore",
    "experience": [
      {"title": "...", "company": "...", "description": "..."},
      ...
    ],
    "projects": [
      {"name": "ApplyLens", "description": "AI-powered job application assistant"},
      {"name": "SiteAgent", "description": "..."},
      ...
    ],
    "skills": ["Python", "TypeScript", "React", "LLMs", ...],
    "education": [...]
  },
  "fields": [
    {
      "canonical": "years_experience",
      "label": "How many years of hands-on coding experience do you have?*",
      "input_type": "number"
    },
    {
      "canonical": "cover_letter",
      "label": "Why do you want to work at SAF?",
      "input_type": "textarea"
    },
    ...
  ]
}
```

---

## 4. Parse and Merge Response

```python
# Call LLM with updated prompt
llm_response = await call_llm(system_prompt, user_message)

# Parse response
try:
    parsed = json.loads(llm_response)
    llm_answers = parsed.get("answers", {})
except:
    llm_answers = {}

# Merge LLM answers with pre-filled profile fields
answers.update(llm_answers)

# Convert to expected format: [{field_id, answer}, ...]
result = {
    "answers": [
        {"field_id": field_id, "answer": value}
        for field_id, value in answers.items()
    ]
}

return result
```

---

## Expected Result

After these changes, the frontend should receive:

```json
{
  "answers": [
    {"field_id": "first_name", "answer": "Leo"},
    {"field_id": "last_name", "answer": "Klemet"},
    {"field_id": "email", "answer": "leoklemet.pa@gmail.com"},
    {"field_id": "phone", "answer": "+65 1234 5678"},
    {"field_id": "linkedin", "answer": "https://www.linkedin.com/in/leoklemet"},
    {"field_id": "years_experience", "answer": "4"},
    {"field_id": "cover_letter", "answer": "I am excited to join SAF's AI Centre because..."}
  ]
}
```

No "Answer for..." placeholders - just clean, form-ready values.

---

## Frontend Safety Guard (Already Added)

The extension now includes a `normalizeAnswerText()` function in `contentV2.js` that filters out placeholder patterns as a safety net:

```javascript
function normalizeAnswerText(label, value) {
  if (!value || typeof value !== 'string') return value;

  const lower = value.toLowerCase();

  // Drop obvious placeholder patterns
  if (lower.startsWith('answer for ') ||
      lower.includes('based on ai engineer') ||
      lower.includes('based on my projects')) {
    return ''; // Filter to empty instead of applying bad text
  }

  return value.trim();
}
```

This prevents accidentally pasting "Answer for..." into live applications while you update the backend.

---

## Testing

After implementing these changes:

1. Reload the extension
2. Navigate to a job application form
3. Click "Scan" then "Generate"
4. Check browser console for:
   ```
   [v0.3] Generated AI suggestions: {
     first_name: "Leo",
     email: "leoklemet.pa@gmail.com",
     years_experience: "4",
     ...
   }
   ```

All values should be form-ready, no placeholder text.
