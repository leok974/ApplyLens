"""phase_52_segment_key

Revision ID: a1b2c3d4e5f6
Revises: 75310f8e88d7
Create Date: 2025-11-14 18:00:00.000000

Phase 5.2: Add segment_key column to autofill_events for segment-aware style tuning
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "a1b2c3d4e5f6"
down_revision = "75310f8e88d7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add segment_key column to autofill_events
    op.add_column(
        "autofill_events",
        sa.Column("segment_key", sa.String(length=128), nullable=True),
    )

    # Add index on segment_key for efficient segment-based queries
    op.create_index(
        op.f("ix_autofill_events_segment_key"),
        "autofill_events",
        ["segment_key"],
        unique=False,
    )


def downgrade() -> None:
    # Remove index first, then column
    op.drop_index(op.f("ix_autofill_events_segment_key"), table_name="autofill_events")
    op.drop_column("autofill_events", "segment_key")
