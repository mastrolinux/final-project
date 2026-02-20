-- Migration: Add has_custom_password flag to auth_users
-- Tracks whether an OAuth user has explicitly set a password
-- (as opposed to the random hash generated at OAuth registration for schema compatibility)

ALTER TABLE auth_users
ADD COLUMN IF NOT EXISTS has_custom_password BOOLEAN NOT NULL DEFAULT false;

-- Backfill: email/password users (provider IS NULL) already have user-chosen passwords
UPDATE auth_users SET has_custom_password = true WHERE provider IS NULL;

COMMENT ON COLUMN auth_users.has_custom_password IS
    'True when the user has explicitly chosen a password. '
    'False for OAuth-only users whose password_hash is a random placeholder.';
