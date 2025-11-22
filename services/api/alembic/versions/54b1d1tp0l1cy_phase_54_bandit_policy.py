"""Phase 5.4: Add bandit policy tracking to autofill_events

Revision ID: 54b1d1tp0l1cy
Revises: a1b2c3d4e5f6
Create Date: 2025-11-14

Adds policy column to autofill_events table to track whether each
autofill used exploit (best style), explore (alternative style), or
fallback (no learning data) during epsilon-greedy bandit selection.
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "54b1d1tp0l1cy"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add policy column with index for bandit tracking."""
    op.add_column(
        "autofill_events",
        sa.Column("policy", sa.String(length=16), nullable=True),
    )
    op.create_index(
        "ix_autofill_events_policy",
        "autofill_events",
        ["policy"],
        unique=False,
    )


def downgrade() -> None:
    """Remove policy column and index."""
    op.drop_index("ix_autofill_events_policy", table_name="autofill_events")
    op.drop_column("autofill_events", "policy")
