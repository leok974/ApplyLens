"""add last_email_id column to applications table

Revision ID: 0020_add_last_email_id
Revises: 0019_add_thread_id
Create Date: 2025-10-14
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0020_add_last_email_id"
down_revision = "0019_add_thread_id"
branch_labels = None
depends_on = None


def upgrade():
    """
    Add the last_email_id column to applications table.
    
    This column is used to track the most recent email associated with an application.
    It participates in a circular FK relationship with emails.application_id, which was
    made deferrable in migration 0018.
    
    Note: Migration 0018 assumes this column exists and only adds the deferrable constraint.
    This migration adds the actual column if it doesn't exist.
    """
    op.execute("""
    DO $$
    BEGIN
        -- Add last_email_id column if it doesn't exist
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'applications' AND column_name = 'last_email_id'
        ) THEN
            ALTER TABLE applications 
                ADD COLUMN last_email_id INTEGER NULL;
            
            -- Create index for FK lookups
            CREATE INDEX IF NOT EXISTS ix_applications_last_email_id 
                ON applications(last_email_id);
        END IF;
        
        -- Ensure the deferrable constraint exists (in case 0018 ran before this)
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.table_constraints 
            WHERE constraint_name = 'fk_applications_last_email' 
            AND table_name = 'applications'
        ) THEN
            ALTER TABLE applications 
                ADD CONSTRAINT fk_applications_last_email 
                FOREIGN KEY (last_email_id) REFERENCES emails(id) 
                DEFERRABLE INITIALLY DEFERRED;
        END IF;
    END$$;
    """)


def downgrade():
    """
    Remove the last_email_id column and its constraint.
    """
    op.execute("""
    DO $$
    BEGIN
        -- Drop constraint if it exists
        IF EXISTS (
            SELECT 1 FROM information_schema.table_constraints 
            WHERE constraint_name = 'fk_applications_last_email' 
            AND table_name = 'applications'
        ) THEN
            ALTER TABLE applications DROP CONSTRAINT fk_applications_last_email;
        END IF;
        
        -- Drop index if it exists
        DROP INDEX IF EXISTS ix_applications_last_email_id;
        
        -- Drop column if it exists
        IF EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'applications' AND column_name = 'last_email_id'
        ) THEN
            ALTER TABLE applications DROP COLUMN last_email_id;
        END IF;
    END$$;
    """)
