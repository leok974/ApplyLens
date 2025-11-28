# ApplyLens Companion – Learning & Bandit System (Phase 5–6)

## Overview

ApplyLens Companion is a browser extension that helps me fill out job applications faster and more consistently.
Under the hood, it runs a small learning loop that adapts to my writing style and the structure of different ATS forms.

This case study covers how the learning system works end-to-end, and how Phase 6 added guardrails and observability to make it production-ready.

## Problem

Most job portals ask similar questions in slightly different ways:

- "Why do you want to work here?"
- "Tell us about your relevant experience."
- "Anything else you'd like us to know?"

I already wrote most of these answers in my resume, LinkedIn, and prior applications. The challenge was:

- Re-using those answers without copy-paste hell
- Keeping tone consistent per user and per ATS
- Experimenting with small style tweaks **safely**, without hurting the user experience

## High-Level Architecture

The learning system has four main pieces:

1. **Extension (front-end)**
   - Reads the current application form
   - Calls the ApplyLens API to generate answers
   - Logs each autofill event with rich context: host, ATS family, segment (intern/junior/senior), chosen style, policy (`exploit|explore|fallback`), and feedback.

2. **Backend (API + learning aggregator)**
   - Stores each event in Postgres (`autofill_events`, `form_profiles`, `gen_styles`)
   - Aggregates performance per form, per ATS family, and per segment
   - Suggests a preferred `gen_style_id` to the extension for each host + segment.

3. **Bandit layer**
   - Uses an epsilon-greedy policy (15% explore, 85% exploit by default)
   - Balances between:
     - **Exploit** – use the style that historically worked best
     - **Explore** – occasionally try a different style to discover better options

4. **Observability & Guardrails (Phase 6)**
   - Prometheus metrics and alerts around bandit policies
   - Grafana dashboard for bandit behavior
   - Kill switches on both backend and extension

## Learning Loop

The learning loop runs continuously:

1. **Generate & autofill**
   - Extension calls `POST /api/extension/generate-form-answers`.
   - Backend uses ATS-specific templates + LLM to generate answers.
   - Extension applies answers to the form.

2. **User edits & feedback**
   - User tweaks the answers or accepts them as-is.
   - Extension logs an `autofill_event` with:
     - Host, ATS family (e.g., greenhouse, lever, workday)
     - Segment (intern/junior/senior/default)
     - Chosen style ID and policy
     - Success/feedback signal (e.g., how much the user edited).

3. **Aggregation**
   - A learning component aggregates events into style statistics:
     - Per form
     - Per ATS family
     - Per segment
   - It picks a preferred style per `family × segment` when enough data is available.

4. **Bandit selection**
   - On the next autofill for a given host/segment:
     - Backend returns a style hint (`preferred_style_id`, source).
     - Extension runs an epsilon-greedy bandit (`pickStyleForBandit`) to decide:
       - Exploit (use the preferred style)
       - Explore (sample an alternate style)
     - Policy (`exploit|explore|fallback`) is logged for each event.

5. **Repeat**
   - Over time, the system converges on styles that produce fewer edits and better consistency, per user and per ATS.

## Guardrails & Kill Switches (Phase 6)

Phase 6 focused on making the system safe to run in production.

### Feature Flags

- **Backend flag**: `COMPANION_BANDIT_ENABLED`
  - When `false`, backend:
    - Stops returning preferred styles.
    - Forces the logged policy to `"fallback"`.

- **Extension flag**: `window.__APPLYLENS_BANDIT_ENABLED`
  - Controlled via the Companion Settings UI ("Allow experimental styles").
  - When disabled:
    - Extension uses the given style hint directly.
    - Logs `policy="fallback"` (no exploration).

This gives me both **infra-level** and **user-level** kill switches.

### UX: Companion Settings

In the ApplyLens web app, Companion Settings now includes:

- An **"Autofill learning"** card explaining the behavior in plain language.
- A toggle for **"Allow experimental styles"**.
- A tooltip with a short explanation:
  - Occasionally tries alternate phrasing/layout
  - You can turn this off at any time
  - Data stays within ApplyLens + configured providers

This is fully covered by Playwright tests (6 tests, including tooltip behavior and toggle persistence).

### Monitoring & Alerts

To make the bandit behavior observable:

- Prometheus metric: `autofill_policy_total{policy, host_family, segment_key}`
- Grafana dashboard: **ApplyLens – Companion Bandit (Phase 6)**
  - Timeseries of policy rates over time
  - Policy × segment tables
  - Explore rate (24h) stat with thresholds

Alerts:

- **High explore rate** (>40% explore of explore+exploit)
- **Fallback spike** (>20% fallback of total bandit events)
- **No-recommendation spike** (>50% source="none" per ATS family)

If the bandit misbehaves (too exploratory, degraded, or not recommending), I get a signal quickly and can flip the kill switch.

## Outcome

The result is a Companion learning system that:

- Learns style preferences per ATS and per segment.
- Experiments safely with bandit logic.
- Gives users a clear opt-out for "experimental styles".
- Has operational guardrails: kill switches, metrics, and alerts.

This is the kind of system I can confidently talk about in interviews:
- not just "we use a bandit," but **how it's monitored, controlled, and explained to users.**

## Technical Implementation Details

### Metrics Collection

The system exposes Prometheus metrics via the `/metrics` endpoint:

```python
# Backend metrics (services/api/app/routers/extension_learning.py)
autofill_policy_total = Counter(
    'autofill_policy_total',
    'Count of autofill events by bandit policy',
    ['policy', 'host_family', 'segment_key']
)

applylens_autofill_style_choice_total = Counter(
    'applylens_autofill_style_choice_total',
    'Count of style choices by source',
    ['source', 'host_family', 'segment_key']
)
```

Every autofill event increments these counters with appropriate labels.

### Bandit Algorithm

The epsilon-greedy implementation in the extension:

```typescript
function pickStyleForBandit(
  preferredStyleId: number | null,
  allStyles: GenStyle[],
  epsilon: number = 0.15
): { styleId: number; policy: 'exploit' | 'explore' | 'fallback' } {
  // If no preferred style, use fallback
  if (!preferredStyleId) {
    return { styleId: allStyles[0].id, policy: 'fallback' };
  }

  // Epsilon-greedy: explore with probability epsilon
  if (Math.random() < epsilon) {
    // Explore: pick random style
    const randomStyle = allStyles[Math.floor(Math.random() * allStyles.length)];
    return { styleId: randomStyle.id, policy: 'explore' };
  }

  // Exploit: use preferred style
  return { styleId: preferredStyleId, policy: 'exploit' };
}
```

### Alert Expressions

The Prometheus alerts use PromQL to detect misbehavior:

```yaml
# High explore rate (>40%)
expr: |
  (sum(rate(autofill_policy_total{policy="explore"}[1h])) /
   sum(rate(autofill_policy_total{policy=~"explore|exploit"}[1h]))) > 0.4

# Fallback spike (>20%)
expr: |
  (sum(rate(autofill_policy_total{policy="fallback"}[1h])) /
   sum(rate(autofill_policy_total[1h]))) > 0.2

# No-recommendation per ATS (>50%)
expr: |
  (sum by (host_family)(rate(applylens_autofill_style_choice_total{source="none"}[1h])) /
   sum by (host_family)(rate(applylens_autofill_style_choice_total[1h]))) > 0.5
```

## Future Enhancements

Potential improvements to the learning system:

1. **Contextual bandits** - Factor in additional context (job title, company size, role level)
2. **Thompson sampling** - More sophisticated exploration strategy
3. **Multi-armed bandit per question type** - Different styles for "Why this company?" vs "Tell us about yourself"
4. **A/B testing framework** - Controlled experiments for new features
5. **User feedback integration** - Explicit thumbs up/down on generated content
6. **Performance tracking** - Correlation between style choice and application outcomes

## Related Documentation

- `PHASE_6_GUARDRAILS.md` - Monitoring infrastructure and guardrails overview
- `PHASE_6_BANDIT_FEATURE_FLAG.md` - Complete feature flag specification
- `DEPLOYMENT_VALIDATION_GUARDRAILS.md` - Deployment best practices
- `infra/grafana/dashboards/companion-bandit.json` - Grafana dashboard
- `infra/prometheus/rules/applylens-prod-alerts.yml` - Prometheus alerts
