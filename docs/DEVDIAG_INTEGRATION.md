# DevDiag HTTP Integration

## Overview
DevDiag HTTP is an external diagnostic service that probes your application for common issues, performance problems, and configuration errors. This integration enables automated health checks and CI/CD quality gates.

## Configuration

### 1. Environment Variables (Production)

Add these to your `.env.prod` file:

```bash
# DevDiag HTTP - Diagnostic Service Integration
DEVDIAG_BASE=https://devdiag.example.com  # Your DevDiag instance URL
DEVDIAG_JWT=<your-jwt-token>              # Authentication token
DEVDIAG_ENABLED=1                         # Enable/disable integration
DEVDIAG_TIMEOUT_S=120                     # Request timeout (seconds)
DEVDIAG_ALLOW_HOSTS=applylens.app,.applylens.app,api.applylens.app
DEVDIAG_HOST=devdiag.example.com          # For Prometheus scraping
```

### 2. Docker Compose

The environment variables are automatically passed to the `api` service in `docker-compose.yml`. No additional configuration needed.

### 3. Prometheus Monitoring (Optional)

If your DevDiag HTTP service exposes Prometheus metrics at `/metrics`, they'll be automatically scraped.

**Metrics to watch:**
- `devdiag_http_up` - Service availability
- `devdiag_http_rate_limit_rps` - Rate limiting status
- `devdiag_http_max_concurrent` - Concurrent request limit

**Grafana Queries:**
```promql
# DevDiag service uptime
up{job="devdiag-http"}

# Request rate
rate(devdiag_http_requests_total[5m])

# Error rate
rate(devdiag_http_errors_total[5m])
```

## CI/CD Integration

### GitHub Actions Workflow

The workflow `.github/workflows/devdiag-quickcheck.yml` runs on every pull request to `main`:

**What it does:**
1. **Health Check** - Verifies DevDiag service is responding
2. **App Probe** - Runs diagnostics on `https://applylens.app`
3. **Quality Gate** - Fails if more than 25 problems detected
4. **Summary** - Posts top problem codes to PR summary

### Setup GitHub Secrets

Add these secrets in your repository settings:

1. **DEVDIAG_BASE**
   - Value: `https://devdiag.example.com`
   - Used by: CI workflow

2. **DEVDIAG_JWT** (Optional)
   - Value: Your JWT token
   - Used by: CI workflow for authenticated requests

### Example Workflow Run

```bash
# Health check passes
✓ DevDiag service is healthy

# Probe ApplyLens
✓ Found 12 issues (threshold: 25)

### DevDiag — Top problem codes
* 5 PERF-001 (Slow initial load)
* 3 SEC-002 (Missing security headers)
* 2 A11Y-001 (Accessibility issues)
* 2 SEO-003 (Meta tags missing)
```

## Usage in Code

If you need to trigger DevDiag probes from your application code:

```python
import os
import httpx

async def run_devdiag_probe(url: str, preset: str = "app"):
    """Run DevDiag probe on a URL."""
    base = os.getenv("DEVDIAG_BASE")
    jwt = os.getenv("DEVDIAG_JWT")

    if not base or os.getenv("DEVDIAG_ENABLED") != "1":
        return None

    headers = {"Content-Type": "application/json"}
    if jwt:
        headers["Authorization"] = f"Bearer {jwt}"

    payload = {
        "url": url,
        "preset": preset,
        "tenant": "applylens"
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{base}/diag/run",
            json=payload,
            headers=headers
        )
        response.raise_for_status()
        return response.json()
```

## Presets

DevDiag supports different diagnostic presets:

- **app** - Full application diagnostics (performance, security, SEO)
- **api** - API-specific checks (endpoints, rate limits, auth)
- **security** - Security-focused scan (headers, CSP, CORS)
- **performance** - Performance analysis (Core Web Vitals, load times)

## Troubleshooting

### CI Workflow Fails: "DEVDIAG_BASE not set"

**Solution:** Add the `DEVDIAG_BASE` secret to your GitHub repository:
- Go to Settings → Secrets and variables → Actions
- Click "New repository secret"
- Name: `DEVDIAG_BASE`
- Value: Your DevDiag service URL

### Timeout Errors

**Solution:** Increase `DEVDIAG_TIMEOUT_S`:
```bash
DEVDIAG_TIMEOUT_S=180  # 3 minutes
```

### Too Many Problems Detected

**Solution:** Adjust the threshold in `.github/workflows/devdiag-quickcheck.yml`:
```bash
# From:
jq -e '(.result.problems // [] | length) < 25' diag.json

# To:
jq -e '(.result.problems // [] | length) < 50' diag.json
```

### DevDiag Not Reachable from Docker Container

**Solution:** Ensure outbound egress is allowed for the API container. No Cloudflare configuration needed - this is outbound traffic from your server.

## Security Notes

1. **JWT Token Storage**
   - Store `DEVDIAG_JWT` in GitHub Secrets
   - Never commit tokens to version control
   - Rotate tokens periodically

2. **Allowed Hosts**
   - `DEVDIAG_ALLOW_HOSTS` prevents probing unauthorized domains
   - Only add domains you own/control

3. **Rate Limiting**
   - DevDiag may have rate limits
   - Use sparingly in CI (only on PRs to main)
   - Consider caching probe results

## Related Documentation

- [Extension API Observability](./EXTENSION_API_OBSERVABILITY.md)
- [Prometheus Setup](../infra/prometheus/README.md)
- [CI/CD Pipeline](../.github/workflows/README.md)
