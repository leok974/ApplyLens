# Active Learning System

## Overview

The Active Learning system closes the learning loop by continuously improving agent performance through:

1. **Labeled Data Collection**: Aggregating human feedback from approvals, thumbs up/down, and gold sets
2. **Heuristic Training**: Training simple ML models to update planner configs
3. **Judge Reliability Weighting**: Assigning trust scores to LLM judges based on calibration
4. **Uncertainty Sampling**: Identifying edge cases for human review
5. **Bundle Deployment**: Safe, gradual rollout of config updates via canary

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Active Learning Loop                      │
└─────────────────────────────────────────────────────────────┘

  [Data Sources]           [Training]          [Deployment]
       │                       │                    │
   ┌───┴────┐           ┌──────┴──────┐      ┌────┴─────┐
   │Approvals│           │  Heuristic  │      │  Bundle  │
   │Feedback │──────────▶│   Trainer   │─────▶│ Manager  │
   │Gold Sets│           │             │      │          │
   └─────────┘           └──────────────┘     └────┬─────┘
                                                    │
  [Uncertainty]                                     ▼
       │                                      [Canary 10%]
   ┌───┴────┐                                       │
   │ Sampler│                                  ┌────┴─────┐
   │  Edge  │                                  │Regression│
   │  Cases │                                  │ Detector │
   └───┬────┘                                  └────┬─────┘
       │                                            │
       ▼                                            ▼
  [Human Review]                            [Promote/Rollback]
                                                    │
  [Judge Weights]                                   ▼
       │                                       [Canary 50%]
   ┌───┴────┐                                       │
   │ Nightly│                                       ▼
   │ Weight │                                  [Full Deploy]
   │ Update │
   └────────┘
```

## Components

### 1. Labeled Example Store (`app/models_al.py`)

**Purpose**: Central repository for all labeled training data

**Model**: `LabeledExample`
- `agent`: inbox_triage, insights_writer, knowledge_update
- `key`: Unique identifier (thread_id, rule_id, task_id)
- `payload`: JSON feature snapshot
- `label`: High-Risk, Offer, Safe, high_quality, etc.
- `source`: approvals|feedback|gold|synthetic
- `confidence`: 0-100 (how confident we are in this label)
- `notes`: Human rationale

**Indexes**:
- agent + source (for training queries)
- agent + label (for label distribution)
- created_at DESC (for recent data)

### 2. Feed Loaders (`app/active/feeds.py`)

**Purpose**: ETL pipeline to populate labeled examples from various sources

**Methods**:
- `load_from_approvals(since, limit)`:
  - Extracts approved/rejected decisions from AgentApproval table
  - Label format: "{action}_approved" or "{action}_rejected"
  - Confidence: 100 (explicit human decision)
  - Deduplication via source="approvals" + source_id=request_id

- `load_from_feedback(since, limit)`:
  - Aggregates thumbs up/down from AgentMetricsDaily
  - Calculates thumbs_up_ratio = thumbs_up / feedback_count
  - Labels: high_quality (≥0.8), medium_quality (≥0.5), low_quality (<0.5)
  - Confidence: int(thumbs_up_ratio * 100)

- `load_from_goldsets(agent, limit)`:
  - Imports curated evaluation tasks from GoldenTask table
  - Confidence: 100 (manually curated)
  - Source: "gold"

**Deduplication**: Checks for existing examples with same source + source_id before creating

### 3. Heuristic Trainer (`app/active/heur_trainer.py`)

**Purpose**: Train deterministic ML models on labeled examples to update planner configs

**Feature Extractors**:
- **inbox_triage** (7 features):
  - risk_score, has_spf_fail, has_dkim_fail, suspicious_keywords_count, attachment_count, sender_domain_age_days, recipient_count

- **insights_writer** (5 features):
  - pattern_strength, data_points_count, confidence_score, statistical_significance, novelty_score

- **knowledge_update** (4 features):
  - similarity_score, frequency_delta, co_occurrence_count, context_overlap_ratio

**Models**:
- **Logistic Regression**: Fast, interpretable, good for binary/multi-class
- **Decision Tree**: Captures non-linear relationships, depth=5 for simplicity

**Training Process**:
1. Fetch labeled examples for agent (min 50 required)
2. Extract features using agent-specific extractor
3. Normalize features with StandardScaler
4. Train model (logistic or tree)
5. Generate config bundle with updated thresholds

**Config Bundle Output**:
```json
{
  "agent": "inbox_triage",
  "version": "v1",
  "created_at": "2024-01-15T10:30:00Z",
  "training_count": 120,
  "accuracy": 0.87,
  "label_distribution": {"quarantine": 80, "safe": 40},
  "feature_importances": [0.45, 0.23, 0.15, 0.10, 0.05, 0.02, 0.01],
  "thresholds": {
    "risk_score_threshold": 65.0,
    "spf_dkim_weight": 1.5
  },
  "model_type": "LogisticRegression",
  "sources_used": ["approvals", "feedback", "gold"]
}
```

**Diff Generation**:
- Compares old vs new bundles
- Tracks changes, additions, removals
- Calculates accuracy delta

### 4. Judge Reliability Weighting (`app/active/weights.py`)

**Purpose**: Assign trust scores to LLM judges based on calibration and agreement

**Metrics**:
- **Agreement Rate**: % of predictions matching human labels (with exponential time decay)
- **Calibration Error**: Mean absolute difference between predicted confidence and actual accuracy
- **Combined Weight**: `agreement_rate - (0.5 * calibration_error)`

**Formula**:
```python
# Time decay (7-day half-life)
decay_weights = exp(-time_deltas * log(2) / 7.0)

# Weighted agreement
weighted_agreement = average(agreements, weights=decay_weights)

# Calibration error
calibration_error = abs(confidences - agreements).mean()

# Final weight (clamped to [0.1, 1.0])
weight = clamp(weighted_agreement - 0.5 * calibration_error, 0.1, 1.0)
```

**Storage**: Stored in runtime_settings as `judge_weights.{agent}`

**Default Weights**:
- gpt-4: 0.8
- gpt-3.5-turbo: 0.6
- claude-3-opus: 0.8
- claude-3-sonnet: 0.7

**Nightly Update**: `nightly_update_weights(db_session)` runs daily to recalculate all weights

### 5. Uncertainty Sampler (`app/active/sampler.py`)

**Purpose**: Identify edge cases for human review based on ensemble disagreement

**Uncertainty Methods**:

1. **Disagreement**: Multiple judges predict different verdicts
   - Uses entropy: `H = -Σ(p * log2(p))`
   - Normalized by max entropy

2. **Low Confidence**: Weighted average confidence < 60%
   - Uncertainty = `1.0 - weighted_confidence`

3. **Weighted Variance**: High variance in confidence scores
   - Uses judge weights for averaging
   - Scaled to [0, 1]

**Sampling Process**:
1. Fetch recent evaluation results (last 7 days)
2. Filter out already-labeled examples
3. Calculate uncertainty for each prediction
4. Sort by uncertainty descending
5. Return top N candidates (default 50)

**Output**:
```json
{
  "task_key": "thread-12345",
  "agent": "inbox_triage",
  "uncertainty": 0.85,
  "method": "disagreement",
  "judge_scores": {...},
  "payload": {...},
  "created_at": "2024-01-15T10:30:00Z"
}
```

**Daily Sampling**: `daily_sample_review_queue(db_session)` samples 20 candidates per agent

### 6. Bundle Manager (`app/active/bundles.py`)

**Purpose**: Manage config bundle lifecycle with approval workflow

**Workflow**:

1. **Create Bundle**: `create_bundle(agent, min_examples, model_type)`
   - Trains model, generates bundle
   - Stores in runtime_settings as `bundle.{agent}.{bundle_id}`
   - Status: "pending"

2. **Propose Bundle**: `propose_bundle(agent, bundle_id, proposer)`
   - Creates AgentApproval request
   - Generates diff from current active bundle
   - Returns approval_id

3. **Approve Bundle**: `approve_bundle(approval_id, approver, rationale)`
   - Updates approval status to "approved"
   - Does NOT auto-apply (requires explicit apply)

4. **Apply Bundle**: `apply_approved_bundle(approval_id, canary_percent)`
   - Backs up current active bundle
   - Applies as canary (if canary_percent set) or full deploy
   - Updates `bundle.{agent}.active` or `bundle.{agent}.canary`

5. **Rollback**: `rollback_bundle(agent)`
   - Restores backup bundle as active
   - Used for emergency reverts

**Storage Keys**:
- `bundle.{agent}.{bundle_id}`: Specific bundle
- `bundle.{agent}.active`: Current active config
- `bundle.{agent}.backup`: Previous config (for rollback)
- `bundle.{agent}.canary`: Canary config

### 7. Online Learning Guardrails (`app/active/guards.py`)

**Purpose**: Safety checks for deployed bundles with auto-promote/rollback

**Canary Flow**:

```
Approved Bundle
      │
      ▼
  [Canary 10%]
      │
  [24h Monitor]
      │
      ├─ Regression? ──▶ [Rollback]
      │
      ├─ Neutral? ───▶ [Continue Monitoring]
      │
      └─ Better? ────▶ [Promote to 50%]
                           │
                       [24h Monitor]
                           │
                           └─ Better? ──▶ [Promote to 100%]
```

**Checks**:
- **Regression Detection**: Uses Phase 5.1's RegressionDetector
  - Quality drop > 5% → Rollback
  - Latency increase > 10% → Rollback

- **Promotion Criteria**:
  - Quality improvement > 2% → Promote
  - Latency reduction > 10% → Promote

**Methods**:
- `check_canary_performance(agent, lookback_hours, threshold)`:
  - Returns: {has_regression, quality_delta, latency_delta, recommendation}
  - Recommendation: "promote" | "rollback" | "monitor"

- `promote_canary(agent, target_percent)`:
  - Increases traffic to target % (50 or 100)
  - At 100%, makes canary the active bundle

- `rollback_canary(agent)`:
  - Sets canary_percent to 0
  - Traffic reverts to active bundle

- `gradual_rollout(agent, stages, check_interval_hours)`:
  - Multi-stage promotion with safety checks
  - Default stages: [10, 50, 100]
  - Default interval: 24h

**Nightly Job**: `nightly_guard_check()` runs daily to check all active canaries

## Usage

### Load Labeled Data

```python
from app.active.feeds import load_all_feeds

# Load from all sources
with session_scope() as session:
    counts = load_all_feeds(session)
    print(f"Loaded: {counts}")
    # {"approvals": 45, "feedback": 120, "gold": 30}
```

### Train and Deploy Bundle

```python
from app.active.bundles import BundleManager

with session_scope() as session:
    mgr = BundleManager(session)
    
    # 1. Create bundle
    bundle = mgr.create_bundle("inbox_triage", min_examples=50)
    
    # 2. Propose for approval
    approval_id = mgr.propose_bundle("inbox_triage", bundle["bundle_id"], proposer="admin")
    
    # 3. Approve
    mgr.approve_bundle(approval_id, approver="ops_lead", rationale="Looks good")
    
    # 4. Deploy as 10% canary
    mgr.apply_approved_bundle(approval_id, canary_percent=10)
```

### Sample Uncertain Predictions

```python
from app.active.sampler import UncertaintySampler

with session_scope() as session:
    sampler = UncertaintySampler(session)
    
    # Get top 50 uncertain predictions
    candidates = sampler.sample_for_review("inbox_triage", top_n=50)
    
    for c in candidates[:5]:
        print(f"{c['task_key']}: {c['uncertainty']:.2f} ({c['method']})")
```

### Check Canary Performance

```python
from app.active.guards import OnlineLearningGuard

with session_scope() as session:
    guard = OnlineLearningGuard(session)
    
    # Check performance
    result = guard.check_canary_performance("inbox_triage")
    
    if result["recommendation"] == "rollback":
        guard.rollback_canary("inbox_triage")
    elif result["recommendation"] == "promote":
        guard.promote_canary("inbox_triage", target_percent=50)
```

## Scheduled Jobs

Add these to `app/scheduler.py`:

```python
from app.active.feeds import load_all_feeds
from app.active.weights import nightly_update_weights
from app.active.sampler import daily_sample_review_queue
from app.active.guards import OnlineLearningGuard

# Daily at 2 AM: Load new labeled data
@scheduler.scheduled_job('cron', hour=2)
def load_labeled_data():
    with session_scope() as session:
        load_all_feeds(session)

# Daily at 3 AM: Update judge weights
@scheduler.scheduled_job('cron', hour=3)
def update_judge_weights():
    with session_scope() as session:
        nightly_update_weights(session)

# Daily at 4 AM: Sample review queue
@scheduler.scheduled_job('cron', hour=4)
def sample_review_queue():
    with session_scope() as session:
        daily_sample_review_queue(session, top_n_per_agent=20)

# Daily at 5 AM: Check canary deployments
@scheduler.scheduled_job('cron', hour=5)
def check_canaries():
    with session_scope() as session:
        guard = OnlineLearningGuard(session)
        guard.nightly_guard_check()
```

## Monitoring

### Labeled Data Stats

```python
from app.active.feeds import FeedLoader

with session_scope() as session:
    loader = FeedLoader(session)
    stats = loader.get_stats()
    # {
    #   "total": 250,
    #   "by_source": {"approvals": 100, "feedback": 120, "gold": 30},
    #   "by_agent": {"inbox_triage": 150, "insights_writer": 100},
    #   "recent_7d": 45
    # }
```

### Review Queue Stats

```python
from app.active.sampler import UncertaintySampler

with session_scope() as session:
    sampler = UncertaintySampler(session)
    stats = sampler.get_review_queue_stats()
    # {
    #   "total_unlabeled": 1500,
    #   "by_agent": {"inbox_triage": 800, "insights_writer": 700}
    # }
```

### Pending Approvals

```python
from app.active.bundles import BundleManager

with session_scope() as session:
    mgr = BundleManager(session)
    pending = mgr.list_pending_approvals()
    # [
    #   {"id": "...", "agent": "inbox_triage", "bundle_id": "...", "diff": {...}},
    #   ...
    # ]
```

## Best Practices

1. **Minimum Data Requirements**:
   - Train only with ≥50 labeled examples per agent
   - Balance label distribution (avoid 90/10 splits)

2. **Canary Deployment**:
   - Always start at 10% canary
   - Monitor for 24h before promoting
   - Use gradual rollout (10% → 50% → 100%)

3. **Review Queue**:
   - Sample daily to build training data
   - Prioritize high-uncertainty predictions
   - Label at least 10-20 examples per agent per week

4. **Judge Weights**:
   - Update nightly with 30-day lookback
   - Use 7-day exponential decay to favor recent performance
   - Require ≥5 predictions per judge for reliable weights

5. **Rollback**:
   - Keep backups of last 3 configs
   - Auto-rollback on >5% quality regression
   - Manual rollback if latency doubles

## Troubleshooting

### Bundle training fails with "Insufficient data"
- Check labeled example count: `loader.get_stats()`
- Need ≥50 examples per agent
- Load more data: `load_all_feeds(session)`

### Canary stuck in monitoring
- Check performance: `guard.check_canary_performance(agent)`
- If neutral for >7 days, manually promote or rollback

### Judge weights not updating
- Check evaluation results exist: `SELECT COUNT(*) FROM evaluation_results WHERE judge_scores IS NOT NULL`
- Check labeled examples exist for validation
- Run manually: `nightly_update_weights(session)`

### Review queue empty
- Check if all predictions already labeled
- Lower uncertainty threshold: `sampler.sample_for_review(agent, min_uncertainty=0.3)`

## Integration with Phase 5

Active Learning (Phase 5.3) integrates with:

- **Phase 5 Eval Harness**: Uses GoldenTask for training data
- **Phase 5.1 Canary**: Uses PlannerSwitchboard for traffic split
- **Phase 5.1 Regression Detector**: Monitors canary performance
- **Phase 5 Online Eval**: Feedback loops into labeled data

## Future Enhancements

1. **Multi-Agent Ensembles**: Train meta-models across agents
2. **Synthetic Data**: Generate edge cases via LLM augmentation
3. **Active Prompting**: Suggest prompt improvements from training
4. **Cost Optimization**: Train models to balance quality vs cost
5. **Explainability**: Surface feature importances in UI
