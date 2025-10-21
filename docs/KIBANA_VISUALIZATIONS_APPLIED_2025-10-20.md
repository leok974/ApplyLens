# Kibana Visualizations Applied — October 20, 2025

**ApplyLens Infrastructure Enhancement**  
**Component:** Kibana Saved Searches & Lens Visualizations  
**Date:** October 20, 2025  
**Status:** ✅ Saved Search Deployed | 📚 Lens Guide Created

---

## Executive Summary

Enhanced Kibana data exploration capabilities with a new saved search for offers and interviews, plus documentation for creating Lens visualizations manually. The saved search is immediately available for filtering job-related emails, while comprehensive step-by-step guides enable creation of powerful stacked bar charts for email analytics and traffic monitoring.

**What Changed:**
- ✅ New saved search deployed for offers/interviews filtering
- 📄 NDJSON files created for Lens visualizations
- 📚 Comprehensive manual creation guide provided
- 📖 Documentation index updated

---

## Components Deployed

### 1. Saved Search: Offers & Interviews ✅

**File:** `infra/kibana/emails_saved_search_offers.ndjson`  
**Status:** Successfully imported

**Details:**
- **ID:** `applylens-emails-discover-offers`
- **Title:** "ApplyLens — Emails (Offers & Interviews)"
- **Description:** Only emails detected as offers or interviews (archived filtered out)
- **Data View:** ApplyLens Emails (`919a7f6d-4431-451f-b5a6-7f3943524bd4`)

**Query:**
```kql
(is_offer:true or is_interview:true) and archived:false
```

**Columns (7 total):**
1. `received_at` (160px) - Timestamp
2. `from` (240px) - Sender email
3. `to` (240px) - Recipient email
4. `subject` (420px) - Email subject
5. `labels_norm` - Normalized Gmail labels
6. `is_interview` - Interview detection flag
7. `is_offer` - Offer detection flag

**Sort:** `received_at` descending (newest first)

**Import Result:**
```json
{
  "successCount": 1,
  "success": true,
  "successResults": [{
    "type": "search",
    "id": "applylens-emails-discover-offers",
    "meta": {
      "title": "ApplyLens — Emails (Offers & Interviews)",
      "icon": "discoverApp"
    }
  }]
}
```

---

### 2. Lens Visualization: Emails Offers vs Interviews 📚

**File:** `infra/kibana/lens_emails_offers_interviews.ndjson`  
**Status:** Template created, manual creation recommended

**Specification:**
- **Type:** Stacked Bar Chart
- **Title:** "Emails — Offers vs Interviews (5m)"
- **Time Interval:** 5 minutes
- **Data View:** ApplyLens Emails (`gmail_emails-*`)
- **Time Field:** `received_at`

**Metrics:**
- **Metric A (Offers):**
  - Function: Count
  - Filter: `is_offer:true`
  - Label: "Offers"
  
- **Metric B (Interviews):**
  - Function: Count
  - Filter: `is_interview:true`
  - Label: "Interviews"

**Query Filter:** `archived:false`

**Visual Configuration:**
- Chart type: Bar (stacked)
- Legend position: Right
- X-axis: `received_at` (5-minute intervals)
- Y-axis: Count of documents

---

### 3. Lens Visualization: Traffic Status Codes 📚

**File:** `infra/kibana/lens_traffic_status_codes.ndjson`  
**Status:** Template created, manual creation recommended

**Specification:**
- **Type:** Stacked Bar Chart
- **Title:** "Traffic — 4xx / 5xx / 429 (5m)"
- **Time Interval:** 5 minutes
- **Data View:** Logs (`logs-*`)
- **Time Field:** `@timestamp`

**Metrics:**
- **Metric A (4xx Errors):**
  - Function: Count
  - Filter: `http_status >= 400 and http_status < 500 and http_status != 429`
  - Label: "4xx"
  - Color: Orange
  
- **Metric B (5xx Errors):**
  - Function: Count
  - Filter: `http_status >= 500`
  - Label: "5xx"
  - Color: Red
  
- **Metric C (Rate Limiting):**
  - Function: Count
  - Filter: `http_status == 429`
  - Label: "429"
  - Color: Yellow

**Visual Configuration:**
- Chart type: Bar (stacked)
- Legend position: Right
- X-axis: `@timestamp` (5-minute intervals)
- Y-axis: Count of log entries

---

## Why Manual Creation for Lens?

Lens visualizations in Kibana 8.13.4 use a complex, version-specific state format that includes:
- Nested datasource configurations
- Layer-specific column definitions
- Reference mapping between data views and layers
- Visualization-specific rendering parameters

**Benefits of Manual Creation:**
1. **Reliability:** UI ensures correct state format for your Kibana version
2. **Flexibility:** Easy customization during creation
3. **Learning:** Better understanding of Lens capabilities
4. **Future-proof:** UI handles version migrations automatically

**Import Challenges:**
- State format varies between Kibana minor versions
- Nested JSON structure with multiple levels of escaping
- Version-specific migration requirements
- Reference ID mapping complexity

---

## Manual Creation Guide Summary

Full step-by-step instructions available in:  
**`docs/KIBANA_LENS_VISUALIZATIONS_2025-10-20.md`**

### Quick Steps for Email Visualization

1. **Navigate:** Analytics → Visualize Library → Create visualization → Lens
2. **Data View:** Select "ApplyLens Emails"
3. **X-Axis:** `received_at` (5-minute intervals)
4. **Add Metric:** Count with filter `is_offer:true`, label "Offers"
5. **Add Metric:** Count with filter `is_interview:true`, label "Interviews"
6. **Configure:** Bar chart (stacked), legend on right
7. **Filter:** `archived:false`
8. **Save:** "Emails — Offers vs Interviews (5m)"

### Quick Steps for Traffic Visualization

1. **Navigate:** Analytics → Visualize Library → Create visualization → Lens
2. **Data View:** Select "logs-*"
3. **X-Axis:** `@timestamp` (5-minute intervals)
4. **Add Metric:** Count with filter for 4xx errors
5. **Add Metric:** Count with filter for 5xx errors
6. **Add Metric:** Count with filter for 429 errors
7. **Configure:** Bar chart (stacked), colored legend
8. **Save:** "Traffic — 4xx / 5xx / 429 (5m)"

---

## Usage Examples

### Accessing the Saved Search

1. Open Kibana: http://localhost:5601/kibana
2. Navigate to **Analytics → Discover**
3. Click the **Saved** icon (bookmark) in toolbar
4. Select **"ApplyLens — Emails (Offers & Interviews)"**
5. View filtered results with configured columns

### Example Queries in Saved Search

**High-priority offers:**
```kql
is_offer:true and labels_norm:important
```

**Interviews from specific company:**
```kql
is_interview:true and from:*@company.com
```

**Recent opportunities (last week):**
```kql
(is_offer:true or is_interview:true) and received_at >= now-7d
```

---

## Files Created

| File | Purpose | Status |
|------|---------|--------|
| `infra/kibana/emails_saved_search_offers.ndjson` | Saved search definition | ✅ Imported |
| `infra/kibana/lens_emails_offers_interviews.ndjson` | Email analytics viz | 📄 Template |
| `infra/kibana/lens_traffic_status_codes.ndjson` | Traffic monitoring viz | 📄 Template |
| `docs/KIBANA_LENS_VISUALIZATIONS_2025-10-20.md` | Creation guide | ✅ Created |
| `docs/KIBANA_VISUALIZATIONS_APPLIED_2025-10-20.md` | This summary | ✅ Created |

---

## Access Information

**Kibana URL:** http://localhost:5601/kibana  
**Username:** elastic  
**Password:** elasticpass

**Key Locations:**
- **Discover:** Analytics → Discover
- **Visualize Library:** Analytics → Visualize Library
- **Dashboards:** Analytics → Dashboard
- **Data Views:** Stack Management → Data Views

---

## Next Steps

1. **Create Lens Visualizations Manually**
   - Follow guide in `docs/KIBANA_LENS_VISUALIZATIONS_2025-10-20.md`
   - Takes ~5 minutes per visualization
   - Ensures compatibility with Kibana 8.13.4

2. **Build Dashboard**
   - Combine both Lens visualizations
   - Add saved search as table
   - Arrange for optimal monitoring
   - Save as "ApplyLens Email Analytics"

3. **Set Up Alerts** (Optional)
   - Alert on spike in offers (e.g., >10 in 1 hour)
   - Alert on sustained 5xx errors (e.g., >50 in 5 min)
   - Alert on rate limiting (e.g., >100 429s in 5 min)

4. **Export for Backup**
   - Once created, export visualizations
   - Store NDJSON in version control
   - Document any custom configurations

---

## Verification

### Verify Saved Search

```powershell
# Check that saved search exists
curl -s -X GET "http://localhost:5601/kibana/api/saved_objects/search/applylens-emails-discover-offers" `
  -H "kbn-xsrf: true" -u "elastic:elasticpass" | ConvertFrom-Json

# Expected: Object with title "ApplyLens — Emails (Offers & Interviews)"
```

### Verify in Kibana UI

1. Open Discover
2. Click saved searches dropdown
3. Confirm "ApplyLens — Emails (Offers & Interviews)" appears
4. Open it and verify query and columns

---

## Troubleshooting

### Saved Search Not Showing Data

**Issue:** No results in saved search  
**Cause:** No emails with `is_offer:true` or `is_interview:true` indexed yet  
**Solution:**
- Index sample emails via pipeline
- Verify pipeline detects offers/interviews correctly
- Adjust time range to match your data

### Cannot Access Kibana

**Issue:** 404 or connection refused  
**Cause:** Kibana not running or wrong URL  
**Solution:**
```powershell
# Check Kibana status
docker ps --filter "name=kibana"

# Check logs
docker logs applylens-kibana-prod --tail 50

# Verify URL includes /kibana base path
```

### Lens Visualization Shows No Data

**Issue:** Empty visualization after manual creation  
**Cause:** Time range, filter, or field mismatch  
**Solution:**
- Extend time range to "Last 90 days"
- Verify data view has required fields
- Remove query filter temporarily
- Check that data has been indexed

---

## Integration with Existing Infrastructure

### With Email Pipeline
- Saved search uses fields populated by `applylens_emails_v1` pipeline
- Requires `is_offer` and `is_interview` flags from pipeline
- Works with archived status from pipeline

### With Grafana Dashboard
- Complements Grafana's HTTP traffic monitoring
- Provides email-specific analytics
- Can combine in unified monitoring view

### With Prometheus Alerts
- Visualizations show same metrics as alerts
- Helps investigate alert triggers
- Provides context for anomalies

---

## Performance Considerations

### Data Volume
- Saved search queries data view directly
- Performance depends on index size
- Consider date filters for large datasets

### Lens Visualizations
- 5-minute intervals balance detail vs performance
- Aggregations cached by Elasticsearch
- Use longer intervals (1h, 1d) for historical views

### Optimization Tips
- Apply filters to reduce data scanned
- Use shorter time ranges for real-time views
- Consider rollup indices for long-term trends
- Enable field caching in data view

---

## Summary

| Component | Status | Action Required |
|-----------|--------|-----------------|
| Saved Search (Offers/Interviews) | ✅ Deployed | None - ready to use |
| Lens Viz (Email Analytics) | 📚 Guide Created | Manual creation (5 min) |
| Lens Viz (Traffic Status) | 📚 Guide Created | Manual creation (5 min) |
| Documentation | ✅ Complete | Reference as needed |

**Overall Status:** Saved search immediately available, comprehensive guide provided for creating Lens visualizations manually for optimal compatibility and reliability.

**Deployment Time:** ~2 minutes (saved search import)  
**Manual Creation Time:** ~10 minutes total (both Lens visualizations)  
**Total Effort:** ~12 minutes for complete setup

---

## Related Documentation

- [Kibana Setup Guide](./KIBANA_SETUP_2025-10-20.md) - Initial data view and saved search
- [Kibana Lens Visualizations Guide](./KIBANA_LENS_VISUALIZATIONS_2025-10-20.md) - Detailed creation instructions
- [Email Pipeline Setup](./EMAIL_PIPELINE_SETUP_2025-10-20.md) - Pipeline that populates data
- [Complete Infrastructure Summary](./COMPLETE_INFRASTRUCTURE_SUMMARY_2025-10-20.md) - Overall system architecture
- [Documentation Index](./DOC_INDEX.md) - All documentation

---

**Deployment Completed:** October 20, 2025  
**By:** GitHub Copilot  
**Status:** ✅ Saved Search Active | 📚 Creation Guide Available
