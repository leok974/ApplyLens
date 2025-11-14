"""phase_5_style_feedback_tracking

Revision ID: 75310f8e88d7
Revises: 368f376b45b8
Create Date: 2025-11-14 11:02:40.773208

Phase 5.0: Add feedback tracking columns to autofill_events and style_hint to form_profiles
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "75310f8e88d7"
down_revision = "368f376b45b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add feedback tracking columns to autofill_events
    op.add_column(
        "autofill_events", sa.Column("feedback_status", sa.Text(), nullable=True)
    )
    op.add_column(
        "autofill_events", sa.Column("edit_chars", sa.Integer(), nullable=True)
    )

    # Add index on feedback_status for efficient queries
    op.create_index(
        op.f("ix_autofill_events_feedback_status"),
        "autofill_events",
        ["feedback_status"],
        unique=False,
    )

    # Add style_hint column to form_profiles
    op.add_column(
        "form_profiles",
        sa.Column("style_hint", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    # Remove style_hint from form_profiles
    op.drop_column("form_profiles", "style_hint")

    # Remove feedback tracking columns from autofill_events
    op.drop_index(
        op.f("ix_autofill_events_feedback_status"), table_name="autofill_events"
    )
    op.drop_column("autofill_events", "edit_chars")
    op.drop_column("autofill_events", "feedback_status")
