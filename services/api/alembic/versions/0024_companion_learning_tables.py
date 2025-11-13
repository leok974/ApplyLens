"""add companion learning tables for autofill improvement

Revision ID: 0024_companion_learning_tables
Revises: 0023_agent_approvals
Create Date: 2025-11-12
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0024_companion_learning_tables"
down_revision = "0023_agent_approvals"
branch_labels = None
depends_on = None


def is_postgres() -> bool:
    """Check if the current database is PostgreSQL."""
    bind = op.get_bind()
    return bind.dialect.name == "postgresql"


def upgrade():
    """Add learning tables for Companion autofill improvement.

    Tables:
    - form_profiles: Per-host+schema canonical field mappings and performance stats
    - autofill_events: Per-run telemetry for learning aggregation
    - gen_styles: Autofill style variants (tone, format, length presets)

    Note: This migration is PostgreSQL-only and will be skipped on SQLite.
    """
    if not is_postgres():
        # Skip this migration entirely on non-Postgres (e.g., SQLite dev)
        return

    # form_profiles table
    op.create_table(
        "form_profiles",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("host", sa.Text(), nullable=False),
        sa.Column("schema_hash", sa.Text(), nullable=False),
        sa.Column(
            "fields",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("success_rate", sa.Numeric(5, 2), nullable=True),
        sa.Column("avg_edit_chars", sa.Numeric(10, 2), nullable=True),
        sa.Column("avg_duration_ms", sa.Integer(), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Indexes for form_profiles
    op.create_index(
        "ix_form_profiles_host_schema",
        "form_profiles",
        ["host", "schema_hash"],
        unique=True,
    )
    op.create_index(
        "ix_form_profiles_last_seen", "form_profiles", ["last_seen_at"], unique=False
    )

    # autofill_events table
    op.create_table(
        "autofill_events",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("host", sa.Text(), nullable=False),
        sa.Column("schema_hash", sa.Text(), nullable=False),
        sa.Column(
            "suggested_map",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "final_map",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("gen_style_id", sa.Text(), nullable=True),
        sa.Column(
            "edit_stats",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column(
            "validation_errors",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("status", sa.Text(), nullable=False, server_default="ok"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["application_id"], ["extension_applications.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Indexes for autofill_events
    op.create_index(
        "ix_autofill_events_user_id", "autofill_events", ["user_id"], unique=False
    )
    op.create_index(
        "ix_autofill_events_host_schema",
        "autofill_events",
        ["host", "schema_hash"],
        unique=False,
    )
    op.create_index(
        "ix_autofill_events_created_at", "autofill_events", ["created_at"], unique=False
    )
    op.create_index(
        "ix_autofill_events_status", "autofill_events", ["status"], unique=False
    )
    op.create_index(
        "ix_autofill_events_gen_style_id",
        "autofill_events",
        ["gen_style_id"],
        unique=False,
    )

    # gen_styles table
    op.create_table(
        "gen_styles",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column(
            "temperature", sa.Numeric(3, 2), nullable=False, server_default="0.7"
        ),
        sa.Column("tone", sa.Text(), nullable=False, server_default="concise"),
        sa.Column("format", sa.Text(), nullable=False, server_default="bullets"),
        sa.Column("length_hint", sa.Text(), nullable=False, server_default="medium"),
        sa.Column(
            "keywords_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
        sa.Column(
            "prior_weight", sa.Numeric(10, 4), nullable=False, server_default="1.0"
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Indexes for gen_styles
    op.create_index(
        "ix_gen_styles_prior_weight", "gen_styles", ["prior_weight"], unique=False
    )

    # Insert default generation styles
    op.execute("""
        INSERT INTO gen_styles (id, name, temperature, tone, format, length_hint, prior_weight) VALUES
        ('concise_bullets_v1', 'Concise Bullets', 0.5, 'concise', 'bullets', 'short', 1.0),
        ('narrative_para_v1', 'Narrative Paragraph', 0.7, 'narrative', 'paragraph', 'medium', 1.0),
        ('confident_detailed_v1', 'Confident & Detailed', 0.6, 'confident', 'bullets', 'long', 1.0)
    """)


def downgrade():
    """Drop learning tables and indexes."""
    if not is_postgres():
        # Skip on non-Postgres (e.g., SQLite dev)
        return

    # Drop gen_styles
    op.drop_index("ix_gen_styles_prior_weight", table_name="gen_styles")
    op.drop_table("gen_styles")

    # Drop autofill_events
    op.drop_index("ix_autofill_events_gen_style_id", table_name="autofill_events")
    op.drop_index("ix_autofill_events_status", table_name="autofill_events")
    op.drop_index("ix_autofill_events_created_at", table_name="autofill_events")
    op.drop_index("ix_autofill_events_host_schema", table_name="autofill_events")
    op.drop_index("ix_autofill_events_user_id", table_name="autofill_events")
    op.drop_table("autofill_events")

    # Drop form_profiles
    op.drop_index("ix_form_profiles_last_seen", table_name="form_profiles")
    op.drop_index("ix_form_profiles_host_schema", table_name="form_profiles")
    op.drop_table("form_profiles")
