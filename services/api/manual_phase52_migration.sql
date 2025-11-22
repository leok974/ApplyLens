-- Phase 5.2 Manual Migration Script
-- Adds segment_key column to autofill_events table
--
-- Run this if Alembic migration fails due to Phase 5.0 migration issues
-- Execute: docker exec applylens-db-prod psql -U applylens -d applylens -f /tmp/manual_phase52_migration.sql

-- Add segment_key column
ALTER TABLE autofill_events
ADD COLUMN IF NOT EXISTS segment_key VARCHAR(128);

-- Create index on segment_key
CREATE INDEX IF NOT EXISTS ix_autofill_events_segment_key
ON autofill_events (segment_key);

-- Update alembic_version to Phase 5.2
UPDATE alembic_version
SET version_num = 'a1b2c3d4e5f6'
WHERE version_num = '75310f8e88d7';

-- Verify migration
SELECT
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'autofill_events'
    AND column_name = 'segment_key';

-- Show sample data
SELECT COUNT(*) as total_events,
       COUNT(segment_key) as with_segment,
       COUNT(DISTINCT segment_key) as unique_segments
FROM autofill_events;
