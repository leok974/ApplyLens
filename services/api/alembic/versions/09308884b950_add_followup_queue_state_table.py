"""add followup queue state table

Revision ID: 09308884b950
Revises: 20251120_165655
Create Date: 2025-11-24 17:15:15.234260

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "09308884b950"
down_revision = "20251120_165655"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "followup_queue_state",
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("thread_id", sa.Text(), nullable=False),
        sa.Column("application_id", sa.Integer(), nullable=True),
        sa.Column(
            "is_done", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column("done_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("user_id", "thread_id"),
    )

    # Index for fast lookups by user
    op.create_index(
        "ix_followup_queue_state_user_id",
        "followup_queue_state",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_table("followup_queue_state")
