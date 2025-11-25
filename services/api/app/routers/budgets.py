"""
API endpoints for budget management and gate evaluation.

Provides:
- GET /budgets - List all budgets
- GET /budgets/{agent} - Get budget for specific agent
- POST /budgets/{agent} - Create/update budget
- POST /budgets/evaluate - Run gate evaluation
- GET /budgets/violations - Get recent violations
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..db import get_db
from ..eval.budgets import (
    GateEvaluator,
    DEFAULT_BUDGETS,
    format_gate_report,
)
from ..config import agent_settings


router = APIRouter(prefix="/budgets", tags=["budgets"])


# ===== Request/Response Models =====


class BudgetSchema(BaseModel):
    """Budget configuration."""

    agent: str
    min_quality_score: Optional[float] = Field(None, ge=0, le=100)
    min_success_rate: Optional[float] = Field(None, ge=0, le=1)
    max_avg_latency_ms: Optional[float] = Field(None, gt=0)
    max_p95_latency_ms: Optional[float] = Field(None, gt=0)
    max_p99_latency_ms: Optional[float] = Field(None, gt=0)
    max_avg_cost_weight: Optional[float] = Field(None, gt=0)
    max_invariant_failures: int = Field(0, ge=0)
    description: Optional[str] = None
    enabled: bool = True


class BudgetResponse(BaseModel):
    """Budget response."""

    budget: BudgetSchema
    is_default: bool


class EvaluateRequest(BaseModel):
    """Gate evaluation request."""

    agent: Optional[str] = None
    lookback_days: int = Field(7, ge=1, le=90)
    baseline_days: int = Field(14, ge=1, le=180)


class ViolationSchema(BaseModel):
    """Budget violation."""

    agent: str
    budget_type: str
    threshold: float
    actual: float
    severity: str
    message: str
    date: datetime


class EvaluationResponse(BaseModel):
    """Gate evaluation response."""

    passed: bool
    violations: List[ViolationSchema]
    current_metrics: Optional[Dict[str, Any]] = None
    baseline_metrics: Optional[Dict[str, Any]] = None
    agent: Optional[str] = None
    total_violations: Optional[int] = None
    critical_violations: Optional[int] = None
    evaluated_agents: Optional[List[str]] = None


# ===== Endpoints =====


@router.get("/", response_model=Dict[str, BudgetResponse])
async def list_budgets():
    """
    List all agent budgets.

    Returns default budgets (customization not implemented yet).
    """
    response = {}
    for agent, budget in DEFAULT_BUDGETS.items():
        response[agent] = BudgetResponse(
            budget=BudgetSchema(
                agent=budget.agent,
                min_quality_score=budget.min_quality_score,
                min_success_rate=budget.min_success_rate,
                max_avg_latency_ms=budget.max_avg_latency_ms,
                max_p95_latency_ms=budget.max_p95_latency_ms,
                max_p99_latency_ms=budget.max_p99_latency_ms,
                max_avg_cost_weight=budget.max_avg_cost_weight,
                max_invariant_failures=budget.max_invariant_failures,
                description=budget.description,
                enabled=budget.enabled,
            ),
            is_default=True,
        )
    return response


@router.get("/{agent}", response_model=BudgetResponse)
async def get_budget(agent: str):
    """
    Get budget for specific agent.

    Args:
        agent: Agent identifier

    Returns:
        Budget configuration
    """
    if agent not in DEFAULT_BUDGETS:
        raise HTTPException(
            status_code=404, detail=f"No budget found for agent: {agent}"
        )

    budget = DEFAULT_BUDGETS[agent]
    return BudgetResponse(
        budget=BudgetSchema(
            agent=budget.agent,
            min_quality_score=budget.min_quality_score,
            min_success_rate=budget.min_success_rate,
            max_avg_latency_ms=budget.max_avg_latency_ms,
            max_p95_latency_ms=budget.max_p95_latency_ms,
            max_p99_latency_ms=budget.max_p99_latency_ms,
            max_avg_cost_weight=budget.max_avg_cost_weight,
            max_invariant_failures=budget.max_invariant_failures,
            description=budget.description,
            enabled=budget.enabled,
        ),
        is_default=True,
    )


@router.post("/evaluate", response_model=EvaluationResponse)
async def evaluate_gates(
    request: EvaluateRequest,
    db: Session = Depends(get_db),
):
    """
    Run gate evaluation against budgets.

    Evaluates agent metrics against budget thresholds and baseline.
    Used in CI to fail builds on regressions.

    Args:
        request: Evaluation parameters
        db: Database session

    Returns:
        Evaluation results with violations
    """
    if not agent_settings.EVAL_BUDGETS_ENABLED:
        return EvaluationResponse(
            passed=True,
            violations=[],
            current_metrics={},
            baseline_metrics={},
        )

    evaluator = GateEvaluator(db)

    if request.agent:
        # Single agent
        result = evaluator.evaluate_agent(
            agent=request.agent,
            lookback_days=request.lookback_days,
            baseline_days=request.baseline_days,
        )

        return EvaluationResponse(
            passed=result["passed"],
            violations=[
                ViolationSchema(
                    agent=v.agent,
                    budget_type=v.budget_type,
                    threshold=v.threshold,
                    actual=v.actual,
                    severity=v.severity,
                    message=v.message,
                    date=v.date,
                )
                for v in result["violations"]
            ],
            current_metrics=result.get("current_metrics"),
            baseline_metrics=result.get("baseline_metrics"),
            agent=result.get("agent"),
        )
    else:
        # All agents
        result = evaluator.evaluate_all_agents(
            lookback_days=request.lookback_days,
            baseline_days=request.baseline_days,
        )

        # Flatten violations from all agents
        all_violations = []
        for agent_result in result["results"].values():
            all_violations.extend(agent_result["violations"])

        return EvaluationResponse(
            passed=result["passed"],
            violations=[
                ViolationSchema(
                    agent=v.agent,
                    budget_type=v.budget_type,
                    threshold=v.threshold,
                    actual=v.actual,
                    severity=v.severity,
                    message=v.message,
                    date=v.date,
                )
                for v in all_violations
            ],
            total_violations=result["total_violations"],
            critical_violations=result["critical_violations"],
            evaluated_agents=result["evaluated_agents"],
        )


@router.get("/violations/recent", response_model=List[ViolationSchema])
async def get_recent_violations(
    agent: Optional[str] = Query(None, description="Filter by agent"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    days: int = Query(7, ge=1, le=90, description="Days to look back"),
    db: Session = Depends(get_db),
):
    """
    Get recent budget violations.

    Args:
        agent: Optional agent filter
        severity: Optional severity filter (critical, error, warning)
        days: Days to look back
        db: Database session

    Returns:
        List of recent violations
    """
    evaluator = GateEvaluator(db)

    # Run evaluation to get violations
    if agent:
        result = evaluator.evaluate_agent(agent=agent, lookback_days=days)
        violations = result["violations"]
    else:
        result = evaluator.evaluate_all_agents(lookback_days=days)
        violations = []
        for agent_result in result["results"].values():
            violations.extend(agent_result["violations"])

    # Filter by severity
    if severity:
        violations = [v for v in violations if v.severity == severity]

    return [
        ViolationSchema(
            agent=v.agent,
            budget_type=v.budget_type,
            threshold=v.threshold,
            actual=v.actual,
            severity=v.severity,
            message=v.message,
            date=v.date,
        )
        for v in violations
    ]


@router.post("/evaluate/report")
async def evaluate_gates_report(
    request: EvaluateRequest,
    db: Session = Depends(get_db),
):
    """
    Run gate evaluation and return formatted report.

    Returns human-readable markdown report suitable for:
    - CI output
    - Slack notifications
    - Email alerts

    Args:
        request: Evaluation parameters
        db: Database session

    Returns:
        Markdown formatted report
    """
    evaluator = GateEvaluator(db)

    if request.agent:
        result = evaluator.evaluate_agent(
            agent=request.agent,
            lookback_days=request.lookback_days,
            baseline_days=request.baseline_days,
        )
    else:
        result = evaluator.evaluate_all_agents(
            lookback_days=request.lookback_days,
            baseline_days=request.baseline_days,
        )

    report = format_gate_report(result)

    return {
        "passed": result["passed"],
        "report": report,
    }
