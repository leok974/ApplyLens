# Budgets and Quality Gates Guide

This guide explains how to configure and use budget gates to maintain agent quality standards.

## Table of Contents

- [Overview](#overview)
- [Default Budget Thresholds](#default-budget-thresholds)
- [Customizing Budgets](#customizing-budgets-per-agent)
- [Regression Detection](#regression-detection-tuning)
- [CI Integration](#ci-integration)
- [Interpreting Violation Reports](#interpreting-violation-reports)
- [Best Practices](#best-practices)

## Overview

Budget gates are quality thresholds that agents must meet. They act as guardrails to prevent quality regressions and ensure consistent performance.

### Why Use Budget Gates?

1. **Prevent Regressions**: Catch quality degradations before they reach production
2. **Enforce Standards**: Set minimum acceptable quality levels
3. **CI/CD Integration**: Block merges that violate quality budgets
4. **Trend Monitoring**: Track quality over time and detect gradual degradation

### How It Works

```
┌─────────────────────────────────────────────────────────┐
│                  Budget Gate Flow                       │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  1. Agent Execution                                     │
│     └─> Metrics Collected (quality, latency, etc.)     │
│                                                         │
│  2. Gate Evaluation                                     │
│     └─> Compare metrics vs. budgets                    │
│                                                         │
│  3. Decision                                            │
│     ├─> All gates pass ✓                               │
│     │   └─> Allow deployment                           │
│     │                                                   │
│     └─> Any gate fails ✗                               │
│         ├─> Block deployment                           │
│         ├─> Create violation report                    │
│         └─> Notify team                                │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

## Default Budget Thresholds

The system comes with sensible defaults for all agents:

### Quality Budgets

```python
DEFAULT_QUALITY_BUDGET = 85.0  # Minimum overall quality score (0-100)
```

**Interpretation:**
- Weighted average across all judges
- Calculated as: `(correctness × 0.4) + (relevance × 0.3) + (safety × 0.2) + (efficiency × 0.1)`
- **Pass**: Score ≥ 85
- **Fail**: Score < 85

### Performance Budgets

```python
DEFAULT_LATENCY_BUDGET = {
    "p50_ms": 1000,   # 50th percentile
    "p95_ms": 2000,   # 95th percentile
    "p99_ms": 5000,   # 99th percentile
}
```

**Interpretation:**
- **p50_ms**: Half of requests must complete in ≤ 1000ms
- **p95_ms**: 95% of requests must complete in ≤ 2000ms
- **p99_ms**: 99% of requests must complete in ≤ 5000ms

### Reliability Budgets

```python
DEFAULT_SUCCESS_RATE = 0.95  # 95% of executions must succeed
```

**Interpretation:**
- **Pass**: ≥ 95% of agent executions succeed without errors
- **Fail**: < 95% success rate

### Invariant Budgets

```python
DEFAULT_INVARIANT_PASS_RATE = 0.95  # 95% of invariants must pass
```

**Interpretation:**
- **Pass**: ≥ 95% of invariant checks pass across all executions
- **Fail**: < 95% invariant pass rate

## Customizing Budgets Per Agent

Different agents may have different quality requirements.

### Configuration File

Create `app/config.py` or update existing config:

```python
# Agent-specific budget configuration

AGENT_BUDGETS = {
    "inbox_triage": {
        "quality_threshold": 90.0,  # Higher bar for email triage
        "latency_p95_ms": 1500,     # Faster response needed
        "success_rate": 0.98,       # Higher reliability required
        "invariant_pass_rate": 0.99, # Stricter invariant checking
    },
    
    "insights_writer": {
        "quality_threshold": 85.0,
        "latency_p95_ms": 5000,     # Can be slower for complex analysis
        "success_rate": 0.95,
        "invariant_pass_rate": 0.95,
    },
    
    "knowledge_update": {
        "quality_threshold": 80.0,   # More permissive for experimental agent
        "latency_p95_ms": 3000,
        "success_rate": 0.90,
        "invariant_pass_rate": 0.90,
    },
}

def get_agent_budgets(agent_id: str) -> dict:
    """Get budget configuration for an agent."""
    return AGENT_BUDGETS.get(agent_id, {
        "quality_threshold": DEFAULT_QUALITY_BUDGET,
        "latency_p95_ms": DEFAULT_LATENCY_BUDGET["p95_ms"],
        "success_rate": DEFAULT_SUCCESS_RATE,
        "invariant_pass_rate": DEFAULT_INVARIANT_PASS_RATE,
    })
```

### Dynamic Budget Adjustment

Adjust budgets based on context:

```python
from app.eval.budgets import GateEvaluator

def get_context_aware_budgets(agent_id: str, context: dict) -> dict:
    """Adjust budgets based on execution context."""
    base_budgets = get_agent_budgets(agent_id)
    
    # Relax latency for complex queries
    if context.get("query_complexity") == "high":
        base_budgets["latency_p95_ms"] *= 2
    
    # Tighten quality for production
    if context.get("environment") == "production":
        base_budgets["quality_threshold"] += 5
    
    # Relax constraints for experimental features
    if context.get("experimental"):
        base_budgets["quality_threshold"] -= 10
        base_budgets["success_rate"] -= 0.05
    
    return base_budgets
```

### Per-Task Budgets

Set different budgets for different task types:

```python
TASK_BUDGETS = {
    "high_priority_email": {
        "quality_threshold": 95.0,  # Critical task
        "latency_p95_ms": 500,      # Must be fast
    },
    "bulk_labeling": {
        "quality_threshold": 80.0,  # Less critical
        "latency_p95_ms": 5000,     # Can be slower
    },
}

def get_task_budgets(task_id: str) -> dict:
    return TASK_BUDGETS.get(task_id, get_agent_budgets(...))
```

## Regression Detection Tuning

Detect when quality degrades over time, even if still within budgets.

### Absolute Regression

Flag if quality drops below a specific threshold:

```python
from app.eval.budgets import GateEvaluator

evaluator = GateEvaluator(db)

# Check for regressions
results = evaluator.evaluate_all_agents(lookback_days=7)

for result in results:
    # Absolute check
    if result.current_quality < result.budgets["quality_threshold"]:
        print(f"❌ {result.agent_id}: Quality below budget")
        print(f"   Current: {result.current_quality:.1f}")
        print(f"   Budget: {result.budgets['quality_threshold']:.1f}")
```

### Relative Regression

Flag if quality drops significantly from baseline, even if within budget:

```python
# Detect relative regressions
REGRESSION_THRESHOLD = 0.05  # 5% drop

for result in results:
    baseline_quality = result.baseline_quality  # From previous period
    current_quality = result.current_quality
    
    drop = baseline_quality - current_quality
    drop_pct = drop / baseline_quality if baseline_quality > 0 else 0
    
    if drop_pct > REGRESSION_THRESHOLD:
        print(f"⚠️  {result.agent_id}: Quality regressed")
        print(f"   Baseline: {baseline_quality:.1f}")
        print(f"   Current: {current_quality:.1f}")
        print(f"   Drop: {drop_pct:.1%}")
```

### Trend-Based Detection

Detect gradual quality degradation:

```python
from scipy.stats import linregress

def detect_quality_trend(agent_id: str, days: int = 30):
    """Detect if quality is trending downward."""
    
    # Get historical metrics
    metrics = db.query(AgentMetricsDaily).filter(
        AgentMetricsDaily.agent_id == agent_id,
        AgentMetricsDaily.date >= datetime.now() - timedelta(days=days)
    ).order_by(AgentMetricsDaily.date).all()
    
    if len(metrics) < 7:
        return None  # Need at least a week of data
    
    # Calculate trend
    x = list(range(len(metrics)))
    y = [m.quality_score for m in metrics]
    
    slope, intercept, r_value, p_value, std_err = linregress(x, y)
    
    # Negative slope = declining quality
    if slope < -0.5 and p_value < 0.05:  # Statistically significant decline
        return {
            "trending": "down",
            "slope": slope,
            "current": y[-1],
            "projected_30d": intercept + slope * (len(x) + 30),
            "significance": p_value
        }
    
    return None

# Use in gate evaluation
trend = detect_quality_trend("inbox_triage")
if trend:
    print(f"📉 Quality trending down")
    print(f"   Slope: {trend['slope']:.2f} points/day")
    print(f"   Current: {trend['current']:.1f}")
    print(f"   Projected (30d): {trend['projected_30d']:.1f}")
```

### Configuring Regression Sensitivity

```python
REGRESSION_CONFIG = {
    "absolute_threshold": 85.0,      # Hard minimum
    "relative_threshold": 0.05,      # 5% drop from baseline
    "trend_slope_threshold": -0.5,   # Quality declining by 0.5 pts/day
    "trend_lookback_days": 30,       # Analyze last 30 days
    "trend_significance": 0.05,      # p-value threshold
}

# Use in evaluator
evaluator = GateEvaluator(
    db,
    regression_config=REGRESSION_CONFIG
)
```

## CI Integration

Integrate budget gates into your CI/CD pipeline to prevent bad deployments.

### GitHub Actions Example

```yaml
# .github/workflows/agent-quality-gate.yml

name: Agent Quality Gate

on:
  pull_request:
    paths:
      - 'services/api/app/agents/**'
      - 'services/api/app/eval/**'

jobs:
  quality-gate:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          cd services/api
          pip install -r requirements.txt
      
      - name: Run database migrations
        run: |
          cd services/api
          alembic upgrade head
      
      - name: Run evaluation suite
        run: |
          cd services/api
          python -m app.eval.runner --agent inbox_triage --export results.jsonl
      
      - name: Check budget gates
        run: |
          cd services/api
          python -m app.eval.run_gates --agent inbox_triage --fail-on-violation
        
      - name: Upload results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: eval-results
          path: services/api/results.jsonl
      
      - name: Comment on PR
        if: failure()
        uses: actions/github-script@v6
        with:
          script: |
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: '❌ Quality gates failed. Please review evaluation results.'
            })
```

### CLI Script Usage

Run gates manually:

```bash
# Check all agents
python -m app.eval.run_gates --all

# Check specific agent
python -m app.eval.run_gates --agent inbox_triage

# Fail on any violation (for CI)
python -m app.eval.run_gates --agent inbox_triage --fail-on-violation

# Check specific budgets only
python -m app.eval.run_gates --agent inbox_triage --budgets quality,latency

# Use custom lookback period
python -m app.eval.run_gates --agent inbox_triage --lookback-days 14

# Output formats
python -m app.eval.run_gates --agent inbox_triage --format json
python -m app.eval.run_gates --agent inbox_triage --format table
```

### Pre-commit Hook

Add to `.git/hooks/pre-commit`:

```bash
#!/bin/bash

# Run quality gates before commit
cd services/api
python -m app.eval.run_gates --agent inbox_triage --fail-on-violation

if [ $? -ne 0 ]; then
    echo "❌ Quality gates failed. Commit blocked."
    echo "Run 'python -m app.eval.run_gates --agent inbox_triage' for details."
    exit 1
fi

echo "✅ Quality gates passed"
exit 0
```

Make executable:
```bash
chmod +x .git/hooks/pre-commit
```

## Interpreting Violation Reports

When gates fail, you'll receive a violation report.

### Report Structure

```
╔══════════════════════════════════════════════════════════╗
║         BUDGET GATE VIOLATION REPORT                     ║
╠══════════════════════════════════════════════════════════╣
║ Agent: inbox_triage                                      ║
║ Date: 2025-10-17                                         ║
║ Lookback: 7 days                                         ║
╚══════════════════════════════════════════════════════════╝

┌──────────────────────────────────────────────────────────┐
│ VIOLATIONS (3)                                           │
├──────────────────────────────────────────────────────────┤
│                                                          │
│ 1. Quality Score Below Threshold                         │
│    Severity: CRITICAL                                    │
│    Budget: 85.0                                          │
│    Actual: 82.3                                          │
│    Gap: -2.7 points                                      │
│    Recommendation: Review failed tasks, improve judges   │
│                                                          │
│ 2. P95 Latency Exceeded                                  │
│    Severity: WARNING                                     │
│    Budget: 2000ms                                        │
│    Actual: 2350ms                                        │
│    Gap: +350ms (+17.5%)                                  │
│    Recommendation: Profile slow operations, optimize     │
│                                                          │
│ 3. Invariant Pass Rate Low                               │
│    Severity: CRITICAL                                    │
│    Budget: 95.0%                                         │
│    Actual: 91.2%                                         │
│    Gap: -3.8%                                            │
│    Top Failing Invariants:                               │
│      - no_pii_leak: 15 failures                         │
│      - valid_action: 8 failures                         │
│    Recommendation: Fix invariant violations              │
│                                                          │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│ PASSED GATES (2)                                         │
├──────────────────────────────────────────────────────────┤
│ ✓ Success Rate: 97.5% (budget: 95.0%)                   │
│ ✓ P50 Latency: 850ms (budget: 1000ms)                   │
└──────────────────────────────────────────────────────────┘
```

### Reading Violation Severity

- **CRITICAL**: Must fix before deployment (blocks CI)
- **WARNING**: Should investigate (logs but doesn't block)
- **INFO**: FYI only (e.g., approaching threshold)

### Common Violations & Fixes

#### 1. Quality Score Below Threshold

**Symptoms:**
- Overall quality score < budget
- Multiple tasks failing

**Diagnosis:**
```bash
# See which tasks are failing
python -m app.eval.runner --agent inbox_triage --min-score 0 --export failures.jsonl

# Analyze failure reasons
cat failures.jsonl | jq 'select(.overall_score < 85) | {task_id, score, failures: .judge_scores}'
```

**Fixes:**
- Improve agent logic for failing tasks
- Update expected outputs if tasks are outdated
- Retrain models if using ML components
- Adjust judge weights if needed

#### 2. Latency Budget Exceeded

**Symptoms:**
- p95 or p99 latency > budget
- Slow user experience

**Diagnosis:**
```bash
# Profile agent execution
python -m cProfile -o profile.stats -m app.agents.inbox_triage

# Analyze profile
python -c "import pstats; p = pstats.Stats('profile.stats'); p.sort_stats('cumulative'); p.print_stats(20)"
```

**Fixes:**
- Cache expensive operations
- Optimize database queries (add indexes)
- Use async/await for I/O
- Reduce LLM prompt size
- Parallelize independent operations

#### 3. Low Success Rate

**Symptoms:**
- High error rate
- Many failed executions

**Diagnosis:**
```bash
# See error patterns
python -c "
from app.models import AgentMetricsDaily
from app.db import SessionLocal

db = SessionLocal()
metrics = db.query(AgentMetricsDaily).filter(
    AgentMetricsDaily.agent_id == 'inbox_triage',
    AgentMetricsDaily.failed_runs > 0
).all()

for m in metrics:
    print(f'{m.date}: {m.failed_runs} failures')
"
```

**Fixes:**
- Add error handling and retries
- Validate inputs before processing
- Handle edge cases (empty inputs, invalid data)
- Improve timeout handling
- Add circuit breakers for external APIs

#### 4. Invariant Violations

**Symptoms:**
- Invariant pass rate < budget
- Specific invariants failing frequently

**Diagnosis:**
```bash
# Find failing invariants
python -m app.eval.run_gates --agent inbox_triage --show-invariant-details
```

**Fixes:**
- Fix root cause of invariant failures
- Update invariant logic if too strict
- Add validation before output
- Sanitize sensitive data (for PII leaks)
- Improve input validation

## Best Practices

### 1. Start Conservative, Relax Gradually

Begin with strict budgets and loosen over time:

```python
# Week 1: Strict budgets
initial_budgets = {
    "quality_threshold": 90.0,
    "latency_p95_ms": 1500,
    "success_rate": 0.98,
}

# Week 4: After baseline established
adjusted_budgets = {
    "quality_threshold": 85.0,  # Relaxed by 5 points
    "latency_p95_ms": 2000,     # +500ms
    "success_rate": 0.95,       # -3%
}
```

### 2. Different Budgets for Different Environments

```python
ENVIRONMENT_BUDGETS = {
    "development": {
        "quality_threshold": 75.0,  # More permissive
        "latency_p95_ms": 5000,
        "success_rate": 0.90,
    },
    "staging": {
        "quality_threshold": 85.0,
        "latency_p95_ms": 2000,
        "success_rate": 0.95,
    },
    "production": {
        "quality_threshold": 90.0,  # Strictest
        "latency_p95_ms": 1500,
        "success_rate": 0.98,
    },
}
```

### 3. Monitor Budget Headroom

Track how close you are to budget limits:

```python
def calculate_budget_headroom(agent_id: str) -> dict:
    """Calculate margin between current metrics and budgets."""
    
    result = evaluator.evaluate_agent(agent_id)
    budgets = result.budgets
    
    return {
        "quality_headroom": result.quality_score - budgets["quality_threshold"],
        "latency_headroom": budgets["latency_p95_ms"] - result.latency_p95,
        "success_rate_headroom": result.success_rate - budgets["success_rate"],
    }

# Alert if headroom < 10%
headroom = calculate_budget_headroom("inbox_triage")
if headroom["quality_headroom"] < 5:
    print("⚠️  Quality approaching budget limit!")
```

### 4. Version Your Budgets

Track budget changes over time:

```python
# budgets_history.yml

inbox_triage:
  - date: "2025-01-01"
    version: "1.0"
    quality_threshold: 80.0
    reason: "Initial baseline"
  
  - date: "2025-02-15"
    version: "1.1"
    quality_threshold: 85.0
    reason: "Agent improvements stabilized"
  
  - date: "2025-10-01"
    version: "2.0"
    quality_threshold: 90.0
    reason: "New judge system, higher bar"
```

### 5. Document Budget Rationale

Explain why each budget is set:

```python
BUDGET_RATIONALE = {
    "inbox_triage": {
        "quality_threshold": {
            "value": 90.0,
            "reason": "Email triage is user-facing and errors are highly visible",
            "impact": "Low quality → user frustration → manual triage needed"
        },
        "latency_p95_ms": {
            "value": 1500,
            "reason": "Users expect fast email processing",
            "impact": "Slow triage → delayed responses → missed opportunities"
        },
    }
}
```

### 6. Regular Budget Reviews

Schedule quarterly reviews:
- Are budgets still appropriate?
- Have agent capabilities improved?
- Are budgets too strict or too lenient?
- Do they align with business objectives?

### 7. Automate Notifications

Alert the team when gates fail:

```python
from app.eval.budgets import GateEvaluator
import slack_sdk

def check_and_notify():
    results = evaluator.evaluate_all_agents()
    
    for result in results:
        if result.has_violations():
            send_slack_alert(
                channel="#agent-quality",
                message=f"❌ Budget gates failed for {result.agent_id}",
                details=result.violation_summary()
            )
```

## Next Steps

- See [EVAL_GUIDE.md](./EVAL_GUIDE.md) for evaluation fundamentals
- See [INTELLIGENCE_REPORT.md](./INTELLIGENCE_REPORT.md) for weekly quality reports
- See [DASHBOARD_ALERTS.md](./DASHBOARD_ALERTS.md) for real-time monitoring
- See [REDTEAM.md](./REDTEAM.md) for security testing
