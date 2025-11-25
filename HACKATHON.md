# ApplyLens Observability Copilot - Hackathon Implementation

**Hackathon**: AI Partner Catalyst: Accelerate Innovation
**Partner**: Google Cloud + Datadog
**Deadline**: December 31, 2025, 2:00 PM PST
**Branch**: `hackathon/datadog-gemini`

## Overview

ApplyLens Observability Copilot: A production-grade LLM job-inbox assistant instrumented with Datadog to monitor Gemini-powered classification and extraction, enforce freshness/latency SLOs, detect drift and cost anomalies, and generate actionable incidents with runbooks.

## Architecture

```
┌─────────────────┐
│  ApplyLens Web  │
│  (React/Vite)   │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────┐
│     ApplyLens API (FastAPI)         │
│  ┌──────────────────────────────┐   │
│  │  Gemini Integration Layer    │   │
│  │  - Email intent classification│   │
│  │  - Entity extraction          │   │
│  │  - Heuristic fallbacks        │   │
│  └──────────────────────────────┘   │
└────────┬────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│         Datadog Observability       │
│  ┌─────────────┬─────────────────┐  │
│  │   Metrics   │     Traces      │  │
│  │   • LLM     │   • Classify    │  │
│  │   • Ingest  │   • Extract     │  │
│  │   • Search  │   • Search      │  │
│  └─────────────┴─────────────────┘  │
│  ┌─────────────────────────────┐    │
│  │  SLOs & Monitors            │    │
│  │  • LLM latency < 2s         │    │
│  │  • Ingest lag < 5min        │    │
│  │  • Error rate < 5%          │    │
│  └─────────────────────────────┘    │
└─────────────────────────────────────┘
```

## Quick Start (Hackathon Mode)

### Prerequisites
- Docker & Docker Compose
- Datadog account with API key
- Google Cloud project with Vertex AI enabled
- ApplyLens repo cloned

### Environment Setup

```bash
# 1. Create .env.hackathon file
cp .env.example .env.hackathon

# 2. Add required variables
cat >> .env.hackathon << EOF
# Gemini Integration
USE_GEMINI_FOR_CLASSIFY=1
USE_GEMINI_FOR_EXTRACT=1
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
GEMINI_MODEL=gemini-1.5-flash
GEMINI_TIMEOUT_SECONDS=5

# Datadog
DD_SERVICE=applylens-api-hackathon
DD_ENV=hackathon
DD_VERSION=hackathon-0.1.0
DD_API_KEY=your-datadog-api-key
DD_SITE=datadoghq.com
DD_AGENT_HOST=datadog-agent
DD_TRACE_ENABLED=true
DD_LOGS_ENABLED=true
DD_PROFILING_ENABLED=true
EOF

# 3. Start hackathon environment
docker-compose -f docker-compose.hackathon.yml up -d

# 4. Run traffic generator
python scripts/traffic_generator.py --mode normal_traffic --rate 10 --duration 300
```

### Generate Demo Traffic

```bash
# Normal traffic
python scripts/traffic_generator.py --mode normal_traffic --rate 10 --duration 300

# Trigger latency spike
python scripts/traffic_generator.py --mode latency_injection --rate 20 --duration 120

# Trigger error burst
python scripts/traffic_generator.py --mode error_injection --rate 15 --duration 90

# Trigger cost anomaly
python scripts/traffic_generator.py --mode token_bloat --rate 25 --duration 60
```

## Implementation Checklist

### ✅ Day 1-2: Gemini Integration (COMPLETE)
- [x] Create hackathon branch
- [x] Add environment flags (USE_GEMINI_FOR_CLASSIFY, USE_GEMINI_FOR_EXTRACT)
- [x] Implement GeminiLLMClient with timeout and fallback
- [x] Add classify_email_intent endpoint
- [x] Add extract_job_entities endpoint
- [x] Implement heuristic fallback on error
- [x] Add /debug/llm route for status monitoring
- [x] Add /hackathon/* test endpoints
- [x] Create integration tests

### Day 2-3: Datadog SDK + Telemetry
- [x] Add Datadog dependencies to pyproject.toml
- [x] Create docker-compose.hackathon.yml with Datadog agent
- [x] Add environment configuration (.env.hackathon)
- [x] Implement Datadog instrumentation wrapper
- [x] Add @instrument_llm_call decorator for APM spans
- [x] Emit metrics: llm_latency_ms, llm_error_total, llm_tokens_used
- [ ] Add ingest_lag_seconds metric (to be integrated with Gmail sync)
- [ ] Add search_latency_ms metric (to be integrated with ES queries)
- [ ] Add security_high_risk_rate metric (future enhancement)
- [x] Configure span tags (task_type, model_provider, env)

### Day 3-4: Dashboards, SLOs, Monitors
- [ ] Add Datadog APM to API container
- [ ] Wrap LLM calls with spans
- [ ] Add metrics: llm_latency_ms, llm_error_total, llm_tokens_used
- [ ] Add ingest_lag_seconds metric
- [ ] Add search_latency_ms metric
- [ ] Add security_high_risk_rate metric
- [ ] Configure span tags

### Day 3-4: Dashboards, SLOs, Monitors
- [ ] Create LLM Health dashboard
- [ ] Create Ingest Freshness dashboard
- [ ] Create Security Signals dashboard
- [ ] Define LLM classify latency SLO (99% < 2s)
- [ ] Define Ingest freshness SLO (99% < 5min)
- [ ] Create LLM latency spike monitor
- [ ] Create LLM error burst monitor
- [ ] Create token/cost anomaly monitor
- [ ] Configure incident templates

### Day 4-5: Traffic Generator
- [ ] Create traffic_generator.py script
- [ ] Implement normal_traffic mode
- [ ] Implement latency_injection mode
- [ ] Implement error_injection mode
- [ ] Implement token_bloat mode
- [ ] Add CLI flags
- [ ] Add HACKATHON_TRAFFIC tag

### Day 5-6: Documentation & Exports
- [ ] Export dashboard JSON from Datadog
- [ ] Export SLO definitions
- [ ] Export monitor JSON configurations
- [x] Create ARCHITECTURE.md with diagrams and data flows
- [x] Create TRAFFIC_GENERATOR.md with usage examples
- [x] Update API README.md with hackathon quick start
- [x] Create hackathon-start.ps1 startup script
- [ ] Test full deployment from scratch

### Day 7: Demo Video
- [ ] Deploy to public URL (e.g., Railway, Render, Cloud Run)
- [ ] Run full smoke test
- [ ] Record 3-minute demo video
  - [ ] 0:00-0:20: Problem introduction
  - [ ] 0:20-1:00: Architecture walkthrough
  - [ ] 1:00-2:10: Datadog dashboard tour
  - [ ] 2:10-2:40: Trigger monitor with traffic generator
  - [ ] 2:40-3:00: Show incident + resolution
- [ ] Upload video to YouTube/Vimeo
- [ ] Submit hackathon entry with public demo URL
- [ ] Export dashboard JSON
- [ ] Export SLO definitions
- [ ] Export monitor JSON
- [ ] Create ARCHITECTURE.md
- [ ] Create TRAFFIC_GENERATOR.md
- [ ] Update README.md

### Day 7: Demo Video
- [ ] Run full smoke test
- [ ] Record 3-minute demo video
- [ ] Upload to public URL
- [ ] Submit hackathon entry

## Key Metrics

| Metric | Type | Description | SLO Target |
|--------|------|-------------|------------|
| `llm_latency_ms` | Histogram | LLM request duration | p99 < 2000ms |
| `llm_error_rate` | Rate | Failed LLM calls / total | < 5% |
| `llm_tokens_used` | Counter | Tokens consumed | - |
| `llm_cost_estimate_usd` | Gauge | Estimated cost | - |
| `ingest_lag_seconds` | Histogram | Gmail fetch → searchable | p99 < 300s |
| `search_latency_ms` | Histogram | ES query duration | p95 < 200ms |
| `security_high_risk_rate` | Gauge | High-risk emails / total | - |

## Monitors & Incidents

### 1. LLM Latency Spike
- **Trigger**: p95 llm_latency_ms > 3000ms for 5 minutes
- **Action**: Create incident with dashboard + trace links

### 2. LLM Error Burst
- **Trigger**: llm_error_rate > 5% for 10 minutes
- **Action**: Create incident with error codes + fallback stats

### 3. Cost Anomaly
- **Trigger**: llm_tokens_used > 3x baseline for 10 minutes
- **Action**: Create incident with suspected loops/retries

## Privacy & Security

- **No raw email bodies in logs**
- **PII redaction** on all logged text fields
- **Hashed user/thread IDs** in traces
- **Confidence thresholds** to avoid noisy labels
- **Fallback to heuristics** when Gemini fails

## Resources

- **Datadog Dashboard**: [Link after deployment]
- **Public Demo**: [Link after deployment]
- **GitHub Repo**: https://github.com/leok974/ApplyLens
- **Video Demo**: [Link after recording]

## Contact

For hackathon questions: [Your contact info]
