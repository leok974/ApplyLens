"""split circular FKs (emails↔applications) into deferrable constraints

Revision ID: 0018_split_fk_cycles
Revises: 0017_phase6_personalization
Create Date: 2025-10-13
"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "0018_split_fk_cycles"
down_revision = "0017_phase6_personalization"
branch_labels = None
depends_on = None


def upgrade():
    """
    Break the circular dependency between emails and applications tables.
    
    The circular FK cycle prevents proper table creation and can cause
    deadlocks during bulk operations. We drop the inline FKs and recreate
    them as DEFERRABLE INITIALLY DEFERRED constraints.
    """
    # Drop inline constraints if present (names may vary across DBs)
    # Try both common names and no-op on failures to keep it idempotent.
    try:
        op.drop_constraint("emails_application_id_fkey", "emails", type_="foreignkey")
    except Exception:
        pass
    
    try:
        op.drop_constraint("applications_last_email_id_fkey", "applications", type_="foreignkey")
    except Exception:
        pass

    # Recreate as deferrable so insert/update order doesn't deadlock CI
    op.create_foreign_key(
        "fk_emails_application",
        source_table="emails",
        referent_table="applications",
        local_cols=["application_id"],
        remote_cols=["id"],
        deferrable=True,
        initially="DEFERRED",
    )
    
    op.create_foreign_key(
        "fk_applications_last_email",
        source_table="applications",
        referent_table="emails",
        local_cols=["last_email_id"],
        remote_cols=["id"],
        deferrable=True,
        initially="DEFERRED",
    )


def downgrade():
    """
    Best-effort drop of deferrable constraints.
    
    Note: We don't recreate the inline FKs in downgrade to avoid
    reintroducing the cycle. Alembic may not allow this if other
    dependencies exist.
    """
    try:
        op.drop_constraint("fk_emails_application", "emails", type_="foreignkey")
    except Exception:
        pass
    
    try:
        op.drop_constraint("fk_applications_last_email", "applications", type_="foreignkey")
    except Exception:
        pass
