-- Adds source_confidence to applications; defaults conservatively to 0.5
ALTER TABLE applications
ADD COLUMN source_confidence REAL NOT NULL DEFAULT 0.5;

-- Optional: backfill existing rows to 0.8 if they already had a clear source
-- (commented out; enable if you want)
-- UPDATE applications
--   SET source_confidence = 0.8
-- WHERE source IN ('Greenhouse','Lever','Workday');
