#!/bin/bash
# Smoke test for Ollama integration in production
# Tests the LLM provider directly inside the API container
#
# PRODUCTION VALIDATION:
# - Confirms API can reach infra-ollama-1:11434
# - Verifies llm_complete() returns ("text", "ollama") in prod
# - Warns if falling back to OpenAI or template
#
# SUCCESS CRITERIA:
# - Exit code 0 (even if using fallback)
# - backend="ollama" in production (expected)
# - backend="openai" or "template" = warning but not failure

set -e

echo "=========================================="
echo "Ollama Integration Smoke Test"
echo "=========================================="
echo ""

# Check if API container is running
API_CONTAINER=$(docker ps --filter "name=applylens-api-prod" --format "{{.Names}}")
if [ -z "$API_CONTAINER" ]; then
    echo "❌ API container not running"
    exit 1
fi

echo "✓ API container running: $API_CONTAINER"
echo ""

# Test LLM provider via Python (using llm_complete function)
echo "Testing LLM provider..."
docker exec "$API_CONTAINER" python - << 'PYTHON'
import asyncio
import sys
import json
sys.path.insert(0, '/app')

from app.llm_provider import llm_complete

async def test():
    prompt = "Summarize mailbox status in one friendly sentence."

    text, backend = await llm_complete(prompt)

    # Output as JSON for parsing
    result = {
        "backend": backend,
        "text": text[:200] if text else ""
    }
    print(json.dumps(result))

    # Validate backend name
    if backend not in ["ollama", "openai", "template"]:
        print(f"ERROR: Invalid backend name: {backend}", file=sys.stderr)
        sys.exit(1)

    # Validate response
    if not text or len(text) < 10:
        print("ERROR: Response too short or empty", file=sys.stderr)
        sys.exit(1)

    # Warn if not using Ollama (expected in production)
    if backend != "ollama":
        print(f"⚠ WARNING: Using {backend} instead of ollama", file=sys.stderr)

asyncio.run(test())
PYTHON

echo ""
echo "=========================================="
echo "✅ Smoke test PASSED"
echo "=========================================="
