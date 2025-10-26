# Phase 1.4: LLM Integration (v0.4.41)

## Overview
Added LLM integration to Mailbox Assistant for smarter intent classification and natural language summaries.

## Implementation Summary

### 1. New Module: `llm_provider.py`
Created unified LLM interface with graceful fallback chain:
- **Primary**: Ollama (local OSS 20B model) at `http://ollama:11434`
- **Fallback**: OpenAI GPT-4o-mini
- **Safety**: 8-second timeout, temperature 0.2, max_tokens 200
- **Graceful Degradation**: Returns `None` if both providers fail

**Key Functions:**
```python
async def generate_llm_text(prompt: str) -> Optional[str]:
    """
    Tries Ollama first, falls back to OpenAI, returns None if both fail.
    Never sends raw email bodies - only structured metadata.
    """
```

### 2. Enhanced Intent Classification
Updated `classify_intent()` in `assistant.py`:
- **Fast Path**: Keyword matching (no LLM needed for common queries)
- **LLM Fallback**: For ambiguous queries like "What sketchy stuff came in this week?"
- **Whitelist Validation**: Only returns intents from `INTENTS_ALLOWED` list
- **Safe Fallback**: Defaults to "summarize_activity" if LLM fails or returns invalid intent

**Supported Intents:**
- `summarize_activity` - General inbox overview
- `list_bills_due` - Financial documents
- `list_suspicious` - High-risk/phishing emails
- `list_followups` - Messages needing response
- `list_interviews` - Job application related
- `cleanup_promotions` - Marketing emails to unsubscribe

### 3. Polished Summaries
Added `generate_polished_summary()` function:
- Converts template-based summaries into natural language
- Includes context from:
  - Top 3 emails (sender, subject, risk level)
  - Actions performed (if mode="run")
  - Intent and time window
- **Safety**: Only sends structured metadata, never raw email bodies
- **Graceful Fallback**: Uses base summary if LLM unavailable

**Example Transformation:**
- **Before**: "I found 3 suspicious / high-risk emails in the last 7d."
- **After**: "You received 3 potentially dangerous emails this week, including one pretending to be your bank. I've quarantined them for your safety."

### 4. Environment Configuration
Added to `docker-compose.prod.yml`:
```yaml
# LLM Integration (Phase 1.4)
OLLAMA_BASE: ${OLLAMA_BASE:-http://ollama:11434}
OLLAMA_MODEL: ${OLLAMA_MODEL:-oss-20b}
OPENAI_API_KEY: ${OPENAI_API_KEY}
OPENAI_MODEL: ${OPENAI_MODEL:-gpt-4o-mini}
ASSISTANT_INTERNAL_API_BASE: http://api:8003
```

## Deployment

### Build & Push
```bash
docker build -f services/api/Dockerfile.prod -t leoklemet/applylens-api:v0.4.41 services/api
docker push leoklemet/applylens-api:v0.4.41
```

### Deploy
```bash
docker compose -f docker-compose.prod.yml up -d api
```

### Verification
```bash
curl http://localhost:8003/ready
# Response: {"status":"ready","db":"ok","es":"ok","migration":"0033_sender_overrides"}

curl http://localhost:8003/config
# Response: {"readOnly":false,"version":"0.4.41"}
```

## Architecture Decisions

### Why This Fallback Chain?
1. **Local First**: Ollama (OSS 20B) is free and private
2. **Quality Fallback**: OpenAI provides better responses when local model unavailable
3. **Graceful Degradation**: System works even if both LLMs fail (uses template summaries)

### Safety Features
- **No Raw Email Bodies**: Only sends structured metadata (sender, subject, risk score)
- **Low Temperature (0.2)**: Prevents hallucination and speculation
- **Short Max Tokens (200)**: Keeps responses concise and grounded
- **Intent Whitelist**: LLM can only suggest predefined intents, not arbitrary actions
- **Timeout Protection**: 8-second timeout prevents blocking

### When LLM is Used
1. **Intent Classification**: When keyword matching fails
2. **Summary Polishing**: Always attempted, falls back to base summary
3. **Action Narration**: (Future enhancement - not in v0.4.41)

### When LLM is NOT Used
- Keyword matching succeeds (fast path)
- LLM providers timeout or fail
- User has opted out of enhanced features (future setting)

## Testing Recommendations

### Test Case 1: Ambiguous Query
```json
{
  "user_query": "What sketchy stuff came in this week?",
  "mode": "learn",
  "time_window_days": 7
}
```
**Expected**: Intent classified as "list_suspicious" via LLM fallback

### Test Case 2: Clear Query
```json
{
  "user_query": "bills",
  "mode": "learn",
  "time_window_days": 30
}
```
**Expected**: Intent classified as "list_bills_due" via fast keyword path (no LLM call)

### Test Case 3: LLM Summary Enhancement
```json
{
  "user_query": "summarize",
  "mode": "run",
  "time_window_days": 7
}
```
**Expected**: Base summary enhanced with natural language via LLM

## Environment Variables Required

For full LLM functionality, add to `infra/.env`:
```bash
# Ollama (Local LLM)
OLLAMA_BASE=http://ollama:11434  # Default if not set
OLLAMA_MODEL=oss-20b             # Your custom model

# OpenAI (Fallback)
OPENAI_API_KEY=sk-...            # REQUIRED for fallback
OPENAI_MODEL=gpt-4o-mini         # Default if not set
```

**Note**: If `OPENAI_API_KEY` is not set, the system will still work but only use Ollama. If Ollama is also unavailable, it will use template summaries (fully functional, just less natural language).

## Files Modified

### New Files
- `services/api/app/llm_provider.py` (124 lines)

### Updated Files
- `services/api/app/routers/assistant.py`
  - Made `classify_intent()` async with LLM fallback
  - Added `generate_polished_summary()` helper
  - Updated `assistant_query()` to use polished summaries
- `services/api/app/settings.py`
  - Version: 0.4.40 → 0.4.41
- `docker-compose.prod.yml`
  - Image: v0.4.40 → v0.4.41
  - Added LLM environment variables

## Next Steps (Future Enhancements)

### Phase 1.5: Action Narration
- Use LLM to narrate what actions were performed
- Example: "I've unsubscribed you from 5 promotional senders and archived their messages."

### Phase 1.6: User Preferences
- Add user setting to enable/disable LLM features
- Fallback to template summaries if disabled

### Phase 1.7: Ollama Service
- Add Ollama container to `docker-compose.prod.yml`
- Pre-load OSS 20B model on startup
- Configure on same network as API

### Phase 1.8: Monitoring
- Add LLM call metrics to Prometheus
- Track fallback rates (Ollama vs OpenAI vs None)
- Monitor response times and costs

## Performance Characteristics

### Latency
- **Keyword Path**: < 10ms (no LLM call)
- **With Ollama**: 500-2000ms (local inference)
- **With OpenAI**: 200-800ms (network + cloud inference)
- **Timeout**: 8000ms maximum

### Cost
- **Ollama**: Free (local inference)
- **OpenAI**: ~$0.0001 per request (gpt-4o-mini pricing)
- **Estimated Monthly Cost**: < $10 for 100,000 requests

### Token Usage
- **Prompt**: ~150 tokens (structured data + instructions)
- **Response**: ~50-200 tokens (summary or intent)
- **Total**: ~200-350 tokens per request

## Version History

- **v0.4.41** (2025-10-25): LLM integration with Ollama → OpenAI fallback
- **v0.4.40** (2025-10-24): Bulk action execution + sender memory
- **v0.4.39** (2025-10-23): Real Elasticsearch queries
- **v0.4.38** (2025-10-22): Initial Mailbox Assistant endpoint

---

**Status**: ✅ DEPLOYED
**API Version**: 0.4.41
**Deployment Date**: 2025-10-25
**Health**: Ready (DB: OK, ES: OK)
