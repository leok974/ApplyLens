# Getting Started

This guide will help you get ApplyLens up and running on your local machine.

## Prerequisites

- **Docker** and **Docker Compose** (for running services)
- **Node.js** 18+ and **npm** (for frontend)
- **Python** 3.11+ (for backend development)
- **PostgreSQL** 16 (via Docker)
- **Elasticsearch** 8.x (via Docker)

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/leok974/ApplyLens.git
cd ApplyLens
```

### 2. Set Up Environment Variables

Copy the example environment file and configure it:

```bash
cp infra/.env.example infra/.env
```

Edit `infra/.env` with your settings:

```env
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=applylens
API_PORT=8003
WEB_PORT=5175

# Gmail OAuth (required for email sync)
GMAIL_CLIENT_ID=your_client_id
GMAIL_CLIENT_SECRET=your_client_secret
GMAIL_REDIRECT_URI=http://localhost:8003/auth/google/callback

# Elasticsearch
ES_URL=http://elasticsearch:9200
ES_EMAIL_INDEX=emails_v1

# Security
CORS_ORIGINS=http://localhost:5175
```

### 3. Start the Infrastructure

```bash
# Start PostgreSQL, Elasticsearch, and other services
docker compose -f infra/docker-compose.yml up -d
```

### 4. Set Up the Database

```bash
# Run Alembic migrations
cd services/api
alembic upgrade head
```

### 5. Start the Backend API

```bash
# Install Python dependencies
cd services/api
pip install -r requirements.txt

# Run the FastAPI server
uvicorn app.main:app --reload --port 8003
```

The API will be available at: <http://localhost:8003>

API docs: <http://localhost:8003/docs>

### 6. Start the Frontend

```bash
# Install Node dependencies
cd services/web
npm install

# Start Vite dev server
npm run dev
```

The web app will be available at: <http://localhost:5175>

## Gmail OAuth Setup

To sync emails from Gmail, you need to set up OAuth credentials:

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Gmail API
4. Create OAuth 2.0 credentials (Web application)
5. Add authorized redirect URI: `http://localhost:8003/auth/google/callback`
6. Copy the Client ID and Client Secret to your `.env` file

See [Gmail Integration](./GMAIL_INTEGRATION.md) for detailed setup instructions.

## Verify Installation

### Check Services

```bash
# Check Docker containers
docker compose -f infra/docker-compose.yml ps

# Should show:
# - applylens-db (PostgreSQL)
# - applylens-es (Elasticsearch)
```

### Check API Health

```bash
curl http://localhost:8003/health
# Should return: {"status":"healthy"}
```

### Check Frontend

Open <http://localhost:5175> in your browser. You should see the ApplyLens login page.

## Development Workflow

### Run Tests

```bash
# Backend tests
cd services/api
pytest

# Frontend E2E tests
cd ../..
npm run test:e2e
```

### Database Migrations

```bash
# Create a new migration
cd services/api
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

### Code Quality

```bash
# Lint Python code
cd services/api
ruff check .
black --check .

# Lint TypeScript/React
cd ../web
npm run lint
```

## Common Issues

### Port Already in Use

If ports 8003 or 5175 are already in use:

```bash
# Change ports in infra/.env
API_PORT=8004
WEB_PORT=5176
```

### Database Connection Failed

Check that PostgreSQL is running:

```bash
docker compose -f infra/docker-compose.yml logs db
```

Verify connection string in `.env`:

```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/applylens
```

### Elasticsearch Not Ready

Wait for Elasticsearch to start (can take 30-60 seconds):

```bash
curl http://localhost:9200/_cluster/health
```

## Next Steps

- [Architecture](./ARCHITECTURE.md) - Understand the system design
- [Backend](./BACKEND.md) - Learn about the API and services
- [Frontend](./FRONTEND.md) - Explore the UI components
- [Testing](./TESTING.md) - Run and write tests
- [Gmail Setup](./GMAIL_SETUP.md) - Configure email sync

## Support

For issues and questions:

- Check existing documentation in `/docs`
- Review [GitHub Issues](https://github.com/leok974/ApplyLens/issues)
- Read [CONTRIBUTING.md](./CONTRIBUTING.md) for development guidelines
