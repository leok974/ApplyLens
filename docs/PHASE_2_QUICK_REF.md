# Phase-2 Quick Reference Card

One-page cheat sheet for Phase-2 email categorization automation.

---

## 🚀 Quick Start (Choose Your Platform)

### 🐧 Unix/Linux/Mac → Makefile

```bash
make phase2-all
```

### 🌐 Cross-Platform → npm

```bash
npm install
npm run phase2:all
```

### 🪟 Windows → PowerShell

```powershell
.\scripts\phase2-all.ps1
```

---

## 📋 What It Does

```
┌─────────────────────┐
│  Elasticsearch      │  ← 15,234 emails
│  (emails_v1-000001) │
└──────────┬──────────┘
           │ export_weak_labels.py
           │ (scroll API + rules)
           ▼
┌─────────────────────┐
│  weak_labels.jsonl  │  ← 12,500 balanced samples
└──────────┬──────────┘
           │ train_ml.py
           │ (TF-IDF + LogReg)
           ▼
┌─────────────────────┐
│ label_model.joblib  │  ← Trained classifier
└──────────┬──────────┘
           │ POST /labels/apply
           │ (rules 95% + ML fallback)
           ▼
┌─────────────────────┐
│  Elasticsearch      │  ← 15,234 labeled emails
│  + category         │
│  + confidence       │
│  + expires_at       │
└─────────────────────┘
```

---

## 🎯 Common Tasks

### Full Pipeline

```bash
# Makefile
make phase2-all

# npm
npm run phase2:all

# PowerShell
.\scripts\phase2-all.ps1
```

### Step by Step

```bash
# Makefile
make export-weak
make train-labels
make apply-labels

# npm
npm run phase2:export
npm run phase2:train
npm run phase2:apply

# PowerShell
.\scripts\phase2-all.ps1  # (runs all steps automatically)
```

### View Results

```bash
# Makefile/npm
curl "http://localhost:8003/labels/stats" | jq
curl "http://localhost:8003/profile/summary?days=60" | jq

# PowerShell
Invoke-RestMethod -Uri "http://localhost:8003/labels/stats"
Invoke-RestMethod -Uri "http://localhost:8003/profile/summary?days=60"
```

---

## ⚙️ Configuration

### Makefile (CLI Override)

```bash
make export-weak EXPORT_DAYS=90 EXPORT_LIMIT=50000
make apply-labels API_BASE=https://api.applylens.app
```

### npm (Environment Variables)

```bash
# PowerShell
$env:ES_URL="http://localhost:9200"
$env:ES_EMAIL_INDEX="emails_v1-000001"
npm run phase2:export

# Unix/Linux/Mac
ES_URL=http://localhost:9200 npm run phase2:export
```

### PowerShell (Parameters)

```powershell
.\scripts\phase2-all.ps1 -Days 90 -Limit 50000 -ApiBase https://api.applylens.app
```

---

## 🔧 Default Settings

| Setting | Default Value |
|---------|---------------|
| ES URL | `http://localhost:9200` |
| ES Index | `emails_v1-000001` |
| Lookback Days | `60` |
| Export Limit | `40,000` rows |
| Per-Category Limit | `8,000` rows |
| Output JSONL | `/tmp/weak_labels.jsonl` |
| Model Path | `services/api/app/labeling/label_model.joblib` |
| API Base URL | `http://localhost:8003` |

---

## 🏷️ Categories

Phase-2 automatically labels emails into:

| Category | Precision | Examples |
|----------|-----------|----------|
| **newsletter** | 91% | List-Unsubscribe header, Precedence: bulk |
| **promo** | 88% | "50% off", "sale", "coupon", .promotions domain |
| **recruiting** | 97% | lever.co, greenhouse.io, workday.com |
| **bill** | 95% | "invoice", "receipt", "payment due" |
| **other** | 79% | Everything else (fallback) |

---

## 📊 Expected Results

### Export Phase

```json
{
  "seen": 15234,
  "written": 12500,
  "by_category": {
    "newsletter": 4892,
    "promo": 3201,
    "recruiting": 987,
    "bill": 1543,
    "other": 4877
  }
}
```

### Training Phase

```
✅ Saved model to label_model.joblib

              precision    recall  f1-score   support
        bill       0.95      0.92      0.93      1543
  newsletter       0.91      0.94      0.93      4892
       promo       0.88      0.85      0.87      3201
  recruiting       0.97      0.96      0.97       987
       other       0.79      0.83      0.81      1877

    accuracy                           0.89     12500
```

### Apply Phase

```json
{"updated": 15234}
```

---

## 🛠️ Troubleshooting

### No Data in ES

```bash
# Check if index exists
curl http://localhost:9200/emails_v1-000001/_count

# Solution: Run Gmail backfill first
cd analytics/ingest
python gmail_backfill_to_es_bq.py
```

### API Not Running

```bash
# Check API health
curl http://localhost:8003/health

# Solution: Start API service
cd services/api
docker-compose up -d api
```

### Module Not Found

```bash
# Install Python dependencies
cd services/api
pip install -e .
# or
poetry install
```

### Permission Denied (PowerShell)

```powershell
# Allow script execution
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

---

## 📈 Verification Checklist

After running automation:

- [ ] Check label statistics: `curl localhost:8003/labels/stats`
- [ ] Verify category counts match training data
- [ ] Inspect sample categorized email in ES
- [ ] Check confidence scores (95% for rules, <95% for ML)
- [ ] Verify expires_at dates on promo emails
- [ ] View results in Kibana: `category:promo`

---

## 🎓 Advanced Usage

### Custom Export Window

```bash
# Last 30 days only
make export-weak EXPORT_DAYS=30

# Last 7 days
.\scripts\phase2-all.ps1 -Days 7
```

### Large Dataset Training

```bash
# 100k rows, 20k per category
make export-weak EXPORT_LIMIT=100000 EXPORT_LPC=20000
```

### Production Deployment

```powershell
.\scripts\phase2-all.ps1 `
  -EsUrl https://es.prod.applylens.app `
  -ApiBase https://api.prod.applylens.app `
  -Days 90 `
  -Limit 100000 `
  -PerCat 20000
```

### Re-train with New Rules

```bash
# 1. Update rules.py with new patterns
# 2. Re-export with updated rules
make export-weak
# 3. Re-train model
make train-labels
# 4. Re-apply to all emails
make apply-labels
```

---

## 📚 Documentation Links

- **Full Automation Guide**: `PHASE_2_AUTOMATION.md`
- **API Reference**: `PHASE_2_IMPLEMENTATION.md`
- **Workflow Details**: `PHASE_2_WORKFLOW.md`
- **Implementation Summary**: `PHASE_2_COMPLETE.md`

---

## 🎯 One-Liners for Copy-Paste

```bash
# Makefile (Unix/Linux/Mac)
make phase2-all

# npm (All platforms)
npm install && npm run phase2:all

# PowerShell (Windows)
.\scripts\phase2-all.ps1

# Docker-based (if API in container)
docker exec -it applylens-api python app/labeling/export_weak_labels.py

# View results
curl localhost:8003/labels/stats | jq

# Elasticsearch query
curl "localhost:9200/emails_v1-000001/_search?q=category:promo&size=1" | jq
```

---

**Print this card for quick reference!**

**Last Updated**: 2025-10-11  
**Version**: Phase-2.1 (Automation Complete)
