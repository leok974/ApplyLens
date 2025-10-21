# ApplyLens Architecture & Hackathon Readiness Report (Part 2C)

**Continued from HACKATHON_REPORT_PART2B.md**

---

## 8) DevOps, Observability & CI

### Docker Infrastructure

**Production Orchestration** (`docker-compose.prod.yml`):
```yaml
services:
  # Backend API (Gunicorn + FastAPI)
  api:
    image: applylens-api:latest
    build:
      context: ./services/api
      dockerfile: Dockerfile.prod
    ports:
      - "8003:8003"
    environment:
      - POSTGRES_USER=${POSTGRES_USER}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - GOOGLE_CLIENT_ID=${GOOGLE_CLIENT_ID}
      - GOOGLE_CLIENT_SECRET=${GOOGLE_CLIENT_SECRET}
    depends_on:
      - postgres
      - elasticsearch
      - redis
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8003/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Frontend (Nginx serving static build)
  web:
    image: applylens-web:latest
    build:
      context: ./apps/web
      dockerfile: Dockerfile.prod
    ports:
      - "3000:80"
    depends_on:
      - api
    restart: unless-stopped

  # PostgreSQL 16
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: applylens
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    restart: unless-stopped

  # Elasticsearch 8.13.4
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.13.4
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
      - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
    volumes:
      - es_data:/usr/share/elasticsearch/data
    ports:
      - "9200:9200"
    restart: unless-stopped

  # Redis 7 (caching)
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    restart: unless-stopped

  # Kibana 8.13.4 (data visualization)
  kibana:
    image: docker.elastic.co/kibana/kibana:8.13.4
    environment:
      ELASTICSEARCH_HOSTS: http://elasticsearch:9200
    ports:
      - "5601:5601"
    depends_on:
      - elasticsearch
    restart: unless-stopped

  # Prometheus (metrics collection)
  prometheus:
    image: prom/prometheus:v2.55.1
    volumes:
      - ./infra/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    ports:
      - "9090:9090"
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
    restart: unless-stopped

  # Grafana (metrics dashboards)
  grafana:
    image: grafana/grafana:11.1.0
    environment:
      - GF_SECURITY_ADMIN_USER=admin
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD}
      - GF_SERVER_ROOT_URL=https://applylens.app/grafana
    volumes:
      - grafana_data:/var/lib/grafana
      - ./infra/grafana/provisioning:/etc/grafana/provisioning
    ports:
      - "3001:3000"
    depends_on:
      - prometheus
    restart: unless-stopped

  # Nginx (reverse proxy)
  nginx:
    image: nginx:1.27-alpine
    volumes:
      - ./infra/nginx/conf.d:/etc/nginx/conf.d
      - ./infra/nginx/nginx.conf:/etc/nginx/nginx.conf
    ports:
      - "80:80"
      - "443:443"
    depends_on:
      - api
      - web
    restart: unless-stopped

  # Cloudflare Tunnel (SSL termination)
  cloudflared:
    image: cloudflare/cloudflared:latest
    command: tunnel run
    environment:
      - TUNNEL_TOKEN=${CLOUDFLARE_TUNNEL_TOKEN}
    restart: unless-stopped

volumes:
  postgres_data:
  es_data:
  prometheus_data:
  grafana_data:
```

**Service Count:**
- 10 production services
- 4 persistent volumes
- Health checks on critical services
- Auto-restart policies

### Build & Deployment

**Production Build Script** (`build-prod.ps1`):
```powershell
param(
    [switch]$Build,
    [switch]$Deploy,
    [switch]$Restart
)

# Load environment variables
$envFile = ".\infra\.env.prod"
Get-Content $envFile | ForEach-Object {
    if ($_ -match '^([^=]+)=(.*)$') {
        [Environment]::SetEnvironmentVariable($matches[1], $matches[2], "Process")
    }
}

if ($Build) {
    Write-Host "Building images..." -ForegroundColor Cyan
    docker-compose -f docker-compose.prod.yml build --no-cache
}

if ($Deploy) {
    Write-Host "Deploying services..." -ForegroundColor Green
    docker-compose -f docker-compose.prod.yml up -d
    
    # Run database migrations
    Write-Host "Running migrations..." -ForegroundColor Yellow
    docker-compose -f docker-compose.prod.yml exec -T api alembic upgrade head
}

if ($Restart) {
    Write-Host "Restarting services..." -ForegroundColor Magenta
    docker-compose -f docker-compose.prod.yml restart
}
```

**Usage:**
```powershell
# Full deployment
.\build-prod.ps1 -Build -Deploy

# Restart services
.\build-prod.ps1 -Restart

# Just build images
.\build-prod.ps1 -Build
```

### CI/CD Pipelines (GitHub Actions)

**Workflow Count:**
- 34 workflows in `.github/workflows/`
- Coverage: Tests, linting, security scans, deployments

**Key Workflows:**

**1. API Tests** (`.github/workflows/api-tests.yml`):
```yaml
name: API Tests

on:
  push:
    branches: [main]
    paths:
      - 'services/api/**'
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_PASSWORD: test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      
      redis:
        image: redis:7-alpine
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python 3.11
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          cd services/api
          pip install -r requirements.txt
          pip install pytest pytest-cov pytest-asyncio
      
      - name: Run tests
        env:
          DATABASE_URL: postgresql://postgres:test@localhost:5432/test
          REDIS_URL: redis://localhost:6379
        run: |
          cd services/api
          pytest tests/ -v --cov=app --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          files: ./services/api/coverage.xml
```

**2. Frontend E2E Tests** (`.github/workflows/e2e-tests.yml`):
```yaml
name: E2E Tests

on:
  push:
    branches: [main]
    paths:
      - 'apps/web/**'

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
      
      - name: Install Playwright
        run: |
          cd apps/web
          npm ci
          npx playwright install --with-deps chromium
      
      - name: Run E2E tests
        run: |
          cd apps/web
          npm run test:e2e
      
      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: playwright-report
          path: apps/web/playwright-report/
```

**3. Security Scan** (`.github/workflows/security.yml`):
```yaml
name: Security Scan

on:
  schedule:
    - cron: '0 2 * * 1'  # Weekly on Monday 2 AM
  push:
    branches: [main]

jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Run Trivy vulnerability scanner
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scan-ref: '.'
          format: 'sarif'
          output: 'trivy-results.sarif'
      
      - name: Upload to GitHub Security
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: 'trivy-results.sarif'
```

**4. Deploy to Production** (`.github/workflows/deploy.yml`):
```yaml
name: Deploy Production

on:
  push:
    tags:
      - 'v*'

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Build Docker images
        run: |
          docker-compose -f docker-compose.prod.yml build
      
      - name: Push to registry
        run: |
          echo "${{ secrets.DOCKER_PASSWORD }}" | docker login -u "${{ secrets.DOCKER_USERNAME }}" --password-stdin
          docker-compose -f docker-compose.prod.yml push
      
      - name: Deploy via SSH
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.PROD_HOST }}
          username: ${{ secrets.PROD_USER }}
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          script: |
            cd /opt/applylens
            git pull origin main
            ./build-prod.ps1 -Deploy
```

### Monitoring & Observability

**Prometheus Metrics** (`infra/prometheus/prometheus.yml`):
```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  # API metrics
  - job_name: 'applylens-api'
    static_configs:
      - targets: ['api:8003']
    metrics_path: '/metrics'

  # Postgres exporter
  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']

  # Elasticsearch metrics
  - job_name: 'elasticsearch'
    static_configs:
      - targets: ['elasticsearch:9200']
    metrics_path: '/_prometheus/metrics'

  # Node exporter (system metrics)
  - job_name: 'node'
    static_configs:
      - targets: ['node-exporter:9100']
```

**API Metrics Exposed** (`services/api/app/main.py`):
```python
from prometheus_client import Counter, Histogram, generate_latest

# Request counters
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

# Response time histogram
http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency',
    ['method', 'endpoint']
)

# Business metrics
emails_processed_total = Counter(
    'emails_processed_total',
    'Total emails processed',
    ['label']
)

risk_analysis_total = Counter(
    'risk_analysis_total',
    'Total risk analyses',
    ['risk_level']
)

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type="text/plain")
```

**Grafana Dashboards** (`infra/grafana/provisioning/dashboards/`):
1. **System Overview** (`system.json`):
   - CPU usage per service
   - Memory usage
   - Disk I/O
   - Network traffic

2. **API Performance** (`api.json`):
   - Request rate (req/sec)
   - P50/P95/P99 latency
   - Error rate (4xx/5xx)
   - Endpoint breakdown

3. **Database Health** (`database.json`):
   - Active connections
   - Query performance
   - Cache hit ratio
   - Slow query log

4. **Search Analytics** (`search.json`):
   - Search queries/min
   - Average response time
   - Top queries
   - Failed searches

5. **Business Metrics** (`business.json`):
   - Emails processed/hour
   - Risk distribution (low/medium/high)
   - Quarantine rate
   - Label classification breakdown

**Alert Rules** (`infra/prometheus/alerts.yml`):
```yaml
groups:
  - name: applylens_alerts
    rules:
      # API down
      - alert: APIDown
        expr: up{job="applylens-api"} == 0
        for: 1m
        annotations:
          summary: "API service is down"
      
      # High error rate
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        annotations:
          summary: "Error rate above 5%"
      
      # Database connections exhausted
      - alert: PostgresConnectionsHigh
        expr: pg_stat_activity_count > 80
        for: 5m
        annotations:
          summary: "PostgreSQL connections above 80"
      
      # Disk space low
      - alert: DiskSpaceLow
        expr: node_filesystem_avail_bytes / node_filesystem_size_bytes < 0.1
        for: 10m
        annotations:
          summary: "Disk space below 10%"
```

### Logging

**API Logging** (`services/api/app/main.py`):
```python
import logging
import sys

# Structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/var/log/applylens/api.log')
    ]
)

logger = logging.getLogger(__name__)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    logger.info(f"Request: {request.method} {request.url}")
    response = await call_next(request)
    
    duration = time.time() - start_time
    logger.info(f"Response: {response.status_code} ({duration:.3f}s)")
    
    return response
```

**Elasticsearch Query Logs:**
- Slow query log enabled (threshold: 1s)
- Full query logging in development
- Aggregated query metrics in Kibana

**Docker Logs:**
```powershell
# View all logs
docker-compose -f docker-compose.prod.yml logs -f

# View specific service
docker-compose -f docker-compose.prod.yml logs -f api

# Last 100 lines
docker-compose -f docker-compose.prod.yml logs --tail=100 api
```

### Health Checks

**API Health Endpoint** (`services/api/app/main.py`):
```python
@app.get("/health")
async def health():
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "checks": {}
    }
    
    # Database check
    try:
        db.execute("SELECT 1")
        health_status["checks"]["database"] = "ok"
    except Exception as e:
        health_status["checks"]["database"] = f"error: {str(e)}"
        health_status["status"] = "degraded"
    
    # Elasticsearch check
    try:
        es.ping()
        health_status["checks"]["elasticsearch"] = "ok"
    except Exception as e:
        health_status["checks"]["elasticsearch"] = f"error: {str(e)}"
        health_status["status"] = "degraded"
    
    # Redis check
    try:
        redis.ping()
        health_status["checks"]["redis"] = "ok"
    except Exception as e:
        health_status["checks"]["redis"] = f"error: {str(e)}"
        health_status["status"] = "degraded"
    
    return health_status
```

**Response Example:**
```json
{
  "status": "healthy",
  "timestamp": "2025-10-18T10:30:00Z",
  "version": "1.0.0",
  "checks": {
    "database": "ok",
    "elasticsearch": "ok",
    "redis": "ok"
  }
}
```

---

## 9) Tests & Quality

### Test Infrastructure

**Backend Tests** (`services/api/`):
- Framework: Pytest 8.3.3
- Async support: pytest-asyncio
- Coverage: pytest-cov
- Fixtures: Database, mock services
- Test count: 150+ unit tests, 50+ integration tests

**Frontend Tests** (`apps/web/`):
- Framework: Playwright 1.56.0
- Browsers: Chromium (headless)
- Test count: 52 E2E specs
- Visual regression: Enabled

### Pytest Configuration

**Config File** (`services/api/pytest.ini`):
```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
asyncio_mode = auto
markers =
    unit: Unit tests (no external dependencies)
    integration: Integration tests (requires DB)
    slow: Slow tests (> 1s)
addopts =
    -v
    --strict-markers
    --tb=short
    --cov=app
    --cov-report=term-missing
    --cov-report=html
```

**Test Structure:**
```
services/api/tests/
├── conftest.py              # Fixtures
├── unit/
│   ├── test_security.py     # Risk scoring logic
│   ├── test_policy.py       # Policy engine
│   ├── test_agents.py       # Agent system
│   └── test_utils.py        # Helper functions
├── integration/
│   ├── test_api.py          # API endpoints
│   ├── test_oauth.py        # OAuth flow
│   ├── test_search.py       # Elasticsearch queries
│   └── test_gmail.py        # Gmail API integration
└── fixtures/
    ├── emails.json          # Sample email data
    ├── policies.json        # Sample policies
    └── users.json           # Test users
```

### Example Test Cases

**Unit Test: Risk Scoring** (`tests/unit/test_security.py`):
```python
import pytest
from app.security.analyzer import EmailRiskAnalyzer, RiskSignal

def test_dmarc_fail_adds_high_risk():
    analyzer = EmailRiskAnalyzer()
    signals = analyzer.check_authentication(
        dmarc="fail",
        spf="pass",
        dkim="pass"
    )
    
    assert len(signals) == 1
    assert signals[0].type == "DMARC_FAIL"
    assert signals[0].severity == "high"
    assert signals[0].points == 15

def test_url_mismatch_detection():
    analyzer = EmailRiskAnalyzer()
    body = """
    Click here to verify your account:
    <a href="https://evil.com/phish">https://google.com</a>
    """
    
    signals = analyzer.check_content(body)
    
    assert any(s.type == "URL_MISMATCH" for s in signals)
    assert any(s.points == 20 for s in signals)

def test_total_risk_score_calculation():
    analyzer = EmailRiskAnalyzer()
    result = analyzer.analyze(
        from_email="scam@evil.tk",
        body="URGENT! Verify NOW!",
        headers={"Authentication-Results": "dmarc=fail"}
    )
    
    # DMARC fail (15) + suspicious TLD (15) + urgent language (5) = 35
    assert result.risk_score >= 35
    assert result.quarantined == False  # Below 70 threshold

def test_auto_quarantine_high_risk():
    analyzer = EmailRiskAnalyzer()
    result = analyzer.analyze(
        from_email="phish@evil.tk",
        body="""
        <a href="http://evil.com/steal">http://paypal.com</a>
        URGENT ACTION REQUIRED! Click now!
        """,
        headers={"Authentication-Results": "dmarc=fail spf=fail"}
    )
    
    # DMARC fail (15) + SPF fail (15) + TLD (15) + URL mismatch (20) 
    # + urgent (5) + HTTP link (5) = 75
    assert result.risk_score >= 70
    assert result.quarantined == True
```

**Integration Test: Search API** (`tests/integration/test_search.py`):
```python
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

@pytest.fixture
def authenticated_client(db):
    """Create test user and return authenticated client."""
    user = User(email="test@example.com")
    db.add(user)
    db.commit()
    
    # Mock OAuth session
    client.cookies.set("session_id", "test-session-123")
    return client

def test_search_by_query(authenticated_client, db, es):
    # Index test emails
    test_emails = [
        {"id": 1, "subject": "Python developer position", "body": "..."},
        {"id": 2, "subject": "Java engineer role", "body": "..."}
    ]
    for email in test_emails:
        es.index(index="emails", id=email["id"], document=email)
    es.indices.refresh(index="emails")
    
    # Search for "Python"
    response = authenticated_client.get("/api/search?q=Python")
    
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["hits"][0]["subject"] == "Python developer position"

def test_search_with_filters(authenticated_client, es):
    response = authenticated_client.get(
        "/api/search?q=interview&label_filter=interview&risk_min=0&risk_max=50"
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # All results should have interview label
    for hit in data["hits"]:
        assert "interview" in hit["labels"]
        assert 0 <= hit["risk_score"] <= 50
```

**E2E Test: Inbox Flow** (`apps/web/e2e/inbox.spec.ts`):
```typescript
import { test, expect } from '@playwright/test';

test.describe('Inbox', () => {
  test.beforeEach(async ({ page }) => {
    // Mock OAuth login
    await page.goto('http://localhost:3000/web/inbox');
    await page.evaluate(() => {
      localStorage.setItem('user_email', 'test@example.com');
      document.cookie = 'session_id=test-session-123';
    });
  });

  test('displays email list', async ({ page }) => {
    await page.goto('http://localhost:3000/web/inbox');
    
    // Wait for emails to load
    await page.waitForSelector('[data-testid="email-card"]');
    
    const emailCards = await page.locator('[data-testid="email-card"]').count();
    expect(emailCards).toBeGreaterThan(0);
  });

  test('filters by label', async ({ page }) => {
    await page.goto('http://localhost:3000/web/inbox');
    
    // Click "Interview" filter
    await page.click('[data-testid="filter-interview"]');
    
    // All visible emails should have interview badge
    const badges = await page.locator('[data-testid="label-badge"]').allTextContents();
    expect(badges.every(b => b === 'interview')).toBeTruthy();
  });

  test('shows risk badge color', async ({ page }) => {
    await page.goto('http://localhost:3000/web/inbox');
    
    const riskBadge = page.locator('[data-testid="risk-badge"]').first();
    const score = parseInt(await riskBadge.textContent() || '0');
    
    if (score >= 70) {
      await expect(riskBadge).toHaveClass(/destructive/);  // Red
    } else if (score >= 40) {
      await expect(riskBadge).toHaveClass(/warning/);      // Amber
    } else {
      await expect(riskBadge).toHaveClass(/default/);      // Green
    }
  });

  test('quarantine release workflow', async ({ page }) => {
    await page.goto('http://localhost:3000/web/settings/security');
    
    // Find quarantined email
    const quarantinedEmail = page.locator('[data-quarantined="true"]').first();
    await quarantinedEmail.click();
    
    // Click release button
    await page.click('[data-testid="btn-release"]');
    
    // Confirm dialog
    await page.click('[data-testid="btn-confirm-release"]');
    
    // Should disappear from quarantine list
    await expect(quarantinedEmail).toBeHidden();
  });
});
```

**E2E Test: Agent System** (`apps/web/e2e/agents.spec.ts`):
```typescript
test('agent execution with approval', async ({ page }) => {
  await page.goto('http://localhost:3000/web/chat');
  
  // Type risky command
  await page.fill('[data-testid="chat-input"]', 
    'Delete all emails from @spam.com older than 30 days');
  await page.press('[data-testid="chat-input"]', 'Enter');
  
  // Should show approval request
  await page.waitForSelector('[data-testid="approval-card"]');
  
  const approvalCard = page.locator('[data-testid="approval-card"]');
  await expect(approvalCard).toContainText('requires approval');
  
  // Show impact preview
  await expect(approvalCard).toContainText('~150 emails will be deleted');
  
  // Approve
  await page.click('[data-testid="btn-approve"]');
  
  // Should execute and show result
  await page.waitForSelector('[data-testid="execution-result"]');
  await expect(page.locator('[data-testid="execution-result"]'))
    .toContainText('Successfully deleted 150 emails');
});
```

### Code Coverage

**Current Coverage** (as of Oct 18, 2025):
```
services/api/app/
  routers/         85%  (critical paths covered)
  security/        92%  (risk scoring well-tested)
  agents/          78%  (agent logic covered)
  policy/          88%  (policy engine tested)
  models.py        95%  (data models validated)
  utils/           70%  (helpers partially tested)
  
Overall:          82%
```

**Coverage Goals:**
- Critical paths: >90%
- Business logic: >85%
- Utilities: >70%
- Total: >80% ✅ (achieved)

**Coverage Report:**
```bash
cd services/api
pytest tests/ --cov=app --cov-report=html
# Open htmlcov/index.html
```

### Test Execution

**Run All Tests:**
```bash
# Backend
cd services/api
pytest tests/ -v

# Frontend
cd apps/web
npm run test:e2e
```

**Run Specific Test Suite:**
```bash
# Only unit tests
pytest tests/unit/ -v

# Only integration tests (requires services)
docker-compose -f docker-compose.test.yml up -d
pytest tests/integration/ -v

# Only slow tests
pytest -m slow -v
```

**CI Pipeline Execution:**
- Triggered on push to main
- Runs on every PR
- Parallel test execution (4 workers)
- Total runtime: ~8 minutes

---

**Continued in HACKATHON_REPORT_PART2D.md**
