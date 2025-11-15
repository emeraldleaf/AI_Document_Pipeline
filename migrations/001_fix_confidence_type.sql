-- ==============================================================================
-- MIGRATION: Fix confidence column type from TEXT to FLOAT
-- ==============================================================================
--
-- ISSUE: confidence column is TEXT but should be FLOAT for OpenSearch compatibility
-- IMPACT: Causes migration failures for 500K+ documents at scale
--
-- SAFETY: This migration preserves existing data by:
-- 1. Creating a new column with correct type
-- 2. Converting numeric values, setting text values to NULL
-- 3. Dropping old column and renaming new one
--
-- ==============================================================================

BEGIN;

-- Step 1: Add new column with correct type
ALTER TABLE documents
ADD COLUMN confidence_numeric FLOAT;

-- Step 2: Migrate numeric values (if any exist)
-- Text values are intentionally set to NULL as they're incompatible
UPDATE documents
SET confidence_numeric = CASE
    WHEN confidence ~ '^[0-9.]+$' THEN confidence::FLOAT
    ELSE NULL
END
WHERE confidence IS NOT NULL;

-- Step 3: Drop old column
ALTER TABLE documents
DROP COLUMN confidence;

-- Step 4: Rename new column to original name
ALTER TABLE documents
RENAME COLUMN confidence_numeric TO confidence;

-- Step 5: Add comment for documentation
COMMENT ON COLUMN documents.confidence IS 'Classification confidence score (0.0-1.0). NULL if not available.';

-- Verify the change
SELECT
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'documents'
AND column_name = 'confidence';

COMMIT;

-- ==============================================================================
-- ROLLBACK INSTRUCTIONS (if needed):
-- ==============================================================================
-- If you need to rollback, run:
--
-- BEGIN;
-- ALTER TABLE documents DROP COLUMN IF EXISTS confidence;
-- ALTER TABLE documents ADD COLUMN confidence TEXT;
-- COMMIT;
-- ==============================================================================
