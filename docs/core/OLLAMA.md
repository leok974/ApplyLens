# Ollama Integration Guide (Production)

**Version**: v0.4.48+ollama
**Date**: October 26, 2025
**Status**: Production-ready

## Overview

This guide documents the complete Ollama integration into ApplyLens production environment, enabling local LLM inference with OpenAI fallback and guaranteed response templates.

## Architecture

### Hybrid LLM Strategy

```
User Query → API Container
              ↓
         1. Try Ollama (local, fast, free)
              ↓ (fail)
         2. Try OpenAI (cloud, slower, cost)
              ↓ (fail)
         3. Use Template (deterministic, always works)
```

### Network Topology

```
Docker Network: applylens-prod (bridge)
  ├── ollama:11434        (Ollama service)
  ├── api:8003            (FastAPI backend)
  ├── web:80              (React frontend)
  ├── db:5432             (PostgreSQL)
  └── elasticsearch:9200  (Search engine)
```

## Implementation Details

### 1. Docker Compose Configuration

**File**: `docker-compose.prod.yml`

Added Ollama service:
```yaml
ollama:
  image: ollama/ollama:latest
  container_name: applylens-ollama-prod
  restart: unless-stopped
  networks:
    - applylens-prod
  expose:
    - "11434"  # Internal only, not exposed to host
  volumes:
    - ollama_models_prod:/root/.ollama
  environment:
    - OLLAMA_KEEP_ALIVE=24h
    - OLLAMA_NUM_PARALLEL=2
    - OLLAMA_MAX_LOADED_MODELS=1
  healthcheck:
    test: ["CMD-SHELL", "curl -f http://localhost:11434/api/tags || exit 1"]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 60s
```

Updated API service:
```yaml
api:
  depends_on:
    ollama:
      condition: service_healthy
  environment:
    OLLAMA_BASE: http://ollama:11434
    OLLAMA_MODEL: ${OLLAMA_MODEL:-llama3.2:3b}
    OPENAI_API_KEY: ${OPENAI_API_KEY}
    OPENAI_MODEL: ${OPENAI_MODEL:-gpt-4o-mini}
```

### 2. LLM Provider Module

**File**: `services/api/app/llm_provider.py`

Key functions:
- `_call_ollama(prompt: str) -> Optional[str]`: Direct Ollama API call
- `_call_openai(prompt: str) -> Optional[str]`: OpenAI fallback
- `generate_assistant_text(kind, prompt, fallback_template) -> tuple[str, str]`: Hybrid with telemetry

Returns tuple: `(generated_text, llm_used)` where `llm_used` is:
- `"ollama"` - Successfully used local Ollama
- `"openai"` - Fell back to OpenAI
- `"fallback"` - Used deterministic template (both LLMs unavailable)

### 3. API Integration

**File**: `services/api/app/routers/assistant.py`

Updated response model:
```python
class AssistantQueryResponse(BaseModel):
    intent: str
    summary: str
    sources: List[AssistantEmailSource]
    suggested_actions: List[AssistantSuggestedAction]
    actions_performed: List[AssistantActionPerformed] = []
    next_steps: Optional[str] = None
    followup_prompt: Optional[str] = None
    llm_used: Optional[str] = None  # Phase 3 telemetry
```

### 4. Frontend Integration

**File**: `apps/web/src/lib/api.ts`

TypeScript types updated:
```typescript
export interface AssistantQueryResponse {
  intent: string
  summary: string
  next_steps?: string
  followup_prompt?: string
  sources: AssistantEmailSource[]
  suggested_actions: AssistantSuggestedAction[]
  actions_performed: AssistantActionPerformed[]
  llm_used?: string  // "ollama", "openai", or "fallback"
}
```

**File**: `apps/web/src/components/MailChat.tsx`

Console logging for telemetry:
```typescript
if (resp.llm_used) {
  console.debug(`[Chat] LLM provider: ${resp.llm_used}`)
}
```

### 5. Testing Infrastructure

#### Smoke Test Scripts

**PowerShell**: `scripts/smoke_llm.ps1`
**Bash**: `scripts/smoke_llm.sh`

Tests:
1. Check API container is running
2. Exec into container
3. Call `llm_provider.generate_assistant_text()` directly
4. Assert valid backend name returned
5. Warn if not using Ollama in production

Usage:
```powershell
# PowerShell
.\scripts\smoke_llm.ps1

# Bash
bash scripts/smoke_llm.sh
```

#### E2E Tests

**File**: `apps/web/tests/mailboxAssistant.spec.ts`

Added test for `llm_used` field:
```typescript
test('shows typing indicator during assistant response @prodSafe', async ({ page }) => {
  // ... setup code ...

  // Listen for API responses to capture llm_used field
  let llmUsedField: string | null = null
  page.on('response', async (response) => {
    if (response.url().includes('/assistant/query')) {
      const json = await response.json()
      if (json.llm_used) {
        llmUsedField = json.llm_used
      }
    }
  })

  // ... test code ...

  // Assert llm_used field is present and valid
  expect(llmUsedField).toBeTruthy()
  expect(['ollama', 'openai', 'fallback']).toContain(llmUsedField)
})
```

## Deployment Steps

### First-Time Setup

1. **Pull Ollama model** (one-time):
   ```bash
   docker-compose -f docker-compose.prod.yml up -d ollama
   docker exec applylens-ollama-prod ollama pull llama3.2:3b
   ```

2. **Verify model loaded**:
   ```bash
   docker exec applylens-ollama-prod ollama list
   ```

3. **Deploy full stack**:
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

4. **Run smoke test**:
   ```bash
   .\scripts\smoke_llm.ps1
   ```

### Expected Output

```
==========================================
Ollama Integration Smoke Test
==========================================

✓ API container running: applylens-api-prod

Testing LLM provider...

Output:
Backend: ollama
Response: Your mailbox shows 6 bills due soon and 5 emails needing replies.
✅ LLM provider working

==========================================
✅ Smoke test PASSED
==========================================
```

### Updating to v0.4.48+ollama

1. **Build new images**:
   ```bash
   # API
   docker build -f services/api/Dockerfile.prod \
     -t leoklemet/applylens-api:v0.4.48 \
     services/api

   # Web
   docker build -f apps/web/Dockerfile.prod \
     -t leoklemet/applylens-web:v0.4.48 \
     apps/web
   ```

2. **Push to registry**:
   ```bash
   docker push leoklemet/applylens-api:v0.4.48
   docker push leoklemet/applylens-web:v0.4.48
   ```

3. **Deploy**:
   ```bash
   docker-compose -f docker-compose.prod.yml pull
   docker-compose -f docker-compose.prod.yml up -d
   ```

4. **Verify**:
   ```bash
   # Check health
   curl http://localhost:8003/ready

   # Test LLM
   .\scripts\smoke_llm.ps1

   # Test full assistant
   .\scripts\smoke_test_assistant_phase3.ps1
   ```

## Monitoring

### LLM Usage Distribution

Monitor which provider is being used:

```bash
# Check logs for LLM telemetry
docker logs applylens-api-prod 2>&1 | grep "llm_provider"

# Expected distribution in production:
# - 90% ollama (local, fast)
# - 8% openai (fallback when Ollama busy)
# - 2% fallback (both unavailable)
```

### Performance Metrics

```bash
# Check Ollama response times
docker logs applylens-ollama-prod 2>&1 | grep "generate"

# Expected: 1-3 seconds for llama3.2:3b
```

### Container Health

```bash
# Check all services
docker ps --format "table {{.Names}}\t{{.Status}}"

# Expected:
# applylens-ollama-prod   Up 2 hours (healthy)
# applylens-api-prod      Up 2 hours (healthy)
# applylens-web-prod      Up 2 hours (healthy)
```

## Troubleshooting

### Issue: Ollama not responding

**Symptoms**: All queries use OpenAI fallback

**Check**:
```bash
docker logs applylens-ollama-prod --tail 50
docker exec applylens-ollama-prod curl http://localhost:11434/api/tags
```

**Fix**:
```bash
docker restart applylens-ollama-prod
# Wait 60s for model to load
.\scripts\smoke_llm.ps1
```

### Issue: Model not loaded

**Symptoms**: `[llm_provider] Ollama unavailable: 404`

**Check**:
```bash
docker exec applylens-ollama-prod ollama list
```

**Fix**:
```bash
docker exec applylens-ollama-prod ollama pull llama3.2:3b
```

### Issue: Network isolation

**Symptoms**: API can't reach Ollama

**Check**:
```bash
docker network inspect applylens_applylens-prod
# Verify both api and ollama are listed
```

**Fix**:
```bash
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d
```

### Issue: Memory exhaustion

**Symptoms**: Ollama crashes, logs show OOM

**Check**:
```bash
docker stats applylens-ollama-prod
```

**Fix**:
```bash
# Reduce concurrent requests in docker-compose.prod.yml:
environment:
  - OLLAMA_NUM_PARALLEL=1  # Was 2
  - OLLAMA_MAX_LOADED_MODELS=1
```

## Model Selection

### Current: llama3.2:3b
- **Size**: 2GB
- **Speed**: 1-3s per query
- **Quality**: Good for summarization, intent classification
- **Memory**: ~4GB RAM when loaded

### Alternative: llama3.1:8b
- **Size**: 4.7GB
- **Speed**: 3-6s per query
- **Quality**: Better reasoning, more detailed summaries
- **Memory**: ~8GB RAM when loaded

### Switching Models

```bash
# 1. Pull new model
docker exec applylens-ollama-prod ollama pull llama3.1:8b

# 2. Update env var
# Edit infra/.env:
OLLAMA_MODEL=llama3.1:8b

# 3. Restart API
docker-compose -f docker-compose.prod.yml restart api

# 4. Test
.\scripts\smoke_llm.ps1
```

## Cost Analysis

### Before Ollama (OpenAI only)
- **Cost**: $0.15 per 1M input tokens (gpt-4o-mini)
- **Typical**: 200 tokens per query
- **100 queries/day**: ~$0.003/day = $1.10/year

### After Ollama (90% local)
- **Local**: $0 (free)
- **OpenAI fallback (10%)**: $0.0003/day = $0.11/year
- **Savings**: 90% reduction ($0.99/year saved)

### Infrastructure Cost
- **Ollama RAM**: 4GB (minimal on modern servers)
- **Disk**: 2GB for model storage
- **Network**: Internal only (no bandwidth cost)

## Security Considerations

1. **Network Isolation**: Ollama only exposed to internal Docker network
2. **No External Access**: Port 11434 not published to host
3. **Data Privacy**: All inference happens locally (no data sent to OpenAI for 90% of queries)
4. **Fallback Safety**: OpenAI still available if Ollama compromised
5. **Template Guarantee**: System never crashes even if both LLMs fail

## Future Enhancements

### Short Term
- [ ] Add Prometheus metrics for LLM provider distribution
- [ ] Implement request queuing for high concurrency
- [ ] Add model warmup on container start

### Medium Term
- [ ] A/B test different models (3b vs 8b)
- [ ] Implement streaming responses for longer summaries
- [ ] Add caching layer for repeated queries

### Long Term
- [ ] Fine-tune model on ApplyLens-specific data
- [ ] Deploy multiple Ollama instances with load balancing
- [ ] Implement model versioning and blue-green deployments

## Support

For issues or questions:
- Check logs: `docker logs applylens-api-prod`
- Run diagnostics: `.\scripts\smoke_llm.ps1`
- Review metrics: Check Grafana dashboard at http://localhost:3000

---

**Last Updated**: October 26, 2025
**Maintainer**: ApplyLens Engineering Team
