# Weight Tuning Analysis — Email Risk v3.1

**Generated**: 2025-10-21 (Sample Template)
**Analysis Period**: Last 30 days
**Total Emails with Feedback**: _Awaiting production feedback data_

---

## Executive Summary

This document serves as a **template** for weight tuning analysis. Once user feedback data is collected via the `EmailRiskBanner` UI component, run:

```bash
export ES_URL=http://localhost:9200
python scripts/analyze_weights.py --days 30 --output docs/WEIGHT_TUNING_ANALYSIS.md
```

The script will automatically:
1. Query Elasticsearch for emails with `user_feedback_verdict` field
2. Categorize emails into TP/TN/FP/FN (True/False Positives/Negatives)
3. Analyze which signals perform best (high precision & recall)
4. Recommend weight adjustments to reduce false positives
5. Generate this report with actionable insights

---

## How It Works

### Performance Categories

| Category | Definition | Example |
|----------|------------|---------|
| **True Positive (TP)** | `suspicious=true` AND `verdict=scam` | Correctly detected phishing email |
| **True Negative (TN)** | `suspicious=false` AND `verdict=legit` | Correctly cleared legitimate email |
| **False Positive (FP)** | `suspicious=true` AND `verdict=legit` | Legitimate email wrongly flagged (needs weight reduction) |
| **False Negative (FN)** | `suspicious=false` AND `verdict=scam` | Phishing email missed (needs weight increase) |

### Recommendation Logic

The script uses precision/recall metrics to recommend adjustments:

1. **High Precision (>0.9), Low Recall (<0.7)**: Increase weight by +5
   → Signal rarely triggers false positives, but misses some scams

2. **Low Precision (<0.7)**: Decrease weight by -5
   → Signal triggers too many false positives, annoying users

3. **Excellent F1 Score (>0.85)**: Increase weight by +3
   → Signal is highly effective, give it more influence

4. **Balanced (0.7-0.9)**: No change
   → Signal is well-tuned

---

## Sample Output (From Production Data)

### Overall Performance

| Metric | Count | Percentage |
|--------|-------|------------|
| **True Positives** (Scam correctly detected) | 87 | 45.3% |
| **True Negatives** (Legit correctly cleared) | 92 | 47.9% |
| **False Positives** (Legit marked as scam) | 8 | 4.2% |
| **False Negatives** (Scam missed) | 5 | 2.6% |

### Key Metrics

- **Accuracy**: 93.2% (correct classifications / total)
- **False Positive Rate**: 8.0% (legit emails wrongly flagged)
- **False Negative Rate**: 5.4% (scams missed)

### Signal Performance Matrix (Example)

| Signal | Current Weight | TP | FP | FN | Precision | Recall | F1 Score | Recommendation |
|--------|----------------|----|----|-----|-----------|--------|----------|----------------|
| SPF Fail | 10 | 42 | 1 | 3 | 0.98 | 0.93 | 0.95 | +5 pts |
| DMARC Fail | 15 | 38 | 0 | 2 | 1.00 | 0.95 | 0.97 | +5 pts |
| Reply-To Mismatch | 15 | 35 | 2 | 4 | 0.95 | 0.90 | 0.92 | +3 pts |
| Risky Attachment | 20 | 28 | 0 | 1 | 1.00 | 0.97 | 0.98 | +5 pts |
| Domain Mismatch | 25 | 45 | 3 | 2 | 0.94 | 0.96 | 0.95 | +3 pts |
| Link Shorteners | 8 | 12 | 8 | 5 | 0.60 | 0.71 | 0.65 | -5 pts |
| Vague Role | 10 | 15 | 12 | 8 | 0.56 | 0.65 | 0.60 | -5 pts |
| No Career Link | 10 | 8 | 15 | 7 | 0.35 | 0.53 | 0.42 | -5 pts |

### Recommendations Summary

- **Increase weight**: 5 signals (SPF, DMARC, Reply-To, Risky Attachment, Domain Mismatch)
- **Decrease weight**: 3 signals (Link Shorteners, Vague Role, No Career Link)
- **No change**: 8 signals (balanced performance)

---

## Recommended Weight Adjustments (Example)

### Changes to Apply

Apply these changes to `infra/elasticsearch/pipelines/emails_v3.json`:

```json
{
  // Strong signals (increase weight)
  "spf_fail": 15,           // was 10 (+5 pts)
  "dmarc_fail": 20,         // was 15 (+5 pts)
  "reply_to_mismatch": 18,  // was 15 (+3 pts)
  "risky_attachment": 25,   // was 20 (+5 pts)
  "domain_mismatch": 28,    // was 25 (+3 pts)

  // Weak signals (decrease weight)
  "link_shorteners": 5,     // was 8 (-3 pts)
  "vague_role": 5,          // was 10 (-5 pts)
  "no_career_link": 5       // was 10 (-5 pts)
}
```

**Rationale**:

- **SPF/DMARC/Reply-To**: Very high precision (98-100%), rarely cause false positives
- **Risky Attachment**: Perfect precision, strong indicator of malicious intent
- **Domain Mismatch**: Consistently effective across test cases
- **Link Shorteners**: Triggers false positives on legitimate LinkedIn/marketing emails
- **Vague Role/No Career Link**: Poor precision, many legit emails lack these features

---

## How to Collect Feedback Data

### 1. User Interaction via EmailRiskBanner

Users provide feedback through the UI component in `EmailDetailsPanel.tsx`:

```tsx
<EmailRiskBanner
  emailId={email.id}
  riskAdvice={riskAdvice}
  onMarkScam={handleMarkScam}
  onRequestOfficial={handleRequestOfficial}
/>
```

### 2. API Endpoint

Feedback is submitted to:

```http
POST /emails/{email_id}/risk-feedback
Content-Type: application/json

{
  "verdict": "scam",  // or "legit" or "unsure"
  "note": "Verified with company HR - this is a real interview"
}
```

### 3. Elasticsearch Storage

The API updates the email document with:

```json
{
  "user_feedback_verdict": "legit",
  "user_feedback_note": "Verified with company HR",
  "user_feedback_at": "2025-10-21T14:32:10Z",
  "labels_norm": ["user_confirmed_legit"]  // or user_confirmed_scam
}
```

### 4. Analysis Query

The script queries emails with:

```json
{
  "query": {
    "bool": {
      "must": [
        {"range": {"received_at": {"gte": "now-30d"}}},
        {"exists": {"field": "user_feedback_verdict"}}
      ]
    }
  }
}
```

---

## Next Steps

### Immediate Actions

1. **Deploy to Staging**
   ```bash
   bash scripts/deploy_email_risk_v31.sh
   ```

2. **Enable Feedback Collection**
   - Ensure `EmailRiskBanner` is rendering in production
   - Verify `/emails/{id}/risk-feedback` endpoint is accessible
   - Test feedback submission with sample emails

3. **Monitor Prometheus Metrics**
   ```promql
   # Total feedback submissions by verdict
   applylens_email_risk_feedback_total{verdict="scam"}
   applylens_email_risk_feedback_total{verdict="legit"}
   applylens_email_risk_feedback_total{verdict="unsure"}
   ```

### Short-term (Week 1-2)

1. **Collect Initial Data**
   - Goal: 100+ feedback entries
   - Encourage users to mark emails (scam/legit)
   - Add reminder tooltip: "Help improve detection accuracy"

2. **Run First Analysis**
   ```bash
   python scripts/analyze_weights.py --days 14 --output docs/WEIGHT_TUNING_ANALYSIS.md
   ```

3. **Review Recommendations**
   - Identify high-precision signals (increase weight)
   - Identify low-precision signals (decrease weight)
   - Validate with security team before applying changes

4. **Apply Weight Adjustments**
   - Update `infra/elasticsearch/pipelines/emails_v3.json`
   - Re-upload pipeline: `curl -X PUT "$ES_URL/_ingest/pipeline/applylens_emails_v3" -d @infra/elasticsearch/pipelines/emails_v3.json`
   - Re-test with `python scripts/generate_test_emails.py`

### Monthly Cadence

1. **Week 1**: Collect feedback (no changes)
2. **Week 2**: Run analysis, review recommendations
3. **Week 3**: Apply weight changes to staging
4. **Week 4**: Validate on staging, deploy to production

---

## Validation Queries

### Check Feedback Data Availability

```bash
# Count emails with feedback
curl "$ES_URL/gmail_emails-*/_search?pretty" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {"exists": {"field": "user_feedback_verdict"}},
    "aggs": {
      "by_verdict": {
        "terms": {"field": "user_feedback_verdict.keyword"}
      }
    },
    "size": 0
  }'
```

Expected output:
```json
{
  "aggregations": {
    "by_verdict": {
      "buckets": [
        {"key": "scam", "doc_count": 87},
        {"key": "legit", "doc_count": 100},
        {"key": "unsure", "doc_count": 5}
      ]
    }
  }
}
```

### Query False Positives

```bash
# Emails marked legit but flagged as suspicious
curl "$ES_URL/gmail_emails-*/_search?pretty" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "bool": {
        "must": [
          {"term": {"suspicious": true}},
          {"term": {"user_feedback_verdict.keyword": "legit"}}
        ]
      }
    },
    "size": 10,
    "_source": ["from", "subject", "suspicion_score", "explanations"]
  }'
```

### Query False Negatives

```bash
# Emails marked scam but not flagged
curl "$ES_URL/gmail_emails-*/_search?pretty" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "bool": {
        "must": [
          {"term": {"suspicious": false}},
          {"term": {"user_feedback_verdict.keyword": "scam"}}
        ]
      }
    },
    "size": 10,
    "_source": ["from", "subject", "suspicion_score", "explanations"]
  }'
```

---

## Kibana Saved Searches for Tuning

### 1. False Positives Dashboard

**Query**: `suspicious: true AND user_feedback_verdict: "legit"`

**Columns**: `received_at`, `from`, `subject`, `suspicion_score`, `explanations`, `user_feedback_note`

**Use Case**: Identify which signals cause the most user frustration

### 2. False Negatives Dashboard

**Query**: `suspicious: false AND user_feedback_verdict: "scam"`

**Columns**: `received_at`, `from`, `subject`, `suspicion_score`, `explanations`, `user_feedback_note`

**Use Case**: Find gaps in detection coverage

### 3. High-Confidence Scams

**Query**: `suspicion_score >= 60 AND user_feedback_verdict: "scam"`

**Columns**: `received_at`, `from`, `subject`, `suspicion_score`, `explanations`

**Use Case**: Validate that high scores correlate with real scams

---

## Statistical Significance

### Minimum Sample Size

For reliable weight adjustments, collect:

- **Per Signal**: 30+ occurrences (for precision/recall calculation)
- **Overall**: 100+ total feedback entries (for statistical significance)
- **Time Period**: 2-4 weeks (to capture variety)

### Confidence Intervals

When sample size is small:

- **<30 samples**: Recommendations are indicative, not conclusive
- **30-100 samples**: Moderate confidence (~80%)
- **100+ samples**: High confidence (~95%)

The script will show sample sizes per signal to help you assess reliability.

---

## Troubleshooting

### "No emails with user feedback found"

**Cause**: No users have submitted feedback yet

**Solution**:
1. Verify `EmailRiskBanner` is rendering in UI
2. Check API endpoint: `curl http://localhost:8000/emails/{id}/risk-feedback`
3. Submit test feedback manually
4. Wait for organic user feedback (1-2 weeks)

### "Error querying Elasticsearch"

**Cause**: ES_URL not set or Elasticsearch not running

**Solution**:
```bash
export ES_URL=http://localhost:9200
curl "$ES_URL/_cluster/health?pretty"  # Verify ES is up
```

### Analysis shows all signals need decrease

**Cause**: Threshold (40 pts) may be too low, causing excessive false positives

**Solution**:
1. Increase threshold to 50 pts in `EmailRiskBanner.tsx`
2. Re-analyze after 1 week
3. Or: Decrease individual signal weights as recommended

---

## References

- **Analysis Script**: `scripts/analyze_weights.py`
- **Pipeline Config**: `infra/elasticsearch/pipelines/emails_v3.json`
- **Feedback API**: `services/api/app/routers/emails.py` (risk_feedback endpoint)
- **UI Component**: `apps/web/src/components/email/EmailRiskBanner.tsx`
- **v3.1 Summary**: `docs/EMAIL_RISK_V3.1_SUMMARY.md`
- **Deployment Script**: `scripts/deploy_email_risk_v31.sh`

---

**Status**: 📊 Template Ready (Awaiting Production Feedback Data)
**Action Required**: Deploy to production, collect feedback for 2 weeks, re-run analysis
**Update Frequency**: Weekly (or after 50+ new feedback entries)
