"""
REST API endpoints for SLO monitoring and alerting.
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.observability.slo import (
    SLOStatus,
    SLOSpec,
    get_slo_evaluator,
)
from app.observability.alerts import (
    Alert,
    AlertManager,
    export_prometheus_metrics,
    get_alert_manager,
)


router = APIRouter(prefix="/observability", tags=["observability"])


class AcknowledgeRequest(BaseModel):
    """Request to acknowledge an alert."""
    acknowledged_by: str


class SLOSummary(BaseModel):
    """Summary of SLO status."""
    agent_name: str
    compliant: bool
    violation_count: int
    burn_rate_alert: bool


@router.get("/slo/agents", response_model=List[str])
async def list_agents():
    """List all agents with SLO definitions."""
    evaluator = get_slo_evaluator()
    return evaluator.list_agents()


@router.get("/slo/{agent_name}", response_model=SLOStatus)
async def get_agent_slo_status(agent_name: str):
    """
    Get current SLO status for an agent.
    
    This endpoint returns the latest SLO evaluation for the specified agent,
    including compliance status, violations, and burn rates.
    """
    evaluator = get_slo_evaluator()
    
    # In production, this would fetch real metrics from telemetry
    # For now, return a mock status
    slo = evaluator.get_slo(agent_name)
    if not slo:
        raise HTTPException(status_code=404, detail=f"No SLO defined for agent: {agent_name}")
    
    # Mock metrics - in production, fetch from telemetry
    metrics = {}
    
    status = evaluator.evaluate(agent_name, metrics)
    return status


@router.get("/slo/{agent_name}/spec", response_model=SLOSpec)
async def get_agent_slo_spec(agent_name: str):
    """Get SLO specification for an agent."""
    evaluator = get_slo_evaluator()
    
    slo = evaluator.get_slo(agent_name)
    if not slo:
        raise HTTPException(status_code=404, detail=f"No SLO defined for agent: {agent_name}")
    
    return slo


@router.get("/alerts", response_model=List[Alert])
async def get_alerts(
    agent_name: Optional[str] = Query(None, description="Filter by agent name"),
    severity: Optional[str] = Query(None, description="Filter by severity (INFO, WARNING, CRITICAL)"),
):
    """
    Get active alerts.
    
    Optionally filter by agent name and/or severity level.
    """
    manager = get_alert_manager()
    
    # Parse severity
    severity_enum = None
    if severity:
        from app.observability.slo import SLOSeverity
        try:
            severity_enum = SLOSeverity[severity.upper()]
        except KeyError:
            raise HTTPException(status_code=400, detail=f"Invalid severity: {severity}")
    
    alerts = manager.get_active_alerts(agent_name=agent_name, severity=severity_enum)
    return alerts


@router.post("/alerts/{alert_key}/acknowledge")
async def acknowledge_alert(alert_key: str, request: AcknowledgeRequest):
    """
    Acknowledge an alert.
    
    Marks the alert as acknowledged and records who acknowledged it.
    """
    manager = get_alert_manager()
    
    success = manager.acknowledge_alert(alert_key, request.acknowledged_by)
    if not success:
        raise HTTPException(status_code=404, detail=f"Alert not found: {alert_key}")
    
    return {"status": "acknowledged", "alert_key": alert_key}


@router.post("/alerts/{alert_key}/resolve")
async def resolve_alert(alert_key: str):
    """
    Resolve an alert.
    
    Marks the alert as resolved and removes it from active alerts.
    """
    manager = get_alert_manager()
    
    success = manager.resolve_alert(alert_key)
    if not success:
        raise HTTPException(status_code=404, detail=f"Alert not found: {alert_key}")
    
    return {"status": "resolved", "alert_key": alert_key}


@router.get("/alerts/summary")
async def get_alert_summary():
    """
    Get summary of active alerts.
    
    Returns counts by severity and status.
    """
    manager = get_alert_manager()
    return manager.get_alert_summary()


@router.get("/metrics", response_class=None)
async def get_prometheus_metrics():
    """
    Prometheus metrics endpoint.
    
    Returns SLO metrics in OpenMetrics format for Prometheus scraping.
    """
    evaluator = get_slo_evaluator()
    
    # Collect metrics for all agents
    all_metrics = []
    for agent_name in evaluator.list_agents():
        # In production, fetch real metrics from telemetry
        status = evaluator.evaluate(agent_name, {})
        metrics_text = export_prometheus_metrics(status)
        all_metrics.append(metrics_text)
    
    combined = "\n".join(all_metrics)
    
    # Return as plain text with proper content type
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(content=combined, media_type="text/plain; version=0.0.4")
