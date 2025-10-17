"""add source_confidence to applications

Revision ID: 0004_add_source_confidence
Revises: 0003_applications
Create Date: 2025-10-09
"""

from alembic import op
import sqlalchemy as sa


revision = "0004_add_source_confidence"
down_revision = "0003_applications"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add source_confidence column to applications table (if it doesn't exist)
    from sqlalchemy import inspect

    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [col["name"] for col in inspector.get_columns("applications")]

    if "source_confidence" not in columns:
        op.add_column(
            "applications",
            sa.Column(
                "source_confidence", sa.Float(), nullable=False, server_default="0.5"
            ),
        )


def downgrade() -> None:
    # Drop source_confidence column
    op.drop_column("applications", "source_confidence")
