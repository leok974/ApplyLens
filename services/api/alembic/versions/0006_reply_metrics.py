"""add reply metrics columns to emails

Revision ID: 0006_reply_metrics
Revises: 0005_add_gmail_tokens
Create Date: 2025-10-09
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0006_reply_metrics"
down_revision = "0005_add_gmail_tokens"
branch_labels = None
depends_on = None


def upgrade():
    # Add reply metric columns (if they don't exist)
    from sqlalchemy import inspect

    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [col["name"] for col in inspector.get_columns("emails")]

    with op.batch_alter_table("emails") as batch:
        if "first_user_reply_at" not in columns:
            batch.add_column(
                sa.Column(
                    "first_user_reply_at", sa.DateTime(timezone=True), nullable=True
                )
            )
        if "last_user_reply_at" not in columns:
            batch.add_column(
                sa.Column(
                    "last_user_reply_at", sa.DateTime(timezone=True), nullable=True
                )
            )
        if "user_reply_count" not in columns:
            batch.add_column(
                sa.Column(
                    "user_reply_count", sa.Integer(), nullable=False, server_default="0"
                )
            )


def downgrade():
    with op.batch_alter_table("emails") as batch:
        batch.drop_column("user_reply_count")
        batch.drop_column("last_user_reply_at")
        batch.drop_column("first_user_reply_at")
