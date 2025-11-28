# CSRF Protection & Machine-to-Machine Authentication

This document explains the CSRF protection system and how to authenticate machine-to-machine (M2M) API requests.

## 🔒 CSRF Protection Overview

Cross-Site Request Forgery (CSRF) protection is enabled by default for all state-changing requests (POST, PUT, PATCH, DELETE). The system uses a cookie-based token approach for browser clients.

### How It Works

1. **Browser Clients**: Receive a CSRF token via cookie, must include it in `X-CSRF-Token` header
2. **M2M Clients**: Bypass CSRF via path exemptions or authentication headers
3. **Safe Methods**: GET, HEAD, OPTIONS are always exempt from CSRF checks

## 🤖 Machine-to-Machine Authentication

### Option 1: Path-Based Exemption (Automatic)

These endpoints automatically bypass CSRF protection:

```
/api/extension/*     - Browser extension endpoints (dev-only)
/api/ops/diag*       - DevDiag diagnostics
/api/gmail/*         - Gmail backfill/ingest automation
/api/profile/me      - Profile brain (dev-only)
```

**No additional headers needed** for these paths.

### Option 2: Authorization Header

Any request with an `Authorization` or `X-API-Key` header bypasses CSRF:

```bash
# Bearer token
curl -X POST http://localhost:8003/api/some-endpoint \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"data": "value"}'

# API Key
curl -X POST http://localhost:8003/api/some-endpoint \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"data": "value"}'
```

**Use cases:**
- CI/CD pipelines
- Scheduled tasks
- Backend-to-backend communication
- CLI tools and scripts

### Option 3: Gmail Backfill API Key (Recommended for Production)

For Gmail backfill endpoints, use a dedicated API key:

**Setup:**
```bash
# Set in environment
export BACKFILL_API_KEY="your-secure-api-key-here"
```

**Usage:**
```bash
curl -X POST http://localhost:8003/gmail/backfill/start \
  -H "X-API-Key: your-secure-api-key-here" \
  -d "days=7"
```

**Development Mode:**
- If `BACKFILL_API_KEY` is not set, API key check is disabled (dev convenience)
- In production, **always set** `BACKFILL_API_KEY` to enable authentication

## 📋 Complete Exemption List

### Path-Based Exemptions

**Automation & M2M** (`EXEMPT_PREFIXES`):
- `/api/extension/` - Browser extension
- `/extension/` - Extension without /api prefix
- `/api/ops/diag` - DevDiag diagnostics
- `/api/gmail/` - Gmail backfill/automation
- `/gmail/` - Gmail without /api prefix

**Exact Paths** (`EXEMPT_EXACT`):
- `/api/profile/me` - Profile brain
- `/profile/me` - Profile without /api
- `/api/ops/diag/health` - Health check

**UX Metrics** (`CSRF_EXEMPT_PATHS`):
- `/ux/heartbeat`, `/api/ux/heartbeat`
- `/ux/chat/opened`, `/api/ux/chat/opened`
- `/chat`, `/api/chat`
- `/chat/stream`, `/api/chat/stream` (SSE)
- `/assistant/query`, `/api/assistant/query`

## 🔧 Configuration

### Environment Variables

```bash
# CSRF Protection
CSRF_ENABLED=1                    # Enable/disable CSRF (default: 1)
CSRF_COOKIE_NAME=csrf_token       # Cookie name
COOKIE_SECURE=1                   # Require HTTPS (production)

# Gmail Backfill API Key (optional)
BACKFILL_API_KEY=               # Leave empty in dev, set in production
```

### VS Code Tasks

The default build task (`Ctrl+Shift+B`) includes all environment variables:

```json
{
  "env": {
    "APPLYLENS_DEV": "1",
    "APPLYLENS_DEV_DB": "sqlite:///./dev_extension.db",
    "DEVDIAG_BASE": "http://127.0.0.1:8080",
    "BACKFILL_API_KEY": ""  // Empty = disabled
  }
}
```

## 🧪 Testing

### Test Browser Client (with CSRF Token)

```javascript
// Get CSRF token from cookie
const csrfToken = document.cookie
  .split('; ')
  .find(row => row.startsWith('csrf_token='))
  ?.split('=')[1];

// Include in request
fetch('/api/some-endpoint', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-CSRF-Token': csrfToken
  },
  body: JSON.stringify({ data: 'value' }),
  credentials: 'include'
});
```

### Test M2M Client (with API Key)

```bash
# DevDiag health check (path exemption - no key needed)
curl http://localhost:8003/api/ops/diag/health

# Gmail backfill (path exemption OR API key)
curl -X POST http://localhost:8003/gmail/backfill/start?days=7

# With API key (when BACKFILL_API_KEY is set)
curl -X POST http://localhost:8003/gmail/backfill/start?days=7 \
  -H "X-API-Key: your-api-key"

# Generic endpoint with Bearer token
curl -X POST http://localhost:8003/api/some-endpoint \
  -H "Authorization: Bearer token123" \
  -d '{"test": true}'
```

### Test CSRF Protection

```bash
# Should succeed (exempt path)
curl -X POST http://localhost:8003/api/extension/applications \
  -H "Content-Type: application/json" \
  -d '{"company":"TestCo","role":"Engineer","job_url":"https://example.com"}'

# Should succeed (has auth header)
curl -X POST http://localhost:8003/api/applications \
  -H "Authorization: Bearer token" \
  -H "Content-Type: application/json" \
  -d '{"company":"TestCo"}'

# Should fail 403 (no CSRF token, not exempt)
curl -X POST http://localhost:8003/api/applications \
  -H "Content-Type: application/json" \
  -d '{"company":"TestCo"}'
```

## 📊 Metrics

CSRF protection emits Prometheus metrics:

```promql
# CSRF failures by path and method
csrf_fail_total{path="/api/applications",method="POST"}

# CSRF successes
csrf_success_total{path="/api/applications",method="POST"}
```

Check current metrics:
```bash
curl http://localhost:8003/metrics | grep csrf
```

## 🛡️ Security Best Practices

### For Development

1. **Path exemptions** are preferred for known automation endpoints
2. Keep `BACKFILL_API_KEY` empty for easier local development
3. Use `ALLOW_DEV_ROUTES=1` to enable dev-only endpoints

### For Production

1. **Always set** `BACKFILL_API_KEY` for Gmail automation
2. **Enable** `COOKIE_SECURE=1` to require HTTPS
3. **Rotate** API keys regularly
4. **Monitor** `csrf_fail_total` metrics for unusual patterns
5. **Use Bearer tokens** for service-to-service communication

### API Key Generation

```bash
# Generate secure random API key (32 bytes)
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Or using openssl
openssl rand -base64 32
```

## 🐛 Troubleshooting

### "CSRF token missing" (403)

**Browser clients:**
- Ensure cookies are enabled
- Check `X-CSRF-Token` header is being sent
- Verify `credentials: 'include'` in fetch requests

**M2M clients:**
- Add `Authorization` or `X-API-Key` header
- OR use an exempt path (`/api/extension/*`, `/api/gmail/*`, etc.)

### "Invalid API key" (401)

- Check `BACKFILL_API_KEY` is set in environment
- Verify `X-API-Key` header value matches environment variable
- In dev mode, unset `BACKFILL_API_KEY` to disable check

### CSRF Metrics Show Failures

```bash
# Check which paths are failing
curl http://localhost:8003/metrics | grep 'csrf_fail_total.*extension'

# If extension paths are failing, routes may not be exempt
# Check app/core/csrf.py EXEMPT_PREFIXES includes the path
```

## 📚 Related Documentation

- [Development Scripts](../scripts/README.md)
- [DevDiag Integration](../../../docs/DEVDIAG_INTEGRATION.md)
- [Extension API Test Suite](../test_extension_endpoints.ps1)
