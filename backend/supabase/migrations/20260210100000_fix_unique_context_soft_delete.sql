-- Replace the plain unique constraint on context_profiles with a partial
-- unique index that excludes soft-deleted rows.  This allows re-creation
-- of a context with the same (user_id, context_type, context_name) after
-- the original has been soft-deleted.

ALTER TABLE context_profiles
  DROP CONSTRAINT IF EXISTS unique_user_context;

CREATE UNIQUE INDEX unique_user_context
  ON context_profiles (user_id, context_type, context_name)
  WHERE deleted_at IS NULL;
