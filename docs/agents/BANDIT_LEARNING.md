# Companion Bandit System - Phase 6

## Overview

The ApplyLens Companion uses a **multi-armed bandit** algorithm to select the best AI generation style for each job application form. Instead of using a single fixed prompt, the system learns which styles work best for different types of forms (ATS platforms, industries, roles) and optimizes over time.

## What is the Companion?

The **Companion** is a Chrome extension that:
1. Detects job application forms on ATS websites
2. Extracts form fields (name, email, cover letter, etc.)
3. Sends context to the backend API
4. Receives AI-generated answers tailored to the form
5. Autofills the form with one click
6. Tracks user edits to learn preferences

## Generation Styles

A **style** is a specific prompt template and generation strategy. Each style produces answers with different tones, lengths, and formats.

### Available Styles

| Style ID | Description | Best For |
|----------|-------------|----------|
| `concise_bullets_v2` | Short bullet points | ATS systems with character limits |
| `detailed_narrative_v1` | Full paragraphs | Traditional cover letters |
| `casual_conversational_v1` | Friendly tone | Startup applications |
| `formal_corporate_v1` | Professional language | Large enterprise jobs |
| `technical_focused_v1` | Emphasizes tech skills | Engineering roles |

### Style Selection Flow

```
User triggers autofill
     ↓
Extension sends form context (fields, URL, job info)
     ↓
Backend determines ATS family/segment
     ↓
Bandit algorithm selects style (exploit / explore / fallback)
     ↓
LLM generates answers using selected style
     ↓
Extension fills form and logs learning event
     ↓
Backend tracks edit metrics for future optimization
```

## Bandit Algorithm

### Epsilon-Greedy Policy

The system uses **epsilon-greedy exploration** with contextual features:

- **70% Exploit**: Use the best-performing style (highest helpful ratio)
- **20% Explore**: Try a random style to discover better options
- **10% Fallback**: Use default safe style if no data exists

### Key Concepts

#### 1. ATS Family

The **ATS family** identifies the platform hosting the form:

```python
# Examples
"greenhouse" → greenhouse.io forms
"lever" → lever.co forms
"workday" → myworkdayjobs.com
"generic" → Unknown/custom ATS
```

**Detection**: URL pattern matching on hostname
- `greenhouse.io` → `greenhouse`
- `lever.co` → `lever`
- `*.myworkdayjobs.com` → `workday`
- Others → `generic`

#### 2. Segment Key

The **segment key** is a hierarchical feature for contextual bandit decisions:

```
Format: {ats_family}|{role_category}|{seniority}

Examples:
- "greenhouse|engineering|senior"
- "lever|product|mid"
- "workday|sales|entry"
- "generic|unknown|unknown"
```

**Components**:
- `ats_family`: Detected from URL (greenhouse, lever, workday, generic)
- `role_category`: Extracted from job title (engineering, product, sales, marketing, etc.)
- `seniority`: Extracted from title (entry, mid, senior, lead, principal)

**Why segments?**
- Different styles work better for different contexts
- Senior engineering roles need different tone than entry-level sales
- Workday forms have different constraints than Greenhouse

#### 3. Helpful Ratio

The **helpful ratio** measures style quality:

```python
helpful_ratio = accepted_autofills / total_autofills

# Factors that decrease ratio:
- User makes significant edits (>500 chars changed)
- User deletes entire answer
- Low confidence score from LLM

# Factors that increase ratio:
- User accepts answer as-is
- User makes minor edits only (<100 chars)
- High LLM confidence + user acceptance
```

### Policy Decision Logic

```python
def select_style(segment_key: str, available_styles: List[str]) -> dict:
    """
    Select generation style using epsilon-greedy bandit.

    Returns:
        {
            "style_id": "concise_bullets_v2",
            "policy": "exploit",  # or "explore" or "fallback"
            "reason": "best_performer_for_segment"
        }
    """

    # Check if bandit is enabled
    if not COMPANION_BANDIT_ENABLED:
        return {
            "style_id": DEFAULT_STYLE,
            "policy": "fallback",
            "reason": "bandit_disabled"
        }

    # Get stats for this segment
    stats = get_segment_stats(segment_key)

    # No data yet? Use fallback
    if stats.total_runs == 0:
        return {
            "style_id": DEFAULT_STYLE,
            "policy": "fallback",
            "reason": "no_data_for_segment"
        }

    # Epsilon-greedy selection
    rand = random.random()

    if rand < 0.70:  # 70% exploit
        best_style = max(stats.styles, key=lambda s: s.helpful_ratio)
        return {
            "style_id": best_style.style_id,
            "policy": "exploit",
            "reason": f"best_ratio_{best_style.helpful_ratio:.2f}"
        }

    elif rand < 0.90:  # 20% explore
        random_style = random.choice(available_styles)
        return {
            "style_id": random_style,
            "policy": "explore",
            "reason": "random_exploration"
        }

    else:  # 10% fallback
        return {
            "style_id": DEFAULT_STYLE,
            "policy": "fallback",
            "reason": "epsilon_fallback"
        }
```

## Kill Switches

The bandit system has **two independent kill switches** for safe rollback:

### 1. Backend Kill Switch

**Environment Variable**: `COMPANION_BANDIT_ENABLED`

```bash
# Enable bandit (default)
COMPANION_BANDIT_ENABLED=true

# Disable bandit → always use default style
COMPANION_BANDIT_ENABLED=false
```

**Behavior when disabled**:
- All requests use `DEFAULT_STYLE` (typically `concise_bullets_v2`)
- Policy set to `"fallback"`
- No bandit stats collected
- Learning events still logged for observability

**When to disable**:
- Bandit causing unexpected behavior
- Need stable/predictable generation
- Debugging generation quality issues
- A/B testing against baseline

### 2. Extension Kill Switch

**Function**: `isBanditEnabled()`

Located in: `apps/extension-applylens/learning/client.js`

```javascript
function isBanditEnabled() {
  // Check window flag (for testing)
  if (typeof window !== 'undefined' &&
      window.__APPLYLENS_BANDIT_ENABLED !== undefined) {
    return window.__APPLYLENS_BANDIT_ENABLED;
  }

  // Default: enabled
  return true;
}
```

**Override for testing**:
```javascript
// In Chrome DevTools console on any page:
window.__APPLYLENS_BANDIT_ENABLED = false;

// Now all autofill requests will skip bandit context
```

**Behavior when disabled**:
- Extension doesn't send segment/ATS info to backend
- Backend treats request as "no context" → uses fallback
- Useful for comparing bandit vs baseline in same session

### Interaction Between Kill Switches

| Backend Enabled | Extension Enabled | Result |
|----------------|-------------------|--------|
| ✅ true | ✅ true | Bandit fully active |
| ✅ true | ❌ false | Backend can't use context → fallback |
| ❌ false | ✅ true | Backend ignores context → fallback |
| ❌ false | ❌ false | Double-fallback → default style |

**Best practice**: Keep both enabled in production. Use extension override for per-user debugging.

## Data Flow

### 1. Autofill Request

```
Extension detects form
     ↓
Extension calls isBanditEnabled()
     ↓
IF enabled:
    Extract ATS family from URL
    Extract segment from job title
    Build context object
     ↓
POST /api/extension/generate-form-answers
{
  "job": { "title": "Senior AI Engineer", "company": "AcmeCo" },
  "fields": [ { "field_id": "cover_letter", "label": "Why here?" } ],
  "context": {
    "ats_family": "greenhouse",
    "segment_key": "greenhouse|engineering|senior",
    "url": "https://boards.greenhouse.io/acmeco/jobs/123"
  }
}
```

### 2. Backend Processing

```python
# 1. Check kill switch
if not COMPANION_BANDIT_ENABLED:
    style_id = DEFAULT_STYLE
    policy = "fallback"
else:
    # 2. Select style using bandit
    selection = bandit.select_style(
        segment_key=context["segment_key"],
        available_styles=ENABLED_STYLES
    )
    style_id = selection["style_id"]
    policy = selection["policy"]

# 3. Generate answers with selected style
answers = llm_generate(
    fields=fields,
    job=job,
    style_id=style_id
)

# 4. Record metrics
prometheus.autofill_policy_total.labels(
    policy=policy,
    ats_family=context["ats_family"],
    style=style_id
).inc()

# 5. Return to extension
return {
    "answers": answers,
    "metadata": {
        "style_id": style_id,
        "policy": policy,
        "segment_key": context["segment_key"]
    }
}
```

### 3. Learning Event Logging

```
User edits answer in form
     ↓
Extension calculates edit_distance and avg_edit_chars
     ↓
POST /api/extension/learning/sync
{
  "host": "boards.greenhouse.io",
  "schema_hash": "md5_of_field_structure",
  "events": [
    {
      "field_id": "cover_letter",
      "user_value": "Final answer after edits...",
      "generated_value": "Original AI answer...",
      "style_id": "concise_bullets_v2",
      "edit_stats": {
        "edit_distance": 45,
        "avg_edit_chars": 120
      }
    }
  ]
}
```

### 4. Metrics and Analysis

Backend calculates helpful ratio:

```python
for event in events:
    # Significant edits → not helpful
    if event.edit_stats.avg_edit_chars > 500:
        helpful = False
    # Minor edits → helpful
    elif event.edit_stats.avg_edit_chars < 100:
        helpful = True
    # Medium edits → neutral (skip)
    else:
        continue

    # Update stats in database
    update_style_stats(
        segment_key=event.segment_key,
        style_id=event.style_id,
        helpful=helpful
    )
```

## Prometheus Metrics

### Key Metrics

#### 1. `autofill_policy_total`

**Type**: Counter

**Labels**:
- `policy`: `exploit`, `explore`, `fallback`
- `ats_family`: `greenhouse`, `lever`, `workday`, `generic`
- `style`: Style ID used

**Purpose**: Track which policy decision was made

**Example queries**:
```promql
# Total autofills by policy
sum(rate(autofill_policy_total[1h])) by (policy)

# Exploit rate by ATS family
rate(autofill_policy_total{policy="exploit"}[1h]) / rate(autofill_policy_total[1h])

# Most used styles
topk(5, sum(rate(autofill_policy_total[1h])) by (style))
```

#### 2. `autofill_style_helpful_ratio`

**Type**: Gauge

**Labels**:
- `segment_key`: Full segment (e.g., "greenhouse|engineering|senior")
- `style`: Style ID

**Purpose**: Current helpful ratio per segment/style

**Example queries**:
```promql
# Best performing styles
topk(10, autofill_style_helpful_ratio)

# Styles below threshold (need tuning)
autofill_style_helpful_ratio < 0.5
```

#### 3. `autofill_learning_events_total`

**Type**: Counter

**Labels**:
- `host`: Hostname of form
- `outcome`: `helpful`, `not_helpful`, `neutral`

**Purpose**: Track learning event volume

**Example queries**:
```promql
# Event rate by outcome
sum(rate(autofill_learning_events_total[1h])) by (outcome)

# Top hosts by events
topk(10, sum(rate(autofill_learning_events_total[1h])) by (host))
```

### Alerts

#### High Explore Rate

```yaml
alert: HighExploreRate
expr: |
  sum(rate(autofill_policy_total{policy="explore"}[5m]))
  / sum(rate(autofill_policy_total[5m])) > 0.30
for: 10m
annotations:
  summary: "Explore rate above 30% (expected 20%)"
  description: "Check if epsilon value changed or stats corrupted"
```

#### High Fallback Rate

```yaml
alert: HighFallbackRate
expr: |
  sum(rate(autofill_policy_total{policy="fallback"}[5m]))
  / sum(rate(autofill_policy_total[5m])) > 0.20
for: 10m
annotations:
  summary: "Fallback rate above 20% (expected 10%)"
  description: "Check if bandit disabled or stats missing"
```

#### Low Helpful Ratio

```yaml
alert: LowHelpfulRatio
expr: |
  autofill_style_helpful_ratio < 0.3
for: 1h
annotations:
  summary: "Style {{ $labels.style }} helpful ratio below 30%"
  description: "Consider disabling style or retuning prompt"
```

## Testing

### Unit Tests

Located in: `services/api/tests/test_bandit.py`

```python
def test_bandit_exploit_policy():
    """Exploit policy should select best style"""

def test_bandit_explore_policy():
    """Explore policy should try random styles"""

def test_bandit_fallback_when_no_data():
    """Fallback when segment has no stats"""

def test_bandit_kill_switch():
    """Disabled bandit should always return default"""
```

### E2E Tests

Located in: `apps/extension-applylens/e2e/autofill-bandit.spec.ts`

```typescript
test("exploit policy uses best style", async ({ page }) => {
  // Mock bandit stats with clear winner
  // Trigger autofill
  // Assert correct style selected
});

test("explore policy tries different styles", async ({ page }) => {
  // Mock equal stats
  // Trigger autofill multiple times
  // Assert variety of styles used
});

test("fallback when bandit disabled", async ({ page }) => {
  // Set COMPANION_BANDIT_ENABLED=false
  // Trigger autofill
  // Assert default style used
});
```

### Manual Testing

```bash
# 1. Enable debug logging
export LOG_LEVEL=DEBUG

# 2. Check current stats
curl http://localhost:8003/api/admin/bandit/stats | jq

# 3. Trigger autofill with known context
curl -X POST http://localhost:8003/api/extension/generate-form-answers \
  -H "Content-Type: application/json" \
  -d '{
    "job": {"title": "Senior AI Engineer"},
    "fields": [{"field_id": "cover_letter", "label": "Why?"}],
    "context": {
      "ats_family": "greenhouse",
      "segment_key": "greenhouse|engineering|senior"
    }
  }' | jq '.metadata'

# 4. Check metrics
curl http://localhost:8003/metrics | grep autofill_policy
```

## Grafana Dashboard

**Name**: "ApplyLens - Companion Bandit (Phase 6)"

**Panels**:
1. **Policy Distribution** - Pie chart of exploit/explore/fallback
2. **Helpful Ratio by Style** - Time series per style
3. **Autofill Rate** - Total autofills per minute
4. **Top ATS Families** - Bar chart of most used platforms
5. **Learning Event Rate** - Helpful vs not helpful events
6. **Segment Coverage** - % of segments with >10 samples

**Access**: http://applylens.app:3001/d/companion-bandit

## Common Issues & Debugging

### Issue: All requests use fallback policy

**Symptoms**:
- Prometheus shows `autofill_policy_total{policy="fallback"}` = 100%
- No exploit or explore decisions

**Possible causes**:
1. Backend kill switch enabled: `COMPANION_BANDIT_ENABLED=false`
2. No stats in database (fresh install)
3. Extension not sending context

**Debug steps**:
```bash
# Check backend env var
docker exec applylens-api-prod printenv | grep COMPANION_BANDIT_ENABLED

# Check database stats
docker exec applylens-api-prod python -c "
from app.bandit import get_segment_stats
stats = get_segment_stats('greenhouse|engineering|senior')
print(f'Total runs: {stats.total_runs}')
"

# Check extension logs in browser console
# Should see: [Bandit] Context: { ats_family: "greenhouse", ... }
```

### Issue: Helpful ratio stuck at 0

**Symptoms**:
- `autofill_style_helpful_ratio` shows 0.0 for all styles
- Learning events logged but not updating stats

**Possible causes**:
1. Learning sync endpoint not processing events
2. Edit stats calculation broken
3. Database write failing

**Debug steps**:
```bash
# Check learning endpoint logs
docker logs applylens-api-prod | grep "learning/sync"

# Manually trigger sync with curl
curl -X POST http://localhost:8003/api/extension/learning/sync \
  -H "Content-Type: application/json" \
  -d '{
    "host": "test.com",
    "schema_hash": "test123",
    "events": [{
      "field_id": "test",
      "generated_value": "Original",
      "user_value": "Edited",
      "style_id": "concise_bullets_v2",
      "edit_stats": { "edit_distance": 10, "avg_edit_chars": 50 }
    }]
  }'

# Check database
docker exec applylens-api-prod python -c "
from app.database import SessionLocal
from app.models import StyleStats
db = SessionLocal()
stats = db.query(StyleStats).first()
print(stats)
"
```

### Issue: High explore rate (>30%)

**Symptoms**:
- Prometheus shows explore policy > 30% (expected 20%)
- Users complain about inconsistent quality

**Possible causes**:
1. Epsilon value misconfigured
2. Random seed issue
3. Stats not updating (treats as "no data")

**Fix**:
```python
# Check epsilon in code
EPSILON_EXPLOIT = 0.70  # Should be 70%
EPSILON_EXPLORE = 0.20  # Should be 20%
EPSILON_FALLBACK = 0.10  # Should be 10%

# Verify sum = 1.0
assert EPSILON_EXPLOIT + EPSILON_EXPLORE + EPSILON_FALLBACK == 1.0
```

## Future Enhancements

### Phase 7: Contextual Features
- Add company size, industry to segment key
- Use embeddings for job description similarity
- Cluster similar segments for cold start

### Phase 8: Thompson Sampling
- Replace epsilon-greedy with Thompson sampling
- Better exploration/exploitation balance
- Bayesian confidence intervals

### Phase 9: Per-User Personalization
- Track helpful ratio per user
- Allow users to set style preferences
- Hybrid user-segment model

### Phase 10: Multi-Objective Optimization
- Optimize for speed + quality
- Balance token cost vs satisfaction
- A/B test different LLM models per segment
