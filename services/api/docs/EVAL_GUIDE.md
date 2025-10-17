# Agent Evaluation System Guide

This guide explains how to use the ApplyLens agent evaluation system to measure and improve agent performance.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Offline Evaluation (Eval Harness)](#offline-evaluation-eval-harness)
- [Online Evaluation](#online-evaluation)
- [Creating Golden Tasks](#creating-golden-tasks)
- [Customizing Judges](#customizing-judges)
- [Defining Invariants](#defining-invariants)
- [Best Practices](#best-practices)

## Overview

The ApplyLens evaluation system provides comprehensive tools for measuring agent quality, performance, and reliability:

- **Offline Evaluation**: Test agents against golden tasks in controlled environments
- **Online Evaluation**: Monitor production agent performance in real-time
- **Quality Metrics**: Multi-dimensional scoring (correctness, relevance, safety, efficiency)
- **Invariant Checking**: Validate agent behavior constraints
- **Red Team Testing**: Test agent resilience against adversarial inputs

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Evaluation System                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐      ┌──────────────┐                   │
│  │   Offline    │      │   Online     │                   │
│  │   Harness    │      │  Evaluator   │                   │
│  └──────┬───────┘      └──────┬───────┘                   │
│         │                     │                            │
│         ├─────────────────────┤                            │
│         │                     │                            │
│  ┌──────▼─────────────────────▼──────┐                    │
│  │         Judge Pipeline             │                    │
│  │  ┌────────┬────────┬────────┐     │                    │
│  │  │Correct.│Relev.  │Safety  │     │                    │
│  │  │Judge   │Judge   │Judge   │...  │                    │
│  │  └────────┴────────┴────────┘     │                    │
│  └────────────────┬───────────────────┘                    │
│                   │                                         │
│  ┌────────────────▼───────────────────┐                    │
│  │      Invariant Checker             │                    │
│  │  • No PII leak                     │                    │
│  │  • Action compliance               │                    │
│  │  • Format validation               │                    │
│  └────────────────┬───────────────────┘                    │
│                   │                                         │
│  ┌────────────────▼───────────────────┐                    │
│  │     Metrics Collection             │                    │
│  │  • AgentMetricsDaily (DB)          │                    │
│  │  • Prometheus metrics              │                    │
│  └────────────────────────────────────┘                    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Components

1. **Eval Harness** (`app/eval/runner.py`): Runs offline evaluations against golden tasks
2. **Judges** (`app/eval/judges.py`): Score agent outputs across multiple dimensions
3. **Invariants** (`app/eval/models.py`): Define and check behavioral constraints
4. **Online Evaluator** (`app/eval/telemetry.py`): Monitor production performance
5. **Red Team** (`app/eval/telemetry.py`): Test adversarial robustness

## Offline Evaluation (Eval Harness)

### Quick Start

Run evaluations from the command line:

```bash
# Run all tasks for an agent
cd services/api
python -m app.eval.runner --agent inbox_triage

# Run specific task
python -m app.eval.runner --agent inbox_triage --task high_priority_email

# Export results to JSONL
python -m app.eval.runner --agent inbox_triage --export results.jsonl

# Use specific judge
python -m app.eval.runner --agent inbox_triage --judge correctness
```

### Using the Python API

```python
from app.eval.runner import EvaluationRunner
from app.eval.tasks import get_all_tasks
from app.db import SessionLocal

# Initialize
db = SessionLocal()
runner = EvaluationRunner(db)

# Run evaluation
tasks = get_all_tasks("inbox_triage")
results = runner.run_evaluation(
    agent_id="inbox_triage",
    tasks=tasks,
    judges=["correctness", "relevance", "safety", "efficiency"]
)

# Access results
for result in results:
    print(f"Task: {result.task_id}")
    print(f"Overall Score: {result.overall_score}/100")
    print(f"Correctness: {result.judge_scores['correctness']}/100")
    print(f"Latency: {result.latency_ms}ms")
    print(f"Invariants Passed: {result.invariants_passed}/{result.invariants_total}")
```

### Understanding Results

Each evaluation produces:

- **overall_score**: Weighted average across all judges (0-100)
- **judge_scores**: Individual scores per judge (0-100 each)
- **latency_ms**: Execution time in milliseconds
- **invariants_passed/total**: Number of invariants that passed
- **error**: Error message if execution failed

### Task Categories

Tasks are organized by agent type:

- **Inbox Tasks** (`tasks_inbox.py`): Email triage, priority detection, label assignment
- **Insights Tasks** (`tasks_insights.py`): Analytics, trend detection, report generation
- **Knowledge Tasks** (`tasks_knowledge.py`): Document retrieval, question answering
- **Warehouse Tasks** (`tasks_warehouse.py`): Data queries, analysis, visualization

## Online Evaluation

Online evaluation monitors agents running in production.

### Enabling Online Evaluation

```python
from app.eval.telemetry import OnlineEvaluator
from app.db import SessionLocal

db = SessionLocal()
evaluator = OnlineEvaluator(db)

# Evaluate agent execution
result = evaluator.evaluate_execution(
    agent_id="inbox_triage",
    task_input={"email_id": 12345, "user_id": 1},
    agent_output={"priority": "high", "labels": ["urgent"]},
    latency_ms=450,
    success=True
)

# Result contains:
# - quality_score (0-100)
# - judge_scores (per judge)
# - invariant_violations (list)
# - stored in AgentMetricsDaily
```

### Feedback Collection

Collect user feedback to improve evaluations:

```python
from app.eval.telemetry import FeedbackCollector

collector = FeedbackCollector(db)

# Record feedback
collector.collect_feedback(
    agent_id="inbox_triage",
    execution_id="exec_123",
    user_id=1,
    rating=5,  # 1-5 stars
    feedback_text="Perfect triage!",
    metadata={"task_type": "email_classification"}
)

# Aggregate feedback
stats = collector.get_feedback_stats(
    agent_id="inbox_triage",
    days=7
)
# Returns: avg_rating, total_feedback, rating_distribution
```

### Red Team Testing

Test agent resilience against adversarial inputs:

```python
from app.eval.telemetry import RedTeamCatalog

catalog = RedTeamCatalog()

# Get attack scenarios for an agent
attacks = catalog.get_attacks_for_agent("inbox_triage")

# Run red team evaluation
for attack in attacks:
    result = evaluator.evaluate_execution(
        agent_id="inbox_triage",
        task_input=attack.input,
        agent_output=run_agent(attack.input),
        latency_ms=...,
        success=True,
        is_redteam=True
    )
    
    # Check if attack was detected/blocked
    if result.has_invariant_violations():
        print(f"✓ Attack {attack.id} was blocked")
    else:
        print(f"✗ Attack {attack.id} was NOT blocked")
```

## Creating Golden Tasks

Golden tasks are reference examples with known correct outputs.

### Task Structure

```python
from app.eval.models import GoldenTask, GoldenTaskInput, GoldenTaskExpected

task = GoldenTask(
    task_id="unique_task_identifier",
    agent_id="inbox_triage",
    category="email_classification",
    description="High priority email from CEO",
    difficulty="medium",  # easy, medium, hard
    
    # Input to agent
    input=GoldenTaskInput(
        email_id=123,
        subject="URGENT: Board meeting tomorrow",
        from_email="ceo@company.com",
        body="Please prepare Q4 financials...",
        metadata={"received_at": "2025-10-17T10:00:00Z"}
    ),
    
    # Expected output
    expected=GoldenTaskExpected(
        priority="high",
        labels=["urgent", "financials", "executive"],
        action="flag_for_review",
        confidence_min=0.9,  # Minimum acceptable confidence
    ),
    
    # Evaluation criteria
    invariants=["no_pii_leak", "valid_priority", "action_matches_priority"],
    
    # Metadata
    created_at=datetime.now(),
    updated_at=datetime.now(),
    tags=["email", "priority", "ceo"]
)
```

### Adding Tasks to the Harness

1. **Create task file**: Add tasks to `app/eval/tasks/tasks_{agent}.py`

```python
# app/eval/tasks/tasks_myagent.py

from app.eval.models import GoldenTask, GoldenTaskInput, GoldenTaskExpected

TASKS = [
    GoldenTask(
        task_id="myagent_basic_001",
        agent_id="myagent",
        category="basic_function",
        description="Basic functionality test",
        difficulty="easy",
        input=GoldenTaskInput(...),
        expected=GoldenTaskExpected(...),
        invariants=["no_errors"]
    ),
    # Add more tasks...
]

def get_tasks():
    return TASKS
```

2. **Register in `__init__.py`**:

```python
# app/eval/tasks/__init__.py

from .tasks_myagent import get_tasks as get_myagent_tasks

TASK_REGISTRY = {
    "myagent": get_myagent_tasks,
    # ... other agents
}
```

### Task Design Best Practices

1. **Coverage**: Test all major agent functions
2. **Difficulty Mix**: Include easy, medium, and hard tasks (aim for 50% easy, 30% medium, 20% hard)
3. **Edge Cases**: Include boundary conditions and error scenarios
4. **Real Data**: Use sanitized production examples when possible
5. **Version Control**: Update tasks when agent capabilities change

## Customizing Judges

Judges score agent outputs. ApplyLens provides 4 default judges:

### Default Judges

1. **CorrectnessJudge**: Does output match expected values?
2. **RelevanceJudge**: Is output relevant to the input?
3. **SafetyJudge**: Does output avoid unsafe content?
4. **EfficiencyJudge**: Is execution fast enough?

### Creating Custom Judges

```python
from app.eval.judges import Judge, JudgeResult

class CustomJudge(Judge):
    """Judge that checks custom criteria."""
    
    def __init__(self):
        super().__init__(
            judge_id="custom",
            name="Custom Judge",
            weight=1.0  # Weight in overall score (0.0-1.0)
        )
    
    def evaluate(
        self,
        task: GoldenTask,
        agent_output: dict,
        agent_metadata: dict
    ) -> JudgeResult:
        """
        Evaluate agent output.
        
        Returns:
            JudgeResult with score (0-100), passed (bool), 
            reasoning (str), and details (dict)
        """
        score = 0.0
        reasoning = []
        
        # Custom scoring logic
        if self._check_criterion_1(agent_output):
            score += 50
            reasoning.append("✓ Criterion 1 passed")
        else:
            reasoning.append("✗ Criterion 1 failed")
        
        if self._check_criterion_2(agent_output):
            score += 50
            reasoning.append("✓ Criterion 2 passed")
        else:
            reasoning.append("✗ Criterion 2 failed")
        
        return JudgeResult(
            judge_id=self.judge_id,
            score=score,
            passed=score >= 70,  # Define pass threshold
            reasoning="\n".join(reasoning),
            details={
                "criterion_1": self._check_criterion_1(agent_output),
                "criterion_2": self._check_criterion_2(agent_output),
            }
        )
    
    def _check_criterion_1(self, output: dict) -> bool:
        # Implement custom logic
        return "required_field" in output
    
    def _check_criterion_2(self, output: dict) -> bool:
        # Implement custom logic
        return output.get("quality_score", 0) > 0.8
```

### Registering Custom Judges

```python
# In app/eval/judges.py or your custom module

from app.eval.runner import EvaluationRunner

# Add to judge registry
runner = EvaluationRunner(db)
runner.register_judge("custom", CustomJudge())

# Use in evaluation
results = runner.run_evaluation(
    agent_id="myagent",
    tasks=tasks,
    judges=["correctness", "custom"]  # Include your judge
)
```

### Judge Best Practices

1. **Clear Criteria**: Define explicit pass/fail conditions
2. **Detailed Reasoning**: Explain why scores were given
3. **Consistent Scoring**: Use same scale (0-100) as other judges
4. **Fast Execution**: Keep judge logic efficient (< 100ms per eval)
5. **Error Handling**: Gracefully handle malformed outputs

## Defining Invariants

Invariants are boolean checks that agent outputs must satisfy.

### Built-in Invariants

1. **no_pii_leak**: Output doesn't contain PII (email, SSN, credit card)
2. **valid_action**: Action is from allowed set
3. **action_priority_match**: High priority → urgent action
4. **valid_output_format**: Output matches expected schema

### Creating Custom Invariants

```python
from app.eval.models import Invariant, InvariantResult

class CustomInvariant(Invariant):
    """Check custom constraint."""
    
    def __init__(self):
        super().__init__(
            invariant_id="custom_check",
            name="Custom Check",
            description="Validates custom business logic",
            category="business_logic",
            severity="warning"  # or "critical"
        )
    
    def check(
        self,
        task: GoldenTask,
        agent_output: dict,
        agent_metadata: dict
    ) -> InvariantResult:
        """
        Check if invariant holds.
        
        Returns:
            InvariantResult with passed (bool), message (str),
            and details (dict)
        """
        # Custom validation logic
        passed = self._validate(agent_output)
        
        return InvariantResult(
            invariant_id=self.invariant_id,
            passed=passed,
            message="Validation passed" if passed else "Validation failed",
            details={
                "checked_field": agent_output.get("field"),
                "expected_range": (0, 100),
                "actual_value": agent_output.get("value")
            }
        )
    
    def _validate(self, output: dict) -> bool:
        # Implement validation
        value = output.get("value", 0)
        return 0 <= value <= 100
```

### Registering Invariants

```python
# In your evaluation setup

from app.eval.runner import EvaluationRunner

runner = EvaluationRunner(db)
runner.register_invariant("custom_check", CustomInvariant())

# Invariants are automatically checked during evaluation
```

### Invariant Best Practices

1. **Critical vs Warning**: Use `critical` for must-pass checks, `warning` for nice-to-have
2. **Fast Checks**: Keep invariant checks lightweight (< 10ms each)
3. **Clear Messages**: Provide actionable error messages
4. **Comprehensive**: Cover security, compliance, and business logic
5. **Versioning**: Update invariants as requirements change

## Best Practices

### 1. Regular Evaluation

Run evaluations:
- **Pre-commit**: Before merging agent changes
- **Daily**: Catch regressions early
- **Weekly**: Full evaluation suite with all tasks

### 2. Progressive Difficulty

Start with easy tasks, gradually add harder ones:
- Week 1: 10 easy tasks
- Week 2: Add 5 medium tasks
- Week 3: Add 3 hard tasks
- Week 4: Add edge cases

### 3. Monitor Trends

Track metrics over time:
- Quality score trends
- Latency trends
- Invariant violation rates
- User feedback ratings

### 4. Use Budgets

Set quality gates (see [BUDGETS_AND_GATES.md](./BUDGETS_AND_GATES.md)):
```python
budgets = {
    "quality_threshold": 85,  # Minimum quality score
    "latency_p95_ms": 2000,   # Maximum p95 latency
    "success_rate": 0.95      # Minimum success rate
}
```

### 5. Iterate Based on Failures

When tasks fail:
1. Review judge reasoning
2. Check invariant violations
3. Fix agent logic or update task expectations
4. Re-run evaluation to verify

### 6. Balance Online & Offline

- **Offline**: Comprehensive testing in controlled environment
- **Online**: Real-world validation with production data
- **Correlation**: Ensure offline scores predict online performance

### 7. Version Control

Track evaluation artifacts:
- Golden tasks in git
- Evaluation results in database
- Judge weights in configuration
- Invariants as code

## Next Steps

- See [BUDGETS_AND_GATES.md](./BUDGETS_AND_GATES.md) for quality gates
- See [INTELLIGENCE_REPORT.md](./INTELLIGENCE_REPORT.md) for weekly reports
- See [DASHBOARD_ALERTS.md](./DASHBOARD_ALERTS.md) for monitoring setup
- See [REDTEAM.md](./REDTEAM.md) for adversarial testing
