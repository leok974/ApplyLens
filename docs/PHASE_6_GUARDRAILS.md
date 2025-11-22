# Phase 6: Guardrails & Monitoring for Companion Bandit

## Overview

Phase 6 adds production-ready guardrails and observability to the Companion bandit learning system. This includes feature flags, UX controls, monitoring dashboards, and safety alerts to ensure the bandit system runs safely in production.

## Monitoring Infrastructure (Phase 6)

### Prometheus Alerts – Activated

The Companion bandit system is now covered by dedicated Prometheus alert rules.

- Rules file: `applylens-prod-alerts.yml`
- Loaded into the running Prometheus container's rules directory
- Prometheus reloaded via `kill -HUP 1`

Active alert group: **`applylens-companion-bandit`**

Alerts:

1. **ApplyLensCompanionBanditExploreRateHigh**
   - Fires when `explore` share exceeds 40% of `explore+exploit` over a 1h window.
   - Catches runaway exploration (e.g. misconfigured epsilon).

2. **ApplyLensCompanionBanditFallbackSpike**
   - Fires when `fallback` accounts for more than 20% of total bandit events over 1h.
   - Catches kill switch stuck "on" or style selection regressions.

3. **ApplyLensCompanionBanditNoRecommendationSpike**
   - Fires when `source="none"` exceeds 50% of style choices for any `host_family` over 1h.
   - Catches ATS-specific regressions (e.g. Workday / Greenhouse parsing changes).

Validation URLs (local dev):

- Prometheus Alerts: `http://localhost:9090/alerts`
- Prometheus Rules: `http://localhost:9090/rules`

### Grafana Dashboard – ApplyLens Companion Bandit

A dedicated Grafana dashboard provides real-time visibility into bandit behavior.

- Dashboard file: `companion-bandit.json`
- Default title: **"ApplyLens – Companion Bandit (Phase 6)"**
- Panels (overview):
  - **Bandit policy over time** – timeseries of `explore`, `exploit`, `fallback`
  - **Policy × segment (7d)** – table of `policy × segment_key`
  - **Explore rate (24h)** – single stat
  - Additional panels for host_family breakdown and fallback/no-rec rates

Import steps (local dev):

1. Open Grafana at `http://localhost:3000`
2. Go to **Dashboards → Import**
3. Click **"Upload JSON file"** and select `companion-bandit.json`
4. Select the Prometheus datasource
5. Click **"Import"**

Once imported, the dashboard shows the live distribution of bandit policies and gives a quick signal that the learning loop is healthy.

## Feature Flags & Kill Switches

### Backend Flag: COMPANION_BANDIT_ENABLED

- Location: `services/api/app/config.py` (`AgentSettings`)
- Default: `True`
- When disabled:
  - Backend stops returning preferred styles
  - Forces logged policy to `"fallback"`
  - Effectively disables the learning loop at the infrastructure level

### Extension Flag: window.__APPLYLENS_BANDIT_ENABLED

- Controlled via Companion Settings UI ("Allow experimental styles")
- User-facing toggle with clear explanation
- When disabled:
  - Extension uses style hint directly
  - Logs `policy="fallback"`
  - No exploration occurs

This provides both **infra-level** and **user-level** kill switches.

## UX: Companion Settings

The Companion Settings page includes an "Autofill learning" card:

- **Toggle**: "Allow experimental styles"
- **Tooltip**: Explains that the system occasionally tries alternate phrasing/layout
- **Full spec**: Covered by 6 Playwright tests
  - Toggle visibility and functionality
  - Tooltip behavior
  - Persistence across sessions
  - Initial state
  - Interaction flows

## Safety & Rollout Strategy

Phase 6 enables a safe 4-phase rollout:

1. **Dark Launch** (bandit disabled, metrics only)
   - `COMPANION_BANDIT_ENABLED=false`
   - Verify metrics collection works
   - Validate dashboard and alerts

2. **Dev Environment** (bandit enabled, internal testing)
   - `COMPANION_BANDIT_ENABLED=true`
   - Test with real ATS forms
   - Monitor explore rate and fallback behavior

3. **Canary** (user opt-in via settings)
   - Backend enabled
   - Users control via "Allow experimental styles" toggle
   - Monitor per-user metrics

4. **Full Rollout** (default enabled)
   - Toggle defaults to ON
   - Users can still disable
   - Full monitoring in place

## Related Documentation

- `PHASE_6_BANDIT_FEATURE_FLAG.md` - Complete feature flag specification
- `docs/case-studies/applylens-companion-learning.md` - Full case study of the learning system
- `infra/grafana/dashboards/companion-bandit.json` - Dashboard JSON
- `infra/prometheus/rules/applylens-prod-alerts.yml` - Alert rules
