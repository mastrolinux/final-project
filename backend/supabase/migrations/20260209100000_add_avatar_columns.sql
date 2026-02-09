-- Add avatar columns to base_profiles and context_profiles.
-- These columns were present in the SQLAlchemy models but missing from the database schema.

-- Base profile avatar fields
ALTER TABLE base_profiles
  ADD COLUMN IF NOT EXISTS avatar_url TEXT,
  ADD COLUMN IF NOT EXISTS avatar_thumbnail_url TEXT,
  ADD COLUMN IF NOT EXISTS avatar_storage_path TEXT;

-- Context profile avatar override fields
ALTER TABLE context_profiles
  ADD COLUMN IF NOT EXISTS avatar_override_url TEXT,
  ADD COLUMN IF NOT EXISTS avatar_override_thumbnail_url TEXT,
  ADD COLUMN IF NOT EXISTS avatar_override_storage_path TEXT;
