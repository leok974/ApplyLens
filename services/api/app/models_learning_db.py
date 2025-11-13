"""
SQLAlchemy ORM models for Companion learning system.

These models map to the database tables created by migration
0024_companion_learning_tables.py and store autofill events
and form profiles for continuous improvement.
"""

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    Index,
    Integer,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

from .db import Base


class FormProfile(Base):
    """
    Aggregated statistics for a specific form schema.

    Each unique (host, schema_hash) combination gets one profile that
    summarizes performance across all autofill events.
    """

    __tablename__ = "form_profiles"

    id = Column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    host = Column(Text, nullable=False, index=True)
    schema_hash = Column(Text, nullable=False, index=True)

    # Canonical field mappings: {semantic_name: field_id}
    fields = Column(JSONB, nullable=False, server_default="{}")

    # Performance metrics (aggregated from events)
    success_rate = Column(Float, nullable=True)
    avg_edit_chars = Column(Float, nullable=True)
    avg_duration_ms = Column(Integer, nullable=True)

    # Tracking
    last_seen_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("ix_form_profiles_host_schema", "host", "schema_hash", unique=True),
        Index("ix_form_profiles_last_seen", "last_seen_at"),
    )


class AutofillEvent(Base):
    """
    Individual autofill event telemetry.

    Each time the extension autofills a form, it creates one event.
    These events are aggregated to build FormProfiles.
    """

    __tablename__ = "autofill_events"

    id = Column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    host = Column(Text, nullable=False, index=True)
    schema_hash = Column(Text, nullable=False, index=True)

    # Field mappings
    suggested_map = Column(JSONB, nullable=False, server_default="{}")
    final_map = Column(JSONB, nullable=False, server_default="{}")

    # Generation settings
    gen_style_id = Column(Text, nullable=True, index=True)

    # Performance metrics
    edit_stats = Column(JSONB, nullable=False, server_default="{}")
    duration_ms = Column(Integer, nullable=True)
    validation_errors = Column(JSONB, nullable=False, server_default="{}")
    status = Column(Text, nullable=False, server_default="ok", index=True)

    # Optional link to application
    application_id = Column(UUID(as_uuid=True), nullable=True)

    # Tracking
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("ix_autofill_events_user_id", "user_id"),
        Index("ix_autofill_events_host_schema", "host", "schema_hash"),
        Index("ix_autofill_events_created_at", "created_at"),
        Index("ix_autofill_events_status", "status"),
        Index("ix_autofill_events_gen_style_id", "gen_style_id"),
    )


class GenStyle(Base):
    """
    Autofill generation style presets.

    Different tone/format/length combinations for A/B testing.
    """

    __tablename__ = "gen_styles"

    id = Column(Text, primary_key=True)
    name = Column(Text, nullable=False)

    # Generation parameters
    temperature = Column(Float, nullable=False, server_default="0.7")
    tone = Column(Text, nullable=False, server_default="concise")
    format = Column(Text, nullable=False, server_default="bullets")
    length_hint = Column(Text, nullable=False, server_default="medium")
    keywords_json = Column(JSONB, nullable=False, server_default="[]")

    # Bayesian prior for A/B testing
    prior_weight = Column(Float, nullable=False, server_default="1.0", index=True)

    # Tracking
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (Index("ix_gen_styles_prior_weight", "prior_weight"),)
