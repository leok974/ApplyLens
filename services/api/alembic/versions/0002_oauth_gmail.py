"""Add OAuth and Gmail fields

Revision ID: 0002_oauth_gmail
Revises: 0001_init
Create Date: 2025-10-09 03:25:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0002_oauth_gmail"
down_revision = "0001_init"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create oauth_tokens table
    op.create_table(
        "oauth_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("user_email", sa.String(length=320), nullable=False),
        sa.Column("access_token", sa.Text(), nullable=False),
        sa.Column("refresh_token", sa.Text(), nullable=True),
        sa.Column("token_uri", sa.Text(), nullable=False),
        sa.Column("client_id", sa.Text(), nullable=False),
        sa.Column("client_secret", sa.Text(), nullable=False),
        sa.Column("scopes", sa.Text(), nullable=False),
        sa.Column("expiry", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_oauth_tokens_provider"), "oauth_tokens", ["provider"], unique=False
    )
    op.create_index(
        op.f("ix_oauth_tokens_user_email"), "oauth_tokens", ["user_email"], unique=False
    )

    # Add new columns to emails table
    op.add_column("emails", sa.Column("gmail_id", sa.String(length=128), nullable=True))
    op.add_column(
        "emails", sa.Column("labels", postgresql.ARRAY(sa.String()), nullable=True)
    )
    op.add_column(
        "emails",
        sa.Column("label_heuristics", postgresql.ARRAY(sa.String()), nullable=True),
    )
    op.add_column("emails", sa.Column("raw", sa.JSON(), nullable=True))

    # Create indexes for gmail_id
    op.create_index(op.f("ix_emails_gmail_id"), "emails", ["gmail_id"], unique=True)
    op.create_index(
        "idx_emails_gmail_search",
        "emails",
        ["subject", "from_addr", "to_addr"],
        unique=False,
    )


def downgrade() -> None:
    # Remove new email columns
    op.drop_index("idx_emails_gmail_search", table_name="emails")
    op.drop_index(op.f("ix_emails_gmail_id"), table_name="emails")
    op.drop_column("emails", "raw")
    op.drop_column("emails", "label_heuristics")
    op.drop_column("emails", "labels")
    op.drop_column("emails", "gmail_id")

    # Drop oauth_tokens table
    op.drop_index(op.f("ix_oauth_tokens_user_email"), table_name="oauth_tokens")
    op.drop_index(op.f("ix_oauth_tokens_provider"), table_name="oauth_tokens")
    op.drop_table("oauth_tokens")
