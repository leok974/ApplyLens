# ApplyLens Overview

## One-Paragraph Pitch

ApplyLens is an AI-powered job application assistant that transforms your Gmail inbox into an intelligent job tracker and provides a Chrome extension for instant form autofill. It ingests emails from recruiters and job boards, surfaces actionable opportunities with risk scoring, and learns your communication style to generate personalized cover letters and responses. Built for active job seekers who need to manage dozens of applications efficiently while maintaining quality and personalization.

## Core Flows

### 1. Gmail Ingestion → Search → Tracker

```
Gmail API → FastAPI Backend → Elasticsearch
     ↓
BigQuery (warehouse) ← Fivetran sync
     ↓
React/Vite Frontend (search, tracker, profile)
```

- **Ingestion**: Backend pulls emails via Gmail API, indexes in Elasticsearch
- **Search**: Full-text search with filters (date range, sender, category)
- **Tracker**: Job application tracking with status, deadlines, and risk scores
- **Profile**: Analytics showing top senders, categories, and email volume

### 2. Companion Extension → Autofill → Logging

```
Chrome Extension (content.js) → Detect ATS form
     ↓
Service Worker (sw.js) → POST /api/extension/generate-form-answers
     ↓
Backend (LLM + bandit) → Generate personalized answers
     ↓
Content Script → Fill form + Log learning events
     ↓
Backend metrics → Grafana dashboards
```

- **Detection**: Extension scans page for job application forms
- **Generation**: Backend uses bandit algorithm to select generation style
- **Autofill**: Extension fills fields with one click
- **Learning**: Tracks edits and quality metrics for continuous improvement

## Main Tech Stack

### Backend
- **FastAPI** (Python 3.12) - API server with async support
- **PostgreSQL** - Relational data (users, sessions, applications)
- **Elasticsearch 8.x** - Email search and indexing
- **BigQuery** - Data warehouse via Fivetran
- **Redis** - Session storage and caching

### Frontend
- **React 18** - UI framework
- **Vite** - Build tool and dev server
- **TailwindCSS** - Styling
- **React Router** - Client-side routing
- **Playwright** - E2E testing

### Extension
- **Manifest V3** - Chrome extension format
- **Zero-bundle** - Plain ES modules (no webpack/rollup)
- **Content Scripts** - Form detection and filling
- **Service Worker** - Background API calls

### Infrastructure
- **Docker Compose** - Service orchestration
- **Cloudflare Tunnel** - Zero-trust network access
- **nginx** - Reverse proxy and static file serving
- **Prometheus + Grafana** - Metrics and monitoring

## Key Links & Documentation

### Infrastructure
- [`infra/README.md`](../infra/README.md) - Production deployment guide
- [`docs/APPLYLENS_ARCHITECTURE.md`](./APPLYLENS_ARCHITECTURE.md) - Service architecture
- [`infra/PHASE_6_PROD_AUTH_ME_502_FIX.md`](../infra/PHASE_6_PROD_AUTH_ME_502_FIX.md) - Auth endpoint fix

### Companion Extension
- [`apps/extension-applylens/README.md`](../apps/extension-applylens/README.md) - Extension dev guide
- [`docs/COMPANION_BANDIT_PHASE6.md`](./COMPANION_BANDIT_PHASE6.md) - Bandit learning system
- [`docs/COMPANION_EXTENSION_PROTOCOL.md`](./COMPANION_EXTENSION_PROTOCOL.md) - Message protocol

### Testing
- [`docs/TESTING_AND_E2E_OVERVIEW.md`](./TESTING_AND_E2E_OVERVIEW.md) - Test strategy
- [`apps/extension-applylens/TESTING.md`](../apps/extension-applylens/TESTING.md) - Extension tests

### Monitoring
- [`docs/METRICS_AND_DASHBOARDS.md`](./METRICS_AND_DASHBOARDS.md) - Observability guide

## Quick Start

### Run Locally

```bash
# Start all services
cd infra
docker compose up -d

# Web app: http://localhost:5175
# API: http://localhost:8003
# API docs: http://localhost:8003/docs
```

### Load Extension

1. Open Chrome → `chrome://extensions`
2. Enable "Developer mode"
3. Load unpacked → `apps/extension-applylens`
4. Test on demo form: `http://localhost:5175/demo-form.html`

### Deploy to Production

```bash
# Build and push web image
cd apps/web
docker build -f Dockerfile.prod -t leoklemet/applylens-web:latest .
docker push leoklemet/applylens-web:latest

# Update production
cd infra
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

## Production URLs

- **Web App**: https://applylens.app
- **API**: https://api.applylens.app
- **Metrics**: http://applylens.app:9090 (Prometheus)
- **Dashboards**: http://applylens.app:3001 (Grafana)

## Repository Structure

```
ApplyLens/
├── apps/
│   ├── web/                 # React/Vite frontend
│   └── extension-applylens/ # Chrome extension
├── services/
│   └── api/                 # FastAPI backend
├── infra/                   # Docker, nginx, Cloudflare
├── docs/                    # Documentation
└── tests/                   # Integration tests
```
