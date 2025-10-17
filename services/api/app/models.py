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
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .db import Base


class OAuthToken(Base):
    __tablename__ = "oauth_tokens"
    id = Column(Integer, primary_key=True)
    provider = Column(String(32), nullable=False, index=True)  # "google"
    user_email = Column(String(320), nullable=False, index=True)
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=True)
    token_uri = Column(Text, nullable=False)
    client_id = Column(Text, nullable=False)
    client_secret = Column(Text, nullable=False)
    scopes = Column(Text, nullable=False)
    expiry = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), onupdate=func.now(), server_default=func.now()
    )


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
        JSONB, nullable=True
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
