"""agent_feedback

Add tables for Agent V2 learning loop with user feedback capture

Revision ID: 20251120_165655
Revises: f6fb0a0
Create Date: 2025-11-20 16:56:55.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20251120_165655"
down_revision = "f6fb0a0"
branch_labels = None
depends_on = None


def upgrade():
    # agent_feedback: capture user feedback on agent cards/items
    op.create_table(
        "agent_feedback",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("intent", sa.Text(), nullable=False),
        sa.Column("query", sa.Text(), nullable=True),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("card_id", sa.Text(), nullable=False),
        sa.Column("item_id", sa.Text(), nullable=True),
        sa.Column(
            "label",
            sa.Text(),
            nullable=False,
            comment="helpful | not_helpful | hide | done",
        ),
        sa.Column("thread_id", sa.Text(), nullable=True),
        sa.Column("message_id", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )

    # Indexes for fast lookups
    op.create_index(
        "ix_agent_feedback_user_intent_created_at",
        "agent_feedback",
        ["user_id", "intent", "created_at"],
    )
    op.create_index(
        "ix_agent_feedback_thread",
        "agent_feedback",
        ["thread_id"],
    )
    op.create_index(
        "ix_agent_feedback_user_id",
        "agent_feedback",
        ["user_id"],
    )

    # agent_preferences: cached per-user preferences for fast filtering
    op.create_table(
        "agent_preferences",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "data",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # Index for updated_at to find stale preferences
    op.create_index(
        "ix_agent_preferences_updated_at",
        "agent_preferences",
        ["updated_at"],
    )


def downgrade():
    op.drop_table("agent_preferences")
    op.drop_table("agent_feedback")
