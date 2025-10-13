"""phase4 actions (proposed/audit/policies)

Revision ID: 0016_phase4_actions
Revises: 0015_add_security_policies
Create Date: 2025-10-12
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import TIMESTAMP

revision = "0016_phase4_actions"
down_revision = "0015_add_security_policies"
branch_labels = None
depends_on = None


def upgrade():
    # Create ActionType enum
    op.execute("""
        CREATE TYPE actiontype AS ENUM (
            'label_email',
            'archive_email',
            'move_to_folder',
            'unsubscribe_via_header',
            'create_calendar_event',
            'create_task',
            'block_sender',
            'quarantine_attachment'
        )
    """)
    
    # Create policies table
    op.create_table(
        "policies",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String, unique=True, nullable=False),
        sa.Column("enabled", sa.Boolean, server_default="true", nullable=False),
        sa.Column("priority", sa.Integer, server_default="100", nullable=False),
        sa.Column("condition", sa.JSON, nullable=False),
        sa.Column("action", sa.Enum(
            "label_email", "archive_email", "move_to_folder", "unsubscribe_via_header",
            "create_calendar_event", "create_task", "block_sender", "quarantine_attachment",
            name="actiontype"
        ), nullable=False),
        sa.Column("confidence_threshold", sa.Float, server_default="0.7", nullable=False),
        sa.Column("created_at", TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    
    # Create proposed_actions table
    op.create_table(
        "proposed_actions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("email_id", sa.Integer, index=True, nullable=False),
        sa.Column("action", sa.Enum(name="actiontype"), nullable=False),
        sa.Column("params", sa.JSON, server_default="{}"),
        sa.Column("confidence", sa.Float, nullable=False),
        sa.Column("rationale", sa.JSON, server_default="{}"),
        sa.Column("policy_id", sa.Integer, sa.ForeignKey("policies.id"), nullable=True),
        sa.Column("created_at", TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("status", sa.String, server_default="'pending'", nullable=False),
        sa.Column("reviewed_by", sa.String, nullable=True),
        sa.Column("reviewed_at", TIMESTAMP(timezone=True), nullable=True),
    )
    
    # Create audit_actions table
    op.create_table(
        "audit_actions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("email_id", sa.Integer, index=True, nullable=False),
        sa.Column("action", sa.Enum(name="actiontype"), nullable=False),
        sa.Column("params", sa.JSON, server_default="{}"),
        sa.Column("actor", sa.String, nullable=False),
        sa.Column("outcome", sa.String, nullable=False),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("why", sa.JSON, server_default="{}"),
        sa.Column("screenshot_path", sa.String, nullable=True),
        sa.Column("created_at", TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
    )


def downgrade():
    op.drop_table("audit_actions")
    op.drop_table("proposed_actions")
    op.drop_table("policies")
    op.execute("DROP TYPE actiontype")
