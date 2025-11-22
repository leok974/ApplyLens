# Cloudflare Rate Limiting for Extension API

## Overview
Rate limiting configuration for `/api/extension/*` endpoints to prevent buggy or malicious extensions from overwhelming the API.

**Target**: 60 requests per 60 seconds per IP address
**Action**: Challenge (not block) - allows legitimate extensions to continue after verification
**Endpoints**: All routes under `/api/extension/`

---

## Option 1: Cloudflare Dashboard (UI)

1. **Navigate to Rate Limiting Rules**
   - Log in to [Cloudflare Dashboard](https://dash.cloudflare.com/)
   - Select your domain (e.g., `applylens.com`)
   - Go to **Security** → **WAF** → **Rate limiting rules**

2. **Create New Rule**
   - Click **Create rate limiting rule**
   - **Rule name**: `Extension API Rate Limit`

3. **Configure Matching Criteria**
   - **Field**: URI Path
   - **Operator**: starts with
   - **Value**: `/api/extension/`

4. **Set Rate Limit**
   - **Requests**: `60`
   - **Period**: `60 seconds`
   - **Counting method**: By IP address
   - **Match**: All traffic

5. **Choose Action**
   - **Action**: Managed Challenge (CAPTCHA for suspicious requests)
   - Alternative: JS Challenge (lighter verification)

6. **Save and Deploy**
   - Click **Deploy** to activate the rule

---

## Option 2: Cloudflare API (Automated)

Use this PowerShell script to create the rate limiting rule programmatically:

```powershell
# Cloudflare API credentials
$ZONE_ID = "YOUR_ZONE_ID"  # Get from Cloudflare Dashboard → Overview
$CF_API_TOKEN = "YOUR_API_TOKEN"  # Create at https://dash.cloudflare.com/profile/api-tokens

# Rate limit configuration
$ruleConfig = @{
    name = "Extension API Rate Limit"
    description = "Limit /api/extension/* to 60 req/60sec per IP"
    enabled = $true
    expression = '(http.request.uri.path matches "^/api/extension/")'
    action = "challenge"
    characteristics = @("ip.src")
    period = 60
    requests_per_period = 60
    mitigation_timeout = 60
    counting_expression = ""
} | ConvertTo-Json -Depth 5

# Create the rule
curl.exe -X POST "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/rate_limits" `
  -H "Authorization: Bearer $CF_API_TOKEN" `
  -H "Content-Type: application/json" `
  --data $ruleConfig
```

### Finding Your Zone ID
```powershell
# List all zones for your account
curl.exe -X GET "https://api.cloudflare.com/client/v4/zones" `
  -H "Authorization: Bearer $CF_API_TOKEN" `
  -H "Content-Type: application/json"
```

---

## Option 3: Terraform Configuration

Add this to your Cloudflare Terraform config:

```hcl
resource "cloudflare_rate_limit" "extension_api" {
  zone_id = var.cloudflare_zone_id

  threshold     = 60
  period        = 60
  match {
    request {
      url_pattern = "*/api/extension/*"
    }
  }

  action {
    mode    = "challenge"
    timeout = 60
  }

  correlate {
    by = "ip"
  }

  description = "Extension API rate limit: 60 req/60sec per IP"
  disabled    = false
}
```

---

## Testing the Rate Limit

### 1. Manual Testing (PowerShell)
```powershell
# Hammer the endpoint from same IP
for ($i=1; $i -le 70; $i++) {
    $response = Invoke-WebRequest -Uri "https://applylens.com/api/profile/me" `
        -Method GET -Headers @{ "Authorization" = "Bearer YOUR_TOKEN" }
    Write-Host "Request $i - Status: $($response.StatusCode)"
    Start-Sleep -Milliseconds 500
}

# After 60 requests in 60 seconds, should receive:
# - 429 Too Many Requests (if action=block)
# - Cloudflare Challenge page (if action=challenge)
```

### 2. Check Rate Limit Analytics
- Navigate to **Security** → **Analytics** in Cloudflare Dashboard
- View **Rate Limiting Events** to see triggered rules
- Filter by rule name: "Extension API Rate Limit"

---

## Recommended Configuration

**For Production:**
```
Rate: 60 requests / 60 seconds
Action: Managed Challenge
Counting: By IP address
Timeout: 60 seconds
```

**Why Challenge instead of Block?**
- Allows legitimate users to continue after verification
- Browser extensions can handle occasional CAPTCHAs
- Reduces false positives from shared IPs (offices, VPNs)

**Adjust if needed:**
- **Higher limit** (e.g., 120/60s): For power users with multiple extensions
- **Block action**: For zero-tolerance abuse prevention
- **JS Challenge**: Lighter than Managed Challenge, faster for users

---

## Monitoring

### Prometheus Alert (Optional)
Add to `infra/prometheus/alerts.yml`:

```yaml
- alert: ExtensionAPIRateLimitHigh
  expr: rate(cloudflare_rate_limit_triggered_total{rule="Extension API Rate Limit"}[5m]) > 0.5
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "Extension API rate limit frequently triggered"
    description: "{{ $value }} rate limit triggers per second over 5 minutes"
```

### Grafana Dashboard Query
```promql
# Rate limit triggers over time
sum(increase(cloudflare_rate_limit_triggered_total{rule="Extension API Rate Limit"}[1h]))
```

---

## Notes

- **Chrome Extension Origins**: Rate limit applies to requests from `chrome-extension://*` origins
- **Development**: Exempt your IP or use dev environment (`localhost`) which isn't rate-limited
- **Multiple IPs**: Users behind NAT/VPN share same IP - consider increasing limit if complaints arise
- **Cloudflare Workers**: If using Workers, ensure rate limiting runs before worker logic

## References
- [Cloudflare Rate Limiting Docs](https://developers.cloudflare.com/waf/rate-limiting-rules/)
- [Rate Limiting API Reference](https://developers.cloudflare.com/api/operations/rate-limits-create-a-rate-limit)
