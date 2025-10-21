"""Add multi-user authentication tables

Revision ID: 0028_multi_user_auth
Revises: 0027_incident_metadata_rename
Create Date: 2025-10-20 19:35:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0028_multi_user_auth"
down_revision: Union[str, None] = "0027_incident_metadata_rename"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        "users",
        sa.Column("id", sa.String(64), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("picture_url", sa.Text(), nullable=True),
        sa.Column("is_demo", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), onupdate=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # Create sessions table
    op.create_table(
        "sessions",
        sa.Column("id", sa.String(64), nullable=False),
        sa.Column("user_id", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_sessions_user_id", "sessions", ["user_id"])

    # Add user_id column to oauth_tokens (nullable for backward compatibility)
    op.add_column("oauth_tokens", sa.Column("user_id", sa.String(64), nullable=True))
    op.create_index("ix_oauth_tokens_user_id", "oauth_tokens", ["user_id"])
    op.create_foreign_key(
        "fk_oauth_tokens_user_id",
        "oauth_tokens",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE"
    )


def downgrade() -> None:
    # Remove foreign key and column from oauth_tokens
    op.drop_constraint("fk_oauth_tokens_user_id", "oauth_tokens", type_="foreignkey")
    op.drop_index("ix_oauth_tokens_user_id", table_name="oauth_tokens")
    op.drop_column("oauth_tokens", "user_id")

    # Drop sessions table
    op.drop_index("ix_sessions_user_id", table_name="sessions")
    op.drop_table("sessions")

    # Drop users table
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
