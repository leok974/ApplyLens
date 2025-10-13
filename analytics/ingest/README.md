# Gmail → Elasticsearch + BigQuery Backfill Script

This script fetches emails from Gmail API and indexes them into both Elasticsearch and BigQuery for analytics.

## 📋 Prerequisites

1. **Gmail OAuth Credentials**
   - Create OAuth 2.0 credentials at <https://console.cloud.google.com/apis/credentials>
   - Download `client_secret.json` and place in this directory

2. **BigQuery Service Account**
   - Set `GOOGLE_APPLICATION_CREDENTIALS` environment variable
   - Windows: `$env:GOOGLE_APPLICATION_CREDENTIALS="D:\ApplyLens\analytics\dbt\applylens-ci.json"`
   - Linux/macOS: `export GOOGLE_APPLICATION_CREDENTIALS=/path/to/applylens-ci.json`

3. **Elasticsearch**
   - Apply index template first (see below)

## 🚀 Quick Start

### 1. Apply Elasticsearch Index Template

```bash
curl -X PUT http://localhost:9200/_index_template/emails_v1 \
  -H 'Content-Type: application/json' \
  --data-binary @../../infra/elasticsearch/emails_v1.template.json
```

### 2. Install Dependencies

```bash
cd analytics/ingest
pip install -r requirements.txt
```

### 3. Set Up Gmail OAuth

Place your `client_secret.json` file in this directory (or set `GMAIL_CLIENT_SECRET` env var).

### 4. Run Backfill

```bash
python gmail_backfill_to_es_bq.py
```

The script will:

- Open your browser for Gmail OAuth (first time only)
- Fetch emails from the last 60 days
- Index them into Elasticsearch
- Insert them into BigQuery
- Cache OAuth token in `token.json` for future runs

## 🔧 Configuration

All settings can be customized via environment variables:

```bash
# Number of days to backfill (default: 60)
export BACKFILL_DAYS=60

# Elasticsearch settings
export ES_URL=http://localhost:9200
export ES_EMAIL_INDEX=emails_v1-000001

# BigQuery settings
export BQ_PROJECT=applylens-gmail-1759983601
export BQ_DATASET=applylens
export BQ_TABLE=public_emails

# Gmail OAuth settings
export GMAIL_CLIENT_SECRET=client_secret.json
export GMAIL_TOKEN_PATH=token.json
```

## 📊 Verification

After running the backfill, verify data was indexed:

### Elasticsearch

```bash
# Count documents
curl -s http://localhost:9200/emails_v1-000001/_count | jq

# Search for promos
curl -s "http://localhost:8000/search/?q=promo&size=5" | jq

# Get a specific document
curl -s http://localhost:9200/emails_v1-000001/_doc/<email_id> | jq
```

### BigQuery

```bash
# Count rows
bq query --project_id=applylens-gmail-1759983601 \
  'SELECT COUNT(*) FROM applylens.public_emails'

# Check recent emails
bq query --project_id=applylens-gmail-1759983601 \
  'SELECT sender, subject, received_at 
   FROM applylens.public_emails 
   ORDER BY received_at DESC 
   LIMIT 10'
```

## 📝 Fields Indexed

The script extracts and indexes the following fields:

**Email Metadata:**

- `id` - Gmail message ID
- `thread_id` - Gmail thread ID
- `sender` - Full sender address
- `sender_domain` - Extracted domain
- `subject` - Email subject
- `body_text` - Plain text body (HTML converted)
- `received_at` - Timestamp

**Labels & Classification:**

- `labels` - Gmail labels (array)
- `reason` - Categorization reason
- `is_newsletter` - Boolean
- `is_promo` - Boolean
- `has_unsubscribe` - Boolean

**Security:**

- `spf_result` - SPF authentication result
- `dkim_result` - DKIM authentication result
- `dmarc_result` - DMARC authentication result

**Content Analysis:**

- `urls` - Extracted URLs (array)
- `list_unsubscribe` - Unsubscribe header value

## 🐛 Troubleshooting

### OAuth Error: `redirect_uri_mismatch`

Make sure your OAuth client is configured with redirect URI: `http://localhost:PORT/`

### BigQuery Permission Denied

Ensure your service account has these roles:

- `BigQuery Data Editor`
- `BigQuery Job User`

### Elasticsearch Connection Refused

Make sure Elasticsearch is running:

```bash
curl http://localhost:9200
```

### Rate Limiting

The script respects Gmail API rate limits. For large backfills (>10k emails), consider:

- Running during off-peak hours
- Using smaller `BACKFILL_DAYS` values
- Batch processing with pagination

## 📚 Architecture

```
Gmail API
    ↓
Python Script
    ├─→ Elasticsearch (emails_v1-000001)
    └─→ BigQuery (applylens.public_emails)
```

## 🔐 Security Notes

- `client_secret.json` - Should be gitignored (never commit)
- `token.json` - OAuth token cache (gitignored)
- Service account JSON - Should be gitignored
- All credentials should be stored securely

## 📈 Performance

- **Small backfill** (< 1k emails): ~2-5 minutes
- **Medium backfill** (1k-10k emails): ~10-30 minutes
- **Large backfill** (10k+ emails): ~1-3 hours

The script processes emails sequentially to avoid rate limits. For production use, consider:

- Implementing concurrent processing with rate limiting
- Adding deduplication logic
- Using bulk insert APIs
- Implementing retry logic with exponential backoff

## 🔄 Running on Schedule

To run this periodically (e.g., daily):

### Linux/macOS (cron)

```bash
# Add to crontab (runs daily at 2 AM)
0 2 * * * cd /path/to/analytics/ingest && python gmail_backfill_to_es_bq.py >> backfill.log 2>&1
```

### Windows (Task Scheduler)

1. Open Task Scheduler
2. Create Basic Task
3. Trigger: Daily at 2:00 AM
4. Action: Start a program
5. Program: `python`
6. Arguments: `gmail_backfill_to_es_bq.py`
7. Start in: `D:\ApplyLens\analytics\ingest`

### Docker (for production)

See `../../infra/docker-compose.yml` for containerized deployment options.

## 📄 License

Part of ApplyLens project. See root LICENSE file.
