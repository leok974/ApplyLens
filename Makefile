# ========= ApplyLens Phase-2 labeling shortcuts =========

# ---- Tunables (override on CLI or via env) ----
ES_URL        ?= http://localhost:9200
ES_INDEX      ?= emails_v1-000001
EXPORT_DAYS   ?= 60
EXPORT_LIMIT  ?= 40000
EXPORT_LPC    ?= 8000
WEAK_JSONL    ?= /tmp/weak_labels.jsonl
MODEL_OUT     ?= services/api/app/labeling/label_model.joblib
API_BASE      ?= http://localhost:8003

PYTHON        ?= python

# ---- Paths ----
EXPORT_SCRIPT := services/api/app/labeling/export_weak_labels.py
TRAIN_SCRIPT  := services/api/app/labeling/train_ml.py

# ---- Meta ----
.PHONY: help export-weak train-labels apply-labels phase2-all clean-weak stats profile test-api test-db-up test-db-down test-db-clean test-all api-dev api-test agent-test

help:
	@echo "ApplyLens Phase-2 Labeling Shortcuts"
	@echo "====================================="
	@echo ""
	@echo "Main Targets:"
	@echo "  make export-weak     Export weak labels JSONL from ES"
	@echo "  make train-labels    Train TF-IDF+LR model from JSONL"
	@echo "  make apply-labels    Apply labels to ES (rules + ML fallback)"
	@echo "  make phase2-all      Run full pipeline: export -> train -> apply"
	@echo ""
	@echo "Agents (Phase 1 Agentic System):"
	@echo "  make api-dev         Run API server with hot reload (port 8003)"
	@echo "  make api-test        Run all API tests including agent tests"
	@echo "  make agent-test      Run only agent tests (core + warehouse)"
	@echo ""
	@echo "Testing:"
	@echo "  make test-api        Run API tests (requires test DB)"
	@echo "  make test-db-up      Start test database"
	@echo "  make test-db-down    Stop test database"
	@echo "  make test-db-clean   Stop and remove test database"
	@echo "  make test-all        Start DB, run tests, stop DB"
	@echo ""
	@echo "Analytics:"
	@echo "  make stats           Show label statistics"
	@echo "  make profile         Show profile summary (60 days)"
	@echo ""
	@echo "Utilities:"
	@echo "  make clean-weak      Remove exported JSONL file"
	@echo ""
	@echo "Configuration (override on CLI):"
	@echo "  ES_URL=$(ES_URL)"
	@echo "  ES_INDEX=$(ES_INDEX)"
	@echo "  EXPORT_DAYS=$(EXPORT_DAYS)"
	@echo "  EXPORT_LIMIT=$(EXPORT_LIMIT)"
	@echo "  EXPORT_LPC=$(EXPORT_LPC)"
	@echo "  WEAK_JSONL=$(WEAK_JSONL)"
	@echo "  MODEL_OUT=$(MODEL_OUT)"
	@echo "  API_BASE=$(API_BASE)"
	@echo ""
	@echo "Examples:"
	@echo "  make phase2-all"
	@echo "  make export-weak EXPORT_DAYS=30 WEAK_JSONL=/tmp/weak30.jsonl"
	@echo "  make apply-labels API_BASE=https://api.applylens.app"

export-weak:
	@echo ">> Exporting weak labels to $(WEAK_JSONL)"
	@echo "   Days: $(EXPORT_DAYS), Limit: $(EXPORT_LIMIT), Per-Cat: $(EXPORT_LPC)"
	@ES_URL=$(ES_URL) ES_EMAIL_INDEX=$(ES_INDEX) \
	$(PYTHON) $(EXPORT_SCRIPT) \
	  --days $(EXPORT_DAYS) \
	  --limit $(EXPORT_LIMIT) \
	  --limit-per-cat $(EXPORT_LPC) \
	  --out $(WEAK_JSONL)

train-labels:
	@echo ">> Training label model -> $(MODEL_OUT)"
	@$(PYTHON) $(TRAIN_SCRIPT) $(WEAK_JSONL) $(MODEL_OUT)

apply-labels:
	@echo ">> Applying labels to ES via $(API_BASE)/labels/apply"
	@curl -s -X POST "$(API_BASE)/labels/apply" \
	  -H "Content-Type: application/json" \
	  -d '{}' | jq . || curl -s -X POST "$(API_BASE)/labels/apply" \
	  -H "Content-Type: application/json" \
	  -d '{}'

stats:
	@echo ">> Label Statistics"
	@curl -s "$(API_BASE)/labels/stats" | jq . || curl -s "$(API_BASE)/labels/stats"

profile:
	@echo ">> Profile Summary (60 days)"
	@curl -s "$(API_BASE)/profile/summary?days=60" | jq . || curl -s "$(API_BASE)/profile/summary?days=60"

phase2-all: export-weak train-labels apply-labels
	@echo ""
	@echo "✅ Phase-2 pipeline finished!"
	@echo ""
	@echo "View results:"
	@echo "  make stats"
	@echo "  make profile"

clean-weak:
	@echo ">> Removing $(WEAK_JSONL)"
	@rm -f $(WEAK_JSONL) || true

# ========= Testing =========

TEST_DB_PASSWORD ?= test_password_change_me

test-db-up:
	@echo ">> Starting test database on port 5433"
	@TEST_DB_PASSWORD=$(TEST_DB_PASSWORD) docker compose -f infra/docker-compose.test.yml up -d
	@echo ">> Waiting for database to be ready..."
	@for i in $$(seq 1 30); do \
		docker exec applylens-test-db pg_isready -U postgres -d applylens && break; \
		echo "   Attempt $$i/30: Waiting..."; \
		sleep 1; \
	done
	@echo ">> Database ready!"

test-db-down:
	@echo ">> Stopping test database"
	@docker compose -f infra/docker-compose.test.yml down

test-db-clean:
	@echo ">> Stopping and removing test database"
	@docker compose -f infra/docker-compose.test.yml down -v

test-api: test-db-up
	@echo ">> Running API tests"
	@cd services/api && \
		TEST_DB_PASSWORD=$(TEST_DB_PASSWORD) alembic upgrade head && \
		TEST_DB_PASSWORD=$(TEST_DB_PASSWORD) pytest -v
	@echo ">> Tests complete!"

test-all: test-db-up
	@echo ">> Running full test suite"
	@cd services/api && \
		TEST_DB_PASSWORD=$(TEST_DB_PASSWORD) alembic upgrade head && \
		TEST_DB_PASSWORD=$(TEST_DB_PASSWORD) pytest -v
	@$(MAKE) test-db-down
	@echo "✅ All tests passed!"

# ========= Agents Development =========

api-dev:
	@echo ">> Starting API server with hot reload on port 8003"
	@cd services/api && uvicorn app.main:app --reload --port 8003

api-test: test-db-up
	@echo ">> Running API tests (including agent tests)"
	@cd services/api && \
		TEST_DB_PASSWORD=$(TEST_DB_PASSWORD) alembic upgrade head && \
		TEST_DB_PASSWORD=$(TEST_DB_PASSWORD) pytest -v tests/
	@echo ">> Tests complete!"

agent-test:
	@echo ">> Running agent tests (core + warehouse)"
	@cd services/api && \
		ES_ENABLED=false USE_MOCK_GMAIL=true pytest -v tests/test_agents_core.py tests/test_agent_warehouse.py
	@echo "✅ Agent tests passed!"
