# Due Date Extraction for Bill Emails

## Overview

This module provides robust date extraction from bill and payment emails using a Python-first approach with Elasticsearch fallback.

**Features:**

- 🎯 Multiple date format support (mm/dd/yyyy, Month dd yyyy, etc.)
- 💰 Money amount extraction with currency detection
- 🏷️ Bill classification heuristic
- 📊 Elasticsearch ingest pipeline for fallback extraction
- 📈 Kibana dashboard for upcoming bills visualization

## Architecture

```
Email Ingestion Flow:
┌─────────────────────────────────────────────────────┐
│ Gmail API → gmail_service.py                        │
│   1. Extract body_text                              │
│   2. Call extract_due_dates() [Python]              │
│   3. Call extract_money_amounts() [Python]          │
│   4. Index to Elasticsearch with dates[] field      │
└─────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────┐
│ Elasticsearch Ingest Pipeline [Fallback]            │
│   1. Check if dates[] already populated             │
│   2. If empty, run Painless regex extraction        │
│   3. Normalize to ISO 8601 format                   │
│   4. Set expires_at to earliest date                │
└─────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────┐
│ Kibana Dashboard                                     │
│   - ES|QL query: Bills due in next 7 days          │
│   - Time series visualization by due date           │
└─────────────────────────────────────────────────────┘
```

## Supported Date Formats

### 1. mm/dd or mm/dd/yyyy

```
"Payment due by 10/15/2025" → 2025-10-15T00:00:00Z
"Due: 10/15" → 2025-10-15T00:00:00Z (defaults to email received year)
"Pay by 2/28/25" → 2025-02-28T00:00:00Z (2-digit year → 20xx)
```

### 2. Month dd, yyyy

```
"Payment due Oct 15, 2025" → 2025-10-15T00:00:00Z
"Due by December 25" → 2025-12-25T00:00:00Z (defaults to received year)
"Amount due: Jan 1, 2026" → 2026-01-01T00:00:00Z
```

### 3. dd Month yyyy

```
"Due on 15 Oct 2025" → 2025-10-15T00:00:00Z
"Payment by 25 Dec" → 2025-12-25T00:00:00Z
```

## Usage

### Python API

```python
from app.ingest.due_dates import (
    extract_due_dates,
    extract_earliest_due_date,
    extract_money_amounts,
    is_bill_related
)
import datetime as dt

# Extract all due dates
received_at = dt.datetime(2025, 10, 8, tzinfo=dt.timezone.utc)
email_text = "Your bill of $125.50 is due by October 15, 2025"

dates = extract_due_dates(email_text, received_at)
# Returns: ['2025-10-15T00:00:00Z']

# Get earliest date (for expires_at field)
earliest = extract_earliest_due_date(email_text, received_at)
# Returns: '2025-10-15T00:00:00Z'

# Extract money amounts
amounts = extract_money_amounts(email_text)
# Returns: [{'amount': 125.5, 'currency': 'USD'}]

# Check if email is bill-related
is_bill = is_bill_related("Bill Statement", email_text)
# Returns: True
```

### Elasticsearch Document Structure

```json
{
  "gmail_id": "msg123",
  "subject": "Your October Bill",
  "body_text": "Payment due by 10/15/2025...",
  "dates": [
    "2025-10-15T00:00:00Z",
    "2025-10-20T00:00:00Z"
  ],
  "money_amounts": [
    {"amount": 125.50, "currency": "USD"}
  ],
  "expires_at": "2025-10-15T00:00:00Z",
  "category": "bills"
}
```

## Deployment

### 1. Update Elasticsearch Mapping

```bash
cd services/api
python -m app.scripts.update_es_mapping
```

This adds:

- `dates`: date array field
- `money_amounts`: nested object with amount/currency
- `expires_at`: date field (already exists)

### 2. Deploy ES Ingest Pipeline

```bash
# Set Elasticsearch URL
$ES_URL = "http://localhost:9200"

# Create pipeline
curl -X PUT "$ES_URL/_ingest/pipeline/emails_due_simple" `
  -H "Content-Type: application/json" `
  --data-binary "@infra/es/pipelines/emails_due_simple.json"

# Verify pipeline created
curl -X GET "$ES_URL/_ingest/pipeline/emails_due_simple"

# (Optional) Set as default on index
curl -X PUT "$ES_URL/emails_v1/_settings" `
  -H "Content-Type: application/json" `
  -d '{
    "index.default_pipeline": "emails_due_simple"
  }'
```

### 3. Import Kibana Dashboard

**Via UI:**

1. Open Kibana: <http://localhost:5601>
2. Go to: Stack Management → Saved Objects → Import
3. Select: `kibana/bills-due-next7d.ndjson`
4. Import with "Overwrite conflicts" enabled

**Via API:**

```bash
curl -X POST "http://localhost:5601/api/saved_objects/_import" `
  -H "kbn-xsrf: true" `
  --form file=@kibana/bills-due-next7d.ndjson
```

### 4. Backfill Existing Emails (Optional)

To extract dates from already-indexed emails:

```bash
cd services/api
python -m app.scripts.backfill_bill_dates
```

## Testing

### Unit Tests (28 tests)

```bash
cd services/api
pytest tests/unit/test_due_date_extractor.py -v
```

**Coverage:**

- Date format variations (mm/dd, Month dd, dd Month)
- Year defaults and 2-digit year handling
- Multiple dates sorting and deduplication
- Invalid date handling
- Money amount extraction
- Bill classification
- Case insensitivity
- Realistic bill email scenarios

### E2E Tests (10+ tests)

```bash
# Requires Docker stack (db, es, kibana)
cd infra
docker-compose up -d db es kibana

cd ../services/api
pytest tests/e2e/test_ingest_bill_dates.py -v
```

**Coverage:**

- Gmail API message format handling
- ES document structure validation
- Multipart email processing
- Date extraction from subject + body
- Integration with classification system

## How It Works

### Regex Pattern

The core pattern looks for dates within 80 characters of "due" keywords:

```python
DUE_SENTENCE_RX = re.compile(
    r"""(?P<prefix>\b(due|pay(?:ment)?\s*(?:is)?\s*due|amount\s*due|due\s*on|due\s*by)\b
         [^\.:\n\r]{0,80}?)
         (?P<date>(?:[A-Z][a-z]{2,12}\s+\d{1,2},?\s*\d{0,4})  # Oct 15 or October 15, 2025
            |(?:\d{1,2}/\d{1,2}(?:/\d{2,4})?)                 # 10/15 or 10/15/2025
            |(?:\d{1,2}\s+(?:Jan|Feb|...)[a-z]*,?\s*\d{0,4})  # 15 Oct 2025
         )""",
    re.I | re.X
)
```

**Keywords matched:**

- `due`
- `payment due`, `payment is due`
- `amount due`
- `due on`, `due by`

### Date Normalization

1. Extract date string from regex match
2. Parse into datetime object (with year inference if missing)
3. Convert to UTC timezone
4. Format as ISO 8601 with Z suffix: `2025-10-15T00:00:00Z`
5. Deduplicate and sort chronologically

### Elasticsearch Pipeline (Fallback)

Painless script that:

1. Checks if `dates[]` already populated by Python
2. If empty, searches `body_text` for simple mm/dd patterns
3. Normalizes to ISO 8601 format
4. Merges with any existing dates
5. Sets `expires_at` to earliest date

**Pattern used:**

```javascript
/due[^\n\r\.:]{0,80}?(\d{1,2}\/\d{1,2}(?:\/\d{2,4})?)/
```

Only handles mm/dd format (simpler than Python for performance).

## Integration with NL Agent

The extracted dates enable natural language queries:

```python
# User command: "Show me bills due before Friday"
from app.routes.nl_agent import find_bills_due_before

bills = find_bills_due_before(
    es_client, 
    before_date="2025-10-17",
    user_email="user@example.com"
)

# ES Query:
# {
#   "query": {
#     "bool": {
#       "must": [
#         {"term": {"category": "bills"}},
#         {"range": {"dates": {"lt": "2025-10-17T00:00:00Z"}}}
#       ]
#     }
#   },
#   "sort": [{"dates": "asc"}]
# }
```

## Performance Considerations

- **Regex compilation**: Pattern compiled once at module import (fast subsequent matches)
- **Proximity constraint**: 80-char window around "due" reduces false positives
- **Early termination**: Invalid dates discarded immediately
- **ES pipeline**: Only runs on docs without Python-extracted dates
- **Deduplication**: Uses set to eliminate duplicate timestamps

## Troubleshooting

### Dates not being extracted

**Check:**

1. Does text contain "due" or related keywords?
2. Is date within 80 chars of "due" keyword?
3. Is date format supported? (see Supported Date Formats)
4. Run unit tests to verify pattern matching

### ES pipeline not working

**Check:**

1. Pipeline deployed? `GET /_ingest/pipeline/emails_due_simple`
2. Default pipeline set? `GET /emails_v1/_settings`
3. Check pipeline errors: `GET /emails_v1/_search?q=pipeline_error:*`

### Kibana dashboard empty

**Check:**

1. Index pattern exists: `GET /emails_v1/_count?q=category:bills`
2. Dates field populated: `GET /emails_v1/_search?q=dates:*`
3. Date range: Dashboard shows next 7 days only
4. ES|QL enabled in Kibana settings

## Examples

### Example 1: Utility Bill

**Input:**

```
Subject: Your Electric Bill is Ready
Body:
  Thank you for being a valued customer.
  
  Amount Due: $127.43
  Due Date: October 15, 2025
  
  Please pay by the due date to avoid late fees.
```

**Extracted:**

```json
{
  "dates": ["2025-10-15T00:00:00Z"],
  "money_amounts": [{"amount": 127.43, "currency": "USD"}],
  "expires_at": "2025-10-15T00:00:00Z"
}
```

### Example 2: Credit Card Statement

**Input:**

```
Subject: Your Credit Card Statement
Body:
  Statement Period: Sep 1 - Sep 30, 2025
  
  Payment Due: 10/25/2025
  Minimum Payment: $35.00
  Statement Balance: $1,432.89
```

**Extracted:**

```json
{
  "dates": ["2025-10-25T00:00:00Z"],
  "money_amounts": [
    {"amount": 35.0, "currency": "USD"},
    {"amount": 1432.89, "currency": "USD"}
  ],
  "expires_at": "2025-10-25T00:00:00Z"
}
```

### Example 3: Multiple Payment Dates

**Input:**

```
Subject: Payment Plan Reminder
Body:
  Your payment plan schedule:
  
  First payment due: 10/15/2025 - $50.00
  Second payment due: 11/15/2025 - $50.00  
  Final payment due: 12/15/2025 - $50.00
```

**Extracted:**

```json
{
  "dates": [
    "2025-10-15T00:00:00Z",
    "2025-11-15T00:00:00Z",
    "2025-12-15T00:00:00Z"
  ],
  "money_amounts": [{"amount": 50.0, "currency": "USD"}],
  "expires_at": "2025-10-15T00:00:00Z"
}
```

## Future Enhancements

- [ ] Support relative dates ("due in 30 days")
- [ ] Handle international date formats (dd/mm/yyyy)
- [ ] Extract payment methods (auto-pay, manual)
- [ ] Link to recurring bill schedules
- [ ] ML-based date extraction as third fallback
- [ ] Support for business days ("due by next business day")

## Related Files

- `app/ingest/due_dates.py` - Main extraction module
- `app/gmail_service.py` - Integration point
- `tests/unit/test_due_date_extractor.py` - Unit tests
- `tests/e2e/test_ingest_bill_dates.py` - E2E tests
- `infra/es/pipelines/emails_due_simple.json` - ES pipeline
- `kibana/bills-due-next7d.ndjson` - Dashboard definition
- `app/scripts/update_es_mapping.py` - Mapping updates
