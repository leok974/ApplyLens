# Active Learning Runbook

## Table of Contents

1. [Daily Operations](#daily-operations)
2. [Deploying a New Bundle](#deploying-a-new-bundle)
3. [Handling Regressions](#handling-regressions)
4. [Manual Interventions](#manual-interventions)
5. [Incident Response](#incident-response)
6. [Monitoring & Alerts](#monitoring--alerts)

---

## Daily Operations

### 1. Check Labeled Data Pipeline

**Frequency**: Daily at 9 AM

```bash
# SSH into API server
ssh api-prod

# Check labeled data stats
curl -X GET http://localhost:8000/api/active/stats/labeled

# Expected output:
# {
#   "total": 1250,
#   "by_source": {"approvals": 450, "feedback": 600, "gold": 200},
#   "by_agent": {"inbox_triage": 700, "insights_writer": 350, "knowledge_update": 200},
#   "recent_7d": 180
# }
```

**Red Flags**:
- `recent_7d` < 50: Low incoming data, may need more human feedback
- Any agent with <100 total examples: Not enough for training

**Action**: If data is low, encourage users to:
- Approve/reject more agent decisions
- Provide thumbs up/down feedback
- Create more golden tasks

### 2. Review Pending Bundle Approvals

**Frequency**: Daily at 10 AM

```bash
# List pending approvals
curl -X GET http://localhost:8000/api/active/approvals/pending

# Expected output:
# [
#   {
#     "id": "approval-123",
#     "agent": "inbox_triage",
#     "bundle_id": "inbox_triage_20240115_100000",
#     "diff": {
#       "changes": [{"param": "risk_score_threshold", "old": 70.0, "new": 65.0, "delta": -5.0}],
#       "accuracy_delta": 0.03
#     },
#     "requested_by": "system",
#     "created_at": "2024-01-15T10:00:00Z"
#   }
# ]
```

**Decision Criteria**:
- ✅ Approve if:
  - `accuracy_delta` > 0.02 (2% improvement)
  - `training_count` ≥ 100
  - Threshold changes are reasonable (not extreme)

- ❌ Reject if:
  - `accuracy_delta` < 0 (worse performance)
  - `training_count` < 50 (insufficient data)
  - Thresholds are extreme (e.g., risk_score_threshold < 30 or > 90)

```bash
# Approve bundle
curl -X POST http://localhost:8000/api/active/approvals/approval-123/approve \
  -H "Content-Type: application/json" \
  -d '{"approver": "ops_lead", "rationale": "3% accuracy improvement, looks good"}'

# Reject bundle (if needed)
curl -X POST http://localhost:8000/api/active/approvals/approval-123/reject \
  -H "Content-Type: application/json" \
  -d '{"rejector": "ops_lead", "rationale": "Insufficient training data"}'
```

### 3. Monitor Active Canaries

**Frequency**: Daily at 11 AM

```bash
# List active canaries
curl -X GET http://localhost:8000/api/active/canaries/active

# Expected output:
# [
#   {
#     "agent": "inbox_triage",
#     "canary_percent": 10,
#     "deployed_at": "2024-01-14T10:00:00Z",
#     "hours_running": 25,
#     "performance": {
#       "quality_delta": 0.01,
#       "latency_delta": -0.05,
#       "recommendation": "monitor"
#     }
#   }
# ]
```

**Red Flags**:
- `recommendation`: "rollback" → Immediate action required
- `hours_running` > 72 and `recommendation`: "monitor" → Stalled, manual decision needed

**Action**:
- If `recommendation`: "promote" → Check diff, then promote
- If `recommendation`: "rollback" → Investigate, then rollback
- If stuck in "monitor" for >72h → Manually promote or rollback

### 4. Check Judge Weights

**Frequency**: Weekly (Mondays at 9 AM)

```bash
# Get judge weights for all agents
curl -X GET http://localhost:8000/api/active/weights

# Expected output:
# {
#   "inbox_triage": {"gpt-4": 0.82, "gpt-3.5-turbo": 0.58, "claude-3-opus": 0.79},
#   "insights_writer": {"gpt-4": 0.85, "claude-3-sonnet": 0.71}
# }
```

**Red Flags**:
- Any weight < 0.3: Judge is performing poorly, consider removing
- Sudden drops (>0.2 in a week): Investigate calibration issues

**Action**: If weights are concerning, review judge prompts and configurations

---

## Deploying a New Bundle

### Step 1: Train Bundle

```bash
# Trigger bundle creation
curl -X POST http://localhost:8000/api/active/bundles/create \
  -H "Content-Type: application/json" \
  -d '{
    "agent": "inbox_triage",
    "min_examples": 50,
    "model_type": "logistic"
  }'

# Response:
# {
#   "bundle_id": "inbox_triage_20240115_140000",
#   "training_count": 120,
#   "accuracy": 0.87,
#   "thresholds": {"risk_score_threshold": 65.0, "spf_dkim_weight": 1.5}
# }
```

### Step 2: Propose for Approval

```bash
# Create approval request
curl -X POST http://localhost:8000/api/active/bundles/propose \
  -H "Content-Type: application/json" \
  -d '{
    "agent": "inbox_triage",
    "bundle_id": "inbox_triage_20240115_140000",
    "proposer": "admin"
  }'

# Response:
# {"approval_id": "approval-456"}
```

### Step 3: Review and Approve

```bash
# Get approval details
curl -X GET http://localhost:8000/api/active/approvals/approval-456

# Review diff, then approve
curl -X POST http://localhost:8000/api/active/approvals/approval-456/approve \
  -H "Content-Type: application/json" \
  -d '{
    "approver": "ops_lead",
    "rationale": "Training looks solid, 2.5% accuracy improvement"
  }'
```

### Step 4: Deploy as Canary

```bash
# Deploy at 10% canary
curl -X POST http://localhost:8000/api/active/approvals/approval-456/apply \
  -H "Content-Type: application/json" \
  -d '{"canary_percent": 10}'

# Response:
# {"status": "deployed", "canary_percent": 10}
```

### Step 5: Monitor and Promote

Wait 24 hours, then check performance:

```bash
# Check canary performance
curl -X GET http://localhost:8000/api/active/canaries/inbox_triage/performance

# If recommendation is "promote":
curl -X POST http://localhost:8000/api/active/canaries/inbox_triage/promote \
  -H "Content-Type: application/json" \
  -d '{"target_percent": 50}'
```

Repeat after another 24h to promote to 100%:

```bash
curl -X POST http://localhost:8000/api/active/canaries/inbox_triage/promote \
  -H "Content-Type: application/json" \
  -d '{"target_percent": 100}'
```

---

## Handling Regressions

### Automatic Rollback (Normal Case)

The nightly guard check will automatically rollback if:
- Quality drops >5%
- Latency increases >10%

**Confirmation**:
```bash
# Check rollback logs
curl -X GET http://localhost:8000/api/active/logs?action=rollback&hours=24

# Expected output:
# [
#   {
#     "timestamp": "2024-01-15T05:00:00Z",
#     "agent": "inbox_triage",
#     "action": "rollback",
#     "reason": "quality_regression",
#     "quality_delta": -0.08
#   }
# ]
```

### Manual Rollback (Emergency)

If automatic rollback didn't trigger but you detect issues:

```bash
# Immediate rollback
curl -X POST http://localhost:8000/api/active/canaries/inbox_triage/rollback

# Response:
# {"status": "rolled_back", "canary_percent": 0}
```

### Post-Rollback Investigation

1. **Check training data quality**:
   ```bash
   # Review recent labeled examples
   curl -X GET http://localhost:8000/api/active/labeled?agent=inbox_triage&limit=50
   ```
   - Look for mislabeled data
   - Check label distribution

2. **Review model diff**:
   ```bash
   # Get bundle diff
   curl -X GET http://localhost:8000/api/active/bundles/inbox_triage_20240115_140000/diff
   ```
   - Were threshold changes too aggressive?
   - Did feature importances change dramatically?

3. **Re-train with adjusted parameters**:
   - Increase `min_examples` to 100+
   - Try `model_type: "tree"` instead of `"logistic"`
   - Filter out low-confidence labeled examples

---

## Manual Interventions

### Force Promotion (Skip Canary)

**Use Case**: Hotfix config needed immediately

```bash
# Approve bundle
curl -X POST http://localhost:8000/api/active/approvals/approval-789/approve \
  -H "Content-Type: application/json" \
  -d '{"approver": "ops_lead", "rationale": "Emergency fix"}'

# Apply at 100% immediately
curl -X POST http://localhost:8000/api/active/approvals/approval-789/apply \
  -H "Content-Type: application/json" \
  -d '{"canary_percent": 100}'
```

**⚠️ Warning**: Only use for critical fixes, bypasses safety checks

### Manual Bundle Edit

**Use Case**: Tweak thresholds without retraining

```bash
# Get current active bundle
curl -X GET http://localhost:8000/api/active/bundles/inbox_triage/active

# Edit thresholds locally (save as bundle.json)
# {
#   "agent": "inbox_triage",
#   "thresholds": {"risk_score_threshold": 68.0, "spf_dkim_weight": 1.4}
# }

# Upload edited bundle
curl -X POST http://localhost:8000/api/active/bundles/upload \
  -H "Content-Type: application/json" \
  -d @bundle.json

# Propose and deploy as usual
```

### Pause Active Learning

**Use Case**: Issues detected, need to pause all training

```bash
# Set pause flag
curl -X POST http://localhost:8000/api/active/pause \
  -H "Content-Type: application/json" \
  -d '{"reason": "Investigating data quality issues"}'

# This will:
# - Stop nightly feed loading
# - Stop nightly weight updates
# - Stop nightly canary checks
# - Allow manual approvals only
```

**Resume**:
```bash
curl -X POST http://localhost:8000/api/active/resume
```

---

## Incident Response

### Incident: Agent Quality Drops Suddenly

**Symptoms**:
- User reports of bad agent decisions
- Dashboard shows quality score drop >10%

**Steps**:

1. **Check if canary is active**:
   ```bash
   curl -X GET http://localhost:8000/api/active/canaries/active
   ```

2. **If canary found, rollback immediately**:
   ```bash
   curl -X POST http://localhost:8000/api/active/canaries/{agent}/rollback
   ```

3. **Check recent approvals**:
   ```bash
   curl -X GET http://localhost:8000/api/active/approvals/recent?hours=48
   ```
   - Identify which bundle caused issues

4. **Review training data**:
   - Look for mislabeled examples
   - Check for data poisoning (malicious labels)

5. **Re-train with filtered data**:
   - Exclude suspicious labeled examples
   - Increase confidence threshold (only use confidence >80)

### Incident: All Canaries Stuck

**Symptoms**:
- Nightly guard check not promoting/rolling back
- Canaries stuck at 10% for >7 days

**Steps**:

1. **Check guard logs**:
   ```bash
   curl -X GET http://localhost:8000/api/active/logs?action=guard_check&hours=168
   ```

2. **Investigate regression detector**:
   ```bash
   # Test regression detection manually
   curl -X POST http://localhost:8000/api/canary/detect \
     -H "Content-Type: application/json" \
     -d '{"agent": "inbox_triage", "since_hours": 24}'
   ```

3. **Manual decision**:
   - If performance is neutral, promote to 50%
   - If uncertain, rollback and re-train

### Incident: Training Fails Repeatedly

**Symptoms**:
- Bundle creation returns "Insufficient data"
- Or: Training succeeds but accuracy <50%

**Steps**:

1. **Check labeled data**:
   ```bash
   curl -X GET http://localhost:8000/api/active/stats/labeled
   ```
   - Need ≥50 examples per agent

2. **Check label distribution**:
   - If one label is >90%, add more diverse examples

3. **Manual labeling sprint**:
   - Sample 50-100 edge cases
   - Label manually via review queue

4. **Import synthetic data** (if available):
   - Use LLM to generate edge cases
   - Label with high confidence

---

## Monitoring & Alerts

### Recommended Alerts

**Critical (PagerDuty)**:
- Canary regression detected and auto-rollback triggered
- Training fails 3 times in a row for any agent
- Judge weight drops below 0.2 for critical judges (gpt-4, claude-3-opus)

**Warning (Slack)**:
- Labeled data growth <20 examples in last 7 days
- Canary stuck in monitoring for >72 hours
- Pending approvals >5

**Info (Email)**:
- Successful canary promotion to 100%
- New bundle trained and proposed
- Weekly judge weight summary

### Dashboard Panels

1. **Labeled Data Growth**: Line chart, by source (approvals, feedback, gold)
2. **Active Canaries**: Table with agent, percent, hours_running, recommendation
3. **Pending Approvals**: Table with agent, bundle_id, accuracy_delta, created_at
4. **Judge Weights**: Heatmap, agents vs judges
5. **Training Success Rate**: % of bundles that reach 100% deploy

### Logs to Monitor

- `app/active/feeds.py`: Feed loading counts
- `app/active/heur_trainer.py`: Training accuracy, feature importances
- `app/active/weights.py`: Judge weight updates
- `app/active/guards.py`: Canary promotions/rollbacks

---

## Appendix: Quick Reference

### API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/active/stats/labeled` | GET | Labeled data stats |
| `/api/active/approvals/pending` | GET | List pending approvals |
| `/api/active/approvals/{id}/approve` | POST | Approve bundle |
| `/api/active/canaries/active` | GET | List active canaries |
| `/api/active/canaries/{agent}/promote` | POST | Promote canary |
| `/api/active/canaries/{agent}/rollback` | POST | Rollback canary |
| `/api/active/bundles/create` | POST | Train new bundle |
| `/api/active/bundles/propose` | POST | Propose bundle for approval |
| `/api/active/weights` | GET | Get judge weights |

### CLI Shortcuts

Add these to `~/.bashrc`:

```bash
alias al-stats='curl -s http://localhost:8000/api/active/stats/labeled | jq'
alias al-pending='curl -s http://localhost:8000/api/active/approvals/pending | jq'
alias al-canaries='curl -s http://localhost:8000/api/active/canaries/active | jq'
alias al-weights='curl -s http://localhost:8000/api/active/weights | jq'

# Usage:
# $ al-stats
# $ al-pending
# $ al-canaries
```

---

## Support

For issues or questions:
- Slack: `#active-learning`
- Email: ops@applylens.com
- Escalation: On-call engineer (PagerDuty)
