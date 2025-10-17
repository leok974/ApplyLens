"""
API endpoints for evaluation metrics and monitoring.

Provides:
- Metrics export endpoints
- Dashboard integration
- Alert status
"""
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from typing import Dict, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from ..db import get_db
from ..eval.metrics import get_metrics_exporter
from ..eval.budgets import GateEvaluator


router = APIRouter(
    prefix="/metrics",
    tags=["metrics"],
)


# Pydantic schemas
class MetricsExportResponse(BaseModel):
    """Response from metrics export."""
    success: bool = Field(..., description="Export succeeded")
    agents_exported: int = Field(..., description="Number of agents exported")
    metrics_exported: int = Field(..., description="Number of metric records processed")
    days_covered: int = Field(..., description="Days of data covered")
    exported_at: datetime = Field(..., description="Export timestamp")


class DashboardStatus(BaseModel):
    """Dashboard health status."""
    agents: list[str] = Field(..., description="List of monitored agents")
    total_agents: int = Field(..., description="Total number of agents")
    passing_gates: int = Field(..., description="Agents passing quality gates")
    failing_gates: int = Field(..., description="Agents failing quality gates")
    active_violations: int = Field(..., description="Active budget violations")
    last_updated: datetime = Field(..., description="Last metrics update")


class AlertSummary(BaseModel):
    """Summary of active alerts."""
    total_alerts: int = Field(..., description="Total active alerts")
    critical_alerts: int = Field(..., description="Critical severity alerts")
    warning_alerts: int = Field(..., description="Warning severity alerts")
    alerts_by_agent: Dict[str, int] = Field(..., description="Alerts grouped by agent")
    alerts_by_type: Dict[str, int] = Field(..., description="Alerts grouped by type")


# API endpoints
@router.post("/export", response_model=MetricsExportResponse)
async def export_metrics(
    lookback_days: int = Query(1, ge=1, le=30, description="Days to export"),
    db: Session = Depends(get_db),
):
    """
    Export agent evaluation metrics to Prometheus.
    
    This endpoint updates Prometheus gauges and counters with the latest
    agent metrics from the database. Call this periodically (e.g., every 30s)
    or trigger on-demand.
    
    The metrics are then scraped by Prometheus and displayed in Grafana.
    """
    exporter = get_metrics_exporter(db)
    stats = exporter.export_all_metrics(lookback_days=lookback_days)
    
    return MetricsExportResponse(
        success=True,
        agents_exported=stats['agents_exported'],
        metrics_exported=stats['metrics_exported'],
        days_covered=stats['days_covered'],
        exported_at=datetime.utcnow(),
    )


@router.get("/dashboard/status", response_model=DashboardStatus)
async def get_dashboard_status(
    db: Session = Depends(get_db),
):
    """
    Get current dashboard status for UI widgets.
    
    Returns summary statistics for displaying in web dashboards
    or status pages.
    """
    # Get gate evaluation results
    evaluator = GateEvaluator(db)
    gate_results = evaluator.evaluate_all_agents(lookback_days=7, baseline_days=7)
    
    agents = list(gate_results["results"].keys())
    passing = sum(1 for r in gate_results["results"].values() if r["passed"])
    failing = len(agents) - passing
    
    return DashboardStatus(
        agents=agents,
        total_agents=len(agents),
        passing_gates=passing,
        failing_gates=failing,
        active_violations=gate_results["total_violations"],
        last_updated=datetime.utcnow(),
    )


@router.get("/alerts/summary", response_model=AlertSummary)
async def get_alert_summary(
    db: Session = Depends(get_db),
):
    """
    Get summary of active alerts.
    
    Note: This is a simplified version. In production, you'd query
    Prometheus Alertmanager API for actual active alerts.
    
    For now, we derive alerts from budget violations.
    """
    evaluator = GateEvaluator(db)
    gate_results = evaluator.evaluate_all_agents(lookback_days=7, baseline_days=7)
    
    # Count violations as "alerts"
    total_critical = 0
    total_warnings = 0
    alerts_by_agent: Dict[str, int] = {}
    alerts_by_type: Dict[str, int] = {}
    
    for agent, result in gate_results["results"].items():
        violation_count = len(result["violations"])
        if violation_count > 0:
            alerts_by_agent[agent] = violation_count
        
        for v in result["violations"]:
            # Count by severity
            if v.severity == "critical":
                total_critical += 1
            else:
                total_warnings += 1
            
            # Count by type
            budget_type = v.budget_type
            alerts_by_type[budget_type] = alerts_by_type.get(budget_type, 0) + 1
    
    return AlertSummary(
        total_alerts=total_critical + total_warnings,
        critical_alerts=total_critical,
        warning_alerts=total_warnings,
        alerts_by_agent=alerts_by_agent,
        alerts_by_type=alerts_by_type,
    )


@router.get("/health")
async def metrics_health():
    """
    Health check for metrics system.
    
    Returns 200 if metrics exporter is functioning.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "prometheus_enabled": True,
        "grafana_dashboard": "/grafana/agent_evaluation_dashboard.json",
        "alert_rules": "/prometheus/agent_alerts.yml",
    }
