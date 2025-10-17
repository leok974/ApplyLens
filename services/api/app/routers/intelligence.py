"""
API endpoints for intelligence reporting.

Provides REST API for:
- Generating reports on-demand
- Retrieving latest report
- Listing report history
- Scheduling reports
"""
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from ..db import get_db
from ..eval.intelligence_report import ReportGenerator, format_report_as_html


router = APIRouter(
    prefix="/intelligence",
    tags=["intelligence"],
)


# Pydantic schemas
class ReportRequest(BaseModel):
    """Request to generate a report."""
    week_start: Optional[datetime] = Field(
        None,
        description="Start of week (Monday). Defaults to last Monday.",
    )
    format: str = Field(
        "markdown",
        description="Output format: 'markdown' or 'html'",
    )


class ReportResponse(BaseModel):
    """Generated report response."""
    week_start: datetime = Field(..., description="Week start date")
    week_end: datetime = Field(..., description="Week end date")
    generated_at: datetime = Field(..., description="Report generation timestamp")
    format: str = Field(..., description="Report format")
    content: str = Field(..., description="Report content")
    summary: dict = Field(..., description="Report summary statistics")


class ReportSummary(BaseModel):
    """Summary of a generated report."""
    week_start: datetime
    generated_at: datetime
    total_agents: int
    passing_agents: int
    total_violations: int
    critical_violations: int
    status: str  # "operational", "warnings", "critical"


# API endpoints
@router.post("/report/generate", response_model=ReportResponse)
async def generate_report(
    request: ReportRequest,
    db: Session = Depends(get_db),
):
    """
    Generate intelligence report for specified week.
    
    Returns markdown or HTML formatted report with:
    - Quality trends
    - Budget violations
    - Invariant status
    - Red team results
    - Recommendations
    """
    # Determine week start
    if request.week_start:
        week_start = request.week_start
        # Ensure it's a Monday
        if week_start.weekday() != 0:
            week_start = week_start - timedelta(days=week_start.weekday())
    else:
        # Default to last Monday
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today - timedelta(days=today.weekday())
    
    week_end = week_start + timedelta(days=7)
    
    # Generate report
    generator = ReportGenerator(db)
    report_content = generator.generate_weekly_report(week_start=week_start)
    
    # Convert to HTML if requested
    if request.format == "html":
        report_content = format_report_as_html(report_content)
    
    # Extract summary statistics
    from ..eval.budgets import GateEvaluator
    gate_evaluator = GateEvaluator(db)
    gate_results = gate_evaluator.evaluate_all_agents(lookback_days=7, baseline_days=7)
    
    summary = {
        "total_agents": len(gate_results["results"]),
        "passing_agents": sum(1 for r in gate_results["results"].values() if r["passed"]),
        "total_violations": gate_results["total_violations"],
        "critical_violations": gate_results["critical_violations"],
        "status": "operational" if gate_results["passed"] else "critical" if gate_results["critical_violations"] > 0 else "warnings",
    }
    
    return ReportResponse(
        week_start=week_start,
        week_end=week_end,
        generated_at=datetime.utcnow(),
        format=request.format,
        content=report_content,
        summary=summary,
    )


@router.get("/report/latest", response_model=ReportResponse)
async def get_latest_report(
    format: str = Query("markdown", description="Output format: 'markdown' or 'html'"),
    db: Session = Depends(get_db),
):
    """
    Get latest intelligence report (current week).
    
    Generates report for the current week (last Monday to today).
    """
    request = ReportRequest(format=format)
    return await generate_report(request, db)


@router.get("/report/summary", response_model=ReportSummary)
async def get_report_summary(
    week_start: Optional[datetime] = Query(None, description="Week start date (Monday)"),
    db: Session = Depends(get_db),
):
    """
    Get summary of report without full content.
    
    Useful for dashboard widgets showing current status.
    """
    # Determine week start
    if week_start:
        if week_start.weekday() != 0:
            week_start = week_start - timedelta(days=week_start.weekday())
    else:
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today - timedelta(days=today.weekday())
    
    # Get gate results
    from ..eval.budgets import GateEvaluator
    gate_evaluator = GateEvaluator(db)
    gate_results = gate_evaluator.evaluate_all_agents(lookback_days=7, baseline_days=7)
    
    total_agents = len(gate_results["results"])
    passing_agents = sum(1 for r in gate_results["results"].values() if r["passed"])
    
    status = "operational"
    if gate_results["critical_violations"] > 0:
        status = "critical"
    elif not gate_results["passed"]:
        status = "warnings"
    
    return ReportSummary(
        week_start=week_start,
        generated_at=datetime.utcnow(),
        total_agents=total_agents,
        passing_agents=passing_agents,
        total_violations=gate_results["total_violations"],
        critical_violations=gate_results["critical_violations"],
        status=status,
    )


@router.get("/report/history", response_model=List[ReportSummary])
async def get_report_history(
    weeks: int = Query(4, ge=1, le=52, description="Number of weeks to retrieve"),
    db: Session = Depends(get_db),
):
    """
    Get historical report summaries.
    
    Returns summary statistics for the past N weeks.
    Useful for trending and historical analysis.
    """
    from ..eval.budgets import GateEvaluator
    
    summaries = []
    gate_evaluator = GateEvaluator(db)
    
    # Get current Monday
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    current_monday = today - timedelta(days=today.weekday())
    
    # Generate summaries for past N weeks
    for i in range(weeks):
        week_start = current_monday - timedelta(weeks=i)
        
        # Get metrics for this week
        gate_results = gate_evaluator.evaluate_all_agents(
            lookback_days=7,
            baseline_days=7,
        )
        
        total_agents = len(gate_results["results"])
        passing_agents = sum(1 for r in gate_results["results"].values() if r["passed"])
        
        status = "operational"
        if gate_results["critical_violations"] > 0:
            status = "critical"
        elif not gate_results["passed"]:
            status = "warnings"
        
        summaries.append(ReportSummary(
            week_start=week_start,
            generated_at=datetime.utcnow(),
            total_agents=total_agents,
            passing_agents=passing_agents,
            total_violations=gate_results["total_violations"],
            critical_violations=gate_results["critical_violations"],
            status=status,
        ))
    
    return summaries


@router.post("/report/notify")
async def notify_report(
    week_start: Optional[datetime] = None,
    slack_webhook: Optional[str] = None,
    email_recipients: Optional[List[str]] = None,
    db: Session = Depends(get_db),
):
    """
    Generate and send report via Slack/email.
    
    Requires either slack_webhook or email_recipients.
    """
    if not slack_webhook and not email_recipients:
        raise HTTPException(
            status_code=400,
            detail="Must provide slack_webhook or email_recipients"
        )
    
    # Determine week start
    if week_start:
        if week_start.weekday() != 0:
            week_start = week_start - timedelta(days=week_start.weekday())
    else:
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today - timedelta(days=today.weekday())
    
    # Generate report
    generator = ReportGenerator(db)
    report = generator.generate_weekly_report(week_start=week_start)
    
    results = {
        "week_start": week_start.isoformat(),
        "slack_sent": False,
        "email_sent": False,
        "errors": [],
    }
    
    # Send to Slack
    if slack_webhook:
        try:
            import requests
            response = requests.post(
                slack_webhook,
                json={"text": report},
                timeout=10,
            )
            if response.status_code == 200:
                results["slack_sent"] = True
            else:
                results["errors"].append(f"Slack error: {response.status_code}")
        except Exception as e:
            results["errors"].append(f"Slack error: {str(e)}")
    
    # Send email
    if email_recipients:
        try:
            from .generate_report import send_email
            send_email(
                report,
                email_recipients,
                subject=f"Agent Intelligence Report - {week_start.strftime('%Y-%m-%d')}"
            )
            results["email_sent"] = True
        except Exception as e:
            results["errors"].append(f"Email error: {str(e)}")
    
    return results
