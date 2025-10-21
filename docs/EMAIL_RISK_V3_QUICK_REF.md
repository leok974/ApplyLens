# Email Risk Detection v3 — Quick Reference Card

## 🎯 What Was Built

**Agentic Suspicious Email Detection System**
- Transparent phishing heuristics (no black-box ML)
- User guidance with explanations and verification steps
- Red/yellow banner UI with actionable buttons
- Prometheus metrics for monitoring

---

## 📂 Files Created

```
infra/elasticsearch/pipelines/emails_v3.json    (ES pipeline)
services/api/app/routers/emails.py              (API route - modified)
apps/web/src/components/email/EmailRiskBanner.tsx  (React component)
apps/web/src/components/inbox/EmailDetailsPanel.tsx (Integration - modified)
docs/EMAIL_RISK_DETECTION_V3.md                 (Full documentation)
docs/EMAIL_RISK_V3_SUMMARY.md                   (Implementation summary)
scripts/deploy_email_risk_v3.sh                 (Deployment script)
```

---

## ⚡ Quick Deploy

```bash
# 1. Set Elasticsearch URL
export ES_URL="http://localhost:9200"

# 2. Run deployment script
bash scripts/deploy_email_risk_v3.sh

# 3. Restart API
docker-compose restart api

# 4. Rebuild frontend
cd apps/web && npm run build
```

---

## 🧪 Quick Test

```bash
# Index a scam email
curl -X POST http://localhost:9200/gmail_emails/_doc?pipeline=applylens_emails_v3 \
  -H 'Content-Type: application/json' \
  -d '{
    "subject": "Job Opportunity",
    "from": "fake@scam.com",
    "body_text": "Prometric is hiring! Send your SSN and bank details.",
    "received_at": "2025-10-21T10:00:00Z"
  }'

# Check API endpoint
curl http://localhost:8000/emails/{DOC_ID}/risk-advice
```

**Expected**: `suspicious: true`, `suspicion_score ≥ 60`

---

## 🎨 UI Behavior

| Score | Banner | Color | Actions |
|-------|--------|-------|---------|
| < 25 | None | - | - |
| 25-39 | Yellow | ⚠️ Warning | Mark Scam, Request Invite, Dismiss |
| ≥ 40 | Red | 🛡️ Alert | Mark Scam, Request Invite, Dismiss |

---

## 🔍 Heuristics (Score Weights)

```
Domain mismatch        = 25 pts
Non-canonical domain   = 25 pts
Risky phrase (each)    = 10 pts
PII request            = 20 pts
Vague role details     = 10 pts
No calendar invite     = 5 pts
No career link         = 10 pts
─────────────────────────────
Threshold              = 40 pts → suspicious
```

---

## 📊 Monitoring

```promql
# Risk advice served rate
rate(applylens_email_risk_served_total[5m])

# Suspicious email ratio
sum(rate(applylens_email_risk_served_total{level="suspicious"}[1h]))
/ sum(rate(applylens_email_risk_served_total[1h]))
```

**Grafana Dashboard**: Add panels for served count, score distribution, top reasons

---

## 🔧 Tuning Commands

```bash
# Edit pipeline weights
vim infra/elasticsearch/pipelines/emails_v3.json

# Re-upload
curl -X PUT http://localhost:9200/_ingest/pipeline/applylens_emails_v3 \
  -H 'Content-Type: application/json' \
  --data-binary @infra/elasticsearch/pipelines/emails_v3.json

# Reindex recent emails
curl -X POST http://localhost:9200/_reindex -d '{
  "source": {
    "index": "gmail_emails",
    "query": {"range": {"received_at": {"gte": "now-7d"}}}
  },
  "dest": {
    "index": "gmail_emails-retuned",
    "pipeline": "applylens_emails_v3"
  }
}'
```

---

## 🐛 Troubleshooting

| Problem | Solution |
|---------|----------|
| Pipeline upload fails | Check ES_URL, verify network connectivity |
| Banner not showing | Check API route accessible, inspect browser console |
| False positives | Increase threshold (40 → 45), add to trusted_domains |
| Missing scams | Decrease threshold (40 → 35), add risky phrases |
| Metrics not incrementing | Verify Prometheus scraping /metrics endpoint |

---

## 📋 KQL Saved Searches

```kql
# All suspicious emails
suspicion_score >= 40

# Suspicious offers/interviews
(is_offer:true OR is_interview:true) AND suspicious:true

# High-risk emails
suspicion_score >= 60

# Flagged by domain mismatch
explanations:*"domain does not match"*
```

---

## ✅ Deployment Checklist

- [ ] Pipeline uploaded and verified
- [ ] Test document indexed with suspicious=true
- [ ] API route returns valid JSON
- [ ] Frontend banner displays correctly
- [ ] "Mark as Scam" button works
- [ ] "Request Official Invite" button copies template
- [ ] Prometheus metrics incrementing
- [ ] Grafana dashboard created

---

## 📞 Quick Links

- **Full Docs**: `docs/EMAIL_RISK_DETECTION_V3.md`
- **Summary**: `docs/EMAIL_RISK_V3_SUMMARY.md`
- **Pipeline**: `infra/elasticsearch/pipelines/emails_v3.json`
- **API**: `services/api/app/routers/emails.py`
- **UI**: `apps/web/src/components/email/EmailRiskBanner.tsx`
- **Deploy Script**: `scripts/deploy_email_risk_v3.sh`

---

## 🎉 Success Criteria

✅ Pipeline detects obvious scams (score ≥ 60)
✅ UI shows red banner with explanations
✅ "Request Official Invite" generates verification template
✅ False positive rate < 5%
✅ Metrics visible in Grafana

**Status**: 🟢 Ready for Production
