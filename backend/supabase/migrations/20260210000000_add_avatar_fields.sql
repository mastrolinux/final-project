-- Avatar Support Migration
-- Adds avatar columns to base_profiles and context_profiles,
-- and inserts the profile:read:photo OAuth scope.
-- Part of MAS-78: Profile Picture / Avatar Upload

-- Base profile avatar columns
ALTER TABLE base_profiles
    ADD COLUMN IF NOT EXISTS avatar_url TEXT,
    ADD COLUMN IF NOT EXISTS avatar_thumbnail_url TEXT,
    ADD COLUMN IF NOT EXISTS avatar_storage_path TEXT;

COMMENT ON COLUMN base_profiles.avatar_url IS 'Public URL of the user avatar (400x400 WebP)';
COMMENT ON COLUMN base_profiles.avatar_thumbnail_url IS 'Public URL of the avatar thumbnail (80x80 WebP)';
COMMENT ON COLUMN base_profiles.avatar_storage_path IS 'Internal storage path for deletion operations';

-- Context profile avatar override columns (null = inherit from base)
ALTER TABLE context_profiles
    ADD COLUMN IF NOT EXISTS avatar_override_url TEXT,
    ADD COLUMN IF NOT EXISTS avatar_override_thumbnail_url TEXT,
    ADD COLUMN IF NOT EXISTS avatar_override_storage_path TEXT;

COMMENT ON COLUMN context_profiles.avatar_override_url IS 'Context-specific avatar override URL';
COMMENT ON COLUMN context_profiles.avatar_override_thumbnail_url IS 'Context-specific avatar thumbnail override URL';
COMMENT ON COLUMN context_profiles.avatar_override_storage_path IS 'Context-specific avatar storage path for deletion';

-- OAuth scope for avatar access
INSERT INTO oauth_scopes (scope_name, description, access_level, allowed_fields, is_sensitive)
VALUES (
    'profile:read:photo',
    'Access to profile avatar and thumbnail URLs',
    'read',
    ARRAY['avatar_url', 'avatar_thumbnail_url'],
    false
)
ON CONFLICT (scope_name) DO NOTHING;
