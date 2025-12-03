"""add email classification tables and columns

Revision ID: 20251203_classification
Revises: bf7f93a3b301
Create Date: 2025-12-03 12:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20251203_classification"
down_revision = "bf7f93a3b301"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- emails table columns ---
    op.add_column(
        "emails",
        sa.Column("category", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "emails",
        sa.Column("is_real_opportunity", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "emails",
        sa.Column("category_confidence", sa.Float(), nullable=True),
    )
    op.add_column(
        "emails",
        sa.Column("classifier_version", sa.String(length=64), nullable=True),
    )

    op.create_index(
        "ix_emails_category",
        "emails",
        ["category"],
        unique=False,
    )
    op.create_index(
        "ix_emails_is_real_opportunity",
        "emails",
        ["is_real_opportunity"],
        unique=False,
    )

    # --- email_classification_events ---
    op.create_table(
        "email_classification_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "email_id",
            sa.Integer(),
            sa.ForeignKey("emails.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("thread_id", sa.String(length=255), nullable=True),
        sa.Column("model_version", sa.String(length=64), nullable=False),
        sa.Column("predicted_category", sa.String(length=64), nullable=False),
        sa.Column("predicted_is_real_opportunity", sa.Boolean(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_index(
        "ix_email_classification_events_email_id",
        "email_classification_events",
        ["email_id"],
        unique=False,
    )
    op.create_index(
        "ix_email_classification_events_created_at",
        "email_classification_events",
        ["created_at"],
        unique=False,
    )

    # --- email_category_corrections ---
    op.create_table(
        "email_category_corrections",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "email_id",
            sa.Integer(),
            sa.ForeignKey("emails.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("thread_id", sa.String(length=255), nullable=True),
        sa.Column("old_category", sa.String(length=64), nullable=True),
        sa.Column("new_category", sa.String(length=64), nullable=False),
        sa.Column("old_is_real_opportunity", sa.Boolean(), nullable=True),
        sa.Column("new_is_real_opportunity", sa.Boolean(), nullable=False),
        sa.Column(
            "user_id",
            sa.String(length=64),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_index(
        "ix_email_category_corrections_email_id",
        "email_category_corrections",
        ["email_id"],
        unique=False,
    )
    op.create_index(
        "ix_email_category_corrections_created_at",
        "email_category_corrections",
        ["created_at"],
        unique=False,
    )

    # --- email_golden_labels ---
    op.create_table(
        "email_golden_labels",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "email_id",
            sa.Integer(),
            sa.ForeignKey("emails.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("thread_id", sa.String(length=255), nullable=True),
        sa.Column("golden_category", sa.String(length=64), nullable=False),
        sa.Column("golden_is_real_opportunity", sa.Boolean(), nullable=False),
        sa.Column("labeler", sa.String(length=128), nullable=True),
        sa.Column(
            "labeled_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_unique_constraint(
        "uq_email_golden_labels_email_id", "email_golden_labels", ["email_id"]
    )

    # --- email_training_labels ---
    op.create_table(
        "email_training_labels",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "email_id",
            sa.Integer(),
            sa.ForeignKey("emails.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("thread_id", sa.String(length=255), nullable=True),
        sa.Column("label_category", sa.String(length=64), nullable=False),
        sa.Column("label_is_real_opportunity", sa.Boolean(), nullable=False),
        sa.Column("label_source", sa.String(length=64), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_index(
        "ix_email_training_labels_email_id",
        "email_training_labels",
        ["email_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_email_training_labels_email_id", table_name="email_training_labels"
    )
    op.drop_table("email_training_labels")

    op.drop_unique_constraint(
        "uq_email_golden_labels_email_id",
        table_name="email_golden_labels",
    )
    op.drop_table("email_golden_labels")

    op.drop_index(
        "ix_email_category_corrections_created_at",
        table_name="email_category_corrections",
    )
    op.drop_index(
        "ix_email_category_corrections_email_id",
        table_name="email_category_corrections",
    )
    op.drop_table("email_category_corrections")

    op.drop_index(
        "ix_email_classification_events_created_at",
        table_name="email_classification_events",
    )
    op.drop_index(
        "ix_email_classification_events_email_id",
        table_name="email_classification_events",
    )
    op.drop_table("email_classification_events")

    op.drop_index("ix_emails_is_real_opportunity", table_name="emails")
    op.drop_index("ix_emails_category", table_name="emails")

    op.drop_column("emails", "classifier_version")
    op.drop_column("emails", "category_confidence")
    op.drop_column("emails", "is_real_opportunity")
    op.drop_column("emails", "category")
