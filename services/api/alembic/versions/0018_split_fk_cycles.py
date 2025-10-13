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
    # Use raw SQL with DO blocks for idempotent constraint handling
    # This avoids transaction failures from try/except in Python
    
    op.execute("""
    DO $$
    BEGIN
        -- Drop emails.application_id FK if exists
        IF EXISTS (
            SELECT 1 FROM information_schema.table_constraints 
            WHERE constraint_name = 'emails_application_id_fkey' 
            AND table_name = 'emails'
        ) THEN
            ALTER TABLE emails DROP CONSTRAINT emails_application_id_fkey;
        END IF;
        
        -- Drop applications.last_email_id FK if exists  
        IF EXISTS (
            SELECT 1 FROM information_schema.table_constraints 
            WHERE constraint_name = 'applications_last_email_id_fkey' 
            AND table_name = 'applications'
        ) THEN
            ALTER TABLE applications DROP CONSTRAINT applications_last_email_id_fkey;
        END IF;
    END$$;
    """)

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
    op.execute("""
    DO $$
    BEGIN
        -- Drop deferrable FK constraints if they exist
        IF EXISTS (
            SELECT 1 FROM information_schema.table_constraints 
            WHERE constraint_name = 'fk_emails_application' 
            AND table_name = 'emails'
        ) THEN
            ALTER TABLE emails DROP CONSTRAINT fk_emails_application;
        END IF;
        
        IF EXISTS (
            SELECT 1 FROM information_schema.table_constraints 
            WHERE constraint_name = 'fk_applications_last_email' 
            AND table_name = 'applications'
        ) THEN
            ALTER TABLE applications DROP CONSTRAINT fk_applications_last_email;
        END IF;
    END$$;
    """)
