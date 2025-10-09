# ApplyLens
Agentic job-inbox MVP: classify job/search emails, extract key facts, and populate a tracker.

## 🎯 Features

✨ **Gmail Integration** - OAuth 2.0 authentication and automated email backfill
🏷️ **Smart Labeling** - Automatic detection of interviews, offers, rejections, and more
🔍 **Advanced Search** - Full-text search with synonym support and recency boosting
💡 **Autocomplete** - Real-time suggestions with "did you mean" spell correction
📊 **Analytics Dashboard** - Kibana visualizations for job search insights
📧 **Inbox Management** - Filter by label, pagination, and bulk sync

## Gmail Integration Setup

ApplyLens now supports **Gmail OAuth authentication** with intelligent email classification!

### Quick Start

1. **Create Google OAuth Credentials:**
   - Follow the detailed guide in [`GMAIL_SETUP.md`](./GMAIL_SETUP.md)
   - Save your `google.json` to `infra/secrets/`

2. **Configure Environment:**
   ```bash
   cp infra/.env.example infra/.env
   # Edit infra/.env and set OAUTH_STATE_SECRET to a random string
   ```

3. **Start Services:**
   ```bash
   docker compose -f infra/docker-compose.yml up -d
   ```

4. **Connect Gmail:**
   - Visit http://localhost:8003/auth/google/login
   - Grant permissions
   - You'll be redirected to the Inbox page

5. **Sync Your Emails:**
   - Click "Sync 60 days" in the Inbox page
   - Or use the API: `curl -X POST "http://localhost:8003/gmail/backfill?days=60&user_email=your@gmail.com"`

### Automatic Email Labeling

Emails are automatically labeled based on content:

- 📅 **interview** - Interview invitations, phone screens, onsite visits
- 🎉 **offer** - Job offers and offer letters
- ❌ **rejection** - Rejection notifications
- ✅ **application_receipt** - Application confirmations
- 📰 **newsletter_ads** - Promotional emails and newsletters

### API Endpoints

```bash
# OAuth Flow
GET  /auth/google/login        # Start OAuth
GET  /auth/google/callback     # OAuth callback

# Gmail Operations
GET  /gmail/status             # Check connection status
GET  /gmail/inbox              # Get paginated emails
POST /gmail/backfill           # Sync emails from Gmail

# Search with label filters
GET  /search?q=interview&label_filter=interview
GET  /suggest?q=interv         # Autocomplete suggestions
```

For complete documentation, see [`GMAIL_SETUP.md`](./GMAIL_SETUP.md).

## Quickstart (Docker) - Minimal Setup

Fast start without Elasticsearch/Kibana:

```bash
cp infra/.env.example infra/.env
docker compose -f infra/docker-compose.minimal.yml up -d

# Seed the database
docker compose -f infra/docker-compose.minimal.yml exec api python -m app.seeds.seed_emails

# Check the ports in infra/.env (defaults: API=8002, Web=5174)
```

**Access:**
- Web: http://localhost:5174 (check `.env` for actual port)
- API: http://localhost:8002
- API Docs: http://localhost:8002/docs

## Full Setup (with Elasticsearch + Kibana)

Includes search and analytics dashboard with synonym support:

```bash
cp infra/.env.example infra/.env
# Optional during dev: force ES index recreation so synonyms/mappings apply
# (already true in .env.example)
# ES_RECREATE_ON_START=true

docker compose -f infra/docker-compose.yml up --build

# In another terminal, seed mock emails and index into Elasticsearch:
docker compose -f infra/docker-compose.yml exec api python -m app.seeds.seed_emails
```

**Access:**
- Web: http://localhost:5175
- API: http://localhost:8003
- Elasticsearch: http://localhost:9200
- Kibana: http://localhost:5601

### Import Kibana Dashboard

Once Kibana is running:
```bash
curl -X POST "http://localhost:5601/api/saved_objects/_import?overwrite=true" \
  -H "kbn-xsrf: true" \
  -F file=@infra/kibana/applylens_dashboard.ndjson
```

Or manually: **Kibana → Stack Management → Saved Objects → Import** and select `infra/kibana/applylens_dashboard.ndjson`

### Test the Search API & Synonyms

Synonym examples that should match due to the analyzer:
- Query **"talent partner"** should match emails containing **"recruiter"**
- Query **"offer letter"** should match **"offer" / "acceptance"**
- Query **"phone screen"** should match **"interview"** content

```bash
curl "http://localhost:8000/search/?q=Interview"
curl "http://localhost:8000/search/?q=talent%20partner"
```

Then visit **http://localhost:5173/search** and try queries like `Interview`, `talent partner`, or `Greenhouse`.

## Local dev (without Docker)

Backend:
```bash
cd services/api
python -m venv .venv && source .venv/bin/activate
pip install -U pip && pip install .
export ES_ENABLED=false  # disable ES when not running locally
uvicorn app.main:app --reload --port 8003
```

Frontend:
```bash
cd apps/web
npm install
npm run dev
```

## Architecture

- **Backend**: FastAPI + SQLAlchemy + PostgreSQL + Elasticsearch
- **Frontend**: React + TypeScript + Vite
- **Search**: Elasticsearch with custom analyzers (synonyms, shingles, completion suggester)
- **Auth**: Google OAuth 2.0 with secure token storage
- **Email Processing**: Gmail API + BeautifulSoup + heuristic labeling

## Next steps
- ✅ ~~Implement Gmail read-only OAuth and backfill endpoint~~ **DONE!**
- Add Applications table UI + reminders
- Elasticsearch relevance tuning (synonyms, boosts)
- Enhance Kibana dashboard with more visualizations
- Add ML-based email classification
- Implement scheduled email sync (cron jobs)
- Multi-user support with session management

## 📚 Documentation

All documentation has been organized in the [`docs/`](./docs/) folder:

- **[Getting Started](./docs/SETUP_COMPLETE_SUMMARY.md)** - Complete setup guide
- **[Gmail Setup](./docs/GMAIL_SETUP.md)** - OAuth configuration
- **[Reply Metrics](./docs/REPLY_METRICS_QUICKSTART.md)** - Filter & TTR badges (5-min guide)
- **[Advanced Filtering](./docs/ADVANCED_FILTERING_SUMMARY.md)** - Label & date filters
- **[Monitoring](./docs/MONITORING_QUICKREF.md)** - Prometheus & Grafana
- **[Production Deployment](./docs/PRODUCTION_SETUP.md)** - Hardening & security
- **[Testing](./docs/RUNNING_TESTS.md)** - Unit & E2E tests

📖 **See the [Documentation Index](./docs/README.md) for the complete list of 70+ guides.**
