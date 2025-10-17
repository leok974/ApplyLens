# Phase 2 - Real Providers & DI Factory

## ✅ PR 1 Complete: Real Provider Implementations

Successfully implemented the provider adapter layer with dependency injection for seamless switching between mock and real providers.

---

## 📦 What Was Built

### **Configuration** (`services/api/app/config.py`)

New `AgentSettings` class with environment-based configuration:

```python
PROVIDERS: "mock" | "real"  # Controls provider mode
GMAIL_OAUTH_SECRETS_PATH   # Gmail OAuth configuration
BQ_PROJECT                 # BigQuery project ID
ES_HOST                    # Elasticsearch endpoint
DBT_CMD                    # dbt command path
```

All settings use `APPLYLENS_` prefix (e.g., `APPLYLENS_PROVIDERS=real`).

### **Provider Factory** (`services/api/app/providers/factory.py`)

Dependency injection factory that returns appropriate provider based on configuration:

- **Mock mode** (default): Returns test providers for CI/development
- **Real mode**: Returns production providers with external integrations

```python
provider_factory.gmail()     # GmailProvider or _MockGmailProvider
provider_factory.bigquery()  # BigQueryProvider or _MockBQProvider
provider_factory.dbt()       # DbtProvider or _MockDbtProvider
provider_factory.es()        # ESProvider or _MockESProvider
```

### **Real Provider Implementations**

#### **Gmail** (`providers/gmail_real.py`)
- Integrates with Gmail API v1
- Uses OAuth2 authentication
- Requires `google-api-python-client`
- Lazy-loads service on first use

#### **BigQuery** (`providers/bigquery_real.py`)
- Uses `google-cloud-bigquery` client
- Supports service account or ADC
- Helper methods: `query_rows()`, `query_scalar()`
- Captures execution statistics

#### **dbt** (`providers/dbt_real.py`)
- Executes dbt via subprocess
- Parses `run_results.json` artifacts
- 5-minute timeout protection
- Supports model selectors

#### **Elasticsearch** (`providers/elasticsearch_real.py`)
- Uses `elasticsearch-py` client
- Connection ping verification
- Additional methods:
  - `aggregate_daily()` - Date histogram aggregation
  - `latest_event_ts()` - Get most recent document timestamp

### **Updated Tools** (Phase 1 → Phase 2)

All tool classes now use the provider factory:

**Before (Phase 1):**
```python
class GmailTool:
    def search_recent(self, days=7):
        # Inline mock data
        return GmailSearchResponse(messages=[...])
```

**After (Phase 2):**
```python
class _MockGmailProvider:
    def search_recent(self, days=7):
        return GmailSearchResponse(messages=[...])

class GmailTool:
    def search_recent(self, days=7):
        provider = provider_factory.gmail()
        return provider.search_recent(days)
```

---

## 🎯 Design Principles

### 1. **Safe by Default**
- Default mode is `mock` for development/CI
- Real providers only enabled with explicit configuration
- No external dependencies in tests

### 2. **Lazy Loading**
- Real providers initialize connections on first use
- Graceful fallback with clear error messages
- Prevents startup failures

### 3. **Protocol-Based**
- Provider factory uses Protocol types
- Mock and real providers implement same interface
- Type-safe across modes

### 4. **Environment-Driven**
- All configuration via environment variables
- No code changes needed to switch modes
- CI/staging/prod use same codebase

---

## 🚀 Usage Examples

### **Development (Mock Mode)**
```bash
# Default - uses mocks
python -m pytest tests/test_agents_core.py
```

### **Integration Testing (Real Mode)**
```bash
# Enable real providers
export APPLYLENS_PROVIDERS=real
export APPLYLENS_ES_HOST=http://localhost:9200
export APPLYLENS_BQ_PROJECT=my-project

python -m pytest tests/integration/
```

### **Production**
```bash
# Environment variables
APPLYLENS_PROVIDERS=real
APPLYLENS_GMAIL_OAUTH_SECRETS_PATH=/secrets/gmail_oauth.json
APPLYLENS_BQ_CREDENTIALS_PATH=/secrets/bq_service_account.json
APPLYLENS_ES_HOST=https://es.applylens.app:9200
APPLYLENS_DBT_PROJECT_DIR=/app/analytics/dbt
```

---

## 📊 Implementation Stats

| Component | Lines | Status |
|-----------|-------|--------|
| config.py | 65 | ✅ |
| factory.py | 130 | ✅ |
| gmail_real.py | 110 | ✅ |
| bigquery_real.py | 125 | ✅ |
| dbt_real.py | 110 | ✅ |
| elasticsearch_real.py | 165 | ✅ |
| Tools updates | 4 files | ✅ |

**Total**: ~800 lines of production-ready code

---

## ✅ Testing Strategy

### **Unit Tests** (Mock Mode)
- All existing Phase 1 tests continue to pass
- No external service dependencies
- Deterministic, fast execution

### **Integration Tests** (Real Mode - Future)
- Separate test suite under `tests/integration/`
- Requires external services (ES, optional BQ)
- Gated by CI secrets/manual trigger

---

## 🔄 Next Steps (Remaining Phase 2 PRs)

### **PR 2**: Agent Audit Logging
- [ ] `AgentAuditLog` model + Alembic migration
- [ ] Executor hooks for start/finish logging
- [ ] Prometheus metrics (counters, histograms)

### **PR 3**: Server-Sent Events
- [ ] Event bus implementation
- [ ] `/agents/events` SSE endpoint
- [ ] Real-time run updates

### **PR 4**: Warehouse Health Agent v2
- [ ] Real parity computation logic
- [ ] Freshness SLO checks (30min threshold)
- [ ] Auto-remediation with `allow_actions`

### **PR 5**: CI Integration Lane
- [ ] Split mock vs integration jobs
- [ ] Add Elasticsearch service to CI
- [ ] Secrets gating for real provider tests

### **PR 6**: Documentation
- [ ] AGENTS_QUICKSTART.md
- [ ] AGENTS_OBSERVABILITY.md
- [ ] RUNBOOK_WAREHOUSE_HEALTH.md

---

## 📝 Migration Notes

### **For Existing Code**
- ✅ **No breaking changes** - all Phase 1 code continues to work
- ✅ Tools automatically use mocks by default
- ✅ Tests pass without modification

### **To Enable Real Providers**
1. Install optional dependencies:
   ```bash
   pip install google-api-python-client google-cloud-bigquery elasticsearch dbt-core
   ```

2. Set environment variable:
   ```bash
   export APPLYLENS_PROVIDERS=real
   ```

3. Configure service-specific settings (OAuth paths, project IDs, etc.)

---

**Status**: ✅ PR 1 Complete - Ready for Review  
**Next**: Agent Audit Logging (PR 2)
