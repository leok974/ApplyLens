"""Pydantic models for the Companion learning loop."""

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class EditStats(BaseModel):
    """Statistics about edits made to generated answers."""

    total_chars_added: int = 0
    total_chars_deleted: int = 0
    per_field: Dict[str, Dict[str, int]] = Field(default_factory=dict)


class AutofillLearningEvent(BaseModel):
    """A single autofill learning event from the extension."""

    host: str
    schema_hash: str
    suggested_map: Dict[str, str] = Field(default_factory=dict)
    final_map: Dict[str, str] = Field(default_factory=dict)
    gen_style_id: Optional[str] = None
    edit_stats: EditStats = Field(default_factory=EditStats)
    duration_ms: int = 0
    validation_errors: Dict[str, Any] = Field(default_factory=dict)
    status: str = "ok"
    application_id: Optional[str] = None
    job: Optional[Dict[str, Any]] = None  # Phase 5.2: Job info for segment derivation


class LearningSyncRequest(BaseModel):
    """Batch of learning events from the extension."""

    host: str
    schema_hash: str
    events: List[AutofillLearningEvent]


class StyleHint(BaseModel):
    """Suggested generation style for a form."""

    gen_style_id: Optional[str] = None
    confidence: float = 0.0
    preferred_style_id: Optional[str] = None  # Phase 5.0: Best performing style


class LearningProfileResponse(BaseModel):
    """Canonical field mapping and style hints for a form."""

    host: str
    schema_hash: str
    canonical_map: Dict[str, str] = Field(default_factory=dict)
    style_hint: Optional[StyleHint] = None


# Phase 5.3: Style choice explanation models


class StyleChoiceStyleStats(BaseModel):
    """Performance metrics for a single generation style variant."""

    style_id: str
    source: Literal["form", "segment", "family", "unknown"] = "unknown"
    segment_key: Optional[str] = None

    total_runs: int = 0
    helpful_runs: int = 0
    unhelpful_runs: int = 0
    helpful_ratio: float = 0.0
    avg_edit_chars: Optional[float] = None

    is_winner: bool = False


class StyleChoiceExplanation(BaseModel):
    """
    Explanation of why a particular style was chosen for a form.

    Provides transparency into the hierarchical decision process:
    form → segment → family → none.
    """

    host: str
    schema_hash: str
    host_family: str
    segment_key: Optional[str] = None

    chosen_style_id: Optional[str] = None
    source: Literal["form", "segment", "family", "none"] = "none"

    considered_styles: List[StyleChoiceStyleStats] = Field(default_factory=list)

    explanation: str
