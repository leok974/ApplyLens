# ApplyLens API - Makefile
# Provides convenient targets for common operations

.PHONY: help test backfill-bills check-bills-missing check-bills-with-dates

# Configuration with defaults
ES_URL ?= http://localhost:9200
ES_EMAIL_INDEX ?= gmail_emails_v2
BATCH ?= 500
DRY_RUN ?= 1
PYTHON ?= python

help:
	@echo "ApplyLens API - Available Targets"
	@echo "=================================="
	@echo ""
	@echo "Testing:"
	@echo "  make test                    - Run all tests"
	@echo "  make test-unit              - Run unit tests only"
	@echo "  make test-e2e               - Run E2E tests only"
	@echo ""
	@echo "Backfill Operations:"
	@echo "  make backfill-bills         - Backfill bill due dates (DRY_RUN=1 by default)"
	@echo "  make backfill-bills-live    - Execute backfill (DRY_RUN=0)"
	@echo "  make check-bills-missing    - Count bills missing dates"
	@echo "  make check-bills-with-dates - Count bills with dates populated"
	@echo ""
	@echo "Configuration:"
	@echo "  ES_URL=$(ES_URL)"
	@echo "  ES_EMAIL_INDEX=$(ES_EMAIL_INDEX)"
	@echo "  BATCH=$(BATCH)"
	@echo "  DRY_RUN=$(DRY_RUN)"
	@echo ""
	@echo "Examples:"
	@echo "  make backfill-bills                          # Dry run"
	@echo "  make backfill-bills DRY_RUN=0               # Execute updates"
	@echo "  make backfill-bills BATCH=200               # Smaller batches"
	@echo "  make backfill-bills ES_EMAIL_INDEX=emails   # Different index"

test:
	@echo "Running all tests..."
	pytest tests/ -v

test-unit:
	@echo "Running unit tests..."
	pytest tests/unit/ -v

test-e2e:
	@echo "Running E2E tests..."
	pytest tests/e2e/ -v

backfill-bills:
	@echo "==========================================="
	@echo "Backfilling bills"
	@echo "==========================================="
	@echo "Mode: $(if $(filter 0,$(DRY_RUN)),LIVE UPDATE,DRY RUN)"
	@echo "ES URL: $(ES_URL)"
	@echo "Index: $(ES_EMAIL_INDEX)"
	@echo "Batch: $(BATCH)"
	@echo "==========================================="
	@ES_URL=$(ES_URL) ES_EMAIL_INDEX=$(ES_EMAIL_INDEX) DRY_RUN=$(DRY_RUN) BATCH=$(BATCH) \
		$(PYTHON) scripts/backfill_bill_dates.py

backfill-bills-live:
	@echo "⚠️  WARNING: This will UPDATE Elasticsearch documents!"
	@echo "Press Ctrl+C to cancel, or wait 5 seconds to continue..."
	@sleep 5
	@$(MAKE) backfill-bills DRY_RUN=0

check-bills-missing:
	@echo "Checking bills missing dates..."
	@curl -s -X POST "$(ES_URL)/$(ES_EMAIL_INDEX)/_search" \
		-H 'Content-Type: application/json' \
		-d '{"query":{"bool":{"must":[{"term":{"category":"bills"}},{"bool":{"must_not":{"exists":{"field":"dates"}}}}]}},"size":0,"track_total_hits":true}' \
		| python -c "import sys, json; data=json.load(sys.stdin); print(f\"Bills missing dates: {data['hits']['total']['value']}\")"

check-bills-with-dates:
	@echo "Checking bills with dates..."
	@curl -s -X POST "$(ES_URL)/$(ES_EMAIL_INDEX)/_search" \
		-H 'Content-Type: application/json' \
		-d '{"query":{"bool":{"must":[{"term":{"category":"bills"}},{"exists":{"field":"dates"}}]}},"size":0,"aggs":{"with_expiry":{"filter":{"exists":{"field":"expires_at"}}}}}' \
		| python -c "import sys, json; data=json.load(sys.stdin); total=data['hits']['total']['value']; expiry=data['aggregations']['with_expiry']['doc_count']; print(f\"Bills with dates: {total}\"); print(f\"Bills with expires_at: {expiry}\")"
