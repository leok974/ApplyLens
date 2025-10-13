# Overview

ApplyLens is an intelligent job application tracking system that helps you manage and organize your job search emails with AI-powered categorization, risk assessment, and automated workflows.

## What is ApplyLens?

ApplyLens automatically:

- **Categorizes emails** into Applications, Rejections, Interviews, Offers, and Other
- **Assesses risk** using confidence learning to identify potentially malicious emails
- **Extracts job details** from application confirmations
- **Manages security policies** for automated actions
- **Provides analytics** on your job search progress

## Key Features

### Email Intelligence

- Elasticsearch-powered full-text search
- AI-based email categorization
- Anomaly detection for phishing/spam
- Thread grouping and conversation history

### Application Tracking

- Automatic extraction of company, position, and application dates
- Status tracking (Applied, Interview, Offer, Rejected)
- Timeline visualization
- Application notes and annotations

### Security & Automation

- Confidence learning for risk scoring
- Policy-based email actions (label, quarantine, archive)
- User feedback loop for model improvement
- Customizable risk thresholds

### Multi-User Support

- Gmail OAuth integration
- Per-user authentication
- Isolated data storage
- Role-based access control (future)

## Architecture at a Glance

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Frontend  │────▶│   FastAPI    │────▶│ PostgreSQL  │
│  (React +   │     │   Backend    │     │  Database   │
│   Vite)     │     └──────────────┘     └─────────────┘
└─────────────┘            │
                           ▼
                    ┌──────────────┐
                    │Elasticsearch │
                    │   (Search)   │
                    └──────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │  Gmail API   │
                    │   (OAuth)    │
                    └──────────────┘
```

## Technology Stack

**Backend:**

- Python 3.11+ with FastAPI
- PostgreSQL 16 with SQLAlchemy
- Alembic for database migrations
- Elasticsearch 8.x for search
- Gmail API for email sync

**Frontend:**

- React 18 with TypeScript
- Vite for build tooling
- shadcn/ui component library
- TailwindCSS for styling
- Playwright for E2E testing

**Infrastructure:**

- Docker Compose for local development
- Nginx for reverse proxy
- Cloudflared for secure tunneling
- Prometheus + Grafana for monitoring

## Getting Started

See [Getting Started](./GETTING_STARTED.md) for installation and setup instructions.

## Documentation

- [Architecture](./ARCHITECTURE.md) - System design and data flow
- [Backend](./BACKEND.md) - API, database, and services
- [Frontend](./FRONTEND.md) - UI components and state management
- [Security](./SECURITY.md) - Risk assessment and policies
- [Testing](./TESTING.md) - Test infrastructure and CI/CD
- [Operations](./OPS.md) - Deployment and monitoring

## License

[Add your license information here]
