import enum
from datetime import datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .db import Base
from .settings import settings

# Use JSON for SQLite, JSONB for PostgreSQL
JSONType = JSON if "sqlite" in settings.DATABASE_URL.lower() else JSONB


class User(Base):
    """User accounts for multi-user authentication."""

    __tablename__ = "users"
    id = Column(String(64), primary_key=True)  # UUID or generated ID
    email = Column(String(320), nullable=False, unique=True, index=True)
    name = Column(String(255), nullable=True)
    picture_url = Column(Text, nullable=True)
    is_demo = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), onupdate=func.now(), server_default=func.now()
    )


class Session(Base):
    """User sessions for cookie-based authentication."""

    __tablename__ = "sessions"
    id = Column(String(64), primary_key=True)  # Session token
    user_id = Column(
        String(64),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    user = relationship("User", backref="sessions")


class OAuthToken(Base):
    __tablename__ = "oauth_tokens"
    id = Column(Integer, primary_key=True)
    user_id = Column(
        String(64),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )  # New: link to User
    provider = Column(String(32), nullable=False, index=True)  # "google"
    user_email = Column(
        String(320), nullable=False, index=True
    )  # Keep for backward compatibility
    access_token = Column(LargeBinary, nullable=False)  # Encrypted with AES-GCM
    refresh_token = Column(LargeBinary, nullable=True)  # Encrypted with AES-GCM
    token_uri = Column(Text, nullable=False)
    client_id = Column(Text, nullable=False)
    client_secret = Column(Text, nullable=False)
    scopes = Column(Text, nullable=False)
    expiry = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), onupdate=func.now(), server_default=func.now()
    )
    user = relationship("User", backref="oauth_tokens")


class GmailToken(Base):
    """Per-user Gmail OAuth tokens for multi-user support."""

    __tablename__ = "gmail_tokens"
    user_email = Column(String(255), primary_key=True)
    access_token = Column(Text, nullable=True)
    refresh_token = Column(Text, nullable=False)
    expiry_date = Column(Integer, nullable=True)  # milliseconds since epoch
    scope = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), onupdate=func.now(), server_default=func.now()
    )


class Email(Base):
    __tablename__ = "emails"
    id = Column(Integer, primary_key=True)
    gmail_id = Column(String(128), unique=True, index=True)
    thread_id = Column(String(128), index=True)
    subject = Column(Text, nullable=True)
    body_text = Column(Text, nullable=True)
    sender = Column(String(512), index=True)
    recipient = Column(String(512), index=True)
    received_at = Column(DateTime(timezone=True), index=True)
    labels = Column(ARRAY(String), nullable=True)
    label_heuristics = Column(ARRAY(String), nullable=True)
    raw = Column(JSON, nullable=True)

    # Multi-user support
    owner_email = Column(String(320), index=True, nullable=True)  # Email owner

    # NEW quick hooks
    company = Column(String(256), index=True)
    role = Column(String(512), index=True)
    source = Column(String(128), index=True)
    source_confidence = Column(Float, default=0.0)

    # Reply metrics
    first_user_reply_at = Column(DateTime(timezone=True), nullable=True)
    last_user_reply_at = Column(DateTime(timezone=True), nullable=True)
    user_reply_count = Column(Integer, default=0)

    # Email automation system fields
    category = Column(
        Text, nullable=True, index=True
    )  # promotions, bills, security, personal, applications
    risk_score = Column(
        Float, nullable=True, index=True
    )  # 0-100, higher = more suspicious
    flags = Column(
        JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb")
    )  # Security risk flags [{signal, evidence, weight}, ...]
    quarantined = Column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )  # Automatically quarantined by security analyzer
    expires_at = Column(
        DateTime(timezone=True), nullable=True, index=True
    )  # When email content expires
    profile_tags = Column(
        ARRAY(Text), nullable=True
    )  # User-specific tags for personalization
    features_json = Column(
        JSONB, nullable=True
    )  # Extracted features for ML/classification

    # Phase 2: ML and event fields
    event_start_at = Column(
        DateTime(timezone=True), nullable=True, index=True
    )  # Event start date/time
    event_location = Column(Text, nullable=True)  # Event location/venue
    ml_features = Column(JSONB, nullable=True)  # ML feature vectors (TF-IDF, etc.)
    ml_scores = Column(JSONB, nullable=True)  # ML model probability scores per category
    amount_cents = Column(Integer, nullable=True)  # Bill amount in cents
    due_date = Column(
        DateTime(timezone=True), nullable=True, index=True
    )  # Bill due date

    # Optional link to application
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=True)
    application = relationship(
        "Application", back_populates="emails", foreign_keys=[application_id]
    )


Index("idx_emails_search", Email.subject, Email.sender, Email.recipient)


class AppStatus(str, enum.Enum):
    applied = "applied"
    hr_screen = "hr_screen"
    interview = "interview"
    offer = "offer"
    rejected = "rejected"
    on_hold = "on_hold"
    ghosted = "ghosted"


class Application(Base):
    __tablename__ = "applications"
    id = Column(Integer, primary_key=True)
    company = Column(String(256), index=True, nullable=False)
    role = Column(String(512), index=True)
    source = Column(String(128), index=True)
    source_confidence = Column(Float, default=0.0)

    # convenience linkage
    thread_id = Column(String(128), index=True)
    gmail_thread_id = Column(
        String(128), index=True
    )  # alias for consistency with patch
    last_email_id = Column(Integer, ForeignKey("emails.id"), nullable=True)
    last_email_snippet = Column(Text, nullable=True)

    status = Column(Enum(AppStatus), default=AppStatus.applied, nullable=False)
    notes = Column(Text, nullable=True)

    # Archive & auto-delete lifecycle fields
    archived_at = Column(DateTime(timezone=True), nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    archive_opt_out = Column(Boolean, nullable=False, default=False)
    auto_delete_opt_out = Column(Boolean, nullable=False, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), onupdate=func.now(), server_default=func.now()
    )

    emails = relationship(
        "Email", back_populates="application", foreign_keys="Email.application_id"
    )


class ActionsAudit(Base):
    """
    Audit log of all actions taken on emails (manual and automated)

    Tracks:
    - What action was taken (archive, label, quarantine, etc.)
    - Who took it (agent/automation or user)
    - Which policy triggered it (if applicable)
    - Confidence and rationale
    - When it happened
    """

    __tablename__ = "actions_audit"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    email_id = Column(Text, nullable=True, index=True)  # Gmail ID (string), not FK
    action = Column(
        Text, nullable=False, index=True
    )  # archive, label, quarantine, delete, etc.
    actor = Column(
        Text, nullable=False, index=True
    )  # "agent" (automation) or "user" (manual)
    policy_id = Column(Text, nullable=True)  # Which policy triggered this
    confidence = Column(Float, nullable=True)  # Confidence score 0-1
    rationale = Column(Text, nullable=True)  # Human-readable explanation
    payload = Column(
        JSONType, nullable=True
    )  # Action-specific data (e.g., {"label": "important"})
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)


class UserProfile(Base):
    """
    User preferences and behavior patterns for personalization

    Stores:
    - User interests (used for classification)
    - Brand preferences (for filtering promotions)
    - Active categories (what they care about)
    - Mute rules (automation preferences)
    - Open rates by category (engagement metrics)
    """

    __tablename__ = "user_profile"

    user_id = Column(Text, primary_key=True)
    interests = Column(ARRAY(Text), nullable=True)  # ["tech", "finance", "travel"]
    brand_prefs = Column(ARRAY(Text), nullable=True)  # ["amazon", "nike", "apple"]
    active_categories = Column(ARRAY(Text), nullable=True)  # ["applications", "bills"]
    mute_rules = Column(
        JSONB, nullable=True
    )  # {"promo": {"expire_auto_archive": true}}
    last_seen_domains = Column(
        ARRAY(Text), nullable=True
    )  # Recently seen sender domains
    open_rates = Column(JSONB, nullable=True)  # {"promo": 0.23, "bills": 0.88}
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ProfileSenderStats(Base):
    """
    Aggregated statistics per sender domain for a user.

    Tracks:
    - Total emails from this sender
    - Last received date
    - Category breakdown
    - Open rate (if available)
    """

    __tablename__ = "profile_sender_stats"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_email = Column(String(320), nullable=False, index=True)
    sender_domain = Column(String(255), nullable=False, index=True)
    total = Column(Integer, nullable=False, server_default="0")
    last_received_at = Column(DateTime(timezone=True), nullable=True)
    categories = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    open_rate = Column(Float, nullable=True)


Index(
    "ix_profile_sender_stats_user_domain",
    ProfileSenderStats.user_email,
    ProfileSenderStats.sender_domain,
    unique=True,
)


class ProfileCategoryStats(Base):
    """
    Aggregated statistics per category for a user.

    Tracks:
    - Total emails in this category
    - Last received date
    """

    __tablename__ = "profile_category_stats"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_email = Column(String(320), nullable=False, index=True)
    category = Column(String(64), nullable=False, index=True)
    total = Column(Integer, nullable=False, server_default="0")
    last_received_at = Column(DateTime(timezone=True), nullable=True)


Index(
    "ix_profile_category_stats_user_cat",
    ProfileCategoryStats.user_email,
    ProfileCategoryStats.category,
    unique=True,
)


class ProfileInterests(Base):
    """
    User interests extracted from email content.

    Tracks:
    - Interest keywords/topics
    - Relevance score
    - Last update time
    """

    __tablename__ = "profile_interests"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_email = Column(String(320), nullable=False, index=True)
    interest = Column(String(128), nullable=False, index=True)
    score = Column(Float, nullable=False, server_default="0")
    updated_at = Column(DateTime(timezone=True), nullable=True)


Index(
    "ix_profile_interests_user_interest",
    ProfileInterests.user_email,
    ProfileInterests.interest,
    unique=True,
)


class SecurityPolicy(Base):
    """
    Security policy configuration for automated email protection.

    Stores user preferences for:
    - Auto-quarantine of high-risk emails
    - Auto-archive of expired promotions
    - Auto-unsubscribe from inactive senders
    """

    __tablename__ = "security_policies"

    id = Column(Integer, primary_key=True)
    user_id = Column(String(320), nullable=True, unique=True)  # Single-user OK (NULL)
    auto_quarantine_high_risk = Column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )
    auto_archive_expired_promos = Column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )
    auto_unsubscribe_enabled = Column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    auto_unsubscribe_threshold = Column(
        Integer, nullable=False, default=10, server_default="10"
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


# ===== Phase 4: Agentic Actions & Approval Loop =====


class ActionType(str, enum.Enum):
    """Available action types for agentic automation"""

    label_email = "label_email"
    archive_email = "archive_email"
    move_to_folder = "move_to_folder"
    unsubscribe_via_header = "unsubscribe_via_header"
    create_calendar_event = "create_calendar_event"
    create_task = "create_task"
    block_sender = "block_sender"
    quarantine_attachment = "quarantine_attachment"


class ProposedAction(Base):
    """
    Queued action proposals pending human-in-the-loop review.

    Lifecycle:
    1. Created by policy evaluation (status=pending)
    2. Reviewed by user (status=approved/rejected)
    3. Executed (status=executed/failed)
    """

    __tablename__ = "proposed_actions"

    id = Column(Integer, primary_key=True)
    email_id = Column(Integer, index=True, nullable=False)
    action = Column(Enum(ActionType), nullable=False)
    params = Column(
        JSON, default=dict
    )  # Action-specific parameters (label name, folder, etc.)
    confidence = Column(Float, nullable=False)  # 0.0-1.0 confidence score
    rationale = Column(JSON, default=dict)  # Features, aggs, neighbors, regex hits
    policy_id = Column(Integer, ForeignKey("policies.id"), nullable=True)
    created_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    status = Column(
        String, default="pending", nullable=False
    )  # pending|approved|rejected|executed|failed
    reviewed_by = Column(String, nullable=True)  # User email/id for HIL
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<ProposedAction(id={self.id}, action={self.action.value}, email_id={self.email_id}, status={self.status})>"


class AuditAction(Base):
    """
    Immutable audit trail for all executed actions.

    Records:
    - Who performed the action (user or system)
    - What action was taken with what parameters
    - Why (rationale/features that triggered it)
    - Outcome (success/fail/noop)
    - Optional screenshot for visual proof
    """

    __tablename__ = "audit_actions"

    id = Column(Integer, primary_key=True)
    email_id = Column(Integer, index=True, nullable=False)
    action = Column(Enum(ActionType), nullable=False)
    params = Column(JSON, default=dict)
    actor = Column(String, nullable=False)  # "system" | user id/email
    outcome = Column(String, nullable=False)  # success|fail|noop
    error = Column(Text, nullable=True)  # Error message if outcome=fail
    why = Column(
        JSON, default=dict
    )  # Same schema as rationale (features, aggs, narrative)
    screenshot_path = Column(String, nullable=True)  # Path to PNG screenshot
    created_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    def __repr__(self):
        return f"<AuditAction(id={self.id}, action={self.action.value}, actor={self.actor}, outcome={self.outcome})>"


class Policy(Base):
    """
    Yardstick policy rules for automated action proposals.

    DSL Schema:
    - condition: JSON object with Yardstick DSL (all/any/not, comparators)
    - action: ActionType enum value
    - confidence_threshold: Minimum confidence to propose (0.0-1.0)
    - priority: Lower number runs first (allows override/short-circuit)

    Example condition:
    {
      "all": [
        {"eq": ["category", "promo"]},
        {"lt": ["expires_at", "now"]}
      ]
    }
    """

    __tablename__ = "policies"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    enabled = Column(Boolean, default=True, nullable=False)
    priority = Column(Integer, default=100, nullable=False)  # Lower runs first
    condition = Column(JSON, default=dict, nullable=False)  # Yardstick DSL (JSON)
    action = Column(Enum(ActionType), nullable=False)
    confidence_threshold = Column(Float, default=0.7, nullable=False)  # 0.0-1.0
    created_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    def __repr__(self):
        return f"<Policy(id={self.id}, name={self.name}, enabled={self.enabled}, priority={self.priority})>"


# Phase 6: Personalization models
class UserWeight(Base):
    """
    Per-user feature weights learned online from approve/reject feedback.

    Features can be:
    - category:<cat> (e.g., category:promo, category:event)
    - sender_domain:<domain> (e.g., sender_domain:bestbuy.com)
    - listid:<list_id> (e.g., listid:github-notifications)
    - contains:<token> (e.g., contains:invoice, contains:meetup)

    Weights are updated using online gradient descent:
    w ← w + η * y * x
    where y=+1 for approve, y=-1 for reject, x=1 for feature presence
    """

    __tablename__ = "user_weights"

    id = Column(Integer, primary_key=True)
    user_id = Column(String, index=True, nullable=False)
    feature = Column(String, nullable=False)  # e.g., 'sender_domain:bestbuy.com'
    weight = Column(Float, default=0.0)  # learned weight
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = ({"schema": None},)  # Use default schema

    def __repr__(self):
        return f"<UserWeight(user={self.user_id}, feature={self.feature}, weight={self.weight:.3f})>"


class PolicyStats(Base):
    """
    Per-user, per-policy performance statistics.

    Tracks:
    - How many times the policy fired (proposed actions)
    - How many proposals were approved
    - How many were rejected
    - Precision (approved/fired)
    - Estimated recall (approved/(approved+should_have))
    """

    __tablename__ = "policy_stats"

    id = Column(Integer, primary_key=True)
    policy_id = Column(Integer, index=True, nullable=False)
    user_id = Column(String, index=True, nullable=False)

    # Counters
    fired = Column(Integer, default=0)  # Total times policy fired
    approved = Column(Integer, default=0)  # User approved proposals
    rejected = Column(Integer, default=0)  # User rejected proposals

    # Metrics
    precision = Column(Float, default=0.0)  # approved/fired
    recall = Column(Float, default=0.0)  # approved/(approved+should_have) — estimated

    # Window
    window_days = Column(Integer, default=30)  # Stats computed over this window
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = ({"schema": None},)  # Use default schema

    def __repr__(self):
        return f"<PolicyStats(policy={self.policy_id}, user={self.user_id}, precision={self.precision:.2f})>"


class AgentAuditLog(Base):
    """Agent execution audit log.

    Tracks all agent runs for observability, debugging, and compliance.
    Stores plan, execution status, timing, and artifacts.
    """

    __tablename__ = "agent_audit_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(128), unique=True, nullable=False, index=True)
    agent = Column(String(128), nullable=False, index=True)
    objective = Column(String(512), nullable=False)
    status = Column(
        String(32), nullable=False, index=True
    )  # queued, running, succeeded, failed, canceled

    # Timestamps
    started_at = Column(DateTime(timezone=True), nullable=False, index=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    duration_ms = Column(Float, nullable=True)

    # Execution details
    plan = Column(JSONType, nullable=True)
    artifacts = Column(JSONType, nullable=True)
    error = Column(String(2048), nullable=True)

    # Metadata
    user_email = Column(String(320), nullable=True, index=True)  # Who triggered it
    dry_run = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_agent_audit_log_agent_status", "agent", "status"),
        Index("ix_agent_audit_log_started_at_desc", started_at.desc()),
    )

    def __repr__(self):
        return f"<AgentAuditLog(run_id={self.run_id}, agent={self.agent}, status={self.status})>"


class AgentApproval(Base):
    """Agent action approval requests with HMAC signatures.

    Tracks approval lifecycle for agent actions that require human review.
    Includes HMAC signatures for secure approval links and nonce protection.
    """

    __tablename__ = "agent_approvals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    request_id = Column(String(128), unique=True, nullable=False, index=True)

    # Agent context
    agent = Column(String(128), nullable=False, index=True)
    action = Column(String(128), nullable=False)
    context = Column(JSONB, nullable=False, default=dict)  # Action parameters

    # Policy decision
    policy_rule_id = Column(String(128), nullable=True)
    reason = Column(String(1024), nullable=False)

    # Approval lifecycle
    status = Column(
        String(32), nullable=False, default="pending", index=True
    )  # pending, approved, rejected, canceled, expired
    requested_by = Column(
        String(320), nullable=True, index=True
    )  # User email who triggered the action
    requested_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    reviewed_by = Column(String(320), nullable=True)  # User email who approved/rejected
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    expires_at = Column(
        DateTime(timezone=True), nullable=True, index=True
    )  # Auto-expire after N hours

    # Security
    signature = Column(
        String(128), nullable=False, unique=True
    )  # HMAC-SHA256 signature
    nonce = Column(
        String(64), nullable=False, unique=True, index=True
    )  # One-time use nonce
    nonce_used = Column(Boolean, default=False, nullable=False)

    # Execution tracking
    executed = Column(Boolean, default=False, nullable=False)
    executed_at = Column(DateTime(timezone=True), nullable=True)
    execution_result = Column(
        JSONType, nullable=True
    )  # Result of executing the approved action

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("ix_agent_approvals_agent_status", "agent", "status"),
        Index("ix_agent_approvals_requested_at_desc", requested_at.desc()),
    )

    def __repr__(self):
        return f"<AgentApproval(request_id={self.request_id}, agent={self.agent}, status={self.status})>"


# ===== Phase 5: Intelligence & Evaluation =====


class AgentMetricsDaily(Base):
    """Daily aggregated metrics for agent quality tracking.

    Captures production quality signals:
    - Success/failure rates
    - User feedback (thumbs up/down)
    - Quality scores from online eval
    - Latency and cost metrics
    - Red-team attack detection

    Used for:
    - Trend analysis and regression detection
    - Weekly intelligence reports
    - Dashboard metrics
    - Budget enforcement
    """

    __tablename__ = "agent_metrics_daily"

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent = Column(String(128), nullable=False, index=True)
    date = Column(DateTime(timezone=True), nullable=False, index=True)

    # Execution metrics
    total_runs = Column(Integer, default=0, nullable=False)
    successful_runs = Column(Integer, default=0, nullable=False)
    failed_runs = Column(Integer, default=0, nullable=False)
    success_rate = Column(Float, nullable=True)  # successful_runs / total_runs

    # Quality metrics
    avg_quality_score = Column(Float, nullable=True)  # 0-100 from judges
    median_quality_score = Column(Float, nullable=True)
    p95_quality_score = Column(Float, nullable=True)
    quality_samples = Column(Integer, default=0)  # How many runs were evaluated

    # User feedback
    thumbs_up = Column(Integer, default=0, nullable=False)
    thumbs_down = Column(Integer, default=0, nullable=False)
    feedback_rate = Column(
        Float, nullable=True
    )  # (thumbs_up + thumbs_down) / total_runs
    satisfaction_rate = Column(
        Float, nullable=True
    )  # thumbs_up / (thumbs_up + thumbs_down)

    # Performance metrics
    avg_latency_ms = Column(Float, nullable=True)
    median_latency_ms = Column(Float, nullable=True)
    p95_latency_ms = Column(Float, nullable=True)
    p99_latency_ms = Column(Float, nullable=True)

    # Cost tracking
    total_cost_weight = Column(Float, default=0.0)  # Relative cost units
    avg_cost_per_run = Column(Float, nullable=True)

    # Invariant tracking
    invariants_passed = Column(Integer, default=0)
    invariants_failed = Column(Integer, default=0)
    failed_invariant_ids = Column(
        ARRAY(Text), nullable=True
    )  # List of failed invariant IDs

    # Red-team tracking
    redteam_attacks_detected = Column(Integer, default=0)
    redteam_attacks_missed = Column(Integer, default=0)
    redteam_false_positives = Column(Integer, default=0)

    # Breakdown by difficulty (JSON)
    quality_by_difficulty = Column(
        JSONB, nullable=True
    )  # {"easy": 95.0, "medium": 80.0, "hard": 65.0}

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("ix_agent_metrics_daily_agent_date", "agent", "date", unique=True),
        Index("ix_agent_metrics_daily_date_desc", date.desc()),
    )

    def __repr__(self):
        return f"<AgentMetricsDaily(agent={self.agent}, date={self.date.date()}, success_rate={self.success_rate:.2%})>"


class UserSenderOverride(Base):
    """User-specific sender overrides for adaptive classification."""

    __tablename__ = "user_sender_overrides"

    id = Column(String(36), primary_key=True)  # UUID
    user_id = Column(String(255), nullable=False, index=True)
    sender = Column(String(512), nullable=False, index=True)
    muted = Column(Boolean, server_default="false", nullable=False)
    safe = Column(Boolean, server_default="false", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("idx_user_sender_unique", "user_id", "sender", unique=True),
    )

    def __repr__(self):
        return f"<UserSenderOverride(user={self.user_id}, sender={self.sender}, safe={self.safe}, muted={self.muted})>"


class ExtensionApplication(Base):
    """Job applications logged from browser extension."""

    __tablename__ = "extension_applications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_email = Column(String(320), nullable=False, index=True)
    company = Column(String(255), nullable=False, index=True)
    role = Column(String(512), nullable=False)
    job_url = Column(Text, nullable=True)
    source = Column(String(128), nullable=False, index=True)
    applied_at = Column(DateTime(timezone=True), nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<ExtensionApplication(id={self.id}, company={self.company}, role={self.role})>"


class ExtensionOutreach(Base):
    """Recruiter outreach logged from browser extension."""

    __tablename__ = "extension_outreach"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_email = Column(String(320), nullable=False, index=True)
    company = Column(String(255), nullable=False, index=True)
    role = Column(String(512), nullable=False)
    recruiter_name = Column(String(255), nullable=True)
    recruiter_profile_url = Column(Text, nullable=True)
    message_preview = Column(Text, nullable=True)
    source = Column(String(128), nullable=False, index=True)
    sent_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<ExtensionOutreach(id={self.id}, company={self.company}, recruiter={self.recruiter_name})>"
