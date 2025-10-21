# Domain Enrichment Worker

## Overview

The **Domain Enrichment Worker** fetches WHOIS data and DNS MX records for email sender domains, populating the `domain_enrich` Elasticsearch index to enable domain age detection in the v3.1 pipeline.

This worker is a critical component that enables the **Domain Age Signal** (+15 pts for domains <30 days old), which was implemented as a placeholder in v3.1 but requires external enrichment data.

## Features

- **WHOIS Data Fetching**: Retrieves domain creation date, registrar info
- **DNS MX Record Query**: Checks mail server configuration
- **Domain Age Calculation**: Computes age in days, assigns risk hints
- **Smart Caching**: Only re-enriches domains older than 7 days
- **Bulk Indexing**: Efficient batch writes to Elasticsearch
- **Rate Limiting**: 1 req/sec to avoid WHOIS throttling
- **Error Handling**: Graceful fallback for missing/invalid domains
- **Daemon Mode**: Continuous enrichment with configurable interval

## Architecture

```
┌─────────────────┐
│  Gmail Emails   │
│     Index       │  1. Query unique
│ (gmail_emails)  │────► sender domains
└─────────────────┘

         │
         │ 2. Filter out
         │    recently enriched
         ▼

┌─────────────────┐
│  Enrichment     │
│     Worker      │  3. Fetch WHOIS
│ (domain_enrich  │────► & DNS MX data
│      .py)       │
└─────────────────┘

         │
         │ 4. Bulk index
         │    enrichments
         ▼

┌─────────────────┐
│   Domain        │
│   Enrichment    │  5. Ingest pipeline
│     Index       │────► reads enrichment
│(domain_enrich)  │      via enrich processor
└─────────────────┘
```

## Installation

### 1. Install Python Dependencies

```bash
# Required for WHOIS lookups
pip install python-whois

# Required for DNS MX lookups
pip install dnspython

# Required for HTTP requests
pip install requests
```

Or install via project requirements:

```bash
pip install -r services/workers/requirements.txt
```

### 2. Create `requirements.txt` (if not exists)

```txt
python-whois>=0.8.0
dnspython>=2.3.0
requests>=2.31.0
```

## Usage

### Run Once (Manual Enrichment)

Enrich all unenriched domains and exit:

```bash
python services/workers/domain_enrich.py --once
```

### Run in Daemon Mode (Continuous)

Enrich continuously with default 1-hour interval:

```bash
python services/workers/domain_enrich.py --daemon
```

Enrich every 30 minutes:

```bash
python services/workers/domain_enrich.py --daemon --interval 1800
```

### Environment Variables

Configure via environment variables:

```bash
# Elasticsearch endpoint
export ES_URL=http://localhost:9200

# Email index to scan for domains
export ES_INDEX=gmail_emails

# Enrichment index to populate
export ES_ENRICH_INDEX=domain_enrich

# Optional: WHOIS API key (if using external API)
export WHOIS_API_KEY=your_api_key_here

# Run worker
python services/workers/domain_enrich.py --daemon --interval 3600
```

## Enrichment Index Schema

The worker creates the `domain_enrich` index with the following mapping:

```json
{
  "mappings": {
    "properties": {
      "domain": { "type": "keyword" },
      "created_at": { "type": "date" },
      "age_days": { "type": "integer" },
      "mx_host": { "type": "keyword" },
      "mx_exists": { "type": "boolean" },
      "registrar": { "type": "keyword" },
      "enriched_at": { "type": "date" },
      "risk_hint": { "type": "keyword" },
      "whois_error": { "type": "text" }
    }
  }
}
```

### Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| `domain` | keyword | Sender domain (e.g., `example.com`) |
| `created_at` | date | Domain registration date (ISO 8601) |
| `age_days` | integer | Domain age in days |
| `mx_host` | keyword | Primary MX host (e.g., `mail.example.com`) |
| `mx_exists` | boolean | Whether MX records exist |
| `registrar` | keyword | Domain registrar (e.g., `GoDaddy`) |
| `enriched_at` | date | Timestamp of enrichment |
| `risk_hint` | keyword | Risk level: `very_young`, `young`, `recent`, `established`, `unknown` |
| `whois_error` | text | Error message if WHOIS lookup failed |

### Risk Hint Classification

| Risk Hint | Age Range | Risk Level | Points in Pipeline |
|-----------|-----------|------------|-------------------|
| `very_young` | 0-29 days | 🔴 High | +15 pts |
| `young` | 30-89 days | 🟡 Medium | +10 pts (optional) |
| `recent` | 90-364 days | 🟢 Low | +5 pts (optional) |
| `established` | 365+ days | ✅ Trusted | 0 pts |
| `unknown` | N/A | ⚪ Unknown | 0 pts |

## Pipeline Integration

The v3.1 pipeline already has a placeholder **Domain Age Processor** (processor 5) that looks up enrichment data:

```json
{
  "enrich": {
    "policy_name": "domain_age_policy",
    "field": "from_domain",
    "target_field": "domain_enrich",
    "max_matches": 1,
    "ignore_missing": true
  }
}
```

### Create Enrich Policy

To enable the pipeline integration, create an enrich policy:

```bash
# 1. Create enrich policy
curl -X PUT "$ES_URL/_enrich/policy/domain_age_policy" \
  -H "Content-Type: application/json" \
  -d '{
    "match": {
      "indices": "domain_enrich",
      "match_field": "domain",
      "enrich_fields": ["age_days", "risk_hint", "registrar", "mx_host"]
    }
  }'

# 2. Execute policy (loads data into memory)
curl -X POST "$ES_URL/_enrich/policy/domain_age_policy/_execute"
```

**Note**: You must re-execute the enrich policy after each enrichment cycle to refresh the in-memory index.

## Testing with Test Emails

### Seed Test Domain

Before running test case `tc6-young-domain`, seed enrichment data:

```bash
# Seed a "very young" domain (7 days old)
curl -X PUT "$ES_URL/domain_enrich/_doc/new-hire-team-hr.com" \
  -H "Content-Type: application/json" \
  -d '{
    "domain": "new-hire-team-hr.com",
    "created_at": "'$(date -u -d '7 days ago' --iso-8601=seconds)'",
    "age_days": 7,
    "mx_host": "mail.new-hire-team-hr.com",
    "mx_exists": true,
    "registrar": "NameCheap",
    "enriched_at": "'$(date -u --iso-8601=seconds)'",
    "risk_hint": "very_young",
    "whois_error": null
  }'

# Re-execute enrich policy to load new data
curl -X POST "$ES_URL/_enrich/policy/domain_age_policy/_execute"
```

### Re-run Test Case tc6

```bash
# Delete old tc6 email
curl -X DELETE "$ES_URL/gmail_emails-999999/_doc/tc6-young-domain"

# Re-generate tc6 with pipeline
python scripts/generate_test_emails.py

# Verify domain age signal was applied
curl "$ES_URL/gmail_emails-999999/_doc/tc6-young-domain?pretty" | jq '._source.suspicion_score'
# Expected: 30+ (15 base + 15 domain age)
```

## Verification

### Check Enrichment Index

```bash
# Count enriched domains
curl "$ES_URL/domain_enrich/_count?pretty"

# Search recently enriched domains
curl "$ES_URL/domain_enrich/_search?pretty" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "range": {
        "enriched_at": {
          "gte": "now-1d"
        }
      }
    },
    "size": 10
  }'
```

### Check Risk Hints Distribution

```bash
curl "$ES_URL/domain_enrich/_search?pretty" \
  -H "Content-Type: application/json" \
  -d '{
    "size": 0,
    "aggs": {
      "risk_breakdown": {
        "terms": {
          "field": "risk_hint",
          "size": 10
        }
      }
    }
  }'
```

Expected output:

```json
{
  "aggregations": {
    "risk_breakdown": {
      "buckets": [
        { "key": "established", "doc_count": 847 },
        { "key": "recent", "doc_count": 103 },
        { "key": "young", "doc_count": 42 },
        { "key": "very_young", "doc_count": 8 }
      ]
    }
  }
}
```

## Deployment

### Systemd Service (Linux)

Create `/etc/systemd/system/domain-enrich.service`:

```ini
[Unit]
Description=Domain Enrichment Worker for Email Risk Detection
After=network.target elasticsearch.service

[Service]
Type=simple
User=applylens
WorkingDirectory=/opt/applylens
Environment="ES_URL=http://localhost:9200"
Environment="ES_INDEX=gmail_emails"
Environment="ES_ENRICH_INDEX=domain_enrich"
ExecStart=/usr/bin/python3 /opt/applylens/services/workers/domain_enrich.py --daemon --interval 3600
Restart=on-failure
RestartSec=30

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable domain-enrich
sudo systemctl start domain-enrich
sudo systemctl status domain-enrich
```

### Cron Job (Alternative)

Add to crontab (runs daily at 2 AM):

```bash
# Domain enrichment worker - runs daily at 2 AM
0 2 * * * cd /opt/applylens && ES_URL=http://localhost:9200 python3 services/workers/domain_enrich.py --once >> /var/log/domain_enrich.log 2>&1
```

### Docker Compose

Add to `docker-compose.yml`:

```yaml
services:
  domain-enrich:
    build:
      context: ./services/workers
      dockerfile: Dockerfile.domain_enrich
    environment:
      - ES_URL=http://elasticsearch:9200
      - ES_INDEX=gmail_emails
      - ES_ENRICH_INDEX=domain_enrich
    restart: unless-stopped
    depends_on:
      - elasticsearch
    command: ["python3", "domain_enrich.py", "--daemon", "--interval", "3600"]
```

## Monitoring

### Logs

The worker outputs structured logs:

```
2024-01-15 14:32:10 [INFO] Starting enrichment cycle
2024-01-15 14:32:11 [INFO] Enrichment index already exists: domain_enrich
2024-01-15 14:32:12 [INFO] Found 47 domains to enrich (out of 1023 total)
2024-01-15 14:32:13 [INFO] Enriching domain: suspicious-bank-alert.com
2024-01-15 14:32:15 [INFO] Enriching domain: new-hire-team-hr.com
...
2024-01-15 14:33:45 [INFO] Successfully indexed 47 domain enrichments
2024-01-15 14:33:45 [INFO] Enrichment cycle complete
```

### Prometheus Metrics (Future)

Add metrics for monitoring:

```python
from prometheus_client import Counter, Histogram, Gauge

enrichments_total = Counter('domain_enrichments_total', 'Total domains enriched')
enrichment_errors_total = Counter('domain_enrichment_errors_total', 'Enrichment failures')
enrichment_duration_seconds = Histogram('domain_enrichment_duration_seconds', 'Time per enrichment')
domains_pending_gauge = Gauge('domains_pending_enrichment', 'Domains awaiting enrichment')
```

## Troubleshooting

### `ModuleNotFoundError: No module named 'whois'`

**Problem**: python-whois not installed

**Solution**:

```bash
pip install python-whois
```

### `WHOIS lookup failed: [Errno -2] Name or service not known`

**Problem**: Domain doesn't exist or WHOIS server unreachable

**Expected Behavior**: Worker logs debug message and continues with next domain. Document indexed with `whois_error` field.

### `Connection refused to Elasticsearch`

**Problem**: ES_URL incorrect or Elasticsearch not running

**Solution**:

```bash
# Check Elasticsearch status
curl http://localhost:9200/_cluster/health

# Update ES_URL if needed
export ES_URL=http://your-es-host:9200
```

### `Rate limit exceeded: Too many WHOIS queries`

**Problem**: Worker making too many requests too fast

**Solution**: The worker already implements 1 req/sec rate limiting. If still hitting limits, increase sleep time:

```python
# In domain_enrich.py, line ~250
time.sleep(2)  # Increase from 1 to 2 seconds
```

### `Enrich processor returns null for domain_enrich field`

**Problem**: Enrich policy not executed or domain not in enrichment index

**Solution**:

```bash
# 1. Check if domain is enriched
curl "$ES_URL/domain_enrich/_doc/example.com?pretty"

# 2. Re-execute enrich policy
curl -X POST "$ES_URL/_enrich/policy/domain_age_policy/_execute"

# 3. Re-index email with pipeline
curl -X POST "$ES_URL/gmail_emails/_update_by_query?pipeline=applylens_emails_v3&conflicts=proceed"
```

## Performance

### Enrichment Speed

- **WHOIS lookup**: ~1-3 seconds per domain (rate limited)
- **DNS MX lookup**: ~50-200ms per domain
- **Bulk indexing**: ~50-100 domains/second (batches of 100)

**Typical performance**: 1000 domains in ~20-30 minutes (with rate limiting)

### Optimization Tips

1. **Cache TTL**: Default 7 days. Reduce to 1 day for more frequent updates:

```python
CACHE_TTL_DAYS = 1  # Re-enrich daily
```

2. **Batch Size**: Default 100. Increase for faster indexing:

```python
BATCH_SIZE = 500  # Index 500 at a time
```

3. **Parallel Workers**: Run multiple workers with different domain shards (advanced):

```bash
# Worker 1: domains A-M
ES_DOMAIN_FILTER='[A-M]' python domain_enrich.py --daemon &

# Worker 2: domains N-Z
ES_DOMAIN_FILTER='[N-Z]' python domain_enrich.py --daemon &
```

## Next Steps

1. ✅ **Deploy Worker**: Run `python domain_enrich.py --once` to enrich existing domains
2. ✅ **Create Enrich Policy**: Enable pipeline integration (see "Pipeline Integration")
3. ✅ **Test tc6**: Validate domain age signal with test case
4. ⏳ **Schedule Daemon**: Set up systemd service or cron job for continuous enrichment
5. ⏳ **Monitor Metrics**: Add Prometheus metrics for observability
6. ⏳ **External API**: Integrate paid WHOIS API for higher rate limits (optional)

## References

- **v3.1 Pipeline**: `infra/elasticsearch/pipelines/emails_v3.json` (processor 5)
- **Test Generator**: `scripts/generate_test_emails.py` (tc6-young-domain)
- **v3.1 Summary**: `docs/EMAIL_RISK_V3.1_SUMMARY.md` (Next Steps section)
- **Elasticsearch Enrich Processor**: https://www.elastic.co/guide/en/elasticsearch/reference/current/enrich-processor.html
