"""Add security analysis fields to emails table

Revision ID: 0014_add_security_fields
Revises: 0013_phase2_ml_profile
Create Date: 2025-10-12 13:15:00.000000

This migration adds comprehensive security analysis fields:
- quarantined: Boolean flag for automatically quarantined emails
- flags: JSONB array of security risk flags with signal/evidence/weight

Note: risk_score already exists as Float from 0010 (will be used as-is for now)
The security analyzer produces integer scores 0-100, which can be stored in Float.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision = "0014_add_security_fields"
down_revision = "0013_phase2_ml_profile"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add security analysis fields to emails table."""
    # Add quarantined boolean flag
    op.add_column(
        "emails",
        sa.Column(
            "quarantined", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
    )

    # Add flags JSONB array for risk flag details
    op.add_column(
        "emails",
        sa.Column(
            "flags",
            JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )

    # Add index for quarantined emails (for efficient filtering)
    op.create_index("ix_emails_quarantined", "emails", ["quarantined"], unique=False)

    # Add comments for documentation
    op.execute(
        "COMMENT ON COLUMN emails.quarantined IS 'Automatically quarantined by security analyzer when risk_score >= threshold'"
    )
    op.execute(
        "COMMENT ON COLUMN emails.flags IS 'Array of security risk flags [{signal, evidence, weight}, ...]'"
    )


def downgrade() -> None:
    """Remove security analysis fields."""
    op.drop_index("ix_emails_quarantined", table_name="emails")
    op.drop_column("emails", "flags")
    op.drop_column("emails", "quarantined")
