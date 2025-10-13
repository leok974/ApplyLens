"""phase6 personalization (user_weights, policy_stats)

Revision ID: 0017_phase6_personalization
Revises: 0016_phase4_actions
Create Date: 2025-10-13
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import TIMESTAMP

revision = "0017_phase6_personalization"
down_revision = "0016_phase4_actions"
branch_labels = None
depends_on = None


def upgrade():
    """
    Create tables for Phase 6: Personalization & Learning
    
    - user_weights: Per-user feature weights learned from approve/reject feedback
    - policy_stats: Per-user, per-policy performance metrics (precision, recall)
    """
    # User weights table
    op.create_table(
        "user_weights",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.String, index=True, nullable=False),
        sa.Column("feature", sa.String, nullable=False),
        sa.Column("weight", sa.Float, server_default="0"),
        sa.Column("updated_at", TIMESTAMP, server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "feature", name="uq_user_feature")
    )
    
    # Policy statistics table
    op.create_table(
        "policy_stats",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("policy_id", sa.Integer, index=True, nullable=False),
        sa.Column("user_id", sa.String, index=True, nullable=False),
        sa.Column("fired", sa.Integer, server_default="0"),
        sa.Column("approved", sa.Integer, server_default="0"),
        sa.Column("rejected", sa.Integer, server_default="0"),
        sa.Column("precision", sa.Float, server_default="0"),
        sa.Column("recall", sa.Float, server_default="0"),
        sa.Column("window_days", sa.Integer, server_default="30"),
        sa.Column("updated_at", TIMESTAMP, server_default=sa.func.now()),
        sa.UniqueConstraint("policy_id", "user_id", name="uq_pol_user")
    )


def downgrade():
    """Drop personalization tables"""
    op.drop_table("policy_stats")
    op.drop_table("user_weights")
