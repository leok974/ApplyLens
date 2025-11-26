"""Fix emails table schema - rename columns and add missing fields

Revision ID: c1d2e3f4g5h6
Revises: bf7f93a3b301
Create Date: 2025-11-26

This migration fixes the emails table schema to match the current Email model:
1. Rename from_addr -> sender
2. Rename to_addr -> recipient
3. Add missing columns that exist in model but not in migrations:
   - gmail_id (unique, indexed)
   - owner_email (for multi-user support)
   - labels, label_heuristics (arrays)
   - raw (JSON)
   - company, role, source, source_confidence
   - first_user_reply_at, last_user_reply_at, user_reply_count
   - category, risk_score, flags, quarantined, expires_at
   - profile_tags, features_json

This ensures migrations match the actual Email model.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "c1d2e3f4g5h6"
down_revision = "bf7f93a3b301"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Step 1: Rename existing columns
    op.alter_column("emails", "from_addr", new_column_name="sender")
    op.alter_column("emails", "to_addr", new_column_name="recipient")

    # Step 2: Modify existing columns to match model
    op.alter_column("emails", "subject", type_=sa.Text(), nullable=True)
    op.alter_column(
        "emails", "label", new_column_name="old_label"
    )  # Will be replaced by labels array

    # Step 3: Add missing columns
    op.add_column(
        "emails",
        sa.Column("gmail_id", sa.String(128), unique=True, index=True, nullable=True),
    )
    op.add_column(
        "emails", sa.Column("labels", postgresql.ARRAY(sa.String()), nullable=True)
    )
    op.add_column(
        "emails",
        sa.Column("label_heuristics", postgresql.ARRAY(sa.String()), nullable=True),
    )
    op.add_column("emails", sa.Column("raw", postgresql.JSONB(), nullable=True))

    # Multi-user support
    op.add_column(
        "emails", sa.Column("owner_email", sa.String(320), index=True, nullable=True)
    )

    # Quick hooks
    op.add_column(
        "emails", sa.Column("company", sa.String(256), index=True, nullable=True)
    )
    op.add_column(
        "emails", sa.Column("role", sa.String(512), index=True, nullable=True)
    )
    op.add_column(
        "emails", sa.Column("source", sa.String(128), index=True, nullable=True)
    )
    op.add_column(
        "emails",
        sa.Column("source_confidence", sa.Float(), nullable=True, server_default="0.0"),
    )

    # Reply metrics
    op.add_column(
        "emails",
        sa.Column("first_user_reply_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "emails",
        sa.Column("last_user_reply_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "emails",
        sa.Column("user_reply_count", sa.Integer(), nullable=True, server_default="0"),
    )

    # Email automation fields
    op.add_column("emails", sa.Column("category", sa.Text(), index=True, nullable=True))
    op.add_column(
        "emails", sa.Column("risk_score", sa.Float(), index=True, nullable=True)
    )
    op.add_column(
        "emails",
        sa.Column(
            "flags", postgresql.JSONB(), nullable=False, server_default="'[]'::jsonb"
        ),
    )
    op.add_column(
        "emails",
        sa.Column("quarantined", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "emails",
        sa.Column("expires_at", sa.DateTime(timezone=True), index=True, nullable=True),
    )
    op.add_column(
        "emails", sa.Column("profile_tags", postgresql.ARRAY(sa.Text()), nullable=True)
    )
    op.add_column(
        "emails", sa.Column("features_json", postgresql.JSONB(), nullable=True)
    )

    # Step 4: Create indexes for sender and recipient
    op.create_index("ix_emails_sender", "emails", ["sender"])
    op.create_index("ix_emails_recipient", "emails", ["recipient"])


def downgrade() -> None:
    # Remove added indexes
    op.drop_index("ix_emails_recipient", table_name="emails")
    op.drop_index("ix_emails_sender", table_name="emails")

    # Remove added columns
    op.drop_column("emails", "features_json")
    op.drop_column("emails", "profile_tags")
    op.drop_column("emails", "expires_at")
    op.drop_column("emails", "quarantined")
    op.drop_column("emails", "flags")
    op.drop_column("emails", "risk_score")
    op.drop_column("emails", "category")
    op.drop_column("emails", "user_reply_count")
    op.drop_column("emails", "last_user_reply_at")
    op.drop_column("emails", "first_user_reply_at")
    op.drop_column("emails", "source_confidence")
    op.drop_column("emails", "source")
    op.drop_column("emails", "role")
    op.drop_column("emails", "company")
    op.drop_column("emails", "owner_email")
    op.drop_column("emails", "raw")
    op.drop_column("emails", "label_heuristics")
    op.drop_column("emails", "labels")
    op.drop_column("emails", "gmail_id")

    # Restore original column names
    op.alter_column("emails", "old_label", new_column_name="label")
    op.alter_column("emails", "subject", type_=sa.String(512))
    op.alter_column("emails", "recipient", new_column_name="to_addr")
    op.alter_column("emails", "sender", new_column_name="from_addr")
