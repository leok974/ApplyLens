"""Pydantic schemas for agent system."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

# Type alias for run status
RunStatus = Literal["queued", "running", "succeeded", "failed", "canceled"]


class AgentPlan(BaseModel):
    """Execution plan for an agent."""
    
    agent: str = Field(..., description="Agent name")
    objective: str = Field(..., description="High-level goal")
    dry_run: bool = Field(default=True, description="Whether to run in dry-run mode")
    steps: List[str] = Field(default_factory=list, description="Execution steps")
    tools: List[str] = Field(default_factory=list, description="Required tools")


class AgentRunRequest(BaseModel):
    """Request to run an agent."""
    
    objective: str = Field(..., description="What the agent should accomplish")
    dry_run: bool = Field(default=True, description="Safe mode - no side effects")
    params: Dict[str, Any] = Field(
        default_factory=dict, 
        description="Additional parameters"
    )


class AgentRunResult(BaseModel):
    """Result of an agent execution."""
    
    run_id: str = Field(..., description="Unique run identifier")
    status: RunStatus = Field(..., description="Current run status")
    started_at: datetime = Field(..., description="When execution started")
    finished_at: Optional[datetime] = Field(None, description="When execution finished")
    logs: List[str] = Field(default_factory=list, description="Execution logs")
    artifacts: Dict[str, Any] = Field(
        default_factory=dict, 
        description="Results and outputs"
    )


class AgentSpec(BaseModel):
    """Agent specification and metadata."""
    
    name: str = Field(..., description="Unique agent name")
    description: str = Field(..., description="What this agent does")
    version: str = Field(default="0.1.0", description="Agent version")
    capabilities: List[str] = Field(
        default_factory=list, 
        description="What this agent can do"
    )
