# ApplyLens – Phase 6 Deployment Status (Companion Guardrails & Monitoring)

## Overview

Phase 6 focuses on rollout guardrails, monitoring, and UX polish for the ApplyLens Companion learning system and bandit policy. This document captures the final production deployment state.

**Production domain:** https://applylens.app
**Version:** `v0.6.0-phase6+9647f1f`
**Build time (from /version.json):** `2025-11-16T15:11:06.271Z`

---

## 1. Runtime & Routing

### Containers

- `applylens-web-prod`: `leoklemet/applylens-web:0.6.0-phase6`
- `applylens-api-prod`: `leoklemet/applylens-api:0.6.0-phase6`
- `applylens-db-prod`: PostgreSQL (prod)
- `applylens-es-prod`: Elasticsearch (prod)
- `applylens-redis-prod`: Redis
- `applylens-backfill`: Gmail backfill scheduler
- `infra-cloudflared`: Cloudflare Tunnel
- `applylens-nginx` (dev): local reverse proxy on port 8888 (not in prod path)

### Cloudflare Tunnel

Tunnel `applylens` routes:

- `applylens.app` → `http://applylens-web-prod:80`
- `api.applylens.app` → `http://applylens-api-prod:8000`

**Note:** API container listens on port 8000 internally, host-mapped as `-p 8003:8000`.

---

## 2. Health & Version Validation

### API readiness

- `GET https://applylens.app/api/ready` → ✅ JSON `{"status":"ready","db":"ok","es":"ok","migration":"a1b2c3d4e5f6"}`

### Web version tracking

- `GET https://applylens.app/version.json` → ✅
  - `version`: `v0.6.0-phase6+9647f1f`
  - `buildTime`: `2025-11-16T15:11:06.271Z`
  - Commit SHA: `9647f1f`

### Cache status

- `CF-Cache-Status: DYNAMIC` for `/` confirms Cloudflare is not serving stale HTML.

### Public routes

- Landing page: `GET https://applylens.app/welcome` → ✅ Hero page with "Connect Gmail" + "Try Demo"

---

## 3. Companion / Bandit Features in Prod

### Backend: Bandit + Kill Switch

- Env flags:
  - `COMPANION_BANDIT_ENABLED=True` (default in `AgentSettings`)
  - `COMPANION_AUTOFILL_AGG_ENABLED=1` (aggregator enabled)
- When disabled:
  - `/api/extension/learning/sync` logs `policy="fallback"`.
  - Profile endpoints stop returning `preferred_style_id`.

### Extension: Bandit Client + Kill Switch

- Bandit selection implemented in `content.js` via `pickStyleForBandit(styleHint)`.
- Client kill switch:
  - Helper `isBanditEnabled()` checks `window.__APPLYLENS_BANDIT_ENABLED` with a sane default.
  - When disabled, extension:
    - Uses styleHint directly.
    - Logs `policy="fallback"`.
    - Emits a clear console message.

---

## 4. Companion Settings UI (Phase 6 UX)

Page: `/settings/companion`

- **"Autofill learning"** card:
  - Describes learning behavior and experimental styles.
  - Stable test ID: `companion-autofill-learning-card`.

- **"Allow experimental styles"** toggle:
  - Backed by `window.__APPLYLENS_BANDIT_ENABLED` + localStorage.
  - Stable test ID: `companion-experimental-styles-toggle`.

- Tooltip:
  - Trigger test ID: `companion-experimental-styles-tooltip-trigger`.
  - Content test ID: `companion-experimental-styles-tooltip-content`.

### Tests

Playwright spec: `apps/web/tests/settings-companion-experimental-styles.spec.ts`

- ✅ 6/6 tests passing:
  - Card visible with heading
  - Toggle default = enabled
  - Toggle off / on behavior
  - Persistence across reload
  - Tooltip content appears on hover

---

## 5. Metrics, Dashboard, Alerts

### Prometheus Metrics

Key counters:

- `autofill_policy_total{policy,host_family,segment_key}`
- `applylens_autofill_style_choice_total{source,host_family,segment_key}`

Collected from the API container and scraped by Prometheus.

### Grafana Dashboard

Dashboard JSON: `infra/grafana/dashboards/companion-bandit.json`
Title: **"ApplyLens – Companion Bandit (Phase 6)"**

Panels (at minimum):

- **Timeseries**: `sum by (policy)(rate(autofill_policy_total[5m]))`
- **Table**: `sum by (policy,segment_key)(increase(autofill_policy_total[7d]))`
- **Stat**: 24h explore rate:
  ```promql
  100 * sum(rate(autofill_policy_total{policy="explore"}[1h]))
        / sum(rate(autofill_policy_total{policy=~"explore|exploit"}[1h]))
  ```
- **Table**: Policy × Host Family × Segment (7d)
- **Timeseries**: Style choice source over time

Import steps:
1. Grafana UI → Dashboards → Import
2. Upload `companion-bandit.json`
3. Select Prometheus datasource

### Prometheus Alerts

Rules file: `infra/prometheus/rules/applylens-prod-alerts.yml`
Group: `applylens-companion-bandit`

Alerts:

1. **ApplyLensCompanionBanditExploreRateHigh**
   - `explore / (explore + exploit) > 0.4` for 15m.
   - Indicates epsilon misconfiguration.

2. **ApplyLensCompanionBanditFallbackSpike**
   - `fallback / total > 0.2` for 30m.
   - Indicates bandit disabled or failing.

3. **ApplyLensCompanionBanditNoRecommendationSpike**
   - `source="none" / total > 0.5` per host_family for 30m.
   - Indicates ATS-specific regression.

Validated via:
- `http://localhost:9090/alerts`
- `http://localhost:9090/rules`

Alert group loaded with 3 rules confirmed.

---

## 6. Final Phase 6 Checklist

- ✅ Backend bandit kill switch (`COMPANION_BANDIT_ENABLED`)
- ✅ Extension kill switch (`isBanditEnabled` + `window.__APPLYLENS_BANDIT_ENABLED`)
- ✅ Companion Settings "Autofill learning" card + toggle + tooltip
- ✅ Playwright coverage for Companion Settings (6 tests)
- ✅ Bandit metrics wired to Prometheus
- ✅ Grafana dashboard JSON ready and importable
- ✅ Bandit safety alerts loaded in Prometheus
- ✅ Production deployment with `/version.json` and `/api/ready` passing
- ✅ Version tracking system (`/version.json` endpoint)
- ✅ Docker images pushed to Docker Hub
- ✅ Cloudflare tunnel routing configured
- ✅ Landing page (`/welcome`) accessible in production

**Status:** ✅ Phase 6 fully deployed and monitored in production.

---

## 7. Deployment Timeline

- **Build**: 2025-11-16 15:11 UTC
- **Images pushed**: Docker Hub @ `leoklemet/applylens-{api,web}:0.6.0-phase6`
- **Containers deployed**: Production environment
- **Verification**: All health checks passing
- **Monitoring**: Prometheus + Grafana active

---

## 8. Related Documentation

- `PHASE_6_GUARDRAILS.md` - Complete monitoring infrastructure guide
- `PHASE_6_BANDIT_FEATURE_FLAG.md` - Feature flag specification
- `DEPLOYMENT_VALIDATION_GUARDRAILS.md` - Deployment best practices
- `docs/case-studies/applylens-companion-learning.md` - Full case study

---

## Portfolio / README Snippet

**Companion Learning & Bandit (Phase 6):**
In ApplyLens I shipped a production-ready learning system for the browser Companion that tunes text generation styles per ATS and per seniority segment using an epsilon-greedy bandit. Phase 6 added dual kill switches (backend + user-level), a dedicated Companion Settings experience ("Autofill learning" + toggle + tooltip), full Playwright coverage, Prometheus metrics for bandit policy events, a Grafana dashboard, and three safety alerts for explore, fallback, and no-recommendation anomalies. Everything is versioned via `/version.json` and validated with `/api/ready` in production.
