"""
Feature Flag Management Router

Provides admin endpoints for managing feature flag rollouts,
particularly for Email Risk v3.1 gradual deployment.
"""

import logging
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/flags", tags=["Feature Flags"])


# In-memory store (replace with DB/Redis in production)
_flag_state = {
    "EmailRiskBanner": {"enabled": True, "rollout_percent": 10},
    "EmailRiskDetails": {"enabled": True, "rollout_percent": 10},
    "EmailRiskAdvice": {"enabled": True, "rollout_percent": 100},
}

# Audit log (replace with DB in production)
_audit_log = []


class FlagConfig(BaseModel):
    """Feature flag configuration"""

    enabled: bool
    rollout_percent: int = Field(ge=0, le=100, description="Rollout percentage (0-100)")


class RampEvent(BaseModel):
    """Feature flag ramp audit event"""

    flag: str
    from_percent: int
    to_percent: int
    timestamp: datetime
    user: str = "admin"  # Replace with actual user from auth


FlagName = Literal["EmailRiskBanner", "EmailRiskDetails", "EmailRiskAdvice"]


@router.get("/{flag}")
def get_flag(flag: FlagName) -> FlagConfig:
    """Get current feature flag configuration"""
    if flag not in _flag_state:
        raise HTTPException(status_code=404, detail=f"Flag '{flag}' not found")

    return FlagConfig(**_flag_state[flag])


@router.get("/")
def list_flags() -> dict[str, FlagConfig]:
    """List all feature flags and their configurations"""
    return {name: FlagConfig(**config) for name, config in _flag_state.items()}


@router.post("/{flag}/ramp")
def ramp_flag(flag: FlagName, to: int = Field(ge=0, le=100)) -> RampEvent:
    """
    Ramp a feature flag to a new rollout percentage.

    Args:
        flag: Feature flag name (EmailRiskBanner, EmailRiskDetails, EmailRiskAdvice)
        to: Target rollout percentage (0-100)

    Returns:
        Audit event with before/after percentages

    Example:
        POST /flags/EmailRiskBanner/ramp?to=25
    """
    if flag not in _flag_state:
        raise HTTPException(status_code=404, detail=f"Flag '{flag}' not found")

    # Validate percentage increments (optional safety check)
    current = _flag_state[flag]["rollout_percent"]
    if to > current and to not in [0, 10, 25, 50, 100]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid ramp target. Use gradual increments: 10, 25, 50, 100. Current: {current}%",
        )

    # Create audit event
    event = RampEvent(
        flag=flag, from_percent=current, to_percent=to, timestamp=datetime.utcnow()
    )

    # Update flag state
    _flag_state[flag]["rollout_percent"] = to
    _audit_log.append(event.model_dump())

    # Log for observability
    logger.info(
        f"Feature flag ramped: {flag} from {current}% to {to}%",
        extra={
            "flag": flag,
            "from_percent": current,
            "to_percent": to,
            "event_type": "flag_ramp",
        },
    )

    return event


@router.post("/{flag}/enable")
def enable_flag(flag: FlagName) -> FlagConfig:
    """Enable a feature flag globally"""
    if flag not in _flag_state:
        raise HTTPException(status_code=404, detail=f"Flag '{flag}' not found")

    _flag_state[flag]["enabled"] = True
    logger.info(
        f"Feature flag enabled: {flag}",
        extra={"flag": flag, "event_type": "flag_enable"},
    )

    return FlagConfig(**_flag_state[flag])


@router.post("/{flag}/disable")
def disable_flag(flag: FlagName) -> FlagConfig:
    """Disable a feature flag globally (emergency kill switch)"""
    if flag not in _flag_state:
        raise HTTPException(status_code=404, detail=f"Flag '{flag}' not found")

    _flag_state[flag]["enabled"] = False
    logger.warning(
        f"Feature flag DISABLED: {flag}",
        extra={"flag": flag, "event_type": "flag_disable"},
    )

    return FlagConfig(**_flag_state[flag])


@router.get("/{flag}/audit")
def get_audit_log(flag: FlagName, limit: int = 50) -> list[RampEvent]:
    """Get audit log for a specific feature flag"""
    events = [e for e in _audit_log if e["flag"] == flag]
    return [RampEvent(**e) for e in events[-limit:]]


@router.get("/audit/all")
def get_all_audit_logs(limit: int = 100) -> list[RampEvent]:
    """Get audit log for all feature flags"""
    return [RampEvent(**e) for e in _audit_log[-limit:]]
