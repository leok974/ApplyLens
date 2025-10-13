# Phase-2 Automation Guide

Quick reference for running Phase-2 email categorization workflows using three different automation options.

---

## 🎯 Overview

Phase-2 provides three automation options for running the complete email categorization pipeline:

1. **Makefile** - For Unix/Linux/Mac users with GNU Make
2. **npm scripts** - Cross-platform Node.js scripting
3. **PowerShell** - Windows-native automation with rich output

All three options run the same underlying workflow:

```
ES → export_weak_labels.py → weak_labels.jsonl
  → train_ml.py → label_model.joblib
  → POST /labels/apply → ES (with categories)
```

---

## Option 1: Makefile (Unix/Linux/Mac)

### Prerequisites

- GNU Make installed
- Python 3.11+
- curl and jq (for API calls)

### Quick Start

```bash
# Run complete pipeline
make phase2-all

# Step by step
make export-weak
make train-labels
make apply-labels

# Show all available targets
make help
```

### Configuration (Override Defaults)

```bash
# Export more data
make export-weak EXPORT_DAYS=90 EXPORT_LIMIT=50000

# Use production API
make apply-labels API_BASE=https://api.applylens.app

# Custom output paths
make export-weak WEAK_JSONL=/data/my_labels.jsonl
make train-labels MODEL_OUT=/models/my_model.joblib
```

### Available Targets

- `make help` - Display all targets with descriptions
- `make export-weak` - Export weak labels from ES to JSONL
- `make train-labels` - Train ML model from JSONL
- `make apply-labels` - Apply labels to ES via API
- `make phase2-all` - Run entire pipeline (export → train → apply)
- `make clean-weak` - Remove exported JSONL file

### Default Configuration

```makefile
ES_URL        = http://localhost:9200
ES_INDEX      = emails_v1-000001
EXPORT_DAYS   = 60
EXPORT_LIMIT  = 40000
EXPORT_LPC    = 8000
WEAK_JSONL    = /tmp/weak_labels.jsonl
MODEL_OUT     = services/api/app/labeling/label_model.joblib
API_BASE      = http://localhost:8003
```

---

## Option 2: npm Scripts (Cross-Platform)

### Prerequisites

- Node.js 18+ and npm 9+
- Python 3.11+
- curl and jq (for stats)

### Quick Start

```bash
# Install dependencies
npm install

# Run complete pipeline
npm run phase2:all

# Step by step
npm run phase2:export
npm run phase2:train
npm run phase2:apply

# Show help
npm run phase2:help
```

### Available Scripts

- `npm run phase2:export` - Export weak labels from ES
- `npm run phase2:train` - Train ML model from JSONL
- `npm run phase2:apply` - Apply labels to ES docs
- `npm run phase2:stats` - Show label statistics
- `npm run phase2:profile` - Show profile summary
- `npm run phase2:all` - Run complete pipeline (export → train → apply → stats)
- `npm run phase2:clean` - Remove exported JSONL
- `npm run phase2:help` - Display all available scripts

### Configuration (via Environment Variables)

```bash
# Windows PowerShell
$env:ES_URL="http://localhost:9200"
$env:ES_EMAIL_INDEX="emails_v1-000001"
npm run phase2:export

# Unix/Linux/Mac
ES_URL=http://localhost:9200 ES_EMAIL_INDEX=emails_v1-000001 npm run phase2:export
```

### Default Configuration

- ES_URL: `http://localhost:9200`
- ES_EMAIL_INDEX: `emails_v1-000001`
- Export days: `60`
- Export limit: `40,000`
- Per-category limit: `8,000`
- Output: `/tmp/weak_labels.jsonl`
- Model: `services/api/app/labeling/label_model.joblib`
- API: `http://localhost:8003`

---

## Option 3: PowerShell (Windows)

### Prerequisites

- PowerShell 5.1+ or PowerShell Core 7+
- Python 3.11+
- Invoke-RestMethod (built-in)

### Quick Start

```powershell
# Run complete pipeline with default settings
.\scripts\phase2-all.ps1

# Custom parameters
.\scripts\phase2-all.ps1 -Days 90 -Limit 50000

# Production API
.\scripts\phase2-all.ps1 -ApiBase https://api.applylens.app

# Custom paths
.\scripts\phase2-all.ps1 -Weak "D:\data\weak_labels.jsonl" -Model "D:\models\label_model.joblib"
```

### Available Parameters

```powershell
-EsUrl      # Elasticsearch URL (default: http://localhost:9200)
-EsIndex    # ES index name (default: emails_v1-000001)
-Days       # Lookback window in days (default: 60)
-Limit      # Total export row cap (default: 40000)
-PerCat     # Per-category cap for balance (default: 8000)
-Weak       # Output JSONL path (default: C:\Windows\Temp\weak_labels.jsonl)
-Model      # Model output path (default: services/api/app/labeling/label_model.joblib)
-ApiBase    # API base URL (default: http://localhost:8003)
```

### Examples

```powershell
# Export last 30 days
.\scripts\phase2-all.ps1 -Days 30

# Large dataset export
.\scripts\phase2-all.ps1 -Limit 100000 -PerCat 20000

# Development environment
.\scripts\phase2-all.ps1 -EsUrl http://localhost:9200 -ApiBase http://localhost:8003

# Production environment
.\scripts\phase2-all.ps1 -EsUrl https://es.applylens.app -ApiBase https://api.applylens.app
```

### Output Features

- 🎨 Color-coded progress indicators
- 📊 Real-time statistics display
- ✅ Post-workflow verification
- 📈 Label distribution summary
- 👥 Top senders analysis
- 📝 Sample categorized document

---

## 🔍 Comparison Matrix

| Feature | Makefile | npm Scripts | PowerShell |
|---------|----------|-------------|------------|
| **Platform** | Unix/Linux/Mac | Cross-platform | Windows |
| **Prerequisites** | make, curl, jq | Node.js, npm | PowerShell 5.1+ |
| **Configuration** | CLI args | Env vars | CLI params |
| **Output Style** | Plain text | Plain text | Color-coded |
| **Verification** | Manual | Manual | Automatic |
| **Error Handling** | Exit codes | Exit codes | Try/catch |
| **API Calls** | curl | curl | Invoke-RestMethod |
| **Best For** | Unix developers | JS/Node devs | Windows users |

---

## 🚀 Recommended Usage

### First-Time Setup

Use **PowerShell** (Windows) or **npm** (Mac/Linux) for rich output and verification:

```powershell
# Windows
.\scripts\phase2-all.ps1

# Mac/Linux
npm run phase2:all
```

### Automated CI/CD Pipelines

Use **Makefile** or **npm** for simplicity and portability:

```bash
# CI/CD with Makefile
make phase2-all

# CI/CD with npm
npm run phase2:all
```

### Development Iteration

Use **Makefile** targets for quick experimentation:

```bash
# Just retrain model
make train-labels

# Just apply labels
make apply-labels
```

### Production Deployment

Use **PowerShell** with custom parameters:

```powershell
.\scripts\phase2-all.ps1 `
  -EsUrl https://es.prod.applylens.app `
  -ApiBase https://api.prod.applylens.app `
  -Days 90 `
  -Limit 100000
```

---

## 📊 Expected Output

### Makefile

```
>> Exporting weak labels to /tmp/weak_labels.jsonl
{"seen":15234,"written":12500,"by_category":{"promo":3201,"newsletter":4892,...}}

>> Training label model
✅ Saved model to label_model.joblib

              precision    recall  f1-score   support
        bill       0.95      0.92      0.93      1543
  newsletter       0.91      0.94      0.93      4892
       promo       0.88      0.85      0.87      3201

>> Applying labels to ES
{"updated":15234}

✅ Phase-2 pipeline finished
```

### npm Scripts

```
> npm run phase2:all

> phase2:all
> npm run phase2:export && npm run phase2:train && npm run phase2:apply && npm run phase2:stats

> phase2:export
{"seen":15234,"written":12500,"by_category":{...}}

> phase2:train
✅ Saved model to label_model.joblib

> phase2:apply
{"updated":15234}

> phase2:stats
{
  "by_category": [
    {"key": "newsletter", "count": 4892},
    {"key": "promo", "count": 3201},
    {"key": "recruiting", "count": 987},
    {"key": "bill", "count": 1543}
  ]
}
```

### PowerShell

```
🎯 Phase 2 - Email Categorization Pipeline
==========================================

📊 Configuration:
   ES URL: http://localhost:9200
   ES Index: emails_v1-000001
   Lookback: 60 days
   ...

>> Phase 1: Exporting weak labels
   Exporting to: C:\Windows\Temp\weak_labels.jsonl
   {"seen":15234,"written":12500,"by_category":{"promo":3201,...}}

>> Phase 2: Training model
   Training from: C:\Windows\Temp\weak_labels.jsonl (2.4 MB)
   ✅ Saved model to label_model.joblib

>> Phase 3: Applying labels
   Calling: http://localhost:8003/labels/apply
   ✅ Labels applied: 15234 documents updated

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📈 Verification Results
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Label Statistics:
   promo: 3201
   newsletter: 4892
   recruiting: 987
   bill: 1543

Profile Summary:
   Categories:
      newsletter: 4892 emails
      promo: 3201 emails
   
   Top Senders:
      example.com (523 emails)
      newsletter.example.com (421 emails)

✅ Phase 2 pipeline complete!
```

---

## 🛠️ Troubleshooting

### Issue: `make: command not found`

**Solution:** Use npm scripts or PowerShell instead:

```bash
npm run phase2:all
```

### Issue: `curl: command not found`

**Solution:**

- **Windows**: Use PowerShell option (uses Invoke-RestMethod)
- **Mac**: Install curl: `brew install curl`
- **Linux**: Install curl: `apt install curl` or `yum install curl`

### Issue: `jq: command not found`

**Solution:**

- **Windows**: Use PowerShell option (parses JSON natively)
- **Mac**: Install jq: `brew install jq`
- **Linux**: Install jq: `apt install jq` or `yum install jq`

### Issue: `cross-env: command not found`

**Solution:** Install npm dependencies:

```bash
npm install
```

### Issue: PowerShell execution policy error

**Solution:** Allow script execution:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Issue: Python module not found

**Solution:** Install Python dependencies:

```bash
cd services/api
pip install -e .
# or
poetry install
```

### Issue: ES connection refused

**Solution:** Start Elasticsearch:

```bash
docker-compose up -d elasticsearch
```

### Issue: API returns 404

**Solution:** Ensure API is running on correct port:

```bash
# Check if API is running
curl http://localhost:8003/health

# Update ApiBase parameter
.\scripts\phase2-all.ps1 -ApiBase http://localhost:8003
```

---

## 📋 Pre-Flight Checklist

Before running Phase-2 automation, verify:

- [ ] Elasticsearch is running (`curl http://localhost:9200`)
- [ ] API service is running (`curl http://localhost:8003/health`)
- [ ] ES index exists (`curl http://localhost:9200/emails_v1-000001`)
- [ ] Gmail backfill has populated data
- [ ] Python environment has all dependencies
- [ ] Sufficient disk space for JSONL export (~100MB per 50k emails)
- [ ] Write permissions to output directories

### Quick Verification Commands

**Makefile:**

```bash
make -v                # Check GNU Make version
python --version       # Check Python version
curl --version         # Check curl
jq --version          # Check jq
```

**npm:**

```bash
node --version         # Check Node.js version
npm --version          # Check npm version
python --version       # Check Python version
```

**PowerShell:**

```powershell
$PSVersionTable        # Check PowerShell version
python --version       # Check Python version
Test-NetConnection -ComputerName localhost -Port 9200  # Check ES
Test-NetConnection -ComputerName localhost -Port 8003  # Check API
```

---

## 🎯 Next Steps

After running Phase-2 automation:

1. **Verify Results**

   ```bash
   # Makefile/npm
   curl "http://localhost:8003/labels/stats" | jq
   
   # PowerShell
   Invoke-RestMethod -Uri "http://localhost:8003/labels/stats"
   ```

2. **Inspect Categorized Emails**

   ```bash
   curl "http://localhost:9200/emails_v1-000001/_search?q=category:promo" | jq
   ```

3. **View in Kibana**
   - Open: <http://localhost:5601>
   - Query: `category:promo AND expires_at:>now`

4. **Integrate with UI**
   - Add category filter to Inbox component
   - Display expires_at countdown
   - Show confidence badges

5. **Iterate on Model**
   - Collect user feedback
   - Re-export with updated rules
   - Retrain with larger dataset
   - Re-apply labels

---

## 📚 Related Documentation

- **API Reference**: `PHASE_2_IMPLEMENTATION.md`
- **Implementation Details**: `PHASE_2_COMPLETE.md`
- **Workflow Guide**: `PHASE_2_WORKFLOW.md`
- **Testing**: `scripts/test-phase2-endpoints.ps1`

---

**Last Updated**: 2025-10-11  
**Phase**: Phase-2 Complete  
**Automation Options**: 3 (Makefile, npm, PowerShell)
