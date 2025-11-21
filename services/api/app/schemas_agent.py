"""
Agent v2 - Core schemas for mailbox agent runs.

This module defines the stable contract for agent runs used across:
- Backend API endpoints
- Frontend TypeScript types
- Prometheus metrics
- Grafana dashboards
"""

from pydantic import BaseModel, Field, validator
from typing import Literal, List, Optional, Dict, Any
from datetime import datetime
import uuid


# ============================================================================
# Agent Run Contract - The Single Source of Truth
# ============================================================================

# Card kind normalization constants
ALLOWED_CARD_KINDS = {
    "suspicious_summary",
    "bills_summary",
    "followups_summary",
    "interviews_summary",
    "generic_summary",
    "thread_list",
    "error",
}

CARD_KIND_ALIASES = {
    "profile_summary": "generic_summary",
    "profile": "generic_summary",
    # Add other future aliases here if the LLM gets creative
}


class AgentMode(str):
    """Agent execution modes."""

    PREVIEW_ONLY = "preview_only"  # Default: only suggest, never apply
    APPLY_ACTIONS = "apply_actions"  # Requires explicit user confirmation


class AgentContext(BaseModel):
    """Context filters and parameters for agent execution."""

    time_window_days: int = Field(default=30, ge=1, le=365)
    filters: Dict[str, Any] = Field(
        default_factory=dict,
        description="ES/DB filters: labels, risk_min, risk_max, sender_domain, etc.",
    )
    session_id: Optional[str] = Field(
        default=None, description="Chat session ID for context continuity"
    )


class ToolResult(BaseModel):
    """Result from a single tool execution."""

    tool_name: str = Field(..., description="email_search, security_scan, etc.")
    status: Literal["success", "error", "timeout"] = "success"
    summary: str = Field(..., description="Short LLM-friendly summary")
    data: Dict[str, Any] = Field(
        default_factory=dict, description="Typed payload for cards"
    )
    duration_ms: int = Field(default=0, ge=0)
    error_message: Optional[str] = None


class AgentCard(BaseModel):
    """
    A single UI card to display tool results.

    Examples:
    - suspicious_summary: domain risk summary
    - bills_summary: pending payments
    - followups_summary: unanswered emails
    - interviews_summary: job-related emails
    - thread_list: thread viewer with mail summaries
    - generic_summary: general query results
    - error: fallback when tools fail

    The 'kind' field accepts any string and normalizes to allowed values:
    - Known aliases (e.g., profile_summary) are mapped to canonical kinds
    - Unknown values fallback to generic_summary to prevent validation errors
    """

    kind: str = Field(..., description="Card type for frontend rendering")
    title: str = Field(..., description="Card title for UI")
    body: str = Field(..., description="Card summary body (different from answer)")

    # Email/message IDs this card is based on (for highlighting / "sources")
    email_ids: List[str] = Field(
        default_factory=list,
        description="Email IDs from RAG contexts that support this card",
    )

    # Free-form extra metadata (counts, modes, etc.)
    meta: Dict[str, Any] = Field(
        default_factory=dict,
        description="Rendering hints: count, time_window_days, mode, etc.",
    )

    # Thread list for thread_list cards
    threads: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Mail thread summaries for thread_list kind",
    )

    @validator("kind", pre=True)
    def normalize_kind(cls, v: str) -> str:
        """
        Normalize card kind to prevent LLM creativity from causing validation errors.

        - Maps known aliases (profile_summary → generic_summary)
        - Fallback to generic_summary for unknown values
        - Ensures frontend only sees canonical kinds
        """
        if not isinstance(v, str):
            return "generic_summary"

        # Apply aliases
        v = CARD_KIND_ALIASES.get(v, v)

        # Fallback for unknown kinds
        if v not in ALLOWED_CARD_KINDS:
            return "generic_summary"

        return v


class AgentMetrics(BaseModel):
    """Telemetry for agent run."""

    emails_scanned: int = 0
    tool_calls: int = 0
    rag_sources: int = 0  # email contexts + KB docs
    duration_ms: int = 0
    redis_hits: int = 0
    redis_misses: int = 0
    llm_used: Optional[str] = None  # "ollama", "openai", "fallback"


class AgentLLMAnswer(BaseModel):
    """
    Structured LLM response format.

    The LLM is asked to return JSON matching this schema:
    - answer: Natural language answer for the user
    - cards: UI cards with citations (email_ids) and metadata
    """

    answer: str = Field(..., description="One-paragraph natural language answer")
    cards: List[AgentCard] = Field(
        default_factory=list, description="UI cards with citations"
    )


class AgentRunRequest(BaseModel):
    """Request to execute a mailbox agent run."""

    query: str = Field(..., min_length=1, description="User's natural language query")
    mode: Literal["preview_only", "apply_actions"] = "preview_only"
    context: AgentContext = Field(default_factory=AgentContext)
    user_id: Optional[str] = Field(
        default=None,
        description="Gmail account ID or user identifier (derived from session if not provided)",
    )


class AgentRunResponse(BaseModel):
    """Complete agent run result."""

    run_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    query: str
    mode: str
    context: AgentContext

    # Results
    status: Literal["running", "done", "error"] = "running"
    intent: Optional[str] = Field(
        default=None,
        description="Classified intent: suspicious, bills, interviews, followups, profile, generic",
    )
    answer: str = Field(
        default="", description="LLM-generated answer synthesizing tool results"
    )
    cards: List[AgentCard] = Field(default_factory=list)
    tools_used: List[str] = Field(
        default_factory=list, description="Tool names invoked during run"
    )
    metrics: AgentMetrics = Field(default_factory=AgentMetrics)

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


# ============================================================================
# Tool Registry Schemas
# ============================================================================


class EmailSearchParams(BaseModel):
    """Parameters for email_search tool."""

    query_text: str = ""
    time_window_days: int = 30
    labels: List[str] = Field(default_factory=list)  # No default filter
    risk_min: Optional[float] = None
    max_results: int = Field(default=50, ge=1, le=100)


class SecurityScanParams(BaseModel):
    """Parameters for security_scan tool."""

    email_ids: List[str] = Field(default_factory=list)
    force_rescan: bool = False


class ThreadDetailParams(BaseModel):
    """Parameters for thread_detail tool."""

    thread_id: Optional[str] = None
    email_ids: List[str] = Field(default_factory=list)
    max_emails: int = Field(50, ge=1, le=200)


class ApplicationsLookupParams(BaseModel):
    """Parameters for applications_lookup tool."""

    email_ids: List[str]
    max_results: int = Field(50, ge=1, le=200)


class ProfileStatsParams(BaseModel):
    """Parameters for profile_stats tool."""

    time_window_days: int = Field(30, ge=1, le=365)


# ============================================================================
# Tool Result Schemas (for cards)
# ============================================================================


class EmailSearchResult(BaseModel):
    """Result payload for email_search tool."""

    emails: List[Dict[str, Any]]  # List of email dicts with id, subject, sender, etc.
    total_found: int
    query_used: str
    filters_applied: Dict[str, Any]


class SecurityScanResult(BaseModel):
    """Result payload for security_scan tool."""

    scanned_count: int
    risky_emails: List[Dict[str, Any]]
    safe_emails: List[Dict[str, Any]]
    domains_checked: List[str]


class ThreadDetailResult(BaseModel):
    """Result payload for thread_detail tool."""

    thread_id: Optional[str] = None
    emails: List[Dict[str, Any]]
    total_found: int


class ApplicationsLookupResult(BaseModel):
    """Result payload for applications_lookup tool."""

    applications: List[Dict[str, Any]]
    total_found: int


class ProfileStatsResult(BaseModel):
    """Result payload for profile_stats tool."""

    total_emails: int
    time_window_days: int
    total_in_window: int
    labels: Dict[str, int]
    risk_buckets: Dict[str, int]


# ============================================================================
# Redis Cache Schemas
# ============================================================================


class DomainRiskCache(BaseModel):
    """Cached domain risk intelligence."""

    domain: str
    risk_score: float = Field(ge=0, le=100)
    first_seen_at: datetime
    last_seen_at: datetime
    email_count: int = 0
    flags: List[str] = Field(
        default_factory=list, description="new_domain, suspicious_tld, dmarc_fail, etc."
    )
    evidence: Dict[str, Any] = Field(
        default_factory=dict,
        description="DMARC/SPF results, URL mismatches, etc.",
    )


class ChatSessionCache(BaseModel):
    """Cached chat session context."""

    user_id: str
    session_id: str
    last_query: str
    last_intent: Optional[str] = None
    pinned_thread_ids: List[str] = Field(default_factory=list)
    last_time_window: int = 30
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# RAG Schemas
# ============================================================================


class RAGContext(BaseModel):
    """Retrieved context for RAG."""

    source_type: Literal["email", "knowledge_base"] = "email"
    source_id: str
    content: str
    score: float = Field(ge=0, le=1)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class KnowledgeBaseEntry(BaseModel):
    """Entry in the curated knowledge base."""

    id: str
    title: str
    content: str
    category: Literal["phishing", "job_search", "applylens_faq"] = "phishing"
    tags: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
