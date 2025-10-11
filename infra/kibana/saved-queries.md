# Kibana ESQL Saved Queries - ApplyLens Email Analytics

This document contains ESQL queries for analyzing email data in Kibana. These queries provide insights into email patterns, sender behavior, and categorization.

## Prerequisites

1. **Data View**: Create a data view in Kibana pointing to `emails_v1*`
2. **Access**: Navigate to **Analytics → Discover** or **Analytics → Dashboard** in Kibana
3. **ESQL Mode**: Switch to ESQL query mode (available in Kibana 8.11+)

## Saved Queries

### 1. Top Senders by Category

**Purpose**: Identify the most active senders broken down by email category (promo, newsletter, other)

**Query**:
```esql
FROM emails_v1-*
| EVAL category = CASE
    WHEN is_promo == true THEN "promo"
    WHEN is_newsletter == true THEN "newsletter"
    ELSE "other" END
| STATS count = COUNT(*) BY sender_domain, category
| SORT count DESC
| LIMIT 25
```

**Usage**:
- Save this query in Kibana Discover as "Top Senders by Category"
- Use for identifying spam/promo senders
- Helps with building unsubscribe lists

**Visualization**: 
- Best as a **Horizontal Bar Chart** or **Table**
- X-axis: count
- Y-axis: sender_domain
- Color by: category

---

### 2. Promos in Last 7 Days

**Purpose**: Track promotional emails received in the past week

**Query**:
```esql
FROM emails_v1-*
| WHERE is_promo == true AND received_at >= NOW() - 7 DAY
| STATS count = COUNT(*) BY sender_domain
| SORT count DESC
| LIMIT 25
```

**Usage**:
- Save as "Recent Promos (7d)"
- Monitor promo email volume
- Identify aggressive marketing campaigns

**Visualization**:
- **Donut Chart** or **Vertical Bar Chart**
- Single metric: Total promo emails

---

### 3. Newsletter Volume by Sender

**Purpose**: Identify which newsletters you're subscribed to and their sending frequency

**Query**:
```esql
FROM emails_v1-*
| WHERE is_newsletter == true
| STATS count = COUNT(*), 
        first_seen = MIN(received_at), 
        last_seen = MAX(received_at) 
  BY sender_domain
| EVAL days_active = (last_seen - first_seen) / 86400000
| SORT count DESC
| LIMIT 50
```

**Usage**:
- Discover all newsletter subscriptions
- Calculate newsletter frequency
- Prioritize unsubscribe actions

---

### 4. Unsubscribe Opportunities

**Purpose**: Find emails with unsubscribe links that you might want to act on

**Query**:
```esql
FROM emails_v1-*
| WHERE has_unsubscribe == true
| STATS count = COUNT(*), 
        last_email = MAX(received_at)
  BY sender_domain, list_unsubscribe
| SORT count DESC
| LIMIT 100
```

**Usage**:
- Generate bulk unsubscribe list
- Export `list_unsubscribe` URLs for automation
- Prioritize high-volume senders

---

### 5. Email Authentication Analysis

**Purpose**: Check SPF/DKIM/DMARC results to identify potential phishing

**Query**:
```esql
FROM emails_v1-*
| WHERE spf_result IS NOT NULL OR dkim_result IS NOT NULL OR dmarc_result IS NOT NULL
| STATS count = COUNT(*) 
  BY sender_domain, spf_result, dkim_result, dmarc_result
| EVAL auth_score = CASE
    WHEN spf_result == "pass" AND dkim_result == "pass" AND dmarc_result == "pass" THEN "trusted"
    WHEN spf_result == "fail" OR dkim_result == "fail" OR dmarc_result == "fail" THEN "suspicious"
    ELSE "unknown" END
| SORT count DESC
| LIMIT 50
```

**Usage**:
- Identify suspicious senders
- Build allowlist of trusted domains
- Flag potential phishing attempts

---

### 6. Gmail Label Distribution

**Purpose**: Understand how Gmail automatically categorizes your emails

**Query**:
```esql
FROM emails_v1-*
| MV_EXPAND labels
| STATS count = COUNT(*) BY labels
| SORT count DESC
| LIMIT 20
```

**Usage**:
- Validate Gmail's categorization accuracy
- Compare against your own label_heuristics
- Find misclassified emails

---

### 7. Time-Based Email Patterns

**Purpose**: Analyze when promotional emails are most commonly sent

**Query**:
```esql
FROM emails_v1-*
| WHERE is_promo == true
| EVAL hour_of_day = DATE_EXTRACT("hour", received_at),
       day_of_week = DATE_EXTRACT("dow", received_at)
| STATS count = COUNT(*) BY hour_of_day, day_of_week
| SORT count DESC
```

**Usage**:
- Identify peak promo sending times
- Schedule email checking during low-volume periods
- Build time-based filtering rules

**Visualization**:
- **Heatmap** with hour_of_day vs day_of_week
- Color intensity = email count

---

### 8. Label Heuristics Performance

**Purpose**: Validate the accuracy of custom label heuristics

**Query**:
```esql
FROM emails_v1-*
| WHERE label_heuristics IS NOT NULL
| MV_EXPAND label_heuristics
| STATS count = COUNT(*), 
        example_subjects = VALUES(subject, 5)
  BY label_heuristics
| SORT count DESC
```

**Usage**:
- Review classification accuracy
- Find misclassified emails
- Tune heuristic rules

---

### 9. URL Extraction Analysis

**Purpose**: Analyze domains linked in emails (useful for tracking ATS platforms)

**Query**:
```esql
FROM emails_v1-*
| WHERE urls IS NOT NULL
| MV_EXPAND urls
| STATS count = COUNT(*) BY urls
| SORT count DESC
| LIMIT 50
```

**Usage**:
- Identify most common ATS platforms (lever.co, greenhouse.io, etc.)
- Track job posting sources
- Build domain reputation database

---

### 10. Expiring Promos (Future Enhancement)

**Purpose**: Find promos with expiration dates (requires `expires_at` field)

**Note**: This query requires adding an `expires_at` field to your mapping and extracting expiration dates during ingestion.

**Query** (placeholder):
```esql
FROM emails_v1-*
| WHERE is_promo == true 
  AND expires_at IS NOT NULL
  AND expires_at <= NOW() + 7 DAY
  AND expires_at > NOW()
| STATS count = COUNT(*), 
        earliest_expiry = MIN(expires_at)
  BY sender_domain, subject
| SORT earliest_expiry ASC
| LIMIT 25
```

**Implementation Steps**:
1. Add `expires_at: { "type": "date" }` to ES mapping
2. Parse expiration dates during ingestion (look for "expires", "valid until", "offer ends" patterns)
3. Save this query once field is populated

---

## How to Save Queries in Kibana

1. **Navigate to Discover**
   ```
   Kibana → Analytics → Discover
   ```

2. **Switch to ESQL Mode**
   - Click the query bar
   - Select "ESQL" from the language dropdown

3. **Paste Query**
   - Copy one of the queries above
   - Paste into the query bar
   - Click **Run** (or press Ctrl+Enter)

4. **Save Query**
   - Click **Save** in the top-right
   - Name: Use the query name from this document
   - Description: Copy the "Purpose" from above
   - Click **Save**

5. **Create Visualizations**
   - After running query, click **Save**
   - Choose **Add to Dashboard** or **Create Visualization**
   - Configure chart type as suggested in each query

---

## Exporting and Version Control

### Export Saved Queries

To export saved queries for version control:

```bash
# Export all saved searches
curl -X POST "http://localhost:5601/api/saved_objects/_export" \
  -H "kbn-xsrf: true" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "search",
    "includeReferencesDeep": true
  }' > infra/kibana/exports/saved_searches.ndjson
```

### Import Saved Queries

To import on a new Kibana instance:

```bash
curl -X POST "http://localhost:5601/api/saved_objects/_import" \
  -H "kbn-xsrf: true" \
  --form file=@infra/kibana/exports/saved_searches.ndjson
```

---

## Dashboard Suggestions

### Email Analytics Dashboard

Create a dashboard with:
1. **Top Senders by Category** (bar chart)
2. **Promos in Last 7 Days** (metric + trend)
3. **Newsletter Volume by Sender** (table)
4. **Email Authentication Analysis** (pie chart)
5. **Time-Based Email Patterns** (heatmap)

### Unsubscribe Action Dashboard

Create a focused dashboard for cleanup:
1. **Unsubscribe Opportunities** (table with drill-down)
2. **Newsletter Volume by Sender** (sortable table)
3. **Recent Promos (7d)** (bar chart)
4. **Promo sender trends** (time series)

---

## Next Steps

1. ✅ Copy queries into Kibana Discover
2. ✅ Save each query with descriptive names
3. ✅ Create visualizations from saved queries
4. ✅ Build two dashboards (Analytics + Unsubscribe)
5. 🔜 Export saved objects to `infra/kibana/exports/`
6. 🔜 Add `expires_at` field for promo expiration tracking
7. 🔜 Implement ELSER semantic search queries (Phase 2)

---

## Troubleshooting

**Query fails with "Field not found"**:
- Ensure your data view pattern is `emails_v1*`
- Check that fields exist in your mapping (some queries use optional fields)
- Verify data has been indexed from Gmail backfill

**ESQL not available**:
- ESQL requires Elasticsearch 8.11+
- Upgrade your stack or use Kibana Query Language (KQL) equivalents

**Performance issues**:
- Add date range filters: `WHERE received_at >= NOW() - 30 DAY`
- Reduce LIMIT values for large datasets
- Consider index patterns with date suffixes (e.g., `emails_v1-2025.10*`)

---

**Last Updated**: 2025-10-11  
**Elasticsearch Version**: 8.11+  
**Kibana Version**: 8.11+
