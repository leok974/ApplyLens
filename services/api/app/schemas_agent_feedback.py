"""
Pydantic schemas for Agent V2 feedback API.

Supports capturing user feedback on agent cards/items for learning loop.
"""

from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


FeedbackLabel = Literal["helpful", "not_helpful", "hide", "done"]


class AgentFeedbackCreate(BaseModel):
    """Request payload for creating agent feedback."""

    intent: str = Field(
        ..., description="Agent intent (suspicious, followups, bills, etc.)"
    )
    query: Optional[str] = Field(None, description="User's original query")
    run_id: Optional[UUID] = Field(None, description="Agent run ID if available")
    card_id: str = Field(..., description="Card ID (e.g., 'suspicious_summary')")
    item_id: Optional[str] = Field(
        None, description="Specific item ID within card (thread_id, message_id)"
    )
    label: FeedbackLabel = Field(..., description="Feedback type")
    thread_id: Optional[str] = Field(None, description="Gmail thread ID for filtering")
    message_id: Optional[str] = Field(None, description="Gmail message ID")
    metrics: Optional[dict] = Field(None, description="Agent metrics snapshot")
    meta: Optional[dict] = Field(None, description="Card metadata snapshot")


class AgentFeedbackResponse(BaseModel):
    """Response for feedback creation."""

    ok: bool = True
    message: str = "Feedback saved"


class AgentPreferencesResponse(BaseModel):
    """User preferences for agent filtering."""

    user_id: str
    data: dict
    updated_at: str
