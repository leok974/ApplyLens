"""
Agent feedback and telemetry API endpoints.

Provides:
- POST /agents/feedback - Submit user feedback on agent outputs
- GET /agents/metrics/{agent} - Get metrics for an agent
- GET /agents/health - Get health status across all agents
- POST /agents/redteam/run - Run red-team evaluation
"""
from typing import Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..db import get_db
from ..eval.telemetry import (
    FeedbackCollector,
    OnlineEvaluator,
    RedTeamCatalog,
    MetricsAggregator,
)
from ..eval.runner import EvalRunner
from ..models import AgentMetricsDaily


router = APIRouter(prefix="/agents", tags=["agents"])


# ===== Request/Response Models =====


class FeedbackRequest(BaseModel):
    """User feedback on an agent run."""
    
    agent: str = Field(..., description="Agent identifier")
    run_id: str = Field(..., description="Unique run identifier")
    feedback_type: str = Field(..., description="thumbs_up or thumbs_down")
    comment: Optional[str] = Field(None, description="Optional user comment")
    context: Optional[dict] = Field(None, description="Additional context")
    
    class Config:
        schema_extra = {
            "example": {
                "agent": "inbox.triage",
                "run_id": "run_abc123",
                "feedback_type": "thumbs_up",
                "comment": "Correctly identified phishing email",
                "context": {"task": "phishing_detection"}
            }
        }


class FeedbackResponse(BaseModel):
    """Feedback submission response."""
    
    status: str = "success"
    message: str = "Feedback recorded"


class AgentMetricsResponse(BaseModel):
    """Agent metrics for a date range."""
    
    agent: str
    start_date: datetime
    end_date: datetime
    total_runs: int
    success_rate: float
    avg_quality_score: Optional[float]
    satisfaction_rate: Optional[float]
    avg_latency_ms: Optional[float]
    total_cost_weight: float
    invariants_failed_count: int
    failed_invariant_ids: list[str]


class AgentHealthStatus(BaseModel):
    """Health status for an agent."""
    
    agent: str
    status: str  # healthy, degraded, critical
    success_rate: float
    quality_score: Optional[float]
    issues: list[str]


class AllAgentsHealthResponse(BaseModel):
    """Health status across all agents."""
    
    timestamp: datetime
    agents: list[AgentHealthStatus]
    overall_status: str  # healthy, degraded, critical


class RedTeamRunResponse(BaseModel):
    """Red-team evaluation run response."""
    
    run_id: str
    total_tasks: int
    passed: int
    failed: int
    success_rate: float
    avg_quality_score: float
    failed_task_ids: list[str]


# ===== Endpoints =====


@router.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(
    request: FeedbackRequest,
    db: Session = Depends(get_db),
):
    """
    Submit user feedback on an agent run.
    
    This helps track user satisfaction and quality signals.
    """
    if request.feedback_type not in ["thumbs_up", "thumbs_down"]:
        raise HTTPException(
            status_code=400,
            detail="feedback_type must be 'thumbs_up' or 'thumbs_down'"
        )
    
    collector = FeedbackCollector(db)
    collector.record_feedback(
        agent=request.agent,
        run_id=request.run_id,
        feedback_type=request.feedback_type,
        comment=request.comment,
        context=request.context,
    )
    
    return FeedbackResponse()


@router.get("/metrics/{agent}", response_model=AgentMetricsResponse)
async def get_agent_metrics(
    agent: str,
    start_date: Optional[datetime] = Query(None, description="Start date (default: 7 days ago)"),
    end_date: Optional[datetime] = Query(None, description="End date (default: today)"),
    db: Session = Depends(get_db),
):
    """
    Get aggregated metrics for an agent over a date range.
    """
    if not end_date:
        end_date = datetime.utcnow()
    if not start_date:
        start_date = end_date - timedelta(days=7)
    
    aggregator = MetricsAggregator(db)
    metrics = aggregator.get_agent_metrics(agent, start_date, end_date)
    
    if not metrics:
        return AgentMetricsResponse(
            agent=agent,
            start_date=start_date,
            end_date=end_date,
            total_runs=0,
            success_rate=0.0,
            avg_quality_score=None,
            satisfaction_rate=None,
            avg_latency_ms=None,
            total_cost_weight=0.0,
            invariants_failed_count=0,
            failed_invariant_ids=[],
        )
    
    # Aggregate across all days
    total_runs = sum(m.total_runs for m in metrics)
    successful_runs = sum(m.successful_runs for m in metrics)
    
    # Weighted averages
    quality_scores = [
        m.avg_quality_score * m.quality_samples
        for m in metrics
        if m.avg_quality_score and m.quality_samples > 0
    ]
    quality_samples = sum(m.quality_samples for m in metrics if m.quality_samples > 0)
    avg_quality = sum(quality_scores) / quality_samples if quality_samples > 0 else None
    
    latencies = [
        m.avg_latency_ms * m.total_runs
        for m in metrics
        if m.avg_latency_ms
    ]
    avg_latency = sum(latencies) / total_runs if total_runs > 0 and latencies else None
    
    thumbs_up = sum(m.thumbs_up for m in metrics)
    thumbs_down = sum(m.thumbs_down for m in metrics)
    satisfaction = (
        thumbs_up / (thumbs_up + thumbs_down)
        if (thumbs_up + thumbs_down) > 0
        else None
    )
    
    total_cost = sum(m.total_cost_weight for m in metrics)
    
    failed_invariants = set()
    for m in metrics:
        if m.failed_invariant_ids:
            failed_invariants.update(m.failed_invariant_ids)
    
    return AgentMetricsResponse(
        agent=agent,
        start_date=start_date,
        end_date=end_date,
        total_runs=total_runs,
        success_rate=successful_runs / total_runs if total_runs > 0 else 0.0,
        avg_quality_score=avg_quality,
        satisfaction_rate=satisfaction,
        avg_latency_ms=avg_latency,
        total_cost_weight=total_cost,
        invariants_failed_count=len(failed_invariants),
        failed_invariant_ids=list(failed_invariants),
    )


@router.get("/health", response_model=AllAgentsHealthResponse)
async def get_all_agents_health(
    db: Session = Depends(get_db),
):
    """
    Get health status across all agents.
    
    Returns overall health and per-agent status.
    """
    agents = ["inbox.triage", "knowledge.update", "insights.write", "warehouse.health"]
    
    aggregator = MetricsAggregator(db)
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=1)  # Last 24 hours
    
    agent_statuses = []
    critical_count = 0
    degraded_count = 0
    
    for agent in agents:
        metrics = aggregator.get_agent_metrics(agent, start_date, end_date)
        
        if not metrics:
            agent_statuses.append(AgentHealthStatus(
                agent=agent,
                status="unknown",
                success_rate=0.0,
                quality_score=None,
                issues=["No recent data"],
            ))
            continue
        
        # Aggregate metrics
        total_runs = sum(m.total_runs for m in metrics)
        successful_runs = sum(m.successful_runs for m in metrics)
        success_rate = successful_runs / total_runs if total_runs > 0 else 0.0
        
        quality_scores = [
            m.avg_quality_score * m.quality_samples
            for m in metrics
            if m.avg_quality_score and m.quality_samples > 0
        ]
        quality_samples = sum(m.quality_samples for m in metrics if m.quality_samples > 0)
        avg_quality = sum(quality_scores) / quality_samples if quality_samples > 0 else None
        
        # Determine status
        issues = []
        status = "healthy"
        
        if success_rate < 0.95:
            issues.append(f"Low success rate: {success_rate:.1%}")
            status = "degraded"
            degraded_count += 1
        
        if avg_quality and avg_quality < 70.0:
            issues.append(f"Low quality score: {avg_quality:.1f}")
            status = "degraded" if status == "healthy" else "critical"
            if status == "critical":
                critical_count += 1
        
        # Check for invariant failures
        failed_invariants = set()
        for m in metrics:
            if m.failed_invariant_ids:
                failed_invariants.update(m.failed_invariant_ids)
        
        if failed_invariants:
            issues.append(f"Invariant failures: {', '.join(failed_invariants)}")
            status = "critical"
            critical_count += 1
        
        agent_statuses.append(AgentHealthStatus(
            agent=agent,
            status=status,
            success_rate=success_rate,
            quality_score=avg_quality,
            issues=issues,
        ))
    
    # Overall status
    if critical_count > 0:
        overall_status = "critical"
    elif degraded_count > 0:
        overall_status = "degraded"
    else:
        overall_status = "healthy"
    
    return AllAgentsHealthResponse(
        timestamp=datetime.utcnow(),
        agents=agent_statuses,
        overall_status=overall_status,
    )


@router.post("/redteam/run", response_model=RedTeamRunResponse)
async def run_redteam_evaluation(
    agent: Optional[str] = Query(None, description="Specific agent to test (default: all)"),
):
    """
    Run red-team adversarial evaluation.
    
    Tests agent robustness against:
    - Edge cases
    - Evasion attacks
    - Boundary conditions
    - Stress tests
    """
    # Get red-team tasks
    if agent:
        # Get tasks for specific agent
        task_getters = {
            "inbox.triage": RedTeamCatalog.get_inbox_redteam_tasks,
            "knowledge.update": RedTeamCatalog.get_knowledge_redteam_tasks,
            "insights.write": RedTeamCatalog.get_insights_redteam_tasks,
            "warehouse.health": RedTeamCatalog.get_warehouse_redteam_tasks,
        }
        
        if agent not in task_getters:
            raise HTTPException(status_code=404, detail=f"Unknown agent: {agent}")
        
        tasks = task_getters[agent]()
    else:
        # All red-team tasks
        tasks = RedTeamCatalog.get_all_redteam_tasks()
    
    if not tasks:
        raise HTTPException(status_code=404, detail="No red-team tasks available")
    
    # Run evaluation
    from ..eval.models import EvalSuite
    import uuid
    
    suite = EvalSuite(
        name=f"redteam_{agent or 'all'}",
        agent=agent or "all",
        version="1.0",
        tasks=tasks,
    )
    
    runner = EvalRunner(use_mock_executor=True)
    run = runner.run_suite(suite)
    
    # Count pass/fail
    passed = sum(1 for r in run.results if r.success and r.quality_score >= 70.0)
    failed = run.total_tasks - passed
    
    failed_task_ids = [
        r.task_id
        for r in run.results
        if not r.success or r.quality_score < 70.0
    ]
    
    return RedTeamRunResponse(
        run_id=run.run_id,
        total_tasks=run.total_tasks,
        passed=passed,
        failed=failed,
        success_rate=passed / run.total_tasks,
        avg_quality_score=run.avg_quality_score,
        failed_task_ids=failed_task_ids,
    )
