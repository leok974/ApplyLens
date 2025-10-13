# Running the Search Scoring Tests

## Prerequisites

The `test_search_scoring.py` test requires:

1. Elasticsearch/OpenSearch running (for integration test)
2. Python `elasticsearch` package installed
3. FastAPI test client (from `conftest.py`)

## Option 1: Run in Docker (Recommended)

```bash
# Start services
cd infra
docker compose up -d

# Run test inside API container
docker compose exec api pytest tests/test_search_scoring.py -v
```

## Option 2: Local with Virtual Environment

```bash
cd services/api

# Install dependencies
pip install elasticsearch pytest httpx

# Start Elasticsearch
docker run -d -p 9200:9200 -e "discovery.type=single-node" elasticsearch:8.11.0

# Set environment
export ES_URL=http://localhost:9200
export ES_ENABLED=true

# Run test
pytest tests/test_search_scoring.py -v
```

## Option 3: Unit Test Only (No ES Required)

The current test is an integration test that needs ES. For unit testing without ES, you would need to:

- Mock the Elasticsearch client
- Test the search endpoint structure
- Verify query building logic

## Test Purpose

The test verifies:

- ✅ Label boost ordering (rejection ≤ neutral)
- ✅ Recency decay (recent > old emails)
- ✅ Response structure and status codes

## Current Status

**Test File**: `services/api/tests/test_search_scoring.py`

- ⚠️ Requires ES to run
- ⚠️ Needs test fixtures (conftest.py)
- ⚠️ Integration test, not unit test

**To run successfully**:

1. Start Docker services with Elasticsearch
2. Run inside Docker API container
3. Or install dependencies locally and start ES

## Quick Smoke Test (Without Running Full Test)

Instead of running the test, you can verify the search endpoint manually:

```bash
# Check if API is running
curl http://localhost:8001/health

# Test search endpoint
curl "http://localhost:8001/search?q=test&size=5"

# Verify response structure
curl "http://localhost:8001/search?q=interview" | jq '.hits[0] | keys'
```

This validates:

- ✅ API is running
- ✅ Search endpoint responds
- ✅ Response has correct structure
- ✅ No import errors in search.py
