"""Guard API endpoints for regression detection and rollback control.

Provides:
- Status endpoint for canary health
- Manual rollback trigger
- Regression evaluation on-demand
- Rollback audit history
"""

from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db import get_db
from ..models_runtime import RuntimeSettingsDAO
from ..guard.regression_detector import RegressionDetector, MetricsStore


router = APIRouter(prefix="/guard", tags=["guard"])


class RollbackRequest(BaseModel):
    """Manual rollback request."""
    reason: str
    updated_by: str = "admin"


class CanaryUpdateRequest(BaseModel):
    """Update canary configuration."""
    canary_pct: float | None = None
    kill_switch: bool | None = None
    updated_by: str = "admin"
    reason: str | None = None


@router.get("/status")
async def get_canary_status(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Get current canary status and recent performance.
    
    Returns:
        Canary configuration, V1 vs V2 stats, and breach indicators
    """
    settings_dao = RuntimeSettingsDAO(db)
    store = MetricsStore(db)
    detector = RegressionDetector(store, settings_dao)
    
    # Get current config
    config = settings_dao.get_planner_config()
    
    # Get recent stats
    stats = store.window_stats(window_runs=100)
    
    # Evaluate for regressions (without triggering rollback)
    evaluation = detector.evaluate()
    
    return {
        "config": config,
        "stats": stats,
        "evaluation": {
            "action": evaluation["action"],
            "reason": evaluation.get("reason"),
            "breaches": evaluation.get("breaches", [])
        },
        "thresholds": {
            "max_quality_drop": 5.0,
            "max_latency_p95_ms": 1600,
            "max_cost_cents": 3.0,
            "min_sample": 30
        }
    }


@router.post("/rollback")
async def trigger_manual_rollback(
    request: RollbackRequest,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Manually trigger rollback to V1.
    
    Sets kill switch = True and canary_pct = 0.
    
    Args:
        request: Rollback request with reason
        
    Returns:
        Updated configuration
    """
    settings_dao = RuntimeSettingsDAO(db)
    
    # Trigger rollback
    updated_settings = settings_dao.reset_canary(
        updated_by=request.updated_by,
        reason=f"manual_rollback: {request.reason}"
    )
    
    return {
        "success": True,
        "message": "Rollback triggered successfully",
        "config": {
            "canary_pct": updated_settings["planner_canary_pct"],
            "kill_switch": updated_settings["planner_kill_switch"]
        },
        "updated_by": request.updated_by,
        "reason": request.reason
    }


@router.post("/evaluate")
async def evaluate_regression(
    window_runs: int = 100,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Evaluate for regressions on-demand.
    
    This will trigger automatic rollback if regressions are detected.
    
    Args:
        window_runs: Number of recent runs to analyze
        
    Returns:
        Evaluation result with action taken
    """
    settings_dao = RuntimeSettingsDAO(db)
    store = MetricsStore(db)
    detector = RegressionDetector(store, settings_dao)
    
    # Evaluate (this may trigger rollback)
    result = detector.evaluate(window_runs=window_runs)
    
    return {
        "timestamp": "now",
        "window_runs": window_runs,
        "action": result["action"],
        "reason": result.get("reason"),
        "breaches": result.get("breaches", []),
        "stats": result["stats"]
    }


@router.put("/config")
async def update_canary_config(
    request: CanaryUpdateRequest,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Update canary configuration.
    
    Args:
        request: Configuration updates
        
    Returns:
        Updated configuration
    """
    settings_dao = RuntimeSettingsDAO(db)
    
    # Build updates dict
    updates = {}
    if request.canary_pct is not None:
        if not 0.0 <= request.canary_pct <= 100.0:
            raise HTTPException(status_code=400, detail="canary_pct must be between 0 and 100")
        updates["planner_canary_pct"] = request.canary_pct
    
    if request.kill_switch is not None:
        updates["planner_kill_switch"] = request.kill_switch
    
    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided")
    
    # Apply updates
    updated_settings = settings_dao.update(
        updates,
        updated_by=request.updated_by,
        reason=request.reason or "config_update"
    )
    
    return {
        "success": True,
        "config": {
            "canary_pct": updated_settings["planner_canary_pct"],
            "kill_switch": updated_settings["planner_kill_switch"]
        },
        "updated_by": request.updated_by,
        "updated_at": updated_settings["updated_at"]
    }


@router.get("/health")
async def guard_health() -> Dict[str, str]:
    """Guard subsystem health check.
    
    Returns:
        Health status
    """
    return {
        "status": "healthy",
        "subsystem": "guard",
        "version": "5.1.0"
    }
