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
    
    Note: This migration is only relevant if the FK columns exist. If they
    don't exist yet (fresh DB), this migration is a no-op.
    """
    # Use raw SQL with DO blocks for idempotent constraint handling
    # This avoids transaction failures from try/except in Python
    
    op.execute("""
    DO $$
    BEGIN
        -- Only proceed if both FK columns exist
        IF EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'emails' AND column_name = 'application_id'
        ) AND EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'applications' AND column_name = 'last_email_id'
        ) THEN
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
            
            -- Create deferrable FK constraints
            ALTER TABLE emails 
                ADD CONSTRAINT fk_emails_application 
                FOREIGN KEY (application_id) REFERENCES applications(id) 
                DEFERRABLE INITIALLY DEFERRED;
            
            ALTER TABLE applications 
                ADD CONSTRAINT fk_applications_last_email 
                FOREIGN KEY (last_email_id) REFERENCES emails(id) 
                DEFERRABLE INITIALLY DEFERRED;
        END IF;
    END$$;
    """)


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
